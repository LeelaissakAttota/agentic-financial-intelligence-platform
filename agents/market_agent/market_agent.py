"""
Market Analysis Agent - Analyzes market data and provides narrative insights.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any

from .schemas import (
    MarketAgentInput,
    MarketAgentOutput,
    PriceMovementAnalysis,
    TechnicalAnalysis,
    FinancialAnalysis,
    MarketTrendsAnalysis,
    WorkerResponse,
)
from .prompts import (
    SYSTEM_PROMPT,
    PRICE_MOVEMENT_PROMPT,
    TECHNICAL_PROMPT,
    FINANCIAL_PROMPT,
    MARKET_TRENDS_PROMPT,
    OVERALL_NARRATIVE_PROMPT,
)
# Use real data adapter instead of mock provider
from data.market_data.adapter import get_real_market_data, CompleteMarketData
from llm.llm_provider import LLMProvider
from agents.manager_agent.manager import BaseWorkerAgent


class MarketAgent(BaseWorkerAgent):
    """Market Analysis Agent - interprets market data and provides narrative insights."""
    
    def __init__(self, llm_provider: LLMProvider, model: str = "openrouter/auto"):
        """
        Initialize the Market Agent.
        
        Args:
            llm_provider: LLM provider for generating analysis
            model: Model to use for analysis
        """
        super().__init__(agent_name="market_agent")
        self.llm_provider = llm_provider
        self.model = model
    
    async def run(self, company: str, context: Dict[str, Any] = None) -> WorkerResponse:
        """
        Execute the market analysis workflow.
        
        Args:
            company: Company name (unused, symbol comes from context)
            context: Optional context containing 'symbol' or 'ticker'
            
        Returns:
            WorkerResponse with market analysis
        """
        # Get symbol from context or use company as fallback
        context = context or {}
        symbol = context.get("symbol") or context.get("ticker") or company
        
        try:
            # Validate input
            input_data = MarketAgentInput(symbol=symbol.upper())
            
            # Get market data from REAL providers
            market_data = await get_real_market_data(input_data.symbol)
            
            if market_data is None:
                return WorkerResponse(
                    status="error",
                    error=f"Failed to fetch market data for {input_data.symbol}",
                    data=None,
                    usage=None
                )
            
            # Build analysis using LLM
            analysis = await self._analyze_market_data(market_data, context)
            
            # Create output
            output = MarketAgentOutput(
                symbol=market_data.symbol,
                company_name=market_data.company_name,
                current_price=market_data.current_price,
                price_change=market_data.price_change,
                price_change_pct=market_data.price_change_pct,
                week_52_high=market_data.week_52_high,
                week_52_low=market_data.week_52_low,
                avg_volume=market_data.avg_volume,
                price_movement=analysis["price_movement"],
                technical_analysis=analysis["technical_analysis"],
                financial_analysis=analysis["financial_analysis"],
                market_trends=analysis["market_trends"],
                overall_narrative=analysis["overall_narrative"],
                confidence=analysis["confidence"],
            )
            
            return WorkerResponse(
                status="success",
                data=output.model_dump(),
                usage=None  # Would be populated from LLM response
            )
            
        except Exception as e:
            return WorkerResponse(
                status="error",
                error=f"Market agent failed: {str(e)}",
                data=None,
                usage=None
            )
    
    async def _analyze_market_data(
        self, 
        data: CompleteMarketData, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze market data using LLM prompts."""
        
        # Calculate percentage in 52-week range
        range_width = data.week_52_high - data.week_52_low
        if range_width > 0:
            pct_in_range = ((data.current_price - data.week_52_low) / range_width) * 100
        else:
            pct_in_range = 50.0
        
        # Price Movement Analysis
        price_prompt = PRICE_MOVEMENT_PROMPT.format(
            current_price=data.current_price,
            price_change=data.price_change,
            price_change_pct=data.price_change_pct,
            week_52_high=data.week_52_high,
            week_52_low=data.week_52_low,
            current_volume=data.price_data[-1].volume if data.price_data else data.avg_volume,
            avg_volume=data.avg_volume,
            pct_in_range=pct_in_range,
        )
        
        # Technical Analysis
        ti = data.technical_indicators
        tech_prompt = TECHNICAL_PROMPT.format(
            rsi_14=ti.rsi_14 if ti.rsi_14 is not None else "N/A",
            sma_20=ti.sma_20 if ti.sma_20 is not None else "N/A",
            sma_50=ti.sma_50 if ti.sma_50 is not None else "N/A",
            sma_200=ti.sma_200 if ti.sma_200 is not None else "N/A",
            macd=ti.macd if ti.macd is not None else "N/A",
            macd_signal=ti.macd_signal if ti.macd_signal is not None else "N/A",
            macd_histogram=ti.macd_histogram if ti.macd_histogram is not None else "N/A",
            bollinger_upper=ti.bollinger_upper if ti.bollinger_upper is not None else "N/A",
            bollinger_middle=ti.bollinger_middle if ti.bollinger_middle is not None else "N/A",
            bollinger_lower=ti.bollinger_lower if ti.bollinger_lower is not None else "N/A",
            current_price=data.current_price,
        )
        
        # Financial Analysis
        fm = data.financial_metrics
        fin_prompt = FINANCIAL_PROMPT.format(
            pe_ratio=fm.pe_ratio if fm.pe_ratio is not None else "N/A",
            forward_pe=fm.forward_pe if fm.forward_pe is not None else "N/A",
            peg_ratio=fm.peg_ratio if fm.peg_ratio is not None else "N/A",
            pb_ratio=fm.pb_ratio if fm.pb_ratio is not None else "N/A",
            ps_ratio=fm.ps_ratio if fm.ps_ratio is not None else "N/A",
            eps=fm.eps if fm.eps is not None else "N/A",
            eps_growth=fm.eps_growth if fm.eps_growth is not None else 0,
            revenue=fm.revenue if fm.revenue is not None else 0,
            revenue_growth=fm.revenue_growth if fm.revenue_growth is not None else 0,
            profit_margin=fm.profit_margin if fm.profit_margin is not None else 0,
            operating_margin=fm.operating_margin if fm.operating_margin is not None else 0,
            roe=fm.roe if fm.roe is not None else 0,
            roa=fm.roa if fm.roa is not None else 0,
            debt_to_equity=fm.debt_to_equity if fm.debt_to_equity is not None else "N/A",
            current_ratio=fm.current_ratio if fm.current_ratio is not None else "N/A",
            dividend_yield=fm.dividend_yield if fm.dividend_yield is not None else 0,
            beta=fm.beta if fm.beta is not None else "N/A",
            current_price=data.current_price,
        )
        
        # Market Trends
        mc = data.market_context
        stock_perf = ((data.current_price / data.price_data[-30].close) - 1) if len(data.price_data) >= 30 else 0
        market_prompt = MARKET_TRENDS_PROMPT.format(
            sector=mc.sector,
            industry=mc.industry,
            sector_performance_1m=mc.sector_performance_1m if mc.sector_performance_1m is not None else 0,
            sector_performance_3m=mc.sector_performance_3m if mc.sector_performance_3m is not None else 0,
            market_cap=mc.market_cap if mc.market_cap is not None else 0,
            shares_outstanding=mc.shares_outstanding if mc.shares_outstanding is not None else 0,
            float_shares=mc.float_shares if mc.float_shares is not None else 0,
            short_interest=mc.short_interest if mc.short_interest is not None else 0,
            institutional_ownership=mc.institutional_ownership if mc.institutional_ownership is not None else 0,
            analyst_rating=mc.analyst_rating if mc.analyst_rating is not None else "N/A",
            analyst_target_price=mc.analyst_target_price if mc.analyst_target_price is not None else "N/A",
            beta=mc.beta if mc.beta is not None else 1.0,
        )
        
        # Call LLM for each analysis section
        # Using a single call with structured prompts for efficiency
        combined_prompt = f"""
{SYSTEM_PROMPT}

Analyze the following market data for {data.symbol} ({data.company_name}):

=== PRICE MOVEMENT ===
{price_prompt}

=== TECHNICAL INDICATORS ===
{tech_prompt}

=== FINANCIAL METRICS ===
{fin_prompt}

=== MARKET CONTEXT ===
{market_prompt}

=== OVERALL SYNTHESIS ===
{OVERALL_NARRATIVE_PROMPT}
"""
        
        response_schema = {
            "type": "object",
            "properties": {
                "price_movement": {
                    "type": "object",
                    "properties": {
                        "trend_direction": {"type": "string", "enum": ["bullish", "bearish", "neutral", "sideways"]},
                        "position_in_range": {"type": "string", "enum": ["near_high", "near_low", "middle", "above_high", "below_low"]},
                        "volume_trend": {"type": "string", "enum": ["increasing", "decreasing", "stable"]},
                        "key_observations": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["trend_direction", "position_in_range", "volume_trend", "key_observations"]
                },
                "technical_analysis": {
                    "type": "object",
                    "properties": {
                        "rsi_interpretation": {"type": "string"},
                        "moving_averages": {"type": "string"},
                        "macd_interpretation": {"type": "string"},
                        "bollinger_bands": {"type": "string"},
                        "overall_signal": {"type": "string", "enum": ["bullish", "bearish", "neutral"]}
                    },
                    "required": ["rsi_interpretation", "moving_averages", "macd_interpretation", "bollinger_bands", "overall_signal"]
                },
                "financial_analysis": {
                    "type": "object",
                    "properties": {
                        "valuation_assessment": {"type": "string", "enum": ["overvalued", "fairly_valued", "undervalued", "insufficient_data"]},
                        "profitability": {"type": "string", "enum": ["strong", "moderate", "weak", "insufficient_data"]},
                        "growth_profile": {"type": "string", "enum": ["high_growth", "moderate_growth", "slow_growth", "declining", "insufficient_data"]},
                        "financial_health": {"type": "string", "enum": ["strong", "adequate", "concerning", "insufficient_data"]},
                        "key_observations": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["valuation_assessment", "profitability", "growth_profile", "financial_health", "key_observations"]
                },
                "market_trends": {
                    "type": "object",
                    "properties": {
                        "sector_performance": {"type": "string", "enum": ["outperforming", "in_line", "underperforming"]},
                        "relative_strength": {"type": "string", "enum": ["strong", "neutral", "weak"]},
                        "institutional_sentiment": {"type": "string", "enum": ["bullish", "neutral", "bearish"]},
                        "analyst_sentiment": {"type": "string", "enum": ["bullish", "neutral", "bearish"]},
                        "key_observations": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["sector_performance", "relative_strength", "institutional_sentiment", "analyst_sentiment", "key_observations"]
                },
                "overall_narrative": {"type": "string"},
                "confidence": {"type": "string", "enum": ["High", "Medium", "Low"]}
            },
            "required": ["price_movement", "technical_analysis", "financial_analysis", "market_trends", "overall_narrative", "confidence"]
        }
        
        try:
            result = self.llm_provider.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_message=combined_prompt,
                response_schema=response_schema,
                model=self.model,
            )
            
            content = result.get("content", {})
            
            # Validate and return
            return {
                "price_movement": PriceMovementAnalysis(**content["price_movement"]),
                "technical_analysis": TechnicalAnalysis(**content["technical_analysis"]),
                "financial_analysis": FinancialAnalysis(**content["financial_analysis"]),
                "market_trends": MarketTrendsAnalysis(**content["market_trends"]),
                "overall_narrative": content["overall_narrative"],
                "confidence": content["confidence"],
            }
            
        except Exception as e:
            # Fallback analysis if LLM fails
            return self._fallback_analysis(data, pct_in_range, stock_perf)
    
    def _fallback_analysis(self, data: CompleteMarketData, pct_in_range: float, stock_perf: float) -> Dict[str, Any]:
        """Provide fallback analysis when LLM is unavailable."""
        
        # Price movement
        if data.price_change_pct > 2:
            trend = "bullish"
        elif data.price_change_pct < -2:
            trend = "bearish"
        elif data.price_change_pct > 0.5:
            trend = "neutral"
        else:
            trend = "sideways"
        
        if pct_in_range > 80:
            position = "near_high"
        elif pct_in_range < 20:
            position = "near_low"
        else:
            position = "middle"
        
        # Technical
        ti = data.technical_indicators
        rsi_interp = "N/A"
        if ti.rsi_14:
            if ti.rsi_14 > 70:
                rsi_interp = f"RSI at {ti.rsi_14:.1f} indicates overbought conditions"
            elif ti.rsi_14 < 30:
                rsi_interp = f"RSI at {ti.rsi_14:.1f} indicates oversold conditions"
            else:
                rsi_interp = f"RSI at {ti.rsi_14:.1f} indicates neutral momentum"
        
        ma_interp = "N/A"
        if ti.sma_50 and ti.sma_200:
            if data.current_price > ti.sma_50 > ti.sma_200:
                ma_interp = "Price above both SMA50 and SMA200 - bullish alignment"
            elif data.current_price < ti.sma_50 < ti.sma_200:
                ma_interp = "Price below both SMA50 and SMA200 - bearish alignment"
            else:
                ma_interp = "Mixed moving average signals"
        
        macd_interp = "N/A"
        if ti.macd and ti.macd_signal:
            if ti.macd > ti.macd_signal:
                macd_interp = "MACD above signal line - bullish momentum"
            else:
                macd_interp = "MACD below signal line - bearish momentum"
        
        bb_interp = "N/A"
        if ti.bollinger_upper and ti.bollinger_lower:
            if data.current_price > ti.bollinger_upper:
                bb_interp = "Price above upper Bollinger Band - potential overextension"
            elif data.current_price < ti.bollinger_lower:
                bb_interp = "Price below lower Bollinger Band - potential oversold"
            else:
                bb_interp = "Price within Bollinger Bands - normal range"
        
        overall_tech = "neutral"
        if rsi_interp != "N/A" and "overbought" not in rsi_interp and "oversold" not in rsi_interp:
            if "bullish" in (ma_interp or "") or "bullish" in (macd_interp or ""):
                overall_tech = "bullish"
            elif "bearish" in (ma_interp or "") or "bearish" in (macd_interp or ""):
                overall_tech = "bearish"
        
        # Financial
        fm = data.financial_metrics
        val = "insufficient_data"
        if fm.pe_ratio and fm.peg_ratio:
            if fm.pe_ratio > 35 and fm.peg_ratio > 2:
                val = "overvalued"
            elif fm.pe_ratio < 20 and fm.peg_ratio < 1:
                val = "undervalued"
            else:
                val = "fairly_valued"
        
        prof = "insufficient_data"
        if fm.profit_margin and fm.roe:
            if fm.profit_margin > 0.20 and fm.roe > 0.25:
                prof = "strong"
            elif fm.profit_margin > 0.10 and fm.roe > 0.15:
                prof = "moderate"
            else:
                prof = "weak"
        
        growth = "insufficient_data"
        if fm.revenue_growth and fm.eps_growth:
            if fm.revenue_growth > 0.20 and fm.eps_growth > 0.20:
                growth = "high_growth"
            elif fm.revenue_growth > 0.05:
                growth = "moderate_growth"
            elif fm.revenue_growth > 0:
                growth = "slow_growth"
            else:
                growth = "declining"
        
        health = "insufficient_data"
        if fm.debt_to_equity and fm.current_ratio:
            if fm.debt_to_equity < 0.5 and fm.current_ratio > 1.5:
                health = "strong"
            elif fm.debt_to_equity < 1.0 and fm.current_ratio > 1.0:
                health = "adequate"
            else:
                health = "concerning"
        
        # Market trends
        mc = data.market_context
        sector_perf = "in_line"
        if mc.sector_performance_1m and stock_perf:
            if stock_perf > mc.sector_performance_1m + 0.02:
                sector_perf = "outperforming"
            elif stock_perf < mc.sector_performance_1m - 0.02:
                sector_perf = "underperforming"
        
        rel_strength = "neutral"
        if mc.beta:
            if mc.beta > 1.3:
                rel_strength = "strong"
            elif mc.beta < 0.8:
                rel_strength = "weak"
        
        inst_sentiment = "neutral"
        if mc.institutional_ownership:
            if mc.institutional_ownership > 0.75:
                inst_sentiment = "bullish"
            elif mc.institutional_ownership < 0.50:
                inst_sentiment = "bearish"
        
        analyst_sentiment = "neutral"
        if mc.analyst_rating:
            # analyst_rating could be a float (from Yahoo Finance recommendationMean) or string
            if isinstance(mc.analyst_rating, (int, float)):
                # Yahoo Finance: 1=Strong Buy, 2=Buy, 3=Hold, 4=Underperform, 5=Sell
                if mc.analyst_rating <= 2:
                    analyst_sentiment = "bullish"
                elif mc.analyst_rating >= 4:
                    analyst_sentiment = "bearish"
            elif isinstance(mc.analyst_rating, str):
                if "Buy" in mc.analyst_rating and "Sell" not in mc.analyst_rating:
                    analyst_sentiment = "bullish"
                elif "Sell" in mc.analyst_rating:
                    analyst_sentiment = "bearish"
        
        # Build narrative
        narrative_parts = [
            f"{data.company_name} ({data.symbol}) trades at ${data.current_price:.2f}, "
            f"{data.price_change_pct:+.2f}% on the day, positioning it in the {position.replace('_', ' ')} "
            f"of its 52-week range (${data.week_52_low:.2f}-${data.week_52_high:.2f}).",
        ]
        
        if rsi_interp != "N/A":
            narrative_parts.append(f"Technical indicators show {rsi_interp.lower()}. {ma_interp}. {macd_interp}.")
        
        if val != "insufficient_data":
            pe_str = f"{fm.pe_ratio:.1f}" if fm.pe_ratio else "N/A"
            peg_str = f"{fm.peg_ratio:.2f}" if fm.peg_ratio else "N/A"
            narrative_parts.append(
                f"Valuation appears {val} (P/E: {pe_str}, PEG: {peg_str}). "
                f"Profitability is {prof} with {growth.replace('_', ' ')} profile. "
                f"Financial health assessed as {health}."
            )
        
        narrative_parts.append(
            f"Sector context: {sector_perf} sector over 1M ({(mc.sector_performance_1m or 0):.1%} vs stock {stock_perf:.1%}). "
            f"Institutional sentiment {inst_sentiment}, analyst sentiment {analyst_sentiment}."
        )
        
        return {
            "price_movement": PriceMovementAnalysis(
                trend_direction=trend,
                position_in_range=position,
                volume_trend="stable",
                key_observations=[
                    f"Price change: {data.price_change_pct:+.2f}%",
                    f"52-week range position: {pct_in_range:.0f}%",
                    f"Volume vs avg: {data.price_data[-1].volume / data.avg_volume:.1f}x" if data.avg_volume else "N/A",
                ]
            ),
            "technical_analysis": TechnicalAnalysis(
                rsi_interpretation=rsi_interp,
                moving_averages=ma_interp,
                macd_interpretation=macd_interp,
                bollinger_bands=bb_interp,
                overall_signal=overall_tech,
            ),
            "financial_analysis": FinancialAnalysis(
                valuation_assessment=val,
                profitability=prof,
                growth_profile=growth,
                financial_health=health,
                key_observations=[
                    f"P/E: {fm.pe_ratio:.1f}" if fm.pe_ratio else "P/E: N/A",
                    f"Profit margin: {fm.profit_margin:.1%}" if fm.profit_margin else "N/A",
                    f"Revenue growth: {fm.revenue_growth:.1%}" if fm.revenue_growth else "N/A",
                    f"ROE: {fm.roe:.1%}" if fm.roe else "N/A",
                    f"Debt/Equity: {fm.debt_to_equity:.2f}" if fm.debt_to_equity else "N/A",
                ]
            ),
            "market_trends": MarketTrendsAnalysis(
                sector_performance=sector_perf,
                relative_strength=rel_strength,
                institutional_sentiment=inst_sentiment,
                analyst_sentiment=analyst_sentiment,
                key_observations=[
                    f"Beta: {fm.beta:.2f}" if fm.beta else "N/A",
                    f"Institutional ownership: {mc.institutional_ownership:.1%}" if mc.institutional_ownership else "N/A",
                    f"Analyst rating: {mc.analyst_rating}" if mc.analyst_rating else "N/A",
                    f"Short interest: {mc.short_interest:.2%}" if mc.short_interest else "N/A",
                ]
            ),
            "overall_narrative": " ".join(narrative_parts),
            "confidence": "Medium",
        }


# Synchronous wrapper for testing
def run_market_agent_sync(llm_provider: LLMProvider, symbol: str) -> Dict[str, Any]:
    """Synchronous wrapper for the MarketAgent."""
    agent = MarketAgent(llm_provider)
    import asyncio
    return asyncio.run(agent.run(symbol))


# Legacy interface
def run(payload: dict) -> dict:
    """Legacy sync interface."""
    raise NotImplementedError("Use MarketAgent class with async run() method")