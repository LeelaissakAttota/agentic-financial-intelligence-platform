"""
Security & Authentication Module

Implements:
- JWT Authentication
- API Key Authentication
- Role-Based Access Control (RBAC)
- Security headers
- Rate limiting
- Input validation
- SQL injection protection
- Prompt injection detection
"""
import hashlib
import hmac
import json
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Union

import jwt
from fastapi import Depends, Header, HTTPException, Request, Response, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, Field, validator

from config.settings import get_settings

# ==================== Models ====================
class UserRole(str, Enum):
    """User roles with hierarchical permissions."""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Granular permissions."""
    # Analysis permissions
    ANALYSIS_CREATE = "analysis:create"
    ANALYSIS_READ = "analysis:read"
    ANALYSIS_UPDATE = "analysis:update"
    ANALYSIS_DELETE = "analysis:delete"

    # Report permissions
    REPORT_CREATE = "report:create"
    REPORT_READ = "report:read"
    REPORT_UPDATE = "report:update"
    REPORT_DELETE = "report:delete"

    # Portfolio permissions
    PORTFOLIO_CREATE = "portfolio:create"
    PORTFOLIO_READ = "portfolio:read"
    PORTFOLIO_UPDATE = "portfolio:update"
    PORTFOLIO_DELETE = "portfolio:delete"

    # Knowledge Graph permissions
    KG_CREATE = "kg:create"
    KG_READ = "kg:read"
    KG_UPDATE = "kg:update"
    KG_DELETE = "kg:delete"

    # Alert permissions
    ALERT_CREATE = "alert:create"
    ALERT_READ = "alert:read"
    ALERT_UPDATE = "alert:update"
    ALERT_DELETE = "alert:delete"

    # Admin permissions
    USER_MANAGE = "user:manage"
    SYSTEM_CONFIG = "system:config"
    METRICS_VIEW = "metrics:view"


# Role-to-permission mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.ADMIN: set(Permission),  # All permissions
    UserRole.ANALYST: {
        Permission.ANALYSIS_CREATE,
        Permission.ANALYSIS_READ,
        Permission.ANALYSIS_UPDATE,
        Permission.REPORT_CREATE,
        Permission.REPORT_READ,
        Permission.REPORT_UPDATE,
        Permission.PORTFOLIO_CREATE,
        Permission.PORTFOLIO_READ,
        Permission.PORTFOLIO_UPDATE,
        Permission.KG_CREATE,
        Permission.KG_READ,
        Permission.KG_UPDATE,
        Permission.ALERT_CREATE,
        Permission.ALERT_READ,
        Permission.ALERT_UPDATE,
        Permission.METRICS_VIEW,
    },
    UserRole.VIEWER: {
        Permission.ANALYSIS_READ,
        Permission.REPORT_READ,
        Permission.PORTFOLIO_READ,
        Permission.KG_READ,
        Permission.ALERT_READ,
    },
}


@dataclass
class User:
    """User model."""
    id: str
    username: str
    email: str
    role: UserRole
    permissions: Set[Permission] = field(default_factory=set)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    api_keys: List[str] = field(default_factory=list)


@dataclass
class APIKey:
    """API Key model."""
    id: str
    key_hash: str  # bcrypt hash
    name: str
    user_id: str
    permissions: Set[Permission] = field(default_factory=set)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # user id
    username: str
    role: UserRole
    permissions: List[str]
    exp: int
    iat: int
    jti: str  # unique token ID
    type: str = "access"  # access or refresh


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class APIKeyCreate(BaseModel):
    """API Key creation request."""
    name: str
    permissions: Optional[List[Permission]] = None
    expires_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    """API Key response (includes raw key only on creation)."""
    id: str
    name: str
    key: Optional[str] = None  # Only on creation
    permissions: List[Permission]
    expires_at: Optional[datetime]
    created_at: datetime


# ==================== Password Hashing ====================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ==================== JWT Handler ====================
class JWTHandler:
    """JWT token management."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = access_token_expire_minutes
        self.refresh_token_expire = refresh_token_expire_days
        self._revoked_tokens: Set[str] = set()

    def create_access_token(
        self,
        user: User,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create access token."""
        now = datetime.utcnow()
        exp = now + timedelta(minutes=self.access_token_expire)

        payload = TokenPayload(
            sub=user.id,
            username=user.username,
            role=user.role,
            permissions=[p.value for p in user.permissions],
            exp=int(exp.timestamp()),
            iat=int(now.timestamp()),
            jti=secrets.token_urlsafe(16),
            type="access"
        )

        if additional_claims:
            payload_dict = payload.dict()
            payload_dict.update(additional_claims)
            payload = TokenPayload(**payload_dict)

        return jwt.encode(payload.dict(), self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user: User) -> str:
        """Create refresh token."""
        now = datetime.utcnow()
        exp = now + timedelta(days=self.refresh_token_expire)

        payload = TokenPayload(
            sub=user.id,
            username=user.username,
            role=user.role,
            permissions=[p.value for p in user.permissions],
            exp=int(exp.timestamp()),
            iat=int(now.timestamp()),
            jti=secrets.token_urlsafe(16),
            type="refresh"
        )

        return jwt.encode(payload.dict(), self.secret_key, algorithm=self.algorithm)

    def create_token_pair(self, user: User) -> TokenResponse:
        """Create both access and refresh tokens."""
        access = self.create_access_token(user)
        refresh = self.create_refresh_token(user)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=self.access_token_expire * 60
        )

    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    def verify_token(self, token: str) -> TokenPayload:
        """Verify token and check revocation."""
        payload = self.decode_token(token)

        if payload.jti in self._revoked_tokens:
            raise HTTPException(status_code=401, detail="Token revoked")

        return payload

    def revoke_token(self, token: str) -> bool:
        """Revoke a token by its JTI."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            self._revoked_tokens.add(payload["jti"])
            return True
        except jwt.InvalidTokenError:
            return False

    def revoke_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for a user (placeholder - would need token store)."""
        # In production, maintain a user->tokens mapping
        return 0


# ==================== API Key Handler ====================
class APIKeyHandler:
    """API Key management."""

    def __init__(self):
        self._keys: Dict[str, APIKey] = {}  # key_id -> APIKey
        self._key_index: Dict[str, str] = {}  # key_hash -> key_id

    def generate_key(self) -> str:
        """Generate a new API key."""
        return f"frap_{secrets.token_urlsafe(32)}"

    def hash_key(self, key: str) -> str:
        """Hash an API key for storage."""
        return hash_password(key)

    def verify_key(self, key: str, key_hash: str) -> bool:
        """Verify an API key against its hash."""
        return verify_password(key, key_hash)

    def create_key(
        self,
        user_id: str,
        name: str,
        permissions: Optional[Set[Permission]] = None,
        expires_days: Optional[int] = None
    ) -> APIKeyResponse:
        """Create a new API key."""
        raw_key = self.generate_key()
        key_hash = self.hash_key(raw_key)
        key_id = secrets.token_urlsafe(16)

        api_key = APIKey(
            id=key_id,
            key_hash=key_hash,
            name=name,
            user_id=user_id,
            permissions=permissions or set(),
            expires_at=datetime.utcnow() + timedelta(days=expires_days) if expires_days else None
        )

        self._keys[key_id] = api_key
        self._key_index[key_hash] = key_id

        return APIKeyResponse(
            id=key_id,
            name=name,
            key=raw_key,  # Only returned on creation
            permissions=list(api_key.permissions),
            expires_at=api_key.expires_at,
            created_at=api_key.created_at
        )

    def validate_key(self, key: str) -> Optional[APIKey]:
        """Validate an API key and return key info."""
        key_hash = self.hash_key(key)

        if key_hash not in self._key_index:
            return None

        key_id = self._key_index[key_hash]
        api_key = self._keys.get(key_id)

        if not api_key or not api_key.is_active:
            return None

        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            return None

        # Update usage stats
        api_key.last_used = datetime.utcnow()
        api_key.usage_count += 1

        return api_key

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if key_id in self._keys:
            self._keys[key_id].is_active = False
            return True
        return False

    def get_user_keys(self, user_id: str) -> List[APIKey]:
        """Get all API keys for a user."""
        return [k for k in self._keys.values() if k.user_id == user_id]

    def delete_key(self, key_id: str) -> bool:
        """Delete an API key completely."""
        if key_id in self._keys:
            key = self._keys[key_id]
            self._key_index.pop(key.key_hash, None)
            del self._keys[key_id]
            return True
        return False


# ==================== RBAC ====================
class RBAC:
    """Role-Based Access Control."""

    def __init__(self):
        self.role_permissions = ROLE_PERMISSIONS.copy()

    def get_permissions(self, role: UserRole) -> Set[Permission]:
        """Get permissions for a role."""
        return self.role_permissions.get(role, set())

    def has_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        if not user.is_active:
            return False
        return permission in user.permissions

    def has_any_permission(self, user: User, permissions: List[Permission]) -> bool:
        """Check if user has any of the given permissions."""
        return any(self.has_permission(user, p) for p in permissions)

    def has_all_permissions(self, user: User, permissions: List[Permission]) -> bool:
        """Check if user has all given permissions."""
        return all(self.has_permission(user, p) for p in permissions)

    def assign_permission(self, role: UserRole, permission: Permission) -> None:
        """Assign a permission to a role."""
        if role not in self.role_permissions:
            self.role_permissions[role] = set()
        self.role_permissions[role].add(permission)

    def revoke_permission(self, role: UserRole, permission: Permission) -> None:
        """Revoke a permission from a role."""
        if role in self.role_permissions:
            self.role_permissions[role].discard(permission)

    def can_access(self, user: User, resource: str, action: str) -> bool:
        """Check if user can access resource with action."""
        permission = Permission(f"{resource}:{action}")
        return self.has_permission(user, permission)


# ==================== Security Headers ====================
class SecurityHeaders:
    """Security headers for HTTP responses."""

    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
        }

    @staticmethod
    def get_csp_header() -> str:
        """Get Content Security Policy header."""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self';"
        )


# ==================== Input Validation ====================
class InputValidator:
    """Input validation and sanitization."""

    # SQL injection patterns
    SQL_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bupdate\b.*\bset\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(\bcreate\b.*\btable\b)",
        r"(\balter\b.*\btable\b)",
        r"(\bexec\b|\bexecute\b)",
        r"(\bdeclare\b)",
        r"(;\s*--)",
        r"(\bor\s+1\s*=\s*1)",
        r"(\band\s+1\s*=\s*1)",
    ]

    # Prompt injection patterns
    PROMPT_INJECTION_PATTERNS = [
        r"ignore\s+(previous|above|all)\s+(instructions|prompts|rules)",
        r"disregard\s+(previous|above|all)\s+(instructions|prompts|rules)",
        r"forget\s+(previous|above|all)\s+(instructions|prompts|rules)",
        r"you\s+are\s+now\s+(a|an)\s+",
        r"act\s+as\s+(a|an)\s+",
        r"pretend\s+to\s+be\s+",
        r"simulate\s+(a|an)\s+",
        r"roleplay\s+(as|a)\s+",
        r"jailbreak",
        r"bypass\s+(security|safety|guidelines)",
        r"override\s+(security|safety|guidelines)",
        r"developer\s+mode",
        r"admin\s+mode",
        r"root\s+access",
        r"system\s+prompt",
        r"<\|.*\|>",
        r"\[INST\].*\[/INST\]",
        r"<<SYS>>.*<</SYS>>",
    ]

    @classmethod
    def detect_sql_injection(cls, text: str) -> bool:
        """Detect potential SQL injection."""
        text_lower = text.lower()
        return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in cls.SQL_PATTERNS)

    @classmethod
    def detect_prompt_injection(cls, text: str) -> bool:
        """Detect potential prompt injection."""
        text_lower = text.lower()
        return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in cls.PROMPT_INJECTION_PATTERNS)

    @classmethod
    def sanitize_input(cls, text: str, max_length: int = 10000) -> str:
        """Sanitize input text."""
        # Truncate
        if len(text) > max_length:
            text = text[:max_length]

        # Remove null bytes
        text = text.replace('\x00', '')

        # Normalize whitespace
        text = ' '.join(text.split())

        return text

    @classmethod
    def validate_company_name(cls, name: str) -> str:
        """Validate company name."""
        sanitized = cls.sanitize_input(name, max_length=200)

        if cls.detect_sql_injection(sanitized):
            raise ValueError("Invalid characters in company name")

        if cls.detect_prompt_injection(sanitized):
            raise ValueError("Potential prompt injection detected")

        return sanitized

    @classmethod
    def validate_ticker(cls, ticker: str) -> str:
        """Validate stock ticker."""
        sanitized = cls.sanitize_input(ticker.upper(), max_length=10)

        # Basic ticker validation
        if not re.match(r'^[A-Z0-9\.\-]{1,10}$', sanitized):
            raise ValueError("Invalid ticker format")

        return sanitized


# ==================== Rate Limiting ====================
class RateLimiter:
    """In-memory rate limiter with sliding window."""

    def __init__(self):
        self._requests: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limit.

        Returns:
            (allowed, info_dict)
        """
        async with self._lock:
            now = time.time()
            window_start = now - window_seconds

            # Clean old entries
            if key in self._requests:
                self._requests[key] = [
                    ts for ts in self._requests[key]
                    if ts > window_start
                ]
            else:
                self._requests[key] = []

            current_count = len(self._requests[key])

            if current_count >= max_requests:
                # Rate limited
                oldest = min(self._requests[key]) if self._requests[key] else now
                retry_after = int(oldest + window_seconds - now) + 1
                return False, {
                    "allowed": False,
                    "current": current_count,
                    "limit": max_requests,
                    "window": window_seconds,
                    "retry_after": retry_after
                }

            # Allow request
            self._requests[key].append(now)
            return True, {
                "allowed": True,
                "current": current_count + 1,
                "limit": max_requests,
                "window": window_seconds,
                "remaining": max_requests - current_count - 1
            }


# ==================== Circuit Breaker ====================
class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        # Check if we should transition from OPEN to HALF_OPEN
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and \
               time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker."""
        if self.state == CircuitState.OPEN:
            raise HTTPException(
                status_code=503,
                detail="Circuit breaker is OPEN - service unavailable"
            )

        if self.state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                raise HTTPException(
                    status_code=503,
                    detail="Circuit breaker HALF_OPEN - max calls reached"
                )
            self._half_open_calls += 1

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Success - reset on CLOSED, close on HALF_OPEN
            async with self._lock:
                if self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                elif self._state == CircuitState.CLOSED:
                    self._failure_count = 0

            return result

        except Exception as e:
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.time()

                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN

            raise


# ==================== Dependency Injection ====================
# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Global instances
_settings = get_settings()
_jwt_handler = JWTHandler(
    secret_key=_settings.openrouter_api_key or "dev-secret-change-in-production",
    access_token_expire_minutes=30,
    refresh_token_expire_days=7
)
_api_key_handler = APIKeyHandler()
_rbac = RBAC()
_rate_limiter = RateLimiter()


# Create demo users
def create_demo_users() -> Dict[str, User]:
    """Create demo users for testing."""
    users = {}

    # Admin user
    admin = User(
        id="user_admin",
        username="admin",
        email="admin@example.com",
        role=UserRole.ADMIN,
        permissions=ROLE_PERMISSIONS[UserRole.ADMIN]
    )
    users[admin.id] = users[admin.username] = admin

    # Analyst user
    analyst = User(
        id="user_analyst",
        username="analyst",
        email="analyst@example.com",
        role=UserRole.ANALYST,
        permissions=ROLE_PERMISSIONS[UserRole.ANALYST]
    )
    users[analyst.id] = users[analyst.username] = analyst

    # Viewer user
    viewer = User(
        id="user_viewer",
        username="viewer",
        email="viewer@example.com",
        role=UserRole.VIEWER,
        permissions=ROLE_PERMISSIONS[UserRole.VIEWER]
    )
    users[viewer.id] = users[viewer.username] = viewer

    return users


_demo_users = create_demo_users()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header)
) -> User:
    """Get current authenticated user from JWT or API key."""
    # Try JWT first
    if credentials:
        try:
            payload = _jwt_handler.verify_token(credentials.credentials)
            user = _demo_users.get(payload.sub)
            if user and user.is_active:
                return user
        except HTTPException:
            pass

    # Try API key
    if api_key:
        api_key_obj = _api_key_handler.validate_key(api_key)
        if api_key_obj:
            user = _demo_users.get(api_key_obj.user_id)
            if user and user.is_active:
                return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header)
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    try:
        return get_current_user(credentials, api_key)
    except HTTPException:
        return None


def require_permission(permission: Permission):
    """Dependency to require a specific permission."""
    def permission_checker(user: User = Depends(get_current_user)) -> User:
        if not _rbac.has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}"
            )
        return user
    return permission_checker


def require_any_permission(*permissions: Permission):
    """Dependency to require any of the given permissions."""
    def permission_checker(user: User = Depends(get_current_user)) -> User:
        if not _rbac.has_any_permission(user, list(permissions)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires one of {[p.value for p in permissions]}"
            )
        return user
    return permission_checker


def require_all_permissions(*permissions: Permission):
    """Dependency to require all given permissions."""
    def permission_checker(user: User = Depends(get_current_user)) -> User:
        if not _rbac.has_all_permissions(user, list(permissions)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires all of {[p.value for p in permissions]}"
            )
        return user
    return permission_checker


def require_role(*roles: UserRole):
    """Dependency to require a specific role."""
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {[r.value for r in roles]}"
            )
        return user
    return role_checker


# ==================== Middleware ====================
async def security_middleware(request: Request, call_next: Callable) -> Response:
    """Security middleware for headers and validation."""
    # Add security headers
    response = await call_next(request)

    for header, value in SecurityHeaders.get_headers().items():
        response.headers[header] = value

    response.headers["Content-Security-Policy"] = SecurityHeaders.get_csp_header()

    return response


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """Rate limiting middleware."""
    settings = get_settings()

    if not settings.rate_limit_enabled:
        return await call_next(request)

    # Get client identifier
    client_ip = request.client.host if request.client else "unknown"
    api_key = request.headers.get("X-API-Key")
    identifier = api_key or client_ip

    # Check rate limit
    allowed, info = await _rate_limiter.check_rate_limit(
        key=identifier,
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window
    )

    # Add rate limit headers
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + info["window"])

    if not allowed:
        response.status_code = 429
        response.headers["Retry-After"] = str(info["retry_after"])
        return Response(
            content=json.dumps({"error": "Rate limit exceeded"}),
            status_code=429,
            headers=dict(response.headers),
            media_type="application/json"
        )

    return response


# ==================== Utility Functions ====================
def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison."""
    return hmac.compare_digest(a.encode(), b.encode())


def mask_secret(secret: str, visible_chars: int = 4) -> str:
    """Mask a secret for logging."""
    if len(secret) <= visible_chars * 2:
        return "*" * len(secret)
    return secret[:visible_chars] + "*" * (len(secret) - visible_chars * 2) + secret[-visible_chars:]


# ==================== Export ====================
__all__ = [
    "UserRole",
    "Permission",
    "User",
    "APIKey",
    "TokenPayload",
    "TokenResponse",
    "APIKeyCreate",
    "APIKeyResponse",
    "JWTHandler",
    "APIKeyHandler",
    "RBAC",
    "SecurityHeaders",
    "InputValidator",
    "RateLimiter",
    "CircuitBreaker",
    "CircuitState",
    "get_current_user",
    "get_optional_user",
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "require_role",
    "security_middleware",
    "rate_limit_middleware",
    "hash_password",
    "verify_password",
    "generate_secure_token",
    "constant_time_compare",
    "mask_secret",
]