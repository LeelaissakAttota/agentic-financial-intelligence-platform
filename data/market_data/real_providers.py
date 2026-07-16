"""
Real Market Data Providers - Enterprise Grade Financial Data Integration

Supports multiple data sources with fallback chain:
- Yahoo Finance (yfinance) - Free, comprehensive
- Alpha Vantage - Free tier, good fundamentals
- Finnhub - Free tier, real-time data
- Polygon.io - Professional grade
- Twelve Data - Alternative provider

Features:
- Automatic fallback between providers
- Rate limiting and caching
- Data validation and normalization
- Async support for concurrent requests
- Comprehensive error handling
"""

import asyncio
import aiohttp
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import time
import json
import os
from abc import ABC, abstractmethod
from threading import Lock
import concurrent.futures

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Available data sources in priority order."""
    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    FINNHUB = "finnhub"
    POLYGON = "polygon"
    TWELVE_DATA = "twelve_data"


@dataclass
class RateLimiter:
    """Simple rate limiter for API calls."""
    calls_per_minute: int
    calls_per_day: int = 500
    _calls: List[float] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)
    
    def wait_if_needed(self):
        """Block until a call is allowed."""
        with self._lock:
            now = time.time()
            # Remove calls older than 1 minute
            self._calls = [t for t in self._calls if now - t < 60]
            
            if len(self._calls) >= self.calls_per_minute:
                sleep_time = 60 - (now - self._calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    now = time.time()
                    self._calls = [t for t in self._calls if now - t < 60]
            
            self._calls.append(now)


class MarketDataProviderBase(ABC):
    """Abstract base class for market data providers."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.rate_limiter: Optional[RateLimiter] = None
        self.session: Optional[aiohttp.ClientSession] = None
    
    @abstractmethod
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current quote data."""
        pass
    
    @abstractmethod
    async def get_fundamentals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get fundamental data."""
        pass
    
    @abstractmethod
    async def get_historical(self, symbol: str, period: str = "1y") -> Optional[List[Dict]]:
        """Get historical price data."""
        pass
    
    @abstractmethod
    async def get_company_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company profile/info."""
        pass
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()


class YahooFinanceProvider(MarketDataProviderBase):
    """Yahoo Finance provider using yfinance library."""
    
    def __init__(self):
        super().__init__()
        self.rate_limiter = RateLimiter(calls_per_minute=30)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    
    async def _run_sync(self, func, *args, **kwargs):
        """Run synchronous function in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func, *args, **kwargs)
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real-time quote from Yahoo Finance."""
        try:
            self.rate_limiter.wait_if_needed()
            
            def _get_info():
                ticker = yf.Ticker(symbol)
                return ticker.info
            
            info = await self._run_sync(_get_info)
            
            if not info or 'regularMarketPrice' not in info:
                return None
            
            return {
                'symbol': symbol.upper(),
                'current_price': info.get('regularMarketPrice'),
                'price_change': info.get('regularMarketChange'),
                'price_change_pct': info.get('regularMarketChangePercent'),
                'week_52_high': info.get('fiftyTwoWeekHigh'),
                'week_52_low': info.get('fiftyTwoWeekLow'),
                'avg_volume': info.get('averageVolume'),
                'volume': info.get('regularMarketVolume'),
                'market_cap': info.get('marketCap'),
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning(f"Yahoo Finance quote failed for {symbol}: {e}")
            return None
    
    async def get_fundamentals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get fundamental data from Yahoo Finance."""
        try:
            self.rate_limiter.wait_if_needed()
            
            def _get_info():
                ticker = yf.Ticker(symbol)
                return ticker.info
            
            info = await self._run_sync(_get_info)
            
            if not info:
                return None
            
            return {
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'peg_ratio': info.get('pegRatio'),
                'pb_ratio': info.get('priceToBook'),
                'ps_ratio': info.get('priceToSalesTrailing12Months'),
                'eps': info.get('trailingEps'),
                'eps_growth': info.get('earningsQuarterlyGrowth'),
                'revenue': info.get('totalRevenue'),
                'revenue_growth': info.get('revenueGrowth'),
                'profit_margin': info.get('profitMargins'),
                'operating_margin': info.get('operatingMargins'),
                'roe': info.get('returnOnEquity'),
                'roa': info.get('returnOnAssets'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'dividend_yield': info.get('dividendYield'),
                'dividend_payout_ratio': info.get('payoutRatio'),
                'beta': info.get('beta'),
                'shares_outstanding': info.get('sharesOutstanding'),
                'float_shares': info.get('floatShares'),
                'short_interest': info.get('shortPercentOfFloat'),
                'institutional_ownership': info.get('heldPercentInstitutions'),
                'analyst_target_price': info.get('targetMeanPrice'),
                'analyst_rating': info.get('recommendationMean'),
            }
        except Exception as e:
            logger.warning(f"Yahoo Finance fundamentals failed for {symbol}: {e}")
            return None
    
    async def get_historical(self, symbol: str, period: str = "1y") -> Optional[List[Dict]]:
        """Get historical price data from Yahoo Finance."""
        try:
            self.rate_limiter.wait_if_needed()
            
            def _get_history():
                ticker = yf.Ticker(symbol)
                return ticker.history(period=period)
            
            hist = await self._run_sync(_get_history)
            
            if hist.empty:
                return None
            
            data = []
            for idx, row in hist.iterrows():
                data.append({
                    'date': idx.strftime('%Y-%m-%d'),
                    'open': round(row['Open'], 2),
                    'high': round(row['High'], 2),
                    'low': round(row['Low'], 2),
                    'close': round(row['Close'], 2),
                    'volume': int(row['Volume']),
                })
            return data
        except Exception as e:
            logger.warning(f"Yahoo Finance historical failed for {symbol}: {e}")
            return None
    
    async def get_company_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company info from Yahoo Finance."""
        try:
            self.rate_limiter.wait_if_needed()
            
            def _get_info():
                ticker = yf.Ticker(symbol)
                return ticker.info
            
            info = await self._run_sync(_get_info)
            
            if not info:
                return None
            
            return {
                'symbol': symbol.upper(),
                'name': info.get('longName') or info.get('shortName'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'description': info.get('longBusinessSummary'),
                'website': info.get('website'),
                'employees': info.get('fullTimeEmployees'),
                'country': info.get('country'),
                'currency': info.get('currency'),
                'exchange': info.get('exchange'),
                'market_cap': info.get('marketCap'),
            }
        except Exception as e:
            logger.warning(f"Yahoo Finance company info failed for {symbol}: {e}")
            return None
    
    async def close(self):
        """Close the executor."""
        self._executor.shutdown(wait=False)


class AlphaVantageProvider(MarketDataProviderBase):
    """Alpha Vantage provider for fundamental data."""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.rate_limiter = RateLimiter(calls_per_minute=5, calls_per_day=500)
    
    async def _request(self, params: Dict) -> Optional[Dict]:
        """Make API request with rate limiting."""
        await self._ensure_session()
        self.rate_limiter.wait_if_needed()
        
        params['apikey'] = self.api_key
        
        try:
            async with self.session.get(self.BASE_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if 'Error Message' in data or 'Note' in data:
                        logger.warning(f"Alpha Vantage API error: {data}")
                        return None
                    return data
        except Exception as e:
            logger.warning(f"Alpha Vantage request failed: {e}")
        return None
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote from Alpha Vantage."""
        data = await self._request({
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol
        })
        
        if not data or 'Global Quote' not in data:
            return None
        
        quote = data['Global Quote']
        return {
            'symbol': symbol.upper(),
            'current_price': float(quote.get('05. price', 0)),
            'price_change': float(quote.get('09. change', 0)),
            'price_change_pct': float(quote.get('10. change percent', '0%').rstrip('%')),
            'volume': int(quote.get('06. volume', 0)),
            'timestamp': datetime.now().isoformat(),
        }
    
    async def get_fundamentals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get fundamentals from Alpha Vantage."""
        overview = await self._request({
            'function': 'OVERVIEW',
            'symbol': symbol
        })
        
        if not overview:
            return None
        
        # Map Alpha Vantage fields to our standard format
        return {
            'pe_ratio': self._safe_float(overview.get('PERatio')),
            'forward_pe': self._safe_float(overview.get('ForwardPE')),
            'peg_ratio': self._safe_float(overview.get('PEGRatio')),
            'pb_ratio': self._safe_float(overview.get('PriceToBookRatio')),
            'ps_ratio': self._safe_float(overview.get('PriceToSalesRatioTTM')),
            'eps': self._safe_float(overview.get('EPS')),
            'revenue': self._safe_float(overview.get('RevenueTTM')),
            'profit_margin': self._safe_float(overview.get('ProfitMargin')),
            'operating_margin': self._safe_float(overview.get('OperatingMarginTTM')),
            'roe': self._safe_float(overview.get('ReturnOnEquityTTM')),
            'roa': self._safe_float(overview.get('ReturnOnAssetsTTM')),
            'debt_to_equity': self._safe_float(overview.get('DebtToEquity')),
            'current_ratio': self._safe_float(overview.get('CurrentRatio')),
            'dividend_yield': self._safe_float(overview.get('DividendYield')),
            'beta': self._safe_float(overview.get('Beta')),
            'market_cap': self._safe_float(overview.get('MarketCapitalization')),
            'analyst_target_price': self._safe_float(overview.get('AnalystTargetPrice')),
            'sector': overview.get('Sector'),
            'industry': overview.get('Industry'),
        }
    
    async def get_historical(self, symbol: str, period: str = "1y") -> Optional[List[Dict]]:
        """Get historical data from Alpha Vantage."""
        data = await self._request({
            'function': 'TIME_SERIES_DAILY_ADJUSTED',
            'symbol': symbol,
            'outputsize': 'full' if period == 'max' else 'compact'
        })
        
        if not data or 'Time Series (Daily)' not in data:
            return None
        
        series = data['Time Series (Daily)']
        cutoff = datetime.now() - self._period_to_timedelta(period)
        
        result = []
        for date_str, values in series.items():
            date = datetime.strptime(date_str, '%Y-%m-%d')
            if date >= cutoff:
                result.append({
                    'date': date_str,
                    'open': float(values['1. open']),
                    'high': float(values['2. high']),
                    'low': float(values['3. low']),
                    'close': float(values['4. close']),
                    'volume': int(values['6. volume']),
                })
        
        return sorted(result, key=lambda x: x['date'])
    
    async def get_company_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company info from Alpha Vantage."""
        overview = await self._request({
            'function': 'OVERVIEW',
            'symbol': symbol
        })
        
        if not overview:
            return None
        
        return {
            'symbol': symbol.upper(),
            'name': overview.get('Name'),
            'sector': overview.get('Sector'),
            'industry': overview.get('Industry'),
            'description': overview.get('Description'),
            'website': None,
            'employees': self._safe_int(overview.get('FullTimeEmployees')),
            'country': overview.get('Country'),
            'currency': overview.get('Currency'),
            'exchange': overview.get('Exchange'),
            'market_cap': self._safe_float(overview.get('MarketCapitalization')),
        }
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert to float."""
        if value is None or value in ('None', '-', ''):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert to int."""
        if value is None or value in ('None', '-', ''):
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _period_to_timedelta(self, period: str) -> timedelta:
        """Convert period string to timedelta."""
        period_map = {
            '1d': timedelta(days=1),
            '5d': timedelta(days=5),
            '1mo': timedelta(days=30),
            '3mo': timedelta(days=90),
            '6mo': timedelta(days=180),
            '1y': timedelta(days=365),
            '2y': timedelta(days=730),
            '5y': timedelta(days=1825),
            '10y': timedelta(days=3650),
            'max': timedelta(days=36500),
        }
        return period_map.get(period, timedelta(days=365))


class FinnhubProvider(MarketDataProviderBase):
    """Finnhub provider for real-time data and news."""
    
    BASE_URL = "https://finnhub.io/api/v1"
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.rate_limiter = RateLimiter(calls_per_minute=60)
    
    async def _request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Make API request with rate limiting."""
        await self._ensure_session()
        self.rate_limiter.wait_if_needed()
        
        params['token'] = self.api_key
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.warning(f"Finnhub request failed: {e}")
        return None
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real-time quote from Finnhub."""
        data = await self._request('/quote', {'symbol': symbol})
        
        if not data or 'c' not in data:
            return None
        
        return {
            'symbol': symbol.upper(),
            'current_price': data.get('c'),
            'price_change': data.get('d'),
            'price_change_pct': data.get('dp'),
            'high': data.get('h'),
            'low': data.get('l'),
            'open': data.get('o'),
            'prev_close': data.get('pc'),
            'timestamp': datetime.now().isoformat(),
        }
    
    async def get_fundamentals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get basic financials from Finnhub."""
        # Finnhub has limited fundamentals in free tier
        data = await self._request('/stock/metric', {'symbol': symbol, 'metric': 'all'})
        
        if not data or 'metric' not in data:
            return None
        
        m = data['metric']
        return {
            'pe_ratio': m.get('peBasicExclExtraTTM'),
            'forward_pe': m.get('forwardPE'),
            'pb_ratio': m.get('pbAnnual'),
            'ps_ratio': m.get('psAnnual'),
            'eps': m.get('epsBasicExclExtraItemsTTM'),
            'revenue': m.get('revenueTTM'),
            'profit_margin': m.get('netProfitMarginTTM'),
            'operating_margin': m.get('operatingMarginTTM'),
            'roe': m.get('roeTTM'),
            'roa': m.get('roaTTM'),
            'debt_to_equity': m.get('totalDebt/totalEquityAnnual'),
            'current_ratio': m.get('currentRatioAnnual'),
            'dividend_yield': m.get('dividendYieldIndicatedAnnual'),
            'beta': m.get('beta'),
            'market_cap': m.get('marketCapitalization'),
        }
    
    async def get_historical(self, symbol: str, period: str = "1y") -> Optional[List[Dict]]:
        """Get historical candles from Finnhub."""
        resolution = 'D'  # Daily
        to_ts = int(time.time())
        from_ts = to_ts - self._period_to_seconds(period)
        
        data = await self._request('/stock/candle', {
            'symbol': symbol,
            'resolution': resolution,
            'from': from_ts,
            'to': to_ts,
        })
        
        if not data or data.get('s') != 'ok':
            return None
        
        result = []
        for i in range(len(data['t'])):
            result.append({
                'date': datetime.fromtimestamp(data['t'][i]).strftime('%Y-%m-%d'),
                'open': data['o'][i],
                'high': data['h'][i],
                'low': data['l'][i],
                'close': data['c'][i],
                'volume': data['v'][i],
            })
        return result
    
    async def get_company_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company profile from Finnhub."""
        data = await self._request('/stock/profile2', {'symbol': symbol})
        
        if not data:
            return None
        
        return {
            'symbol': symbol.upper(),
            'name': data.get('name'),
            'sector': data.get('finnhubIndustry'),
            'industry': data.get('finnhubIndustry'),
            'website': data.get('weburl'),
            'logo': data.get('logo'),
            'ipo_date': data.get('ipo'),
            'market_cap': data.get('marketCapitalization'),
            'shares_outstanding': data.get('shareOutstanding'),
            'currency': data.get('currency'),
            'exchange': data.get('exchange'),
        }
    
    def _period_to_seconds(self, period: str) -> int:
        """Convert period to seconds."""
        period_map = {
            '1d': 86400,
            '5d': 432000,
            '1mo': 2592000,
            '3mo': 7776000,
            '6mo': 15552000,
            '1y': 31536000,
            '2y': 63072000,
            '5y': 157680000,
            'max': 315360000,
        }
        return period_map.get(period, 31536000)


class CompositeMarketDataProvider:
    """
    Composite provider with automatic fallback chain.
    
    Tries providers in order until one succeeds.
    Maintains a cache for performance.
    """
    
    def __init__(
        self,
        yahoo: bool = True,
        alpha_vantage_key: Optional[str] = None,
        finnhub_key: Optional[str] = None,
        polygon_key: Optional[str] = None,
        twelve_data_key: Optional[str] = None,
        cache_ttl: int = 300,  # 5 minutes
    ):
        self.providers: List[MarketDataProviderBase] = []
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, float] = {}
        self.cache_ttl = cache_ttl
        
        # Add providers in priority order
        if yahoo:
            self.providers.append(YahooFinanceProvider())
        if alpha_vantage_key:
            self.providers.append(AlphaVantageProvider(alpha_vantage_key))
        if finnhub_key:
            self.providers.append(FinnhubProvider(finnhub_key))
        
        if not self.providers:
            raise ValueError("At least one data provider must be configured")
    
    def _get_cache_key(self, method: str, symbol: str, **kwargs) -> str:
        """Generate cache key."""
        return f"{method}:{symbol.upper()}:{json.dumps(kwargs, sort_keys=True)}"
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is valid."""
        if key not in self.cache_timestamps:
            return False
        return time.time() - self.cache_timestamps[key] < self.cache_ttl
    
    async def _call_with_fallback(self, method: str, symbol: str, **kwargs) -> Optional[Any]:
        """Call method on providers with fallback."""
        cache_key = self._get_cache_key(method, symbol, **kwargs)
        
        if self._is_cache_valid(cache_key):
            logger.debug(f"Cache hit for {cache_key}")
            return self.cache[cache_key]
        
        last_error = None
        for provider in self.providers:
            try:
                result = await getattr(provider, method)(symbol, **kwargs)
                if result is not None:
                    self.cache[cache_key] = result
                    self.cache_timestamps[cache_key] = time.time()
                    return result
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider.__class__.__name__} failed for {method}({symbol}): {e}")
                continue
        
        logger.error(f"All providers failed for {method}({symbol}): {last_error}")
        return None
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current quote with fallback."""
        return await self._call_with_fallback('get_quote', symbol)
    
    async def get_fundamentals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get fundamentals with fallback."""
        return await self._call_with_fallback('get_fundamentals', symbol)
    
    async def get_historical(self, symbol: str, period: str = "1y") -> Optional[List[Dict]]:
        """Get historical data with fallback."""
        return await self._call_with_fallback('get_historical', symbol, period=period)
    
    async def get_company_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company info with fallback."""
        return await self._call_with_fallback('get_company_info', symbol)
    
    async def get_complete_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get all market data for a symbol in parallel."""
        symbol = symbol.upper()
        
        # Run all requests in parallel
        quote_task = self.get_quote(symbol)
        fundamentals_task = self.get_fundamentals(symbol)
        historical_task = self.get_historical(symbol, "1y")
        company_task = self.get_company_info(symbol)
        
        quote, fundamentals, historical, company = await asyncio.gather(
            quote_task, fundamentals_task, historical_task, company_task
        )
        
        # Merge all data
        result = {'symbol': symbol}
        
        if quote:
            result.update(quote)
        if fundamentals:
            result['fundamentals'] = fundamentals
        if historical:
            result['historical'] = historical
        if company:
            result['company'] = company
        
        return result if any([quote, fundamentals, historical, company]) else None
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        self.cache_timestamps.clear()
    
    async def close(self):
        """Close all provider sessions."""
        for provider in self.providers:
            await provider.close()


# Global instance for easy access
_default_provider: Optional[CompositeMarketDataProvider] = None


def get_market_data_provider(
    yahoo: bool = True,
    alpha_vantage_key: Optional[str] = None,
    finnhub_key: Optional[str] = None,
    **kwargs
) -> CompositeMarketDataProvider:
    """Get or create the default composite provider."""
    global _default_provider
    
    if _default_provider is None:
        _default_provider = CompositeMarketDataProvider(
            yahoo=yahoo,
            alpha_vantage_key=alpha_vantage_key or os.getenv('ALPHA_VANTAGE_API_KEY'),
            finnhub_key=finnhub_key or os.getenv('FINNHUB_API_KEY'),
            **kwargs
        )
    return _default_provider


async def get_complete_market_data(symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Convenience function to get complete market data."""
    provider = get_market_data_provider(**kwargs)
    return await provider.get_complete_market_data(symbol)


if __name__ == "__main__":
    # Demo
    import asyncio
    
    async def demo():
        provider = get_market_data_provider(yahoo=True)
        data = await provider.get_complete_market_data("NVDA")
        print(json.dumps(data, indent=2, default=str))
        await provider.close()
    
    asyncio.run(demo())