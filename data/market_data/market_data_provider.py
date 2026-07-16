"""
Market Data Provider - Mock/simulation of financial market data.

Provides realistic financial data for testing and development without
requiring live API connections. In production, this would be replaced
with real data sources (Yahoo Finance, Alpha Vantage, Polygon, etc.)
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class PriceData:
    """Single price point data."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class TechnicalIndicators:
    """Technical analysis indicators."""
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
    """Fundamental financial metrics."""
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
    """Market/sector context data."""
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
    """Complete market data package for a company."""
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


# Company profiles for realistic data generation
COMPANY_PROFILES = {
    "NVDA": {
        "name": "NVIDIA Corporation",
        "sector": "Technology",
        "industry": "Semiconductors",
        "base_price": 875.0,
        "volatility": 0.035,
        "market_cap": 2_150_000_000_000,
        "pe_range": (45, 65),
        "beta": 1.75,
        "avg_volume": 45_000_000,
    },
    "AAPL": {
        "name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "base_price": 185.0,
        "volatility": 0.018,
        "market_cap": 2_880_000_000_000,
        "pe_range": (25, 32),
        "beta": 1.25,
        "avg_volume": 55_000_000,
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "sector": "Technology",
        "industry": "Software",
        "base_price": 415.0,
        "volatility": 0.017,
        "market_cap": 3_080_000_000_000,
        "pe_range": (30, 38),
        "beta": 0.95,
        "avg_volume": 25_000_000,
    },
    "GOOGL": {
        "name": "Alphabet Inc.",
        "sector": "Technology",
        "industry": "Internet Services",
        "base_price": 172.0,
        "volatility": 0.022,
        "market_cap": 2_150_000_000_000,
        "pe_range": (22, 28),
        "beta": 1.10,
        "avg_volume": 28_000_000,
    },
    "AMZN": {
        "name": "Amazon.com Inc.",
        "sector": "Consumer Cyclical",
        "industry": "Internet Retail",
        "base_price": 178.0,
        "volatility": 0.025,
        "market_cap": 1_850_000_000_000,
        "pe_range": (40, 55),
        "beta": 1.35,
        "avg_volume": 35_000_000,
    },
    "META": {
        "name": "Meta Platforms Inc.",
        "sector": "Technology",
        "industry": "Internet Services",
        "base_price": 485.0,
        "volatility": 0.028,
        "market_cap": 1_220_000_000_000,
        "pe_range": (20, 28),
        "beta": 1.20,
        "avg_volume": 18_000_000,
    },
    "TSLA": {
        "name": "Tesla Inc.",
        "sector": "Consumer Cyclical",
        "industry": "Auto Manufacturers",
        "base_price": 248.0,
        "volatility": 0.045,
        "market_cap": 790_000_000_000,
        "pe_range": (55, 85),
        "beta": 2.10,
        "avg_volume": 95_000_000,
    },
    "JPM": {
        "name": "JPMorgan Chase & Co.",
        "sector": "Financial Services",
        "industry": "Banks",
        "base_price": 195.0,
        "volatility": 0.015,
        "market_cap": 560_000_000_000,
        "pe_range": (10, 14),
        "beta": 1.15,
        "avg_volume": 12_000_000,
    },
}


class MarketDataProvider:
    """
    Mock market data provider.
    
    Generates realistic financial data for testing. Uses seeded random
    generation for reproducibility.
    """
    
    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._cache: Dict[str, CompleteMarketData] = {}
    
    def _get_profile(self, symbol: str) -> dict:
        """Get or create company profile."""
        if symbol not in COMPANY_PROFILES:
            return {
                "name": f"{symbol} Inc.",
                "sector": "Technology",
                "industry": "Software",
                "base_price": 100.0,
                "volatility": 0.02,
                "market_cap": 10_000_000_000,
                "pe_range": (15, 25),
                "beta": 1.0,
                "avg_volume": 5_000_000,
            }
        return COMPANY_PROFILES[symbol]
    
    def _generate_price_history(
        self, 
        symbol: str, 
        days: int = 252
    ) -> List[PriceData]:
        """Generate realistic price history using geometric Brownian motion."""
        profile = self._get_profile(symbol)
        base_price = profile["base_price"]
        volatility = profile["volatility"]
        avg_volume = profile["avg_volume"]
        
        prices = []
        current_price = base_price
        
        end_date = datetime.now()
        
        for i in range(days):
            date = end_date - timedelta(days=days - i - 1)
            
            # Random walk with drift
            daily_return = self._rng.gauss(0.0003, volatility)
            current_price *= (1 + daily_return)
            
            # Generate OHLC
            daily_vol = current_price * 0.015
            high = current_price * (1 + abs(self._rng.gauss(0, 0.008)))
            low = current_price * (1 - abs(self._rng.gauss(0, 0.008)))
            open_price = current_price * (1 + self._rng.gauss(0, 0.005))
            
            # Ensure high >= max(open, close) and low <= min(open, close)
            high = max(high, open_price, current_price)
            low = min(low, open_price, current_price)
            
            volume = int(avg_volume * self._rng.lognormvariate(0, 0.3))
            
            prices.append(PriceData(
                date=date.strftime("%Y-%m-%d"),
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(current_price, 2),
                volume=volume
            ))
        
        return prices
    
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
        
        # MACD Signal (9-period EMA of MACD)
        macd_signal = None
        if macd is not None:
            # Simplified - use recent MACD values
            macd_signal = macd * 0.9  # Approximation
        
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
    
    def _generate_financial_metrics(self, symbol: str) -> FinancialMetrics:
        """Generate realistic financial metrics."""
        profile = self._get_profile(symbol)
        
        # Use company-specific ranges
        pe_min, pe_max = profile["pe_range"]
        
        return FinancialMetrics(
            pe_ratio=round(self._rng.uniform(pe_min, pe_max), 2),
            forward_pe=round(self._rng.uniform(pe_min * 0.85, pe_max * 0.85), 2),
            peg_ratio=round(self._rng.uniform(0.8, 2.5), 2),
            pb_ratio=round(self._rng.uniform(2.0, 15.0), 2),
            ps_ratio=round(self._rng.uniform(3.0, 25.0), 2),
            eps=round(self._rng.uniform(2.0, 25.0), 2),
            eps_growth=round(self._rng.uniform(-0.15, 0.45), 4),
            revenue=round(self._rng.uniform(50_000_000_000, 500_000_000_000), 2),
            revenue_growth=round(self._rng.uniform(-0.10, 0.35), 4),
            profit_margin=round(self._rng.uniform(0.05, 0.35), 4),
            operating_margin=round(self._rng.uniform(0.10, 0.40), 4),
            roe=round(self._rng.uniform(0.10, 0.50), 4),
            roa=round(self._rng.uniform(0.05, 0.20), 4),
            debt_to_equity=round(self._rng.uniform(0.1, 1.5), 2),
            current_ratio=round(self._rng.uniform(0.8, 3.0), 2),
            dividend_yield=round(self._rng.uniform(0.0, 0.03), 4),
            dividend_payout_ratio=round(self._rng.uniform(0.15, 0.60), 2),
            beta=profile["beta"],
        )
    
    def _generate_market_context(self, symbol: str) -> MarketContext:
        """Generate market/sector context."""
        profile = self._get_profile(symbol)
        
        return MarketContext(
            sector=profile["sector"],
            industry=profile["industry"],
            sector_performance_1m=round(self._rng.uniform(-0.08, 0.08), 4),
            sector_performance_3m=round(self._rng.uniform(-0.15, 0.15), 4),
            market_cap=profile["market_cap"],
            shares_outstanding=profile["market_cap"] / profile["base_price"],
            float_shares=profile["market_cap"] / profile["base_price"] * 0.85,
            short_interest=round(self._rng.uniform(0.005, 0.05), 4),
            institutional_ownership=round(self._rng.uniform(0.55, 0.85), 4),
            analyst_rating=self._rng.choice(["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]),
            analyst_target_price=round(profile["base_price"] * self._rng.uniform(0.9, 1.2), 2),
        )
    
    def get_market_data(self, symbol: str, use_cache: bool = True) -> CompleteMarketData:
        """
        Get complete market data for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., "NVDA")
            use_cache: Whether to use cached data
            
        Returns:
            CompleteMarketData object with all market information
        """
        symbol = symbol.upper()
        
        if use_cache and symbol in self._cache:
            return self._cache[symbol]
        
        profile = self._get_profile(symbol)
        
        # Generate price history
        price_data = self._generate_price_history(symbol, 252)
        current_price = price_data[-1].close
        prev_close = price_data[-2].close if len(price_data) > 1 else current_price
        
        price_change = current_price - prev_close
        price_change_pct = (price_change / prev_close) * 100 if prev_close > 0 else 0
        
        # Calculate 52-week high/low
        highs = [p.high for p in price_data]
        lows = [p.low for p in price_data]
        week_52_high = max(highs)
        week_52_low = min(lows)
        
        # Average volume
        avg_volume = int(sum(p.volume for p in price_data[-20:]) / 20)
        
        # Technical indicators
        technical = self._calculate_technical_indicators(price_data)
        
        # Financial metrics
        financial = self._generate_financial_metrics(symbol)
        
        # Market context
        market_ctx = self._generate_market_context(symbol)
        
        data = CompleteMarketData(
            symbol=symbol,
            company_name=profile["name"],
            current_price=round(current_price, 2),
            price_change=round(price_change, 2),
            price_change_pct=round(price_change_pct, 2),
            price_data=price_data,
            technical_indicators=technical,
            financial_metrics=financial,
            market_context=market_ctx,
            week_52_high=round(week_52_high, 2),
            week_52_low=round(week_52_low, 2),
            avg_volume=avg_volume,
            timestamp=datetime.now().isoformat(),
        )
        
        if use_cache:
            self._cache[symbol] = data
        
        return data
    
    def get_price_data_only(self, symbol: str, days: int = 30) -> List[PriceData]:
        """Get just price data for a symbol."""
        full_data = self.get_market_data(symbol)
        return full_data.price_data[-days:]
    
    def clear_cache(self):
        """Clear the data cache."""
        self._cache.clear()


# Singleton instance
_default_provider: Optional[MarketDataProvider] = None


def get_market_data_provider(seed: Optional[int] = None) -> MarketDataProvider:
    """Get the default market data provider."""
    global _default_provider
    if _default_provider is None:
        _default_provider = MarketDataProvider(seed=seed)
    return _default_provider


def get_market_data(symbol: str, seed: Optional[int] = None) -> CompleteMarketData:
    """Convenience function to get market data."""
    provider = get_market_data_provider(seed)
    return provider.get_market_data(symbol)


if __name__ == "__main__":
    # Demo
    provider = MarketDataProvider(seed=42)
    data = provider.get_market_data("NVDA")
    
    print(f"Symbol: {data.symbol}")
    print(f"Company: {data.company_name}")
    print(f"Current Price: ${data.current_price}")
    print(f"Change: ${data.price_change} ({data.price_change_pct:.2f}%)")
    print(f"52-Week Range: ${data.week_52_low} - ${data.week_52_high}")
    print(f"PE Ratio: {data.financial_metrics.pe_ratio}")
    print(f"RSI: {data.technical_indicators.rsi_14}")
    print(f"Sector: {data.market_context.sector}")