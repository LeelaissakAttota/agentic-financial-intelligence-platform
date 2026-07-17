"""
SEC Filing Downloader

Downloads SEC filings (10-K, 10-Q, 8-K, DEF14A, S-1, 13F, etc.) from EDGAR.
Supports rate limiting, caching, and incremental updates.
"""

import asyncio
import hashlib
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, AsyncGenerator, Optional
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# SEC EDGAR constants
SEC_BASE_URL = "https://www.sec.gov"
SEC_SEARCH_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
SEC_API_URL = "https://data.sec.gov/api/xbrl/companyfacts"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions"

# Supported SEC form types
SEC_FORM_TYPES = {
    "10-K": "annual_report",
    "10-Q": "quarterly_report",
    "8-K": "current_report",
    "DEF14A": "proxy_statement",
    "S-1": "registration_statement",
    "13F": "institutional_holdings",
    "20-F": "foreign_annual_report",
    "40-F": "canadian_annual_report",
    "6-K": "foreign_current_report",
    "20-F/A": "foreign_annual_report_amendment",
    "10-K/A": "annual_report_amendment",
    "10-Q/A": "quarterly_report_amendment",
    "8-K/A": "current_report_amendment",
    "DEF14A/A": "proxy_statement_amendment",
    "S-1/A": "registration_statement_amendment",
    "13F/A": "institutional_holdings_amendment",
}

# Rate limiting
SEC_RATE_LIMIT = 10  # requests per second
SEC_USER_AGENT = "FinancialResearchAgent/1.0 (contact@example.com)"


@dataclass
class SECFiling:
    """Represents an SEC filing with metadata."""
    cik: str
    company_name: str
    form_type: str
    filing_date: date
    accession_number: str
    document_url: str
    primary_document: Optional[str] = None
    file_size: Optional[int] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    form_type_category: Optional[str] = None
    filing_hash: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SECCompanyInfo:
    """Company information from SEC."""
    cik: str
    name: str
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    sic: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    fiscal_year_end: Optional[str] = None
    former_names: list[str] = field(default_factory=list)


class SECRateLimiter:
    """Rate limiter for SEC EDGAR requests."""
    
    def __init__(self, max_requests_per_second: float = SEC_RATE_LIMIT):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a request."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_request_time
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self.last_request_time = time.monotonic()


class SECCache:
    """Cache for SEC filings with TTL and persistence."""
    
    def __init__(self, cache_dir: Path = Path("./data/sec/cache"), ttl_days: int = 30):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(days=ttl_days)
        self._memory_cache: dict[str, tuple[Any, datetime]] = {}
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for key."""
        safe_key = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self.cache_dir / f"{safe_key}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        # Check memory cache first
        if key in self._memory_cache:
            value, timestamp = self._memory_cache[key]
            if datetime.now() - timestamp < self.ttl:
                return value
            else:
                del self._memory_cache[key]
        
        # Check disk cache
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                import json
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                timestamp = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - timestamp < self.ttl:
                    value = data['value']
                    self._memory_cache[key] = (value, timestamp)
                    return value
            except Exception as e:
                logger.warning(f"Cache read failed for {key}: {e}")
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        timestamp = datetime.now()
        self._memory_cache[key] = (value, timestamp)
        
        # Persist to disk
        cache_path = self._get_cache_path(key)
        try:
            import json
            # Convert dataclasses to dict for JSON serialization
            if hasattr(value, '__dataclass_fields__'):
                from dataclasses import asdict
                value = asdict(value)
            elif isinstance(value, list) and value and hasattr(value[0], '__dataclass_fields__'):
                from dataclasses import asdict
                value = [asdict(v) for v in value]
            
            data = {
                'timestamp': timestamp.isoformat(),
                'value': value
            }
            with open(cache_path, 'w') as f:
                json.dump(data, f, default=str)
        except Exception as e:
            logger.warning(f"Cache write failed for {key}: {e}")
    
    def clear_expired(self) -> int:
        """Clear expired cache entries. Returns count cleared."""
        cleared = 0
        now = datetime.now()
        
        # Clear memory cache
        expired_keys = [
            k for k, (_, ts) in self._memory_cache.items()
            if now - ts > self.ttl
        ]
        for k in expired_keys:
            del self._memory_cache[k]
            cleared += 1
        
        # Clear disk cache
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                import json
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                timestamp = datetime.fromisoformat(data['timestamp'])
                if now - timestamp > self.ttl:
                    cache_file.unlink()
                    cleared += 1
            except Exception:
                cache_file.unlink()
                cleared += 1
        
        return cleared


class SECDownloader:
    """Downloads SEC filings from EDGAR with rate limiting and caching."""
    
    def __init__(
        self,
        cache: Optional[SECCache] = None,
        rate_limiter: Optional[SECRateLimiter] = None,
        session: Optional[aiohttp.ClientSession] = None,
        user_agent: str = SEC_USER_AGENT
    ):
        self.cache = cache or SECCache()
        self.rate_limiter = rate_limiter or SECRateLimiter()
        self._session = session
        self._own_session = session is None
        self.user_agent = user_agent
        self._headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    
    async def __aenter__(self):
        if self._own_session and self._session is None:
            timeout = aiohttp.ClientTimeout(total=60, connect=10)
            self._session = aiohttp.ClientSession(
                headers=self._headers,
                timeout=timeout,
                connector=aiohttp.TCPConnector(limit=10)
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._own_session and self._session:
            await self._session.close()
    
    async def _get(self, url: str, params: dict = None) -> str:
        """Make GET request with rate limiting and caching."""
        cache_key = f"sec_get_{url}_{str(params)}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        await self.rate_limiter.acquire()
        
        if not self._session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        async with self._session.get(url, params=params) as response:
            response.raise_for_status()
            text = await response.text()
            
            # Cache successful responses
            self.cache.set(cache_key, text)
            return text
    
    async def _get_json(self, url: str, params: dict = None) -> dict:
        """Make GET request expecting JSON response."""
        text = await self._get(url, params)
        import json
        return json.loads(text)
    
    async def search_filings(
        self,
        cik: str,
        form_types: Optional[list[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        count: int = 100
    ) -> list[SECFiling]:
        """Search SEC filings for a company CIK."""
        form_types = form_types or list(SEC_FORM_TYPES.keys())
        
        # Use SEC submissions API
        url = f"{SEC_SUBMISSIONS_URL}/CIK{int(cik):010d}.json"
        
        try:
            data = await self._get_json(url)
            filings = data.get("filings", {}).get("recent", {})
            
            results = []
            for i in range(len(filings.get("accessionNumber", []))):
                form_type = filings["form"][i]
                if form_type not in form_types:
                    continue
                
                filing_date = datetime.strptime(filings["filingDate"][i], "%Y-%m-%d").date()
                if start_date and filing_date < start_date:
                    continue
                if end_date and filing_date > end_date:
                    continue
                
                # Build document URL
                accession = filings["accessionNumber"][i].replace("-", "")
                primary_doc = filings["primaryDocument"][i]
                doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary_doc}"
                
                filing = SECFiling(
                    cik=cik,
                    company_name="",  # Will be filled by company info
                    form_type=form_type,
                    filing_date=filing_date,
                    accession_number=filings["accessionNumber"][i],
                    document_url=doc_url,
                    primary_document=primary_doc,
                    file_size=filings.get("size", [None])[i],
                    form_type_category=SEC_FORM_TYPES.get(form_type, "other"),
                    filing_hash=hashlib.sha256(f"{cik}{filings['accessionNumber'][i]}".encode()).hexdigest()[:16]
                )
                results.append(filing)
                
                if len(results) >= count:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search filings for CIK {cik}: {e}")
            raise
    
    async def get_company_info(self, cik: str) -> SECCompanyInfo:
        """Get company information from SEC."""
        cache_key = f"company_info_{cik}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        url = f"{SEC_SUBMISSIONS_URL}/CIK{int(cik):010d}.json"
        data = await self._get_json(url)
        
        company = SECCompanyInfo(
            cik=cik,
            name=data.get("name", ""),
            ticker=data.get("tickers", [None])[0],
            exchange=data.get("exchanges", [None])[0],
            sic=data.get("sic"),
            state=data.get("stateOfIncorporation"),
            phone=data.get("phone"),
            website=data.get("website"),
            fiscal_year_end=data.get("fiscalYearEnd"),
            former_names=data.get("formerNames", [])
        )
        
        self.cache.set(cache_key, company)
        return company
    
    async def download_filing(
        self,
        filing: SECFiling,
        output_dir: Path,
        save_metadata: bool = True
    ) -> Path:
        """Download a specific filing document."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine filename
        ext = ".pdf" if filing.document_url.endswith(".pdf") else ".htm"
        filename = f"{filing.cik}_{filing.form_type}_{filing.filing_date}_{filing.accession_number}{ext}"
        filepath = output_dir / filename
        
        # Check if already downloaded
        if filepath.exists():
            logger.info(f"Filing already downloaded: {filepath}")
            return filepath
        
        # Download
        async with self._session.get(filing.document_url) as response:
            response.raise_for_status()
            content = await response.read()
            
            with open(filepath, 'wb') as f:
                f.write(content)
        
        logger.info(f"Downloaded filing: {filepath}")
        
        # Save metadata
        if save_metadata:
            import json
            meta_path = filepath.with_suffix('.json')
            from dataclasses import asdict
            with open(meta_path, 'w') as f:
                json.dump(asdict(filing), f, default=str, indent=2)
        
        return filepath
    
    async def download_company_filings(
        self,
        cik: str,
        form_types: Optional[list[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        output_dir: Path = Path("./data/filings"),
        max_filings: int = 100
    ) -> list[Path]:
        """Download multiple filings for a company."""
        filings = await self.search_filings(
            cik=cik,
            form_types=form_types,
            start_date=start_date,
            end_date=end_date,
            count=max_filings
        )
        
        downloaded = []
        for filing in filings:
            try:
                path = await self.download_filing(filing, output_dir)
                downloaded.append(path)
            except Exception as e:
                logger.error(f"Failed to download filing {filing.accession_number}: {e}")
        
        return downloaded


# Factory function
async def create_sec_downloader(
    cache_dir: Path = Path("./data/sec/cache"),
    cache_ttl_days: int = 30,
    rate_limit: float = SEC_RATE_LIMIT,
    output_dir: Path = Path("./data/filings")
) -> SECDownloader:
    """Create and initialize SEC downloader."""
    cache = SECCache(cache_dir=cache_dir, ttl_days=cache_ttl_days)
    rate_limiter = SECRateLimiter(max_requests_per_second=rate_limit)
    
    timeout = aiohttp.ClientTimeout(total=60, connect=10)
    connector = aiohttp.TCPConnector(limit=10)
    session = aiohttp.ClientSession(timeout=timeout, connector=connector)
    
    downloader = SECDownloader(
        cache=cache,
        rate_limiter=rate_limiter,
        session=session
    )
    
    return downloader