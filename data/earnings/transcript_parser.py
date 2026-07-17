"""
Earnings Call Transcript Parser.

Parses earnings call transcripts to extract:
- Speaker identification
- Presentation vs Q&A sections
- Key metrics mentioned
- Guidance and forward-looking statements
- Sentiment analysis per speaker
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Speaker:
    """Speaker in an earnings call."""
    name: str
    role: str  # CEO, CFO, Operator, Analyst, etc.
    company: Optional[str] = None
    title: Optional[str] = None


@dataclass
class TranscriptSection:
    """A section of the earnings call transcript."""
    section_type: str  # presentation, qa, prepared_remarks, opening, closing
    speaker: Optional[str] = None
    text: str = ""
    start_char: int = 0
    end_char: int = 0
    timestamp: Optional[str] = None


@dataclass
class QAExchange:
    """A Q&A exchange in the earnings call."""
    question: str
    answer: str
    questioner: Optional[str] = None
    answerer: Optional[str] = None
    questioner_role: Optional[str] = None
    answerer_role: Optional[str] = None
    topic: Optional[str] = None
    sentiment: Optional[str] = None  # positive, negative, neutral


@dataclass
class GuidanceItem:
    """Forward-looking guidance from earnings call."""
    metric: str  # revenue, eps, gross_margin, etc.
    period: str  # Q1 2024, FY 2024, etc.
    value: Optional[str] = None  # ">$10B", "20-25%", etc.
    direction: Optional[str] = None  # raise, lower, maintain, reaffirm
    confidence: str = "medium"  # high, medium, low
    source_text: str = ""
    speaker: Optional[str] = None


@dataclass
class KeyMetric:
    """Key metric mentioned in earnings call."""
    metric: str
    value: str
    period: str
    context: str  # surrounding text
    speaker: Optional[str] = None
    sentiment: Optional[str] = None


@dataclass
class EarningsCallTranscript:
    """Parsed earnings call transcript."""
    company: str
    ticker: Optional[str] = None
    quarter: Optional[str] = None
    year: Optional[int] = None
    date: Optional[date] = None
    
    # Participants
    speakers: list[str] = field(default_factory=list)
    speaker_roles: dict[str, str] = field(default_factory=dict)
    
    # Sections
    sections: list = field(default_factory=list)  # TranscriptSection
    
    # Q&A
    qa_exchanges: list = field(default_factory=list)  # QAExchange
    
    # Key content
    key_metrics: list = field(default_factory=list)  # KeyMetric
    guidance: list = field(default_factory=list)  # GuidanceItem
    sentiment_by_speaker: dict[str, str] = field(default_factory=dict)
    
    # Metadata
    raw_text: str = ""
    source_file: Optional[str] = None
    parsed_at: datetime = field(default_factory=datetime.now)


class EarningsCallTranscriptParser:
    """
    Parses earnings call transcripts from various formats (PDF, text, HTML).
    
    Features:
    - Speaker identification and role classification
    - Section segmentation (presentation, Q&A, prepared remarks)
    - Q&A extraction with questioner/answerer roles
    - Guidance extraction with direction and confidence
    - Key metric extraction
    - Speaker sentiment analysis
    """
    
    def __init__(self):
        # Speaker role patterns
        self.role_patterns = {
            "operator": [
                r"operator",
                r"moderator",
                r"conference\s+operator",
            ],
            "ceo": [
                r"chief\s+executive\s+officer",
                r"ceo",
                r"president\s+and\s+ceo",
            ],
            "cfo": [
                r"chief\s+financial\s+officer",
                r"cfo",
                r"chief\s+financial\s+officer\s+and",
            ],
            "coo": [
                r"chief\s+operating\s+officer",
                r"coo",
            ],
            "cto": [
                r"chief\s+technology\s+officer",
                r"cto",
            ],
            "analyst": [
                r"analyst",
                r"research\s+analyst",
                r"investment\s+analyst",
            ],
            "investor_relations": [
                r"investor\s+relations",
                r"ir",
                r"vp\s+investor\s+relations",
            ],
        }
        
        # Section type patterns
        self.section_patterns = {
            "opening": [
                r"opening\s+remarks",
                r"welcome",
                r"good\s+(morning|afternoon|evening)",
                r"thank\s+you\s+(?:operator|everyone)",
            ],
            "prepared_remarks": [
                r"prepared\s+remarks",
                r"prepared\s+statement",
                r"remarks",
                r"presentation",
            ],
            "presentation": [
                r"presentation",
                r"slide\s+\d+",
                r"slide\s+deck",
            ],
            "qa": [
                r"q\s*&\s*a",
                r"q\s*&\s*a\s+session",
                r"questions?\s+and\s+answers?",
                r"question\s+and\s+answer",
                r"q\s*&\s*a\s+portion",
            ],
            "closing": [
                r"closing\s+remarks",
                r"thank\s+you",
                r"that\s+concludes",
                r"end\s+of\s+(?:the\s+)?(?:call|session)",
            ],
        }
        
        # Guidance patterns
        self.guidance_patterns = {
            "revenue": [
                r"revenue\s+(?:of|is|expected|projected|estimated|guided|guiding)\s*[:\-]?\s*[\$£€]?\s*[\d,\.]+(?:\s*(?:million|billion|b|m|mm))?",
                r"revenue\s+(?:growth|guidance|guidance\s+of)\s*[:\-]?\s*[\d,\.]+\s*%",
            ],
            "eps": [
                r"(?:eps|earnings\s+per\s+share)\s+(?:of|is|expected|projected|estimated|guided|guiding)\s*[:\-]?\s*[\$£€]?\s*[\d,\.]+",
                r"(?:eps|earnings\s+per\s+share)\s+(?:growth|guidance)\s*[:\-]?\s*[\d,\.]+\s*%",
            ],
            "gross_margin": [
                r"gross\s+margin\s+(?:of|is|expected|projected|estimated|guided|guiding)\s*[:\-]?\s*[\d,\.]+\s*%",
            ],
            "operating_margin": [
                r"operating\s+margin\s+(?:of|is|expected|projected|estimated|guided|guiding)\s*[:\-]?\s*[\d,\.]+\s*%",
            ],
            "capex": [
                r"capex\s+(?:of|is|expected|projected|estimated|guided|guiding)\s*[:\-]?\s*[\$£€]?\s*[\d,\.]+(?:\s*(?:million|billion|b|m|mm))?",
                r"capital\s+expenditure\s+(?:of|is|expected|projected|estimated|guided|guiding)\s*[:\-]?\s*[\$£€]?\s*[\d,\.]+",
            ],
            "operating_margin": [
                r"operating\s+margin\s+(?:of|is|expected|projected|estimated|guided|guiding)\s*[:\-]?\s*[\d,\.]+\s*%",
            ],
        }
        
        # Direction patterns
        self.direction_patterns = {
            "raise": [
                r"rais(?:e|ing)",
                r"increas(?:e|ing)",
                r"higher",
                r"improv(?:e|ing)",
                r"upward",
                r"above",
            ],
            "lower": [
                r"lower(?:ing)?",
                r"reduc(?:e|ing)",
                r"decreas(?:e|ing)",
                r"lower",
                r"downward",
                r"below",
            ],
            "maintain": [
                r"maintain",
                r"reaffirm",
                r"confirm",
                r"unchanged",
                r"same",
                r"steady",
            ],
        }
    
    def _compile_patterns(self):
        """Pre-compile regex patterns."""
        self._compiled_section_patterns = {}
        for section_type, patterns in self.section_patterns.items():
            self._compiled_section_patterns[section_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        self._compiled_guidance_patterns = {}
        for metric, patterns in self.guidance_patterns.items():
            self._compiled_guidance_patterns[metric] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        self._compiled_direction_patterns = {}
        for direction, patterns in self.direction_patterns.items():
            self._compiled_direction_patterns[direction] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    async def parse(self, file_path: Path) -> EarningsCallTranscript:
        """Parse earnings call transcript from file."""
        # Extract text from file
        text = await self._extract_text(file_path)
        
        transcript = EarningsCallTranscript(
            raw_text=text,
            source_file=str(file_path)
        )
        
        # Parse components
        await self._parse_speakers(text, transcript)
        await self._parse_sections(text, transcript)
        await self._parse_qa_exchanges(text, transcript)
        await self._extract_guidance(text, transcript)
        await self._extract_key_metrics(text, transcript)
        await self._analyze_sentiment(transcript)
        await self._extract_company_info(text, transcript)
        
        return transcript
    
    async def parse_text(self, text: str, company: str = "") -> EarningsCallTranscript:
        """Parse earnings call transcript from raw text."""
        transcript = EarningsCallTranscript(
            raw_text=text,
            company=company
        )
        
        await self._parse_speakers(text, transcript)
        await self._parse_sections(text, transcript)
        await self._parse_qa_exchanges(text, transcript)
        await self._extract_guidance(text, transcript)
        await self._extract_key_metrics(text, transcript)
        await self._analyze_sentiment(transcript)
        
        return transcript
    
    async def _extract_text(self, file_path: Path) -> str:
        """Extract text from various file formats."""
        suffix = file_path.suffix.lower()
        
        if suffix == ".txt":
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        
        elif suffix == ".pdf":
            # Use PDF parser
            from ..parser import parse_financial_pdf
            result = await parse_financial_pdf(file_path)
            if result.success:
                return "\n\n".join(page.text for page in result.pages)
            return ""
        
        elif suffix in [".htm", ".html"]:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                html = f.read()
            # Simple HTML to text
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
        
        else:
            # Try as text
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception:
                return ""
    
    async def _parse_speakers(self, text: str, transcript: EarningsCallTranscript):
        """Identify speakers and their roles."""
        # Find speaker patterns: "Name: text" or "NAME: text"
        speaker_pattern = re.compile(
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*:\s*(.+)$',
            re.MULTILINE
        )
        
        speakers = {}
        for match in speaker_pattern.finditer(transcript.raw_text):
            name = match.group(1).strip()
            text = match.group(2).strip()
            
            if name not in speakers:
                speakers[name] = {"text": [], "role": "unknown"}
            speakers[name]["text"].append(text)
        
        # Classify roles
        for name, data in speakers.items():
            combined_text = " ".join(data["text"]).lower()
            role = "participant"
            
            for role, patterns in self.role_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, combined_text, re.IGNORECASE):
                        data["role"] = role
                        break
            
            # If name appears frequently at start of exchanges, might be Q&A participant
            if len(data["text"]) > 3:
                data["role"] = data.get("role", "qa_participant")
        
        transcript.speakers = list(speakers.keys())
        transcript.speaker_roles = {name: data["role"] for name, data in speakers.items()}
        
        # Identify key executives
        for name, data in speakers.items():
            if data["role"] in ["ceo", "cfo", "coo", "cto"]:
                transcript.speakers.insert(0, transcript.speakers.pop(transcript.speakers.index(name)))
    
    async def _parse_sections(self, text: str, transcript: EarningsCallTranscript):
        """Parse transcript into sections."""
        sections = []
        
        # Find section boundaries
        section_matches = []
        for section_type, patterns in self._compiled_section_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    section_matches.append({
                        "type": section_type,
                        "start": match.start(),
                        "end": match.end(),
                        "text": match.group(0)
                    })
        
        # Sort by position
        section_matches.sort(key=lambda x: x["start"])
        
        # Create sections
        for i, match in enumerate(section_matches):
            start = match["start"]
            end = section_matches[i + 1]["start"] if i + 1 < len(section_matches) else len(text)
            
            section_text = text[start:end]
            
            # Find speaker for this section
            speaker = self._find_speaker_for_position(text, start, transcript)
            
            section = TranscriptSection(
                section_type=match["type"],
                speaker=speaker,
                text=section_text.strip(),
                start_char=start,
                end_char=end
            )
            sections.append(section)
        
        # If no sections found, treat as single presentation
        if not sections:
            sections = [TranscriptSection(
                section_type="presentation",
                speaker=None,
                text=text,
                start_char=0,
                end_char=len(text)
            )]
        
        transcript.sections = sections
    
    def _find_speaker_for_position(self, text: str, position: int, transcript: EarningsCallTranscript) -> Optional[str]:
        """Find speaker closest to a position in text."""
        # Look backwards for speaker pattern
        before_text = text[max(0, position-500):position]
        
        # Look for "Name:" pattern
        matches = list(re.finditer(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*:', before_text, re.MULTILINE))
        if matches:
            return matches[-1].group(1)
        
        # Check known speakers
        for speaker in transcript.speakers:
            if speaker.lower() in text[max(0, position-200):position].lower():
                return speaker
        
        return None
    
    async def _parse_qa_exchanges(self, text: str, transcript: EarningsCallTranscript):
        """Extract Q&A exchanges."""
        qa_exchanges = []
        
        # Find Q&A section
        qa_section = None
        for section in transcript.sections:
            if section.section_type == "qa":
                qa_section = section
                break
        
        if not qa_section:
            # Try to find Q&A in full text
            qa_start = None
            for pattern in self._compiled_section_patterns["qa"]:
                match = pattern.search(text)
                if match:
                    qa_start = match.start()
                    break
            
            if qa_start:
                qa_text = text[qa_start:]
            else:
                return
        else:
            qa_text = qa_section.text
        
        # Parse Q&A exchanges
        # Pattern: "Analyst: Question?" followed by "Executive: Answer"
        qa_pattern = re.compile(
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*:\s*(.+?)(?=\n\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*:|$)',
            re.DOTALL | re.MULTILINE
        )
        
        exchanges = []
        matches = list(self.qa_pattern.finditer(qa_text))
        
        for i, match in enumerate(matches):
            speaker = match.group(1).strip()
            text = match.group(2).strip()
            
            if i + 1 < len(matches):
                next_speaker = matches[i + 1].group(1).strip()
            else:
                next_speaker = None
            
            # Classify as question or answer
            is_question = "?" in text or any(word in text.lower() for word in ["what", "how", "why", "when", "where", "can you", "could you", "would you"])
            
            if is_question:
                # Look for next answer
                if next_speaker and i + 1 < len(matches):
                    answer_text = matches[i + 1].group(2).strip()
                    exchanges.append(QAExchange(
                        question=text,
                        answer=answer_text,
                        questioner=speaker,
                        answerer=next_speaker,
                        questioner_role=transcript.speaker_roles.get(speaker),
                        answerer_role=transcript.speaker_roles.get(next_speaker)
                    ))
        
        transcript.qa_exchanges = exchanges
    
    async def _extract_guidance(self, text: str, transcript: EarningsCallTranscript):
        """Extract forward-looking guidance from transcript."""
        guidance_items = []
        
        for metric, patterns in self._compiled_guidance_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    matched_text = match.group(0)
                    
                    # Determine direction
                    direction = "maintain"
                    context = text[max(0, match.start()-100):match.end()+100].lower()
                    
                    for direction_type, patterns in self._compiled_direction_patterns.items():
                        for pattern in patterns:
                            if pattern.search(context):
                                direction = direction_type
                                break
                    
                    # Extract value
                    value_match = re.search(r'[\$£€]?\s*[\d,\.]+(?:\s*(?:million|billion|b|m|mm))?', matched_text)
                    value = value_match.group(0) if value_match else None
                    
                    # Extract period
                    period_match = re.search(r'(?:fy|q[1-4]|quarter|year|20\d{2})', matched_text, re.IGNORECASE)
                    period = period_match.group(0) if period_match else "near term"
                    
                    # Determine confidence
                    confidence = "medium"
                    if any(word in matched_text.lower() for word in ["expect", "anticipate", "project", "estimate"]):
                        confidence = "medium"
                    if any(word in matched_text.lower() for word in ["guidance", "guide", "outlook", "target"]):
                        confidence = "high"
                    if any(word in matched_text.lower() for word in ["roughly", "approximately", "around", "about"]):
                        confidence = "medium"
                    
                    # Find speaker
                    speaker = self._find_speaker_for_position(text, match.start())
                    
                    guidance = GuidanceItem(
                        metric=metric,
                        period=period,
                        value=value,
                        direction=direction,
                        confidence=confidence,
                        source_text=matched_text[:200],
                        speaker=speaker
                    )
                    
                    # Avoid duplicates
                    if not any(g.metric == metric and g.period == period and g.value == value for g in guidance_items):
                        guidance_items.append(guidance)
        
        transcript.guidance = guidance_items
    
    async def _extract_key_metrics(self, text: str, transcript: EarningsCallTranscript):
        """Extract key metrics mentioned in the call."""
        key_metrics = []
        
        # Common financial metrics
        metric_patterns = {
            "revenue": r"revenue\s+(?:of|was|is|came in at|came in)\s*[:\-]?\s*[\$£€]?\s*[\d,\.]+(?:\s*(?:million|billion|b|m|mm))?",
            "net_income": r"net income\s+(?:of|was|is)\s*[:\-]?\s*[\$£€]?\s*[\d,\.]+(?:\s*(?:million|billion|b|m|mm))?",
            "eps": r"(?:eps|earnings per share)\s+(?:of|was|is)\s*[:\-]?\s*[\$£€]?\s*[\d,\.]+",
            "gross_margin": r"gross margin\s+(?:of|was|is)\s*[\d,\.]+\s*%",
            "operating_margin": r"operating margin\s+(?:of|was|is)\s*[\d,\.]+\s*%",
            "operating_income": r"operating income\s+(?:of|was|is)\s*[:\-]?\s*[\$£€]?\s*[\d,\.]+(?:\s*(?:million|billion|b|m|mm))?",
            "free_cash_flow": r"free cash flow\s+(?:of|was|is)\s*[:\-]?\s*[\$£€]?\s*[\d,\.]+(?:\s*(?:million|billion|b|m|mm))?",
        }
        
        for metric, pattern in metric_patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Extract context
                context = text[max(0, match.start()-100):match.end()+100]
                speaker = self._find_speaker_for_position(text, match.start())
                
                # Determine sentiment
                sentiment = "neutral"
                context_lower = context.lower()
                if any(word in context_lower for word in ["beat", "exceed", "strong", "stronger", "better", "above", "record"]):
                    sentiment = "positive"
                elif any(word in context_lower for word in ["miss", "below", "weak", "weaker", "disappoint", "lower", "decline"]):
                    sentiment = "negative"
                
                metric_obj = KeyMetric(
                    metric=metric,
                    value=match.group(0),
                    period="current quarter",  # Would need more context
                    context=context.strip(),
                    speaker=speaker,
                    sentiment=sentiment
                )
                key_metrics.append(metric_obj)
        
        transcript.key_metrics = key_metrics
    
    async def _analyze_sentiment(self, transcript: EarningsCallTranscript):
        """Analyze sentiment by speaker."""
        from ..intelligence import RiskOpportunityExtractor
        
        extractor = RiskOpportunityExtractor()
        
        for name, role in transcript.speaker_roles.items():
            # Get all text for this speaker
            speaker_text = ""
            for section in transcript.sections:
                if section.speaker == name:
                    speaker_text += section.text + " "
            
            for exchange in transcript.qa_exchanges:
                if exchange.answerer == name:
                    speaker_text += exchange.answer + " "
                if exchange.questioner == name:
                    speaker_text += exchange.question + " "
            
            if not speaker_text:
                continue
            
            # Simple sentiment analysis
            positive_words = ["strong", "stronger", "growth", "growth", "record", "beat", "exceed", "outperform", "improve", "better", "higher", "increase", "positive", "optimistic", "confident", "pleased", "excited"]
            negative_words = ["miss", "missed", "weak", "decline", "decrease", "lower", "disappoint", "challenge", "headwind", "pressure", "concern", "risk", "uncertain", "difficult", "tough", "below"]
            
            text_lower = speaker_text.lower()
            pos_count = sum(1 for word in positive_words if word in text_lower)
            neg_count = sum(1 for word in negative_words if word in text_lower)
            
            if pos_count > neg_count:
                sentiment = "positive"
            elif neg_count > pos_count:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            transcript.sentiment_by_speaker[name] = sentiment
    
    async def _extract_company_info(self, text: str, transcript: EarningsCallTranscript):
        """Extract company name, ticker, quarter, year from text."""
        # Extract quarter/year
        quarter_patterns = [
            r"q[1-4]\s+(?:20\d{2}|fiscal\s+20\d{2})",
            r"quarter\s+ended\s+\w+\s+\d{1,2},?\s+20\d{2}",
            r"fiscal\s+q[1-4]\s+20\d{2}",
            r"q[1-4]\s+20\d{2}",
        ]
        
        for pattern in re.finditer(r"q[1-4]\s+20\d{2}", transcript.raw_text, re.IGNORECASE):
            transcript.quarter = match.group(0).upper()
            break
        
        year_match = re.search(r"20\d{2}", transcript.raw_text)
        if year_match:
            transcript.year = int(year_match.group(0))
        
        # Try to extract company name from header
        lines = transcript.raw_text.split('\n')[:10]
        for line in lines:
            if any(word in line.lower() for word in ["corporation", "inc", "inc.", "company", "ltd", "llc"]):
                transcript.company = line.strip()
                break
        
        # Try to find ticker
        ticker_match = re.search(r'\(([A-Z]{1,5})\)', transcript.raw_text[:500])
        if ticker_match:
            transcript.ticker = ticker_match.group(1)
    
    def _compile_patterns(self):
        """Compile regex patterns for performance."""
        self._compiled_section_patterns = {}
        for section_type, patterns in self.section_patterns.items():
            self._compiled_section_patterns[section_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        self._compiled_guidance_patterns = {}
        for metric, patterns in self.guidance_patterns.items():
            self._compiled_guidance_patterns[metric] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        self._compiled_direction_patterns = {}
        for direction, patterns in self.direction_patterns.items():
            self._compiled_direction_patterns[direction] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]


class EarningsCallProcessor:
    """Process multiple earnings call transcripts."""
    
    def __init__(self, parser: Optional[EarningsCallTranscriptParser] = None):
        self.parser = parser or EarningsCallTranscriptParser()
    
    async def process_directory(self, directory: Path, pattern: str = "*.txt") -> list[EarningsCallTranscript]:
        """Process all transcript files in a directory."""
        transcripts = []
        
        for file_path in directory.glob(pattern):
            try:
                transcript = await self.parser.parse(file_path)
                transcripts.append(transcript)
                logger.info(f"Parsed: {file_path.name}")
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")
        
        return transcripts
    
    async def process_company_transcripts(self, company_ticker: str, directory: Path) -> list[EarningsCallTranscript]:
        """Process all transcripts for a specific company."""
        # Look for files matching ticker pattern
        pattern = f"*{company_ticker}*.txt"
        return await self.process_directory(directory, pattern)
    
    def get_summary(self, transcripts: list[EarningsCallTranscript]) -> dict:
        """Generate summary statistics for a collection of transcripts."""
        if not transcripts:
            return {}
        
        total_calls = len(transcripts)
        companies = set(t.company for t in transcripts)
        tickers = set(t.ticker for t in transcripts if t.ticker)
        
        # Aggregate guidance
        all_guidance = []
        for t in transcripts:
            all_guidance.extend(t.guidance)
        
        # Aggregate key metrics
        all_metrics = []
        for t in transcripts:
            all_metrics.extend(t.key_metrics)
        
        # Sentiment distribution
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        for t in transcripts:
            for speaker, sentiment in t.sentiment_by_speaker.items():
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        return {
            "total_calls": total_calls,
            "unique_companies": len(companies),
            "tickers": list(tickers),
            "total_guidance_items": len(all_guidance),
            "total_key_metrics": len(all_metrics),
            "sentiment_distribution": sentiment_counts,
            "avg_qa_exchanges": sum(len(t.qa_exchanges) for t in transcripts) / total_calls if total_calls > 0 else 0,
        }


# Export
__all__ = [
    "EarningsCallTranscriptParser",
    "EarningsCallProcessor",
    "EarningsCallTranscript",
    "Speaker",
    "TranscriptSection",
    "QAExchange",
    "GuidanceItem",
    "KeyMetric",
]