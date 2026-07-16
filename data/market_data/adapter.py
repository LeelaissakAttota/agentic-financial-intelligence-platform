"""
Adapter to bridge real market data providers to the existing CompleteMarketData format.

This allows the MarketAgent to work with both mock data (for testing) and real data
(from Yahoo Finance, Alpha Vantage, etc.) without code changes.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from data.market_data.real_providers import (
    get_market_data_provider,
    CompositeMarketDataProvider,
    MarketDataProviderBase,
)


@dataclass
class PriceData:
    """Single price point data (compatible with existing schema)."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class TechnicalIndicators:
    """Technical analysis indicators (compatible with existing schema)."""
    rsi_14: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_middle: Optional[float] = None
    bollinger_lower: Optional[float] = None


@dataclass
class FinancialMetrics:
    """Fundamental financial metrics (compatible with existing schema)."""
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    eps: Optional[float] = None
    eps_growth: Optional[float] = None
    revenue: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    dividend_payout_ratio: Optional[float] = None
    beta: Optional[float] = None


@dataclass
class MarketContext:
    """Market/sector context data (compatible with existing schema)."""
    sector: str
    industry: str
    sector_performance_1m: Optional[float] = None
    sector_performance_3m: Optional[float] = None
    market_cap: Optional[float] = None
    shares_outstanding: Optional[float] = None
    float_shares: Optional[float] = None
    short_interest: Optional[float] = None
    institutional_ownership: Optional[float] = None
    analyst_rating: Optional[str] = None
    analyst_target_price: Optional[float] = None
    beta: Optional[float] = None


@dataclass
class CompleteMarketData:
    """Complete market data package for a company (compatible with existing schema)."""
    symbol: str
    company_name: str
    current_price: float
    price_change: float
    price_change_pct: float
    price_data: List[PriceData]
    technical_indicators: TechnicalIndicators
    financial_metrics: FinancialMetrics
    market_context: MarketContext
    week_52_high: float
    week_52_low: float
    avg_volume: int
    timestamp: str


class RealDataAdapter:
    """
    Adapter that converts real provider data to CompleteMarketData format.
    
    This allows the MarketAgent to use real-time data seamlessly.
    """
    
    def __init__(self, provider: Optional[CompositeMarketDataProvider] = None):
        self.provider = provider or get_market_data_provider(yahoo=True)
    
    def _calculate_technical_indicators(self, price_data: List[PriceData]) -> TechnicalIndicators:
        """Calculate technical indicators from price history."""
        if len(price_data) < 200:
            return TechnicalIndicators()
        
        closes = [p.close for p in price_data]
        
        # RSI (14-period)
        rsi = self._calculate_rsi(closes, 14)
        
        # Simple Moving Averages
        sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
        sma_200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else None
        
        # MACD
        ema_12 = self._ema(closes, 12)
        ema_26 = self._ema(closes, 26)
        macd = ema_12 - ema_26 if ema_12 and ema_26 else None
        macd_signal = macd * 0.9 if macd else None  # Approximation
        macd_histogram = (macd - macd_signal) if macd and macd_signal else None
        
        # Bollinger Bands (20-period, 2 std dev)
        if len(closes) >= 20:
            recent = closes[-20:]
            middle = sum(recent) / 20
            std = (sum((x - middle) ** 2 for x in recent) / 20) ** 0.5
            bollinger_upper = middle + 2 * std
            bollinger_lower = middle - 2 * std
        else:
            middle = bollinger_upper = bollinger_lower = None
        
        return TechnicalIndicators(
            rsi_14=rsi,
            sma_20=sma_20,
            sma_50=sma_50,
            sma_200=sma_200,
            macd=macd,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            bollinger_upper=bollinger_upper,
            bollinger_middle=middle,
            bollinger_lower=bollinger_lower,
        )
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> Optional[float]:
        """Calculate RSI."""
        if len(closes) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, period + 1):
            change = closes[-i] - closes[-i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    
    def _ema(self, closes: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average."""
        if len(closes) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = closes[-period]
        
        for price in closes[-period + 1:]:
            ema = (price - ema) * multiplier + ema
        
        return round(ema, 2)
    
    def _adapt_quote(self, quote: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt quote data to standard format."""
        return {
            'symbol': quote.get('symbol'),
            'current_price': quote.get('current_price'),
            'price_change': quote.get('price_change', 0),
            'price_change_pct': quote.get('price_change_pct', 0),
            'week_52_high': quote.get('week_52_high'),
            'week_52_low': quote.get('week_52_low'),
            'avg_volume': quote.get('avg_volume'),
            'volume': quote.get('volume'),
        }
    
    def _adapt_fundamentals(self, fundamentals: Dict[str, Any]) -> FinancialMetrics:
        """Adapt fundamentals data to FinancialMetrics."""
        return FinancialMetrics(
            pe_ratio=fundamentals.get('pe_ratio'),
            forward_pe=fundamentals.get('forward_pe'),
            peg_ratio=fundamentals.get('peg_ratio'),
            pb_ratio=fundamentals.get('pb_ratio'),
            ps_ratio=fundamentals.get('ps_ratio'),
            eps=fundamentals.get('eps'),
            eps_growth=fundamentals.get('eps_growth'),
            revenue=fundamentals.get('revenue'),
            revenue_growth=fundamentals.get('revenue_growth'),
            profit_margin=fundamentals.get('profit_margin'),
            operating_margin=fundamentals.get('operating_margin'),
            roe=fundamentals.get('roe'),
            roa=fundamentals.get('roa'),
            debt_to_equity=fundamentals.get('debt_to_equity'),
            current_ratio=fundamentals.get('current_ratio'),
            dividend_yield=fundamentals.get('dividend_yield'),
            dividend_payout_ratio=fundamentals.get('dividend_payout_ratio'),
            beta=fundamentals.get('beta'),
        )
    
    def _adapt_company_info(self, company: Dict[str, Any], fundamentals: Dict[str, Any]) -> MarketContext:
        """Adapt company info to MarketContext."""
        return MarketContext(
            sector=company.get('sector', 'Technology'),
            industry=company.get('industry', 'Software'),
            sector_performance_1m=None,  # Would need sector ETF data
            sector_performance_3m=None,
            market_cap=company.get('market_cap') or fundamentals.get('market_cap'),
            shares_outstanding=company.get('shares_outstanding'),
            float_shares=company.get('float_shares'),
            short_interest=fundamentals.get('short_interest'),
            institutional_ownership=fundamentals.get('institutional_ownership'),
            analyst_rating=fundamentals.get('analyst_rating'),
            analyst_target_price=fundamentals.get('analyst_target_price'),
            beta=fundamentals.get('beta'),
        )
    
    def _adapt_historical(self, historical: List[Dict]) -> List[PriceData]:
        """Adapt historical data to PriceData list."""
        return [
            PriceData(
                date=h['date'],
                open=h['open'],
                high=h['high'],
                low=h['low'],
                close=h['close'],
                volume=h['volume'],
            )
            for h in historical
        ]
    
    async def get_market_data(self, symbol: str) -> Optional[CompleteMarketData]:
        """
        Get complete market data in the format expected by MarketAgent.
        
        This is the main entry point that replaces get_market_data from the mock provider.
        """
        symbol = symbol.upper()
        
        # Fetch all data from real providers
        raw_data = await self.provider.get_complete_market_data(symbol)
        
        if not raw_data:
            return None
        
        # Extract components
        quote = self._adapt_quote(raw_data) if raw_data else {}
        fundamentals = raw_data.get('fundamentals', {})
        historical = raw_data.get('historical', [])
        company = raw_data.get('company', {})
        
        # Validate minimum required data
        if not quote.get('current_price'):
            return None
        
        # Convert historical to PriceData
        price_data = self._adapt_historical(historical) if historical else []
        
        # Calculate technical indicators from price data
        technical = self._calculate_technical_indicators(price_data)
        
        # Adapt fundamentals
        financial_metrics = self._adapt_fundamentals(fundamentals)
        
        # Adapt company info
        market_context = self._adapt_company_info(company, fundamentals)
        
        # Determine 52-week high/low from historical data if not in quote
        week_52_high = quote.get('week_52_high')
        week_52_low = quote.get('week_52_low')
        avg_volume = quote.get('avg_volume')
        
        if not week_52_high or not week_52_low or not avg_volume:
            if price_data:
                highs = [p.high for p in price_data]
                lows = [p.low for p in price_data]
                volumes = [p.volume for p in price_data]
                week_52_high = week_52_high or max(highs)
                week_52_low = week_52_low or min(lows)
                avg_volume = avg_volume or int(sum(volumes[-20:]) / min(20, len(volumes)))
        
        return CompleteMarketData(
            symbol=symbol,
            company_name=company.get('name', f'{symbol} Inc.'),
            current_price=quote['current_price'],
            price_change=quote.get('price_change', 0),
            price_change_pct=quote.get('price_change_pct', 0),
            price_data=price_data,
            technical_indicators=technical,
            financial_metrics=financial_metrics,
            market_context=market_context,
            week_52_high=week_52_high,
            week_52_low=week_52_low,
            avg_volume=avg_volume or 0,
            timestamp=datetime.now().isoformat(),
        )
    
    async def close(self):
        """Close the provider."""
        await self.provider.close()


# Global adapter instance
_default_adapter: Optional[RealDataAdapter] = None


def get_real_data_adapter(
    yahoo: bool = True,
    alpha_vantage_key: Optional[str] = None,
    finnhub_key: Optional[str] = None,
) -> RealDataAdapter:
    """Get or create the default real data adapter."""
    global _default_adapter
    
    if _default_adapter is None:
        provider = get_market_data_provider(
            yahoo=yahoo,
            alpha_vantage_key=alpha_vantage_key,
            finnhub_key=finnhub_key,
        )
        _default_adapter = RealDataAdapter(provider)
    
    return _default_adapter


async def get_real_market_data(symbol: str, **kwargs) -> Optional[CompleteMarketData]:
    """Convenience function to get real market data in CompleteMarketData format."""
    adapter = get_real_data_adapter(**kwargs)
    return await adapter.get_market_data(symbol)


if __name__ == "__main__":
    # Demo
    import asyncio
    
    async def demo():
        adapter = get_real_data_adapter(yahoo=True)
        data = await adapter.get_market_data("NVDA")
        if data:
            print(f"Symbol: {data.symbol}")
            print(f"Company: {data.company_name}")
            print(f"Price: ${data.current_price:.2f} ({data.price_change_pct:+.2f}%)")
            print(f"52W Range: ${data.week_52_low:.2f} - ${data.week_52_high:.2f}")
            print(f"P/E: {data.financial_metrics.pe_ratio}")
            print(f"RSI: {data.technical_indicators.rsi_14}")
            print(f"Sector: {data.market_context.sector}")
        else:
            print("Failed to fetch data")
        await adapter.close()
    
    asyncio.run(demo())