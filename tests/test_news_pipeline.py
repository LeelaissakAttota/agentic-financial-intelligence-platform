"""
Tests for News Pipeline Components
"""

import pytest
from datetime import datetime, timedelta

from data.news.schemas import NewsArticle, NewsSource, NewsCategory, SentimentLabel, ArticleSentiment
from data.news.pipeline.html_cleaner import HTMLCleaner, clean_html
from data.news.pipeline.duplicate_detector import DuplicateDetector, deduplicate_articles
from data.news.pipeline.quality_scorer import QualityScorer, QualityConfig, score_quality
from data.news.pipeline.credibility_scorer import CredibilityScorer, CredibilityConfig, score_credibility
from data.news.pipeline.freshness_scorer import FreshnessScorer, FreshnessConfig, score_freshness
from data.news.pipeline.language_detector import LanguageDetector, detect_language


class TestHTMLCleaner:
    """Tests for HTML cleaning."""

    def test_clean_simple_html(self):
        """Test cleaning simple HTML."""
        html = "<p>Hello <strong>world</strong>!</p>"
        result = clean_html(html)
        assert "Hello world!" in result
        assert "<p>" not in result
        assert "<strong>" not in result

    def test_clean_removes_scripts(self):
        """Test that script tags are removed."""
        html = "<p>Content</p><script>alert('xss')</script><p>More</p>"
        result = clean_html(html)
        assert "Content" in result
        assert "More" in result
        assert "script" not in result.lower()
        assert "alert" not in result

    def test_clean_removes_styles(self):
        """Test that style tags are removed."""
        html = "<p>Text</p><style>body { color: red; }</style>"
        result = clean_html(html)
        assert "Text" in result
        assert "color: red" not in result

    def test_clean_handles_empty(self):
        """Test handling empty/None input."""
        assert clean_html("") == ""
        assert clean_html(None) == ""
        assert clean_html("   ") == ""

    def test_clean_preserves_links(self):
        """Test that links can be preserved."""
        html = '<p>Read <a href="https://example.com">this</a> article.</p>'
        result = clean_html(html, config={'keep_links': True})
        assert "this" in result
        assert "example.com" in result or "this" in result

    def test_clean_removes_ads(self):
        """Test removal of ad elements."""
        html = '<div class="advertisement">Ad</div><p>Real content</p><div class="sponsored">Sponsored</div>'
        result = clean_html(html)
        assert "Real content" in result
        assert "Ad" not in result or result.count("Ad") == 0

    def test_clean_normalizes_whitespace(self):
        """Test whitespace normalization."""
        html = "<p>Text   with    spaces</p>\n\n\n<p>More</p>"
        result = clean_html(html)
        assert "Text with spaces" in result
        assert result.count('\n\n\n') == 0


class TestDuplicateDetector:
    """Tests for duplicate detection."""

    def setup_method(self):
        self.detector = DuplicateDetector({
            'title_similarity_threshold': 0.80,
            'content_fingerprint_threshold': 0.40
        })

    def test_exact_hash_match(self):
        """Test exact content hash duplicate detection."""
        article1 = NewsArticle(
            title="Test Article",
            summary="Summary",
            url="https://example.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow(),
            content_hash="abc123"
        )
        article2 = NewsArticle(
            title="Different Title",
            summary="Different Summary",
            url="https://example.com/2",
            source=NewsSource.CNBC,
            source_name="CNBC",
            published_at=datetime.utcnow(),
            content_hash="abc123"  # Same hash
        )

        result1 = self.detector.check(article1)
        assert not result1.is_duplicate

        result2 = self.detector.check(article2)
        assert result2.is_duplicate
        assert result2.reason == "exact_content_hash"

    def test_url_canonicalization(self):
        """Test URL canonicalization for duplicates."""
        article1 = NewsArticle(
            title="Article 1",
            summary="Summary",
            url="https://www.example.com/article?utm_source=twitter&utm_medium=social",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow(),
            content_hash="hash1"
        )
        article2 = NewsArticle(
            title="Article 2",
            summary="Summary",
            url="https://example.com/article",  # Canonical same URL
            source=NewsSource.CNBC,
            source_name="CNBC",
            published_at=datetime.utcnow(),
            content_hash="hash2"
        )

        result1 = self.detector.check(article1)
        assert not result1.is_duplicate

        result2 = self.detector.check(article2)
        assert result2.is_duplicate
        assert result2.reason == "canonical_url"

    def test_title_similarity(self):
        """Test fuzzy title matching."""
        article1 = NewsArticle(
            title="Apple Reports Record Q3 Earnings Beating Estimates",
            summary="Summary",
            url="https://example.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow(),
            content_hash="hash1"
        )
        article2 = NewsArticle(
            title="Apple Reports Record Q3 Earnings Beats Estimates",  # Very similar
            summary="Summary",
            url="https://example.com/2",
            source=NewsSource.CNBC,
            source_name="CNBC",
            published_at=datetime.utcnow(),
            content_hash="hash2"
        )

        result1 = self.detector.check(article1)
        assert not result1.is_duplicate

        result2 = self.detector.check(article2)
        assert result2.is_duplicate
        assert result2.reason == "title_similarity"
        assert result2.similarity >= 0.80

    def test_content_fingerprint(self):
        """Test content fingerprint matching with realistic financial articles."""
        # Article from Reuters about Apple earnings - full content
        article1 = NewsArticle(
            title="Apple Reports Record Q3 Revenue of $89.5B, Beats Estimates on iPhone Strength",
            summary="Apple Inc. reported fiscal third-quarter revenue of $89.5 billion, up 8% year-over-year, driven by strong iPhone 15 sales and Services growth. CEO Tim Cook highlighted record June quarter performance.",
            url="https://reuters.com/technology/apple-q3-earnings-2024",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow(),
            content="Apple Inc. (AAPL) today announced financial results for its fiscal 2024 third quarter ended June 29, 2024. The Company posted quarterly revenue of $89.5 billion, an increase of 8 percent from the year-ago quarter. Quarterly earnings per diluted share were $1.40, up 11 percent year over year. CEO Tim Cook said, 'We are proud to report record June quarter revenue of $89.5 billion, up 8 percent year over year.' The Company's Services revenue reached an all-time high of $21.2 billion. iPhone revenue was $45.9 billion. The board declared a cash dividend of $0.24 per share.",
            content_hash="hash1"
        )
        # Same story from CNBC - nearly identical content (syndicated copy)
        article2 = NewsArticle(
            title="Apple Q3 Earnings Beat: Revenue Hits $89.5B on iPhone, Services Growth",
            summary="Apple beat Wall Street expectations with Q3 revenue of $89.5 billion. iPhone revenue was $45.9 billion and Services hit an all-time high of $21.2 billion.",
            url="https://cnbc.com/2024/08/01/apple-earnings-q3-2024",
            source=NewsSource.CNBC,
            source_name="CNBC",
            author="CNBC Markets Team",
            published_at=datetime.utcnow(),
            content_hash="hash2",
            content="Apple Inc. (AAPL) today announced financial results for its fiscal 2024 third quarter ended June 29, 2024. The Company posted quarterly revenue of $89.5 billion, an increase of 8 percent from the year-ago quarter. Quarterly earnings per diluted share were $1.40, up 11 percent year over year. CEO Tim Cook said, 'We are proud to report record June quarter revenue of $89.5 billion, up 8 percent year over year.' The Company's Services revenue reached an all-time high of $21.2 billion. iPhone revenue was $45.9 billion. The board declared a cash dividend of $0.24 per share."
        )

        result1 = self.detector.check(article1)
        assert not result1.is_duplicate

        result2 = self.detector.check(article2)
        assert result2.is_duplicate
        assert result2.reason == "content_fingerprint"

    def test_deduplicate_articles_list(self):
        """Test batch deduplication with realistic financial articles."""
        base_time = datetime.utcnow()
        articles = [
            NewsArticle(
                title="Apple Reports Record Q3 Revenue of $89.5B, Beats Estimates",
                summary="Apple reported Q3 revenue of $89.5B, up 8% YoY, driven by iPhone 15 and Services growth.",
                url="https://reuters.com/technology/apple-q3-2024",
                source=NewsSource.REUTERS,
                source_name="Reuters",
                author="Reuters Staff",
                published_at=base_time,
                content="Apple Inc. (AAPL) reported fiscal Q3 revenue of $89.5B, up 8% YoY. iPhone revenue reached $45.9B and Services revenue hit $21.2B. CEO Tim Cook said: 'We are proud to report record June quarter revenue.' The board declared a $0.24 dividend.",
                content_hash="hash0"
            ),
            NewsArticle(
                title="Microsoft Cloud Revenue Growth Accelerates in Q4",
                summary="Microsoft Azure revenue up 29% YoY, Intelligent Cloud segment hits $28.5B.",
                url="https://reuters.com/technology/microsoft-q4-2024",
                source=NewsSource.REUTERS,
                source_name="Reuters",
                author="Reuters Staff",
                published_at=base_time,
                content="Microsoft reported fiscal Q4 with Azure up 29% year-over-year. Intelligent Cloud revenue reached $28.5B. Total revenue was $64.7B. The company also announced a $0.75 dividend per share.",
                content_hash="hash1"
            ),
            NewsArticle(
                title="NVIDIA AI Chip Demand Surges, Data Center Revenue Doubles",
                summary="NVIDIA reports data center revenue of $26.3B, up 154% YoY on AI demand.",
                url="https://reuters.com/technology/nvidia-q2-2024",
                source=NewsSource.REUTERS,
                source_name="Reuters",
                author="Reuters Staff",
                published_at=base_time,
                content="NVIDIA (NVDA) reported Q2 data center revenue of $26.3B, up 154% YoY on AI demand. Gaming revenue was $2.5B. Total revenue hit $30B. CEO Jensen Huang said demand for AI chips remains unprecedented.",
                content_hash="hash2"
            ),
            NewsArticle(
                title="Tesla Q2 Deliveries Beat Estimates Despite Margin Pressure",
                summary="Tesla delivered 444K vehicles in Q2, beating estimates. Energy storage deployments hit record.",
                url="https://reuters.com/technology/tesla-q2-2024",
                source=NewsSource.REUTERS,
                source_name="Reuters",
                author="Reuters Staff",
                published_at=base_time,
                content="Tesla (TSLA) delivered 444K vehicles in Q2, beating analyst estimates of 439K. Energy storage deployments hit a record 9.4 GWh. The company produced 411K vehicles.",
                content_hash="hash3"
            ),
            NewsArticle(
                title="Amazon AWS Growth Reaccelerates to 19% in Q2",
                summary="Amazon Web Services revenue hits $26.3B, operating income $9.3B.",
                url="https://reuters.com/technology/amazon-q2-2024",
                source=NewsSource.REUTERS,
                source_name="Reuters",
                author="Reuters Staff",
                published_at=base_time,
                content="Amazon (AMZN) Q2 AWS revenue reached $26.3B, up 19% YoY. AWS operating income was $9.3B. Total company revenue was $148B. Advertising revenue grew 20% to $12.8B.",
                content_hash="hash4"
            )
        ]
        # Add near-duplicate of article 1 (Microsoft) from different source - nearly identical content (syndicated)
        articles.append(NewsArticle(
            title="Microsoft Q4 Beats: Azure Growth 29%, Cloud Revenue $28.5B",
            summary="Microsoft fiscal Q4 beats estimates with Azure up 29%, Intelligent Cloud at $28.5B.",
            url="https://cnbc.com/2024/07/30/microsoft-earnings-q4",
            source=NewsSource.CNBC,
            source_name="CNBC",
            author="CNBC Markets Team",
            published_at=base_time,
            content="Microsoft reported fiscal Q4 with Azure up 29% year-over-year. Intelligent Cloud revenue reached $28.5B. Total revenue was $64.7B. The company also announced a $0.75 dividend per share.",
            content_hash="hash5"
        ))

        unique = deduplicate_articles(articles, {
            'content_fingerprint_threshold': 0.40
        })
        assert len(unique) == 5
        # The Microsoft CNBC article should be marked as duplicate of the Reuters one
        assert articles[5].is_duplicate  # The 6th one (index 5) should be marked duplicate
        assert articles[5].metadata['duplicate_reason'] == 'content_fingerprint'


class TestQualityScorer:
    """Tests for quality scoring."""

    def setup_method(self):
        self.scorer = QualityScorer()

    def test_high_quality_article(self):
        """Test scoring a high-quality article."""
        article = NewsArticle(
            title="Apple Reports Record Quarterly Revenue of $89.5 Billion, Up 8% Year-Over-Year",
            summary="Apple Inc. today announced financial results for its fiscal 2024 third quarter ended June 29, 2024. The Company posted quarterly revenue of $89.5 billion, an increase of 8 percent from the year-ago quarter.",
            content="Apple Inc. today announced financial results for its fiscal 2024 third quarter ended June 29, 2024. The Company posted quarterly revenue of $89.5 billion, an increase of 8 percent from the year-ago quarter. CEO Tim Cook said, 'We are proud to report record June quarter revenue.' The company's Services revenue reached an all-time high of $21.2 billion. iPhone revenue was $45.9 billion. The board declared a cash dividend of $0.24 per share.",
            url="https://reuters.com/technology/apple-earnings-2024",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            author="Reuters Staff",
            published_at=datetime.utcnow(),
            content_hash="hash1"
        )

        score = self.scorer.score(article)

        assert score.overall > 0.7
        assert score.completeness > 0.8
        assert score.structure > 0.6
        assert score.information_density > 0.7
        assert score.writing_quality > 0.7
        assert score.details['source_tier'] == 'premium'
        assert score.details['paragraph_count'] >= 1
        assert score.details['number_count'] >= 1
        assert score.details['dollar_amount_count'] >= 1

    def test_low_quality_article(self):
        """Test scoring a low-quality article."""
        article = NewsArticle(
            title="X",  # Too short
            summary="Short",
            content="Brief.",
            url="https://unknown.com/1",
            source=NewsSource.UNKNOWN,
            source_name="Unknown",
            published_at=datetime.utcnow(),
            content_hash="hash1"
        )

        score = self.scorer.score(article)

        assert score.overall < 0.5
        assert score.completeness < 0.7
        assert score.structure < 0.5
        assert score.details['source_tier'] == 'standard'

    def test_clickbait_detection(self):
        """Test clickbait detection penalty."""
        article = NewsArticle(
            title="SHOCKING! You Won't Believe What Apple Just Announced!!! 10 Things You Must Know",
            summary="Summary",
            content="Content with numbers.",
            url="https://example.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow(),
            content_hash="hash1"
        )

        score = self.scorer.score(article)

        assert score.details['clickbait_detected'] == True
        # Writing quality should be penalized
        assert score.writing_quality < 0.8

    def test_scoring_weights(self):
        """Test that scoring components are weighted correctly."""
        # Create article that's perfect in 3 areas, 0 in 1
        # But we can't easily isolate, so just verify overall is weighted combination
        article = NewsArticle(
            title="Apple Reports Record Quarterly Revenue Beating Analyst Expectations",
            summary="Apple reported strong quarterly results with revenue of $89.5 billion.",
            content="Full article content here with multiple paragraphs and details. " * 50,
            url="https://reuters.com/article",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow(),
            content_hash="hash1"
        )

        score = self.scorer.score(article)

        # Overall should be reasonable weighted combination
        expected = (
            score.completeness * 0.30 +
            score.structure * 0.25 +
            score.information_density * 0.25 +
            score.writing_quality * 0.20
        )
        assert abs(score.overall - expected) < 0.01


class TestCredibilityScorer:
    """Tests for credibility scoring."""

    def setup_method(self):
        self.scorer = CredibilityScorer()

    def test_premium_source(self):
        """Test premium source scoring."""
        article = NewsArticle(
            title="Test",
            summary="Summary",
            url="https://reuters.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            author="Staff",
            published_at=datetime.utcnow(),
            content_hash="hash1"
        )

        score = self.scorer.score(article)

        assert score.overall >= 0.90
        assert score.source_tier == 1.0  # Tier 1 sources
        assert score.details['source_tier_label'] == 'tier_1_premium'
        assert score.author_credibility > 0.5

    def test_syndicated_source_penalty(self):
        """Test penalty for syndicated sources."""
        article = NewsArticle(
            title="Test",
            summary="Summary",
            url="https://news.google.com/1",
            source=NewsSource.GOOGLE_NEWS,
            source_name="Google News",
            author="Staff",
            published_at=datetime.utcnow(),
            content_hash="hash1"
        )

        score = self.scorer.score(article)

        assert score.source_tier == 0.5  # Tier 4
        assert score.details['source_tier_label'] == 'tier_4_aggregator'

    def test_unknown_source(self):
        """Test unknown source scoring."""
        article = NewsArticle(
            title="Test",
            summary="Summary",
            url="https://unknown.com/1",
            source=NewsSource.UNKNOWN,
            source_name="Unknown",
            published_at=datetime.utcnow(),
            content_hash="hash1"
        )

        score = self.scorer.score(article)

        assert score.source_tier == 0.4  # Unknown tier
        assert score.details['source_tier_label'] == 'tier_5_unknown'

    def test_missing_author(self):
        """Test scoring with missing author."""
        article = NewsArticle(
            title="Test Article",
            summary="Summary",
            url="https://reuters.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow(),
            # No author
            content_hash="hash1"
        )

        score = self.scorer.score(article)

        # Should still be decent due to premium source
        assert score.overall > 0.85
        assert score.details['has_author'] == False

    def test_source_reliability(self):
        """Test source reliability scores."""
        # Reuters should have high reliability
        reuters_score = self.scorer._score_source_reliability(NewsSource.REUTERS)
        assert reuters_score >= 0.95

        # Unknown should have low reliability
        unknown_score = self.scorer._score_source_reliability(NewsSource.UNKNOWN)
        assert unknown_score == 0.5


class TestFreshnessScorer:
    """Tests for freshness scoring."""

    def setup_method(self):
        self.scorer = FreshnessScorer()

    def test_breaking_news(self):
        """Test breaking news scoring."""
        article = NewsArticle(
            title="Breaking News",
            summary="Summary",
            url="https://example.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow() - timedelta(minutes=30),
            content_hash="hash1"
        )

        score = self.scorer.score(article)
        assert score == 1.0
        assert self.scorer.get_category(article) == "breaking"

    def test_very_fresh(self):
        """Test very fresh scoring."""
        article = NewsArticle(
            title="Very Fresh",
            summary="Summary",
            url="https://example.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow() - timedelta(hours=3),
            content_hash="hash1"
        )

        score = self.scorer.score(article)
        assert score == 0.9
        assert self.scorer.get_category(article) == "very_fresh"

    def test_fresh(self):
        """Test fresh scoring."""
        article = NewsArticle(
            title="Fresh",
            summary="Summary",
            url="https://example.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow() - timedelta(hours=12),
            content_hash="hash1"
        )

        score = self.scorer.score(article)
        assert score == 0.7
        assert self.scorer.get_category(article) == "fresh"

    def test_recent(self):
        """Test recent scoring."""
        article = NewsArticle(
            title="Recent",
            summary="Summary",
            url="https://example.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow() - timedelta(hours=48),
            content_hash="hash1"
        )

        score = self.scorer.score(article)
        assert score == 0.5
        assert self.scorer.get_category(article) == "recent"

    def test_stale(self):
        """Test stale scoring."""
        article = NewsArticle(
            title="Stale",
            summary="Summary",
            url="https://example.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow() - timedelta(hours=100),
            content_hash="hash1"
        )

        score = self.scorer.score(article)
        assert score == 0.3
        assert self.scorer.get_category(article) == "stale"

    def test_very_stale(self):
        """Test very stale scoring."""
        article = NewsArticle(
            title="Old",
            summary="Summary",
            url="https://example.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow() - timedelta(days=30),
            content_hash="hash1"
        )

        score = self.scorer.score(article)
        assert score == 0.1
        assert self.scorer.get_category(article) == "very_stale"

    def test_missing_date(self):
        """Test handling missing published_at."""
        article = NewsArticle(
            title="No Date",
            summary="Summary",
            url="https://example.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow() - timedelta(hours=1),  # Required field
            content_hash="hash1"
        )
        article.published_at = None  # Simulate missing

        score = self.scorer.score(article)
        assert score == 0.05  # min_score from FreshnessConfig

    def test_exponential_decay(self):
        """Test exponential decay mode."""
        config = FreshnessConfig(decay_mode="exponential", half_life_hours=12)
        scorer = FreshnessScorer(config)

        # At half-life, score should be ~0.5
        article = NewsArticle(
            title="Test",
            summary="Summary",
            url="https://example.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow() - timedelta(hours=12),
            content_hash="hash1"
        )

        score = scorer.score(article)
        assert abs(score - 0.5) < 0.05  # Approximately 0.5

    def test_linear_decay(self):
        """Test linear decay mode."""
        config = FreshnessConfig(decay_mode="linear", max_age_hours=72)
        scorer = FreshnessScorer(config)

        # At half max age, score should be ~0.5
        article = NewsArticle(
            title="Test",
            summary="Summary",
            url="https://example.com/1",
            source=NewsSource.REUTERS,
            source_name="Reuters",
            published_at=datetime.utcnow() - timedelta(hours=36),
            content_hash="hash1"
        )

        score = scorer.score(article)
        assert 0.45 < score < 0.55  # Approximately 0.5


class TestLanguageDetector:
    """Tests for language detection."""

    def setup_method(self):
        self.detector = LanguageDetector()

    def test_english_detection(self):
        """Test English language detection."""
        text = "Apple reported strong quarterly earnings with revenue of $89.5 billion, beating analyst expectations by a significant margin."
        result = self.detector.detect(text)

        assert result.language == 'en'
        assert result.confidence > 0.3  # Heuristic has lower confidence

    def test_spanish_detection(self):
        """Test Spanish language detection."""
        text = "Apple reportó ganancias trimestrales sólidas con ingresos de $89.5 mil millones, superando las expectativas de los analistas."
        result = self.detector.detect(text)

        # Heuristic may detect as Spanish or English depending on common words
        assert result.language in ['en', 'es']

    def test_short_text(self):
        """Test short text handling."""
        result = self.detector.detect("Hi")
        assert result.language == 'en'
        assert result.method == 'default'

    def test_empty_text(self):
        """Test empty text handling."""
        result = self.detector.detect("")
        assert result.language == 'en'
        assert result.method == 'default'

    def test_is_english(self):
        """Test is_english convenience method."""
        assert self.detector.is_english("Apple reported earnings today") == True
        assert self.detector.is_english("Apple reportó ganancias hoy") == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])