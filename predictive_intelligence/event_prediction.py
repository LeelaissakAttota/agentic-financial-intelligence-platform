"""
Event Prediction
Predicts likelihood and impact of specific financial events.
"""

import asyncio
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventCategory(str, Enum):
    """Categories of predictable events."""
    EARNINGS = "earnings"                 # Earnings announcements
    MERGERS = "mergers"                   # M&A announcements
    DIVIDENDS = "dividends"               # Dividend changes
    SPLITS = "splits"                     # Stock splits
    BUYBACKS = "buybacks"                 # Share buybacks
    GUIDANCE = "guidance"                 # Guidance changes
    REGULATORY = "regulatory"             # Regulatory decisions
    MACRO = "macro"                       # Macro data releases
    CENTRAL_BANK = "central_bank"         # Central bank decisions
    GEOPOLITICAL = "geopolitical"         # Geopolitical events
    PRODUCT_LAUNCH = "product_launch"     # Product launches
    MANAGEMENT_CHANGE = "management_change"  # CEO/CFO changes
    ANALYST_ACTION = "analyst_action"     # Rating changes
    SHORT_SQUEEZE = "short_squeeze"       # Short squeeze potential
    INSIDER_TRADING = "insider_trading"   # Insider activity


class PredictionHorizon(str, Enum):
    """Prediction time horizons."""
    IMMEDIATE = "immediate"    # 0-1 days
    SHORT = "short"            # 1-7 days
    MEDIUM = "medium"          # 1-4 weeks
    LONG = "long"              # 1-3 months


@dataclass
class EventPredictionResult:
    """Result of event prediction."""
    event_id: str
    category: EventCategory
    symbol: str
    predicted_date: Optional[datetime]
    probability: float
    confidence: float
    horizon: PredictionHorizon
    expected_impact: float  # Expected price impact %
    impact_direction: str  # "positive", "negative", "uncertain"
    key_factors: List[str]
    historical_accuracy: float
    similar_events: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EventSignal:
    """Signal indicating potential event."""
    signal_id: str
    category: EventCategory
    symbol: str
    signal_strength: float  # 0-1
    description: str
    supporting_evidence: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventPrediction:
    """
    Predicts likelihood and timing of specific financial events.
    Uses pattern recognition, news analysis, and historical patterns.
    """
    
    def __init__(self):
        self._event_models: Dict[EventCategory, Any] = {}
        self._event_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._active_signals: Dict[str, EventSignal] = {}
        self._pattern_library: Dict[str, Any] = {}
    
    async def initialize(self) -> None:
        """Initialize event prediction system."""
        logger.info("Event prediction system initialized")
        await self._load_patterns()
    
    async def _load_patterns(self) -> None:
        """Load historical event patterns."""
        # In production, would load from database
        self._pattern_library = {
            EventCategory.EARNINGS: {
                "pre_earnings_drift": 0.65,
                "post_earnings_drift": 0.45,
                "surprise_correlation": 0.72
            },
            EventCategory.MERGERS: {
                "rumor_premium": 0.15,
                "announcement_pop": 0.25,
                "deal_completion_rate": 0.75
            },
            EventCategory.DIVIDENDS: {
                "increase_signal": 0.80,
                "cut_signal": -0.15,
                "initiation_pop": 0.05
            }
        }
        logger.info("Event patterns loaded")
    
    def register_event_model(self, category: EventCategory, model: Any) -> None:
        """Register a custom event prediction model."""
        self._event_models[category] = model
        logger.info(f"Registered event model for {category.value}")
    
    async def predict_event(
        self,
        category: EventCategory,
        symbol: str,
        market_data: Dict[str, Any],
        news_data: Optional[List[Dict[str, Any]]] = None,
        fundamental_data: Optional[Dict[str, Any]] = None
    ) -> EventPredictionResult:
        """Predict likelihood of a specific event."""
        
        logger.info(f"Predicting {category.value} for {symbol}")
        
        # Get relevant signals
        signals = await self._detect_signals(category, symbol, market_data, news_data, fundamental_data)
        
        # Calculate probability
        probability = await self._calculate_probability(category, symbol, signals, market_data)
        
        # Determine predicted date
        predicted_date = await self._predict_timing(category, symbol, signals, market_data)
        
        # Estimate impact
        impact = await self._estimate_impact(category, symbol, signals, market_data)
        
        # Get historical accuracy
        accuracy = self._get_historical_accuracy(category, symbol)
        
        # Find similar historical events
        similar = await self._find_similar_events(category, symbol, signals)
        
        result = EventPredictionResult(
            event_id=f"evt_{category.value}_{symbol}_{datetime.utcnow().timestamp()}",
            category=category,
            symbol=symbol,
            predicted_date=predicted_date,
            probability=probability,
            confidence=self._calculate_confidence(signals, market_data),
            horizon=self._determine_horizon(predicted_date),
            expected_impact=impact["magnitude"],
            impact_direction=impact["direction"],
            key_factors=[s.description for s in signals[:3]],
            historical_accuracy=accuracy,
            similar_events=similar,
            metadata={
                "signals_count": len(signals),
                "signal_strengths": [s.signal_strength for s in signals],
                "market_regime": market_data.get("regime", "unknown")
            }
        )
        
        # Store signal for tracking
        for signal in signals:
            self._active_signals[signal.signal_id] = signal
        
        return result
    
    async def _detect_signals(
        self,
        category: EventCategory,
        symbol: str,
        market_data: Dict[str, Any],
        news_data: Optional[List[Dict[str, Any]]],
        fundamental_data: Optional[Dict[str, Any]]
    ) -> List[EventSignal]:
        """Detect signals for a specific event category."""
        
        signals = []
        
        # Category-specific signal detection
        if category == EventCategory.EARNINGS:
            signals.extend(await self._detect_earnings_signals(symbol, market_data, news_data, fundamental_data))
        elif category == EventCategory.MERGERS:
            signals.extend(await self._detect_merger_signals(symbol, market_data, news_data))
        elif category == EventCategory.DIVIDENDS:
            signals.extend(await self._detect_dividend_signals(symbol, market_data, fundamental_data))
        elif category == EventCategory.MERGERS:
            signals.extend(await self._detect_merger_signals(symbol, market_data, news_data))
        elif category == EventCategory.GUIDANCE:
            signals.extend(await self._detect_guidance_signals(symbol, market_data, news_data))
        elif category == EventCategory.ANALYST_ACTION:
            signals.extend(await self._detect_analyst_signals(symbol, market_data, news_data))
        elif category == EventCategory.SHORT_SQUEEZE:
            signals.extend(await self._detect_short_squeeze_signals(symbol, market_data))
        elif category == EventCategory.MANAGEMENT_CHANGE:
            signals.extend(await self._detect_management_signals(symbol, news_data))
        elif category == EventCategory.PRODUCT_LAUNCH:
            signals.extend(await self._detect_product_launch_signals(symbol, news_data))
        elif category == EventCategory.REGULATORY:
            signals.extend(await self._detect_regulatory_signals(symbol, news_data))
        elif category == EventCategory.CENTRAL_BANK:
            signals.extend(await self._detect_central_bank_signals(market_data))
        
        return signals
    
    async def _detect_earnings_signals(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        news_data: Optional[List[Dict[str, Any]]],
        fundamental_data: Optional[Dict[str, Any]]
    ) -> List[EventSignal]:
        """Detect earnings-related signals."""
        
        signals = []
        
        # Check earnings date proximity
        if fundamental_data and "next_earnings_date" in fundamental_data:
            earnings_date = fundamental_data["next_earnings_date"]
            if isinstance(earnings_date, str):
                earnings_date = datetime.fromisoformat(earnings_date)
            
            days_until = (earnings_date - datetime.utcnow()).days
            
            if 0 <= days_until <= 7:
                signals.append(EventSignal(
                    signal_id=f"earn_date_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.EARNINGS,
                    symbol=symbol,
                    signal_strength=0.9,
                    description=f"Earnings in {days_until} days",
                    supporting_evidence=[f"Confirmed earnings date: {earnings_date.strftime('%Y-%m-%d')}"]
                ))
            elif 8 <= days_until <= 30:
                signals.append(EventSignal(
                    signal_id=f"earn_approaching_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.EARNINGS,
                    symbol=symbol,
                    signal_strength=0.6,
                    description=f"Earnings in {days_until} days",
                    supporting_evidence=[f"Earnings date: {earnings_date.strftime('%Y-%m-%d')}"]
                ))
        
        # Pre-earnings drift
        if "pre_earnings_return" in market_data:
            pre_return = market_data["pre_earnings_return"]
            if abs(pre_return) > 0.05:
                signals.append(EventSignal(
                    signal_id=f"earn_drift_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.EARNINGS,
                    symbol=symbol,
                    signal_strength=min(abs(pre_return) * 10, 0.8),
                    description=f"Pre-earnings drift: {pre_return:.1%}",
                    supporting_evidence=[f"Stock moved {pre_return:.1%} in pre-earnings period"]
                ))
        
        # Analyst estimate revisions
        if fundamental_data and "estimate_revisions" in fundamental_data:
            revisions = fundamental_data["estimate_revisions"]
            if revisions.get("upward", 0) > revisions.get("downward", 0) * 2:
                signals.append(EventSignal(
                    signal_id=f"earn_revision_up_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.EARNINGS,
                    symbol=symbol,
                    signal_strength=0.7,
                    description="Positive analyst estimate revisions",
                    supporting_evidence=[f"Upward: {revisions.get('upward', 0)}, Downward: {revisions.get('downward', 0)}"]
                ))
        
        # Options implied volatility
        if "iv_rank" in market_data:
            iv_rank = market_data["iv_rank"]
            if iv_rank > 80:
                signals.append(EventSignal(
                    signal_id=f"earn_iv_high_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.EARNINGS,
                    symbol=symbol,
                    signal_strength=0.6,
                    description=f"High implied volatility rank: {iv_rank}",
                    supporting_evidence=["Elevated IV suggests expected large move"]
                ))
        
        # News sentiment
        if news_data:
            earnings_news = [n for n in news_data if "earning" in n.get("title", "").lower() or "earning" in n.get("content", "").lower()]
            if len(earnings_news) > 3:
                avg_sentiment = np.mean([n.get("sentiment", 0) for n in earnings_news])
                signals.append(EventSignal(
                    signal_id=f"earn_sentiment_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.EARNINGS,
                    symbol=symbol,
                    signal_strength=abs(avg_sentiment) * 0.7,
                    description=f"Earnings news sentiment: {avg_sentiment:.2f}",
                    supporting_evidence=[f"{len(earnings_news)} earnings-related articles"]
                ))
        
        return signals
    
    async def _detect_merger_signals(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        news_data: Optional[List[Dict[str, Any]]]
    ) -> List[EventSignal]:
        """Detect M&A signals."""
        
        signals = []
        
        # Volume spike
        if "volume_ratio" in market_data and market_data["volume_ratio"] > 3:
            signals.append(EventSignal(
                signal_id=f"mna_volume_{symbol}_{datetime.utcnow().timestamp()}",
                category=EventCategory.MERGERS,
                symbol=symbol,
                signal_strength=0.7,
                description=f"Unusual volume: {market_data['volume_ratio']:.1f}x average",
                supporting_evidence=["Potential accumulation or leak"]
            ))
        
        # Price gap
        if "gap_up" in market_data and market_data["gap_up"] > 0.05:
            signals.append(EventSignal(
                signal_id=f"mna_gap_{symbol}_{datetime.utcnow().timestamp()}",
                category=EventCategory.MERGERS,
                symbol=symbol,
                signal_strength=0.8,
                description=f"Large gap up: {market_data['gap_up']:.1%}",
                supporting_evidence=["Potential buyout premium"]
            ))
        
        # News keywords
        if news_data:
            mna_keywords = ["merger", "acquisition", "buyout", "takeover", "bid", "offer"]
            mna_news = [n for n in news_data if any(kw in n.get("title", "").lower() or n.get("content", "").lower() for kw in mna_keywords)]
            
            if mna_news:
                avg_sentiment = np.mean([n.get("sentiment", 0) for n in mna_news])
                signals.append(EventSignal(
                    signal_id=f"mna_news_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.MERGERS,
                    symbol=symbol,
                    signal_strength=min(0.9, 0.5 + len(mna_news) * 0.1),
                    description=f"M&A rumors in news: {len(mna_news)} articles",
                    supporting_evidence=[f"Avg sentiment: {np.mean([n.get('sentiment', 0) for n in mna_news]):.2f}"]
                ))
        
        # Short interest drop (covering)
        if "short_interest_change" in market_data and market_data["short_interest_change"] < -0.2:
            signals.append(EventSignal(
                signal_id=f"mna_short_cover_{symbol}_{datetime.utcnow().timestamp()}",
                category=EventCategory.MERGERS,
                symbol=symbol,
                signal_strength=0.6,
                description=f"Short interest dropped {abs(market_data['short_interest_change']):.1%}",
                supporting_evidence=["Potential short covering on deal news"]
            ))
        
        return signals
    
    async def _detect_dividend_signals(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        fundamental_data: Optional[Dict[str, Any]]
    ) -> List[EventSignal]:
        """Detect dividend change signals."""
        
        signals = []
        
        if not fundamental_data:
            return signals
        
        # Payout ratio trends
        if "payout_ratio" in fundamental_data:
            payout = fundamental_data["payout_ratio"]
            if payout > 0.8:
                signals.append(EventSignal(
                    signal_id=f"div_cut_risk_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.DIVIDENDS,
                    symbol=symbol,
                    signal_strength=0.7,
                    description=f"High payout ratio: {payout:.0%}",
                    supporting_evidence=["Dividend cut risk elevated"]
                ))
            elif payout < 0.3 and "dividend_history" in fundamental_data:
                hist = fundamental_data["dividend_history"]
                if len(hist) >= 4 and all(h["increase"] for h in hist[-4:]):
                    signals.append(EventSignal(
                        signal_id=f"div_increase_{symbol}_{datetime.utcnow().timestamp()}",
                        category=EventCategory.DIVIDENDS,
                        symbol=symbol,
                        signal_strength=0.8,
                        description="Strong dividend growth history with low payout",
                        supporting_evidence=["4+ consecutive increases", "Room for further increases"]
                    ))
        
        # Free cash flow coverage
        if "fcf_coverage" in fundamental_data:
            coverage = fundamental_data["fcf_coverage"]
            if coverage > 2.0:
                signals.append(EventSignal(
                    signal_id=f"div_fcf_strong_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.DIVIDENDS,
                    symbol=symbol,
                    signal_strength=0.6,
                    description=f"Strong FCF coverage: {coverage:.1f}x",
                    supporting_evidence=["Dividend well covered by free cash flow"]
                ))
        
        return signals
    
    async def _detect_guidance_signals(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        news_data: Optional[List[Dict[str, Any]]]
    ) -> List[EventSignal]:
        """Detect guidance change signals."""
        
        signals = []
        
        if news_data:
            guidance_keywords = ["guidance", "outlook", "forecast", "expects", "sees", "projects"]
            guidance_news = [n for n in news_data if any(kw in n.get("title", "").lower() for kw in guidance_keywords)]
            
            if guidance_news:
                for n in guidance_news:
                    content = (n.get("title", "") + " " + n.get("content", "")).lower()
                    
                    if any(kw in content for kw in ["raise", "increase", "higher", "upgrad"]):
                        signals.append(EventSignal(
                            signal_id=f"guide_up_{symbol}_{datetime.utcnow().timestamp()}",
                            category=EventCategory.GUIDANCE,
                            symbol=symbol,
                            signal_strength=0.8,
                            description="Positive guidance revision detected",
                            supporting_evidence=[n.get("title", "")[:200]]
                        ))
                    elif any(kw in content for kw in ["lower", "cut", "reduce", "down"]):
                        signals.append(EventSignal(
                            signal_id=f"guide_down_{symbol}_{datetime.utcnow().timestamp()}",
                            category=EventCategory.GUIDANCE,
                            symbol=symbol,
                            signal_strength=0.8,
                            description="Negative guidance revision detected",
                            supporting_evidence=[n.get("title", "")[:200]]
                        ))
        
        return signals
    
    async def _detect_analyst_signals(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        news_data: Optional[List[Dict[str, Any]]]
    ) -> List[EventSignal]:
        """Detect analyst action signals."""
        
        signals = []
        
        if "analyst_actions" in market_data:
            actions = market_data["analyst_actions"]
            
            upgrades = sum(1 for a in actions if a.get("action") == "upgrade")
            downgrades = sum(1 for a in actions if a.get("action") == "downgrade")
            
            if upgrades > downgrades * 2:
                signals.append(EventSignal(
                    signal_id=f"analyst_up_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.ANALYST_ACTION,
                    symbol=symbol,
                    signal_strength=min(0.8, 0.4 + upgrades * 0.1),
                    description=f"Analyst upgrades: {upgrades} vs {downgrades} downgrades",
                    supporting_evidence=[f"Net upgrades: {upgrades - downgrades}"]
                ))
            elif downgrades > upgrades * 2:
                signals.append(EventSignal(
                    signal_id=f"analyst_down_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.ANALYST_ACTION,
                    symbol=symbol,
                    signal_strength=min(0.8, 0.4 + downgrades * 0.1),
                    description=f"Analyst downgrades: {downgrades} vs {upgrades} upgrades",
                    supporting_evidence=[f"Net downgrades: {downgrades - upgrades}"]
                ))
        
        return signals
    
    async def _detect_short_squeeze_signals(
        self,
        symbol: str,
        market_data: Dict[str, Any]
    ) -> List[EventSignal]:
        """Detect short squeeze potential."""
        
        signals = []
        
        # High short interest
        if "short_interest" in market_data:
            si = market_data["short_interest"]
            if si > 0.20:  # 20%+ of float
                signals.append(EventSignal(
                    signal_id=f"squeeze_si_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.SHORT_SQUEEZE,
                    symbol=symbol,
                    signal_strength=min(0.9, si * 3),
                    description=f"High short interest: {si:.1%} of float",
                    supporting_evidence=[f"Days to cover: {market_data.get('days_to_cover', 'N/A')}"]
                ))
        
        # Days to cover
        if "days_to_cover" in market_data:
            dtc = market_data["days_to_cover"]
            if dtc > 5:
                signals.append(EventSignal(
                    signal_id=f"squeeze_dtc_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.SHORT_SQUEEZE,
                    symbol=symbol,
                    signal_strength=min(0.8, dtc / 10),
                    description=f"High days to cover: {dtc:.1f}",
                    supporting_evidence=["Shorts would need many days to cover"]
                ))
        
        # Price momentum + high SI
        if "short_interest" in market_data and "momentum" in market_data:
            si = market_data["short_interest"]
            mom = market_data["momentum"]
            if si > 0.15 and mom > 0.10:
                signals.append(EventSignal(
                    signal_id=f"squeeze_momentum_{symbol}_{datetime.utcnow().timestamp()}",
                    category=EventCategory.SHORT_SQUEEZE,
                    symbol=symbol,
                    signal_strength=0.85,
                    description="Short squeeze in progress: high SI + positive momentum",
                    supporting_evidence=[f"SI: {si:.1%}, Momentum: {mom:.1%}"]
                ))
        
        return signals
    
    async def _detect_management_signals(
        self,
        symbol: str,
        news_data: Optional[List[Dict[str, Any]]]
    ) -> List[EventSignal]:
        """Detect management change signals."""
        
        signals = []
        
        if news_data:
            mgmt_keywords = ["ceo", "cfo", "president", "chairman", "executive", "resign", "retire", "depart", "appoint", "hire"]
            mgmt_news = [n for n in news_data if any(kw in n.get("title", "").lower() for kw in mgmt_keywords)]
            
            if mgmt_news:
                for n in mgmt_news:
                    content = n.get("title", "").lower()
                    if any(kw in content for kw in ["resign", "retire", "depart", "leave"]):
                        signals.append(EventSignal(
                            signal_id=f"mgmt_depart_{symbol}_{datetime.utcnow().timestamp()}",
                            category=EventCategory.MANAGEMENT_CHANGE,
                            symbol=symbol,
                            signal_strength=0.8,
                            description="Executive departure announced",
                            supporting_evidence=[n.get("title", "")[:200]]
                        ))
                    elif any(kw in content for kw in ["appoint", "hire", "name", "select"]):
                        signals.append(EventSignal(
                            signal_id=f"mgmt_appoint_{symbol}_{datetime.utcnow().timestamp()}",
                            category=EventCategory.MANAGEMENT_CHANGE,
                            symbol=symbol,
                            signal_strength=0.7,
                            description="New executive appointment",
                            supporting_evidence=[n.get("title", "")[:200]]
                        ))
        
        return signals
    
    async def _detect_product_launch_signals(
        self,
        symbol: str,
        news_data: Optional[List[Dict[str, Any]]]
    ) -> List[EventSignal]:
        """Detect product launch signals."""
        
        signals = []
        
        if news_data:
            launch_keywords = ["launch", "unveil", "introduce", "release", "debut", "new product", "new service"]
            launch_news = [n for n in news_data if any(kw in n.get("title", "").lower() for kw in launch_keywords)]
            
            if launch_news:
                for n in launch_news:
                    signals.append(EventSignal(
                        signal_id=f"launch_{symbol}_{datetime.utcnow().timestamp()}",
                        category=EventCategory.PRODUCT_LAUNCH,
                        symbol=symbol,
                        signal_strength=0.7,
                        description="Product/service launch announced",
                        supporting_evidence=[n.get("title", "")[:200]]
                    ))
        
        return signals
    
    async def _detect_regulatory_signals(
        self,
        symbol: str,
        news_data: Optional[List[Dict[str, Any]]]
    ) -> List[EventSignal]:
        """Detect regulatory action signals."""
        
        signals = []
        
        if news_data:
            reg_keywords = ["sec", "fda", "ftc", "doj", "regulatory", "investigation", "probe", "fine", "penalty", "compliance", "approval", "clearance"]
            reg_news = [n for n in news_data if any(kw in n.get("title", "").lower() or n.get("content", "").lower() for kw in reg_keywords)]
            
            if reg_news:
                for n in reg_news:
                    content = (n.get("title", "") + " " + n.get("content", "")).lower()
                    if any(kw in content for kw in ["investigation", "probe", "fine", "penalty", "lawsuit"]):
                        severity = 0.9
                        desc = "Regulatory investigation or enforcement action"
                    elif any(kw in content for kw in ["approval", "clearance", "authorized"]):
                        severity = 0.7
                        desc = "Regulatory approval received"
                    else:
                        severity = 0.6
                        desc = "Regulatory news"
                    
                    signals.append(EventSignal(
                        signal_id=f"reg_{symbol}_{datetime.utcnow().timestamp()}",
                        category=EventCategory.REGULATORY,
                        symbol=symbol,
                        signal_strength=severity,
                        description=desc,
                        supporting_evidence=[n.get("title", "")[:200]]
                    ))
        
        return signals
    
    async def _detect_central_bank_signals(
        self,
        market_data: Dict[str, Any]
    ) -> List[EventSignal]:
        """Detect central bank policy signals."""
        
        signals = []
        
        if "fed_decision" in market_data:
            decision = market_data["fed_decision"]
            if decision != "unchanged":
                signals.append(EventSignal(
                    signal_id=f"fed_{datetime.utcnow().timestamp()}",
                    category=EventCategory.CENTRAL_BANK,
                    symbol="MARKET",
                    signal_strength=0.8,
                    description=f"Fed {decision}",
                    supporting_evidence=[f"Rate change: {market_data.get('rate_change', 0)}bps"]
                ))
        
        if "forward_guidance" in market_data:
            signals.append(EventSignal(
                signal_id=f"fed_guidance_{datetime.utcnow().timestamp()}",
                category=EventCategory.CENTRAL_BANK,
                symbol="MARKET",
                signal_strength=0.7,
                description="Fed forward guidance updated",
                supporting_evidence=[market_data["forward_guidance"][:200]]
            ))
        
        return signals
    
    async def _calculate_probability(
        self,
        category: EventCategory,
        symbol: str,
        signals: List[EventSignal],
        market_data: Dict[str, Any]
    ) -> float:
        """Calculate event probability from signals."""
        
        if not signals:
            return 0.05  # Base rate
        
        # Weighted average of signal strengths
        total_weight = sum(s.signal_strength for s in signals)
        avg_strength = total_weight / len(signals)
        
        # Category base rates
        base_rates = {
            EventCategory.EARNINGS: 0.95,      # Very predictable
            EventCategory.DIVIDENDS: 0.70,
            EventCategory.MERGERS: 0.05,       # Rare
            EventCategory.GUIDANCE: 0.30,
            EventCategory.ANALYST_ACTION: 0.40,
            EventCategory.SHORT_SQUEEZE: 0.10,
            EventCategory.MANAGEMENT_CHANGE: 0.15,
            EventCategory.PRODUCT_LAUNCH: 0.20,
            EventCategory.REGULATORY: 0.10,
            EventCategory.CENTRAL_BANK: 0.25,
            EventCategory.MACRO: 0.50,
        }
        
        base_rate = base_rates.get(category, 0.10)
        
        # Combine base rate with signal strength
        probability = base_rate + (1 - base_rate) * avg_strength * 0.5
        
        return min(max(probability, 0.01), 0.99)
    
    async def _predict_timing(
        self,
        category: EventCategory,
        symbol: str,
        signals: List[EventSignal],
        market_data: Dict[str, Any]
    ) -> Optional[datetime]:
        """Predict event timing."""
        
        # Category-specific timing
        if category == EventCategory.EARNINGS:
            # Use confirmed earnings date if available
            pass
        
        # For now, return None (unknown timing)
        return None
    
    async def _estimate_impact(
        self,
        category: EventCategory,
        symbol: str,
        signals: List[EventSignal],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Estimate event impact magnitude and direction."""
        
        # Default impacts by category
        impacts = {
            EventCategory.EARNINGS: {"magnitude": 0.05, "direction": "uncertain"},
            EventCategory.MERGERS: {"magnitude": 0.25, "direction": "positive"},
            EventCategory.DIVIDENDS: {"magnitude": 0.02, "direction": "positive"},
            EventCategory.GUIDANCE: {"magnitude": 0.08, "direction": "uncertain"},
            EventCategory.ANALYST_ACTION: {"magnitude": 0.03, "direction": "uncertain"},
            EventCategory.SHORT_SQUEEZE: {"magnitude": 0.15, "direction": "positive"},
            EventCategory.MANAGEMENT_CHANGE: {"magnitude": 0.05, "direction": "uncertain"},
            EventCategory.PRODUCT_LAUNCH: {"magnitude": 0.05, "direction": "positive"},
            EventCategory.REGULATORY: {"magnitude": 0.10, "direction": "uncertain"},
            EventCategory.CENTRAL_BANK: {"magnitude": 0.02, "direction": "uncertain"},
        }
        
        default = impacts.get(category, {"magnitude": 0.05, "direction": "uncertain"})
        
        # Adjust based on signal strength
        if signals:
            avg_strength = sum(s.signal_strength for s in signals) / len(signals)
            default["magnitude"] *= (0.5 + avg_strength)
        
        return default
    
    def _calculate_confidence(
        self,
        signals: List[EventSignal],
        market_data: Dict[str, Any]
    ) -> float:
        """Calculate prediction confidence."""
        
        if not signals:
            return 0.1
        
        # Based on signal strength and count
        avg_strength = sum(s.signal_strength for s in signals) / len(signals)
        count_factor = min(1.0, len(signals) / 5)
        
        confidence = 0.3 + 0.4 * avg_strength + 0.3 * count_factor
        return min(max(confidence, 0.1), 0.95)
    
    def _determine_horizon(self, predicted_date: Optional[datetime]) -> PredictionHorizon:
        """Determine prediction horizon."""
        
        if not predicted_date:
            return PredictionHorizon.MEDIUM
        
        days = (predicted_date - datetime.utcnow()).days
        
        if days <= 1:
            return PredictionHorizon.IMMEDIATE
        elif days <= 7:
            return PredictionHorizon.SHORT
        elif days <= 30:
            return PredictionHorizon.MEDIUM
        else:
            return PredictionHorizon.LONG
    
    def _get_historical_accuracy(self, category: EventCategory, symbol: str) -> float:
        """Get historical prediction accuracy for category/symbol."""
        
        history = self._event_history.get(f"{category.value}_{symbol}", [])
        if not history:
            # Return category average
            category_accuracies = {
                EventCategory.EARNINGS: 0.85,
                EventCategory.MERGERS: 0.40,
                EventCategory.DIVIDENDS: 0.75,
                EventCategory.GUIDANCE: 0.65,
                EventCategory.ANALYST_ACTION: 0.60,
                EventCategory.SHORT_SQUEEZE: 0.55,
                EventCategory.MANAGEMENT_CHANGE: 0.50,
                EventCategory.PRODUCT_LAUNCH: 0.70,
                EventCategory.REGULATORY: 0.45,
                EventCategory.CENTRAL_BANK: 0.70,
            }
            return category_accuracies.get(category, 0.50)
        
        correct = sum(1 for h in history if h.get("correct", False))
        return correct / len(history)
    
    async def _find_similar_events(
        self,
        category: EventCategory,
        symbol: str,
        signals: List[EventSignal]
    ) -> List[Dict[str, Any]]:
        """Find similar historical events."""
        
        # Would search historical database
        # Return mock similar events
        similar = []
        
        if category == EventCategory.EARNINGS:
            similar.append({
                "date": "2023-10-15",
                "symbol": symbol,
                "outcome": "beat",
                "move": 0.05,
                "similarity": 0.85
            })
        elif category == EventCategory.MERGERS:
            similar.append({
                "date": "2023-05-20",
                "symbol": "TARGET",
                "outcome": "acquired",
                "premium": 0.35,
                "similarity": 0.75
            })
        
        return similar
    
    def record_outcome(
        self,
        event_id: str,
        occurred: bool,
        actual_date: Optional[datetime] = None,
        actual_impact: Optional[float] = None
    ) -> None:
        """Record actual outcome for accuracy tracking."""
        
        # Extract category and symbol from event_id
        parts = event_id.split("_")
        if len(parts) >= 3:
            category = parts[1]
            symbol = parts[2]
            
            history = self._event_history[f"{category}_{symbol}"]
            history.append({
                "event_id": event_id,
                "occurred": occurred,
                "actual_date": actual_date.isoformat() if actual_date else None,
                "actual_impact": actual_impact,
                "recorded_at": datetime.utcnow().isoformat()
            })
            
            # Keep last 100
            if len(history) > 100:
                self._event_history[f"{category}_{symbol}"] = history[-100:]
    
    def get_active_signals(self, category: Optional[EventCategory] = None) -> List[EventSignal]:
        """Get active event signals."""
        
        signals = list(self._active_signals.values())
        
        if category:
            signals = [s for s in signals if s.category == category]
        
        return sorted(signals, key=lambda s: s.signal_strength, reverse=True)
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_signals": len(self._active_signals),
            "by_category": {
                cat.value: len([s for s in self._active_signals.values() if s.category == cat])
                for cat in EventCategory
            },
            "event_history": {k: len(v) for k, v in self._event_history.items()},
            "patterns_loaded": len(self._pattern_library)
        }


# Global event prediction instance
_event_prediction: Optional[EventPrediction] = None


def get_event_prediction() -> EventPrediction:
    global _event_prediction
    if _event_prediction is None:
        _event_prediction = EventPrediction()
    return _event_prediction


async def close_event_prediction() -> None:
    global _event_prediction
    if _event_prediction:
        _event_prediction = None