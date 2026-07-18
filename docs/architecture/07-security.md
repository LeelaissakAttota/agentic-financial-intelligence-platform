# Security Architecture
## Agentic Financial Intelligence Platform

---

## Overview

Security is implemented as a **defense-in-depth** strategy across multiple layers: network, application, data, and operational security. All security controls are implemented in the `security/` and `middleware/` packages with integration points throughout the platform.

---

## Security Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY LAYER ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  NETWORK LAYER                                                              │
│  ├── TLS 1.2+ (all external connections)                                   │
│  ├── Private VPC (internal services)                                       │
│  ├── Firewall rules (deny by default)                                      │
│  └── DDoS protection (Cloudflare/AWS Shield)                               │
│                                                                             │
│  APPLICATION LAYER                                                          │
│  ├── Authentication (JWT RS256 + API Keys)                                 │
│  ├── Authorization (RBAC: Admin/Analyst/Viewer)                            │
│  ├── Rate Limiting (Token bucket + Sliding window)                         │
│  ├── Circuit Breakers (3-state with auto-recovery)                         │
│  ├── Input Validation (Pydantic + SQL injection detection)                 │
│  ├── Prompt Injection Detection (Heuristic + LLM-based)                    │
│  └── Security Headers (CSP, HSTS, X-Frame, etc.)                           │
│                                                                             │
│  DATA LAYER                                                                 │
│  ├── Encryption at rest (AES-256, TDE)                                     │
│  ├── Encryption in transit (TLS 1.3)                                       │
│  ├── Secrets management (Environment variables, no hardcoded)              │
│  ├── API Key hashing (bcrypt, 12 rounds)                                   │
│  ├── PII minimization (No PII stored)                                      │
│  └── Audit logging (Immutable, tamper-evident)                             │
│                                                                             │
│  OPERATIONAL LAYER                                                          │
│  ├── Structured logging (JSON, correlation IDs)                            │
│  ├── Security event detection (SQLi, prompt injection, brute force)        │
│  ├── Vulnerability scanning (Dependency scan, SAST)                        │
│  ├── Incident response playbooks                                           │
│  └── Compliance (SOC 2 Type II ready, GDPR)                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Authentication

### JWT (RS256)
```python
# security/auth.py
class JWTManager:
    """RS256 JWT with JWKS support."""
    
    def __init__(self):
        self.private_key = load_private_key()
        self.public_key = load_public_key()
        self.algorithm = "RS256"
        self.access_token_ttl = timedelta(minutes=15)
        self.refresh_token_ttl = timedelta(days=7)
    
    def create_access_token(self, subject: str, roles: List[str]) -> str:
        payload = {
            "sub": subject,
            "roles": roles,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + self.access_token_ttl,
            "type": "access"
        }
        return jwt.encode(payload, self.private_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> TokenPayload:
        payload = jwt.decode(
            token, 
            self.public_key, 
            algorithms=[self.algorithm],
            audience="financial-research-api"
        )
        return TokenPayload(**payload)
```

### API Keys (bcrypt)
```python
class APIKeyManager:
    """API Key management with bcrypt hashing."""
    
    def generate_key(self, name: str, scopes: List[str], owner: str) -> Tuple[str, str]:
        """Generate new API key. Returns (key_id, plain_key) - plain_key shown once."""
        plain_key = f"fra_{secrets.token_urlsafe(32)}"
        key_hash = bcrypt.hashpw(plain_key.encode(), bcrypt.gensalt(rounds=12))
        
        key_record = APIKey(
            key_id=f"key_{secrets.token_hex(8)}",
            name=name,
            key_hash=key_hash,
            scopes=scopes,
            owner=owner,
            created_at=datetime.utcnow()
        )
        db.save(key_record)
        return key_record.key_id, plain_key
    
    def verify_key(self, plain_key: str) -> Optional[APIKey]:
        """Verify API key against stored hash."""
        candidates = db.query(APIKey).filter(APIKey.is_active == True).all()
        for candidate in candidates:
            if bcrypt.checkpw(plain_key.encode(), candidate.key_hash):
                return candidate
        return None
```

---

## Authorization (RBAC)

### Roles & Permissions
```python
class Role(Enum):
    ADMIN = "admin"           # Full system access
    ANALYST = "analyst"       # Research, reports, watchlists
    VIEWER = "viewer"         # Read-only access
    API_ONLY = "api_only"     # Programmatic access only

PERMISSIONS = {
    "admin": [
        "research:create", "research:read", "research:delete",
        "watchlist:create", "watchlist:read", "watchlist:update", "watchlist:delete",
        "report:generate", "report:read", "report:delete",
        "approval:create", "approval:read", "approval:action",
        "admin:users", "admin:config", "admin:metrics",
        "copilot:chat", "copilot:plan", "copilot:execute"
    ],
    "analyst": [
        "research:create", "research:read",
        "watchlist:create", "watchlist:read", "watchlist:update",
        "report:generate", "report:read",
        "approval:read", "approval:action",
        "copilot:chat", "copilot:plan", "copilot:execute"
    ],
    "viewer": [
        "research:read",
        "watchlist:read",
        "report:read",
        "copilot:chat"
    ],
    "api_only": [
        "research:create", "research:read",
        "watchlist:create", "watchlist:read",
        "report:generate", "report:read",
        "copilot:chat", "copilot:plan", "copilot:execute"
    ]
}
```

### Dependency Injection (FastAPI)
```python
# api/dependencies.py
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Extract and validate JWT from Authorization header."""
    token = credentials.credentials
    payload = jwt_manager.verify_token(token)
    user = await db.get_user(payload.sub)
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")
    return user

async def require_permission(permission: str):
    """Dependency factory for permission checks."""
    async def checker(user: User = Depends(get_current_user)):
        if permission not in PERMISSIONS.get(user.role, []):
            raise HTTPException(403, f"Permission '{permission}' required")
        return user
    return checker

# Usage in routes
@router.post("/research/start", dependencies=[Depends(require_permission("research:create"))])
async def start_research(...):
    ...
```

---

## Rate Limiting

### Dual Strategy
```python
# middleware/rate_limit.py
class RateLimiter:
    """Hybrid rate limiter: Token bucket (local) + Sliding window (Redis)."""
    
    def __init__(self):
        self.local_bucket = TokenBucket(capacity=100, refill_rate=10)  # Per-process
        self.redis_client = redis.Redis(decode_responses=True)
    
    async def check_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        strategy: RateLimitStrategy = RateLimitStrategy.ADAPTIVE
    ) -> RateLimitResult:
        """Check rate limit with fallback strategies."""
        
        if strategy == RateLimitStrategy.ADAPTIVE:
            # Adaptive: Reduce limits under high load
            cpu_percent = psutil.cpu_percent()
            if cpu_percent > 80:
                limit = int(limit * 0.5)
            elif cpu_percent > 60:
                limit = int(limit * 0.75)
        
        # Try Redis first (distributed)
        try:
            result = await self._redis_sliding_window(key, limit, window_seconds)
            if result.limited:
                return result
        except RedisError:
            # Fallback to local token bucket
            pass
        
        return await self._local_token_bucket(key, limit, window_seconds)
```

### Standard Headers
```python
# Rate limit headers on all responses
headers = {
    "X-RateLimit-Limit": str(limit),
    "X-RateLimit-Remaining": str(remaining),
    "X-RateLimit-Reset": str(reset_timestamp),
    "Retry-After": str(retry_after)  # On 429
}
```

---

## Circuit Breakers

### 3-State Pattern
```python
# middleware/circuit_breaker.py
class CircuitBreaker:
    """3-state circuit breaker: Closed → Open → Half-Open → Closed"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.last_failure_time = None
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs):
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise CircuitOpenError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                self._on_success()
            return result
        except self.expected_exception as e:
            async with self._lock:
                self._on_failure()
            raise
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

### Integration Points
| Service | Circuit Breaker Config |
|---------|------------------------|
| OpenRouter LLM | 5 failures, 60s timeout, auto-recovery |
| PostgreSQL | 3 failures, 30s timeout |
| ChromaDB | 3 failures, 30s timeout |
| SEC EDGAR | 10 failures, 120s timeout |
| News APIs | 5 failures per provider, 60s timeout |
| Market Data | 5 failures, 60s timeout |

---

## Input Validation & Injection Prevention

### Pydantic Models (Primary Defense)
```python
# All API inputs validated via Pydantic
class ResearchRequest(BaseModel):
    company: str = Field(..., min_length=1, max_length=100, pattern=r'^[A-Za-z0-9\s\.\-]+$')
    query: str = Field(..., min_length=10, max_length=5000)
    context: Dict[str, Any] = Field(default_factory=dict)
    auto_approve: bool = False
    
    @field_validator('company')
    @classmethod
    def sanitize_company(cls, v: str) -> str:
        # Remove potential injection chars
        return re.sub(r'[;\'\"\\]', '', v).strip()
```

### SQL Injection Detection
```python
# middleware/security_middleware.py
SQL_INJECTION_PATTERNS = [
    r"(\bunion\b.*\bselect\b)",
    r"(\bselect\b.*\bfrom\b)",
    r"(\binsert\b.*\binto\b)",
    r"(\bupdate\b.*\bset\b)",
    r"(\bdelete\b.*\bfrom\b)",
    r"(\bdrop\b.*\btable\b)",
    r"(\bor\b\s+\d+\s*=\s*\d+)",
    r"(--|;|/\*|\*/)",
    r"(\bxp_cmdshell\b)",
]

def detect_sql_injection(input_str: str) -> Tuple[bool, List[str]]:
    """Detect potential SQL injection attempts."""
    detected = []
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, input_str, re.IGNORECASE):
            detected.append(pattern)
    return len(detected) > 0, detected
```

### Prompt Injection Detection
```python
# middleware/security_middleware.py
PROMPT_INJECTION_PATTERNS = [
    r"(ignore\s+(previous|above|all)\s+(instructions|prompts|rules))",
    r"(you\s+are\s+now\s+(a|an)\s+)",
    r"(system\s+prompt\s*:)",
    r"(pretend\s+to\s+be\s+)",
    r"(act\s+as\s+(a|an)\s+)",
    r"(forget\s+(everything|all\s+previous))",
    r"(new\s+instructions\s*:)",
    r"(override\s+.*\s+instructions)",
]

def detect_prompt_injection(input_str: str) -> Tuple[bool, List[str]]:
    """Detect potential prompt injection attempts."""
    detected = []
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, input_str, re.IGNORECASE):
            detected.append(pattern)
    return len(detected) > 0, detected

# Middleware integration
async def security_middleware(request: Request, call_next):
    body = await request.body()
    body_str = body.decode() if body else ""
    
    # Check for SQL injection
    has_sql, sql_patterns = detect_sql_injection(body_str)
    if has_sql:
        logger.warning("SQL injection detected", patterns=sql_patterns, client=request.client.host)
        security_events.log("sql_injection_attempt", {"patterns": sql_patterns})
    
    # Check for prompt injection
    has_prompt, prompt_patterns = detect_prompt_injection(body_str)
    if has_prompt:
        logger.warning("Prompt injection detected", patterns=prompt_patterns, client=request.client.host)
        security_events.log("prompt_injection_attempt", {"patterns": prompt_patterns})
    
    return await call_next(request)
```

---

## Security Headers

```python
# middleware/security_middleware.py
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.openai.com https://api.anthropic.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin"
}

def add_security_headers(response: Response):
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response
```

---

## Secrets Management

### Environment Variables Only
```python
# config/settings.py
class Settings(BaseSettings):
    """All secrets via environment variables - NO HARDCODED SECRETS."""
    
    # Database
    postgres_host: str
    postgres_port: int = 5432
    postgres_user: str
    postgres_password: str  # From env
    postgres_db: str
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    
    # LLM Providers (OpenRouter unified)
    openrouter_api_key: str  # From env
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # Security
    jwt_private_key_path: str  # Path to PEM file
    jwt_public_key_path: str   # Path to PEM file
    api_key_bcrypt_rounds: int = 12
    
    # Optional notification channels
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None  # From env
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Secrets never logged
        secret_fields = {
            "postgres_password",
            "redis_password", 
            "openrouter_api_key",
            "smtp_password",
            "slack_webhook_url",
            "discord_webhook_url",
            "webhook_url"
        }
```

### .env.example
```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=financial_research
POSTGRES_PASSWORD=CHANGE_ME_IN_PRODUCTION
POSTGRES_DB=financial_research

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# LLM
OPENROUTER_API_KEY=sk-or-v1-CHANGE_ME

# JWT Keys (generate with: openssl genrsa -out private.pem 2048)
JWT_PRIVATE_KEY_PATH=./keys/private.pem
JWT_PUBLIC_KEY_PATH=./keys/public.pem

# Optional: Notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@yourdomain.com
SMTP_PASSWORD=CHANGE_ME
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
WEBHOOK_URL=https://yourdomain.com/webhook
```

---

## Audit Logging

### Security Event Types
```python
# security/audit.py
class SecurityEventType(Enum):
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    TOKEN_REFRESH = "token_refresh"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    
    # Authorization
    PERMISSION_DENIED = "permission_denied"
    ROLE_CHANGED = "role_changed"
    
    # Injection Attempts
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    PROMPT_INJECTION_ATTEMPT = "prompt_injection_attempt"
    PATH_TRAVERSAL_ATTEMPT = "path_traversal_attempt"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # Circuit Breakers
    CIRCUIT_BREAKER_OPENED = "circuit_breaker_opened"
    CIRCUIT_BREAKER_CLOSED = "circuit_breaker_closed"
    
    # Data Access
    SENSITIVE_DATA_ACCESSED = "sensitive_data_accessed"
    BULK_EXPORT = "bulk_export"
    
    # Configuration
    CONFIG_CHANGED = "config_changed"
    SECRET_ROTATED = "secret_rotated"
```

### Audit Log Entry
```python
@dataclass
class AuditLogEntry:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_type: SecurityEventType
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    outcome: str  # success, failure, blocked
    details: Dict[str, Any] = field(default_factory=dict)
    risk_score: int = 0  # 0-100
```

---

## Vulnerability Management

### Automated Scanning
```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run pip-audit
        run: pip-audit -r requirements.txt --format=json --output=audit.json
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: dependency-audit
          path: audit.json
  
  sast-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Bandit
        run: bandit -r src/ -f json -o bandit.json
      - name: Run Semgrep
        run: semgrep --config=auto --json=semgrep.json src/
  
  container-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t financial-research:scan .
      - name: Scan with Trivy
        run: trivy image --severity HIGH,CRITICAL financial-research:scan
```

---

## Compliance Readiness

| Standard | Status | Evidence |
|----------|--------|----------|
| **SOC 2 Type II** | Ready | Audit logs, access controls, encryption, monitoring |
| **GDPR** | Ready | Data minimization, right to deletion, DPA ready |
| **ISO 27001** | Partial | Risk assessment, controls documented |
| **PCI DSS** | N/A | No cardholder data processed |

---

## Incident Response

### Playbook: Suspicious Activity
```markdown
## IR-001: Injection Attack Detected

### Detection
- Security middleware logs SQL/prompt injection attempt
- Alert fired to security channel (Slack/PagerDuty)

### Response
1. **Immediate** (0-5 min):
   - Block offending IP at WAF
   - Review audit log for successful exploitation
   - Notify security team

2. **Short-term** (5-60 min):
   - Analyze attack pattern
   - Update detection rules if novel
   - Check for data exfiltration

3. **Long-term** (1-24 hours):
   - Root cause analysis
   - Update WAF rules
   - Document lessons learned
   - Retrain detection if ML-based
```

---

*Document Version: 1.0*  
*Last Updated: 2026-07-18*  
*Platform: Agentic Financial Intelligence Platform v1.7.0-phase8*