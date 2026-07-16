"""
Language Detector for News Articles

Detects article language using multiple strategies:
- FastText (if available)
- langdetect (fallback)
- Heuristic analysis (final fallback)
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class LanguageResult:
    """Language detection result."""
    language: str  # ISO 639-1 code
    confidence: float  # 0.0 - 1.0
    method: str  # 'fasttext', 'langdetect', 'heuristic'
    alternatives: List[Tuple[str, float]] = None


class LanguageDetector:
    """
    Detects language of news articles.
    
    Supports multiple backends with fallback chain:
    1. FastText (fast, accurate, offline)
    2. langdetect (reasonable, small)
    3. Heuristic analysis (no dependencies)
    """
    
    # Common English words for heuristic detection
    ENGLISH_COMMON = {
        'the', 'and', 'to', 'of', 'a', 'in', 'is', 'it', 'you', 'that',
        'he', 'was', 'for', 'on', 'are', 'as', 'with', 'his', 'they',
        'be', 'at', 'one', 'have', 'this', 'from', 'or', 'had', 'by',
        'not', 'but', 'what', 'all', 'were', 'we', 'when', 'your',
        'can', 'said', 'there', 'use', 'an', 'each', 'which', 'she',
        'do', 'how', 'their', 'if', 'will', 'up', 'other', 'about',
        'out', 'many', 'then', 'them', 'these', 'so', 'some', 'her',
        'would', 'make', 'like', 'into', 'him', 'has', 'two', 'more',
        'very', 'after', 'words', 'long', 'much', 'own', 'say', 'now',
        'new', 'year', 'stock', 'market', 'company', 'shares', 'price',
        'earnings', 'revenue', 'profit', 'quarter', 'analyst', 'report',
        'billion', 'million', 'percent', 'growth', 'investment', 'trading'
    }
    
    # Language-specific stop words for heuristic
    LANGUAGE_MARKERS = {
        'en': {'the', 'and', 'to', 'of', 'a', 'in', 'is', 'it', 'you', 'that', 'he', 'was', 'for', 'on', 'are', 'as'},
        'es': {'el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'una', 'del', 'los', 'las'},
        'fr': {'le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir', 'que', 'pour', 'dans', 'ce', 'il', 'qui', 'ne', 'sur', 'se', 'pas', 'plus', 'pouvoir', 'par', 'je', 'avec', 'tout', 'faire', 'son', 'mettre', 'autre', 'nous', 'comme', 'mais', 'son', 'celui', 'sans', 'or', 'aussi', 'donc', 'si', 'voir', 'très', 'dire', 'avant', 'deux', 'même', 'premier', 'encore', 'nouveau', 'après', 'grand', 'mon', 'me', 'même', 'tout', 'sous', 'avoir', 'falloir', 'savoir', 'valoir', 'vouloir'},
        'de': {'der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich', 'des', 'auf', 'für', 'ist', 'im', 'dem', 'nicht', 'ein', 'eine', 'als', 'auch', 'es', 'an', 'werden', 'aus', 'er', 'hat', 'dass', 'sie', 'nach', 'wird', 'bei', 'einer', 'um', 'am', 'sind', 'noch', 'wie', 'einem', 'über', 'einen', 'so', 'zum', 'war', 'haben', 'nur', 'oder', 'aber', 'vor', 'zur', 'bis', 'mehr', 'durch', 'man', 'sein', 'wurde', 'sei', 'ihre', 'dann', 'unter', 'wir', 'soll', 'ich', 'eines', 'jahre', 'zwei', 'hatte', 'wenn', 'diese', 'kann', 'gegen', 'ihn', 'ihm', 'dies', 'seine', 'manche', 'meine', 'uns', 'euch', 'eurem', 'ihre'},
        'zh': {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '里', '来', '他', '为', '么', '都', '什么', '时候', '公司', '市场', '股票', '价格', '收益', '分析', '报告', '投资', '增长', '十亿', '百万', '百分比'},
        'ja': {'の', 'に', 'は', 'を', 'た', 'が', 'で', 'て', 'と', 'し', 'れ', 'さ', 'ある', 'いる', 'も', 'する', 'から', 'な', 'こと', 'として', 'い', 'や', 'れ', 'など', 'な', 'ん', 'なっ', 'それ', 'この', 'その', 'あの', 'こんな', 'そんな', 'あんな', 'これ', 'それ', 'あれ', 'ここ', 'そこ', 'あそこ', 'どこ', 'だれ', 'なに', 'いつ', 'どう', 'なぜ', 'どれ', 'どの', 'どちら'},
        'pt': {'o', 'a', 'de', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não', 'uma', 'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'foi', 'ele', 'das', 'tem', 'à', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'há', 'nos', 'já', 'está', 'eu', 'também', 'só', 'pelo', 'pela', 'até', 'isso', 'ela', 'entre', 'era', 'depois', 'sem', 'mesmo', 'aos', 'ter', 'seus', 'suas', 'meu', 'minha', 'nosso', 'nossa', 'deles', 'delas', 'este', 'esta', 'estes', 'estas', 'aquele', 'aquela', 'aqueles', 'aquelas'},
    }
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._fasttext_model = None
        self._langdetect_available = False
        self._init_detectors()
    
    def _init_detectors(self):
        """Initialize available detectors."""
        # Try FastText
        try:
            import fasttext
            model_path = self.config.get('fasttext_model', 'lid.176.bin')
            self._fasttext_model = fasttext.load_model(model_path)
            logger.info("FastText language detector loaded")
        except Exception as e:
            logger.debug(f"FastText not available: {e}")
        
        # Try langdetect
        try:
            from langdetect import detect, detect_langs
            self._langdetect_available = True
            logger.info("langdetect available")
        except Exception as e:
            logger.debug(f"langdetect not available: {e}")
    
    def detect(self, text: str) -> LanguageResult:
        """
        Detect language of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            LanguageResult with language code, confidence, and method
        """
        if not text or len(text.strip()) < 10:
            return LanguageResult(
                language='en',
                confidence=0.5,
                method='default',
                alternatives=[]
            )
        
        # Try FastText first
        if self._fasttext_model:
            try:
                result = self._detect_fasttext(text)
                if result.confidence >= 0.5:
                    return result
            except Exception as e:
                logger.debug(f"FastText detection failed: {e}")
        
        # Try langdetect
        if self._langdetect_available:
            try:
                result = self._detect_langdetect(text)
                if result.confidence >= 0.5:
                    return result
            except Exception as e:
                logger.debug(f"langdetect failed: {e}")
        
        # Fallback to heuristic
        return self._detect_heuristic(text)
    
    def _detect_fasttext(self, text: str) -> LanguageResult:
        """Detect using FastText."""
        # FastText expects single line
        clean_text = text.replace('\n', ' ')[:1000]
        predictions = self._fasttext_model.predict(clean_text, k=3)
        
        labels = predictions[0]
        probs = predictions[1]
        
        # FastText returns labels like '__label__en'
        languages = [label.replace('__label__', '') for label in labels]
        
        alternatives = list(zip(languages[1:], probs[1:])) if len(languages) > 1 else []
        
        return LanguageResult(
            language=languages[0],
            confidence=float(probs[0]),
            method='fasttext',
            alternatives=alternatives
        )
    
    def _detect_langdetect(self, text: str) -> LanguageResult:
        """Detect using langdetect."""
        from langdetect import detect, detect_langs
        
        # langdetect works better with more text
        clean_text = text[:5000]
        
        # Get single detection
        lang = detect(clean_text)
        
        # Get probabilities
        probs = detect_langs(clean_text)
        alternatives = [(str(p).split(':')[0], float(str(p).split(':')[1])) for p in probs[1:]]
        
        return LanguageResult(
            language=lang,
            confidence=float(probs[0].prob),
            method='langdetect',
            alternatives=alternatives
        )
    
    def _detect_heuristic(self, text: str) -> LanguageResult:
        """
        Heuristic language detection using stop word frequency.
        
        Simple but effective for clean text.
        """
        # Tokenize
        words = re.findall(r'\b\w+\b', text.lower())
        
        if not words:
            return LanguageResult(language='en', confidence=0.3, method='heuristic')
        
        # Count matches for each language
        scores = {}
        for lang, markers in self.LANGUAGE_MARKERS.items():
            match_count = sum(1 for w in words if w in markers)
            scores[lang] = match_count / len(words) if words else 0
        
        # Also check English common words
        en_count = sum(1 for w in words if w in self.ENGLISH_COMMON)
        scores['en'] = max(scores.get('en', 0), en_count / len(words))
        
        # Find best language
        if not scores or max(scores.values()) < 0.02:
            return LanguageResult(language='en', confidence=0.4, method='heuristic')
        
        best_lang = max(scores, key=scores.get)
        best_score = scores[best_lang]
        
        # Normalize confidence
        confidence = min(best_score * 5, 0.85)  # Cap at 0.85 for heuristic
        
        # Alternatives
        sorted_langs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        alternatives = [(lang, min(score * 5, 0.8)) for lang, score in sorted_langs[1:3]]
        
        return LanguageResult(
            language=best_lang,
            confidence=confidence,
            method='heuristic',
            alternatives=alternatives
        )
    
    def is_english(self, text: str, threshold: float = 0.5) -> bool:
        """Quick check if text is English."""
        result = self.detect(text)
        return result.language == 'en' and result.confidence >= threshold
    
    def batch_detect(self, texts: List[str]) -> List[LanguageResult]:
        """Detect language for multiple texts."""
        return [self.detect(text) for text in texts]


# Global instance
_detector: Optional[LanguageDetector] = None


def get_language_detector(config: Optional[dict] = None) -> LanguageDetector:
    """Get or create global language detector."""
    global _detector
    if _detector is None:
        _detector = LanguageDetector(config)
    return _detector


def detect_language(text: str, config: Optional[dict] = None) -> LanguageResult:
    """Convenience function to detect language."""
    detector = get_language_detector(config)
    return detector.detect(text)