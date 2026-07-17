"""
News Dashboard Components - Latest News, Top Headlines, News Timeline, News Sentiment, Source Breakdown
"""

import streamlit as st
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from data.news.schemas import NewsSource, NewsCategory, SentimentLabel


def render_news_dashboard_tab(company: str, ticker: Optional[str] = None):
    """Render comprehensive news dashboard tab."""
    st.subheader(f"📰 News Intelligence: {company}" + (f" ({ticker})" if ticker else ""))
    
    # Fetch news data via API
    news_data = fetch_news_data(company, ticker)
    
    if not news_data or not news_data.get("articles"):
        st.info("No news articles found for this company in the selected period.")
        return
    
    articles = news_data.get("articles", [])
    summary = news_data.get("summary", {})
    
    # Create tabs for different views
    tab_news, tab_timeline, tab_sentiment, tab_sources, tab_companies = st.tabs([
        "📋 Latest News", 
        "📅 Timeline", 
        "📊 Sentiment", 
        "📈 Sources", 
        "🏢 Companies"
    ])
    
    with tab_news:
        render_latest_news(articles)
    
    with tab_timeline:
        render_news_timeline(articles)
    
    with tab_sentiment:
        render_news_sentiment(articles, summary)
    
    with tab_sources:
        render_source_breakdown(articles)
    
    with tab_companies:
        render_related_companies(articles, summary)


def fetch_news_data(company: str, ticker: Optional[str] = None, lookback_hours: int = 48) -> Optional[Dict[str, Any]]:
    """Fetch news data from API."""
    try:
        response = requests.post(
            "http://financial-research-api:8000/api/v1/news/aggregate",
            json={
                "company": company,
                "ticker": ticker,
                "lookback_hours": lookback_hours,
                "max_articles": 100,
                "min_relevance": 0.2
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch news data: {e}")
        return None


def render_latest_news(articles: List[Dict[str, Any]]):
    """Render latest news articles with filtering and sorting."""
    st.markdown("### Latest News Articles")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        source_filter = st.multiselect(
            "Filter by Source",
            options=list(set(a.get("source", "Unknown") for a in articles)),
            default=[]
        )
    with col2:
        category_filter = st.multiselect(
            "Filter by Category",
            options=list(set(a.get("category", "General") for a in articles if a.get("category"))),
            default=[]
        )
    with col3:
        sentiment_filter = st.multiselect(
            "Filter by Sentiment",
            options=["Positive", "Negative", "Neutral"],
            default=[]
        )
    with col3:
        sort_by = st.selectbox(
            "Sort By",
            options=["Relevance", "Importance", "Market Impact", "Freshness", "Date"],
            index=0
        )
    
    # Apply filters
    filtered = articles
    if source_filter:
        filtered = [a for a in filtered if a.get("source") in source_filter]
    if category_filter:
        filtered = [a for a in filtered if a.get("category") in category_filter]
    if sentiment_filter:
        filtered = [a for a in filtered if a.get("sentiment", {}).get("label", "").capitalize() in sentiment_filter]
    
    # Sort
    sort_key_map = {
        "Relevance": "relevance_score",
        "Importance": "importance_score",
        "Market Impact": "market_impact_score",
        "Freshness": "freshness_score",
        "Date": "published_at"
    }
    sort_key = sort_key_map.get(sort_by, "relevance_score")
    filtered.sort(key=lambda a: a.get(sort_key, 0), reverse=True)
    
    st.markdown(f"**Showing {len(filtered)} of {len(articles)} articles**")
    
    # Display articles
    for i, article in enumerate(filtered[:50]):
        render_article_card(article, i)


def render_article_card(article: Dict[str, Any], index: int):
    """Render a single article card."""
    # Determine sentiment badge
    sentiment = article.get("sentiment", {})
    sentiment_label = sentiment.get("label", "neutral").capitalize()
    sentiment_score = sentiment.get("score", 0)
    
    sentiment_colors = {
        "Positive": "🟢",
        "Negative": "🔴", 
        "Neutral": "⚪"
    }
    
    # Importance indicator
    importance = article.get("importance_score", 0)
    market_impact = article.get("market_impact_score", 0)
    relevance = article.get("relevance_score", 0)
    
    with st.container():
        col1, col2 = st.columns([1, 20])
        
        with col1:
            # Sentiment indicator
            st.markdown(f"<h3>{sentiment_colors.get(sentiment_label, '⚪')}</h3>", unsafe_allow_html=True)
        
        with col2:
            # Title and source
            title = article.get("title", "Untitled")
            source = article.get("source", "Unknown")
            published = article.get("published_at", "")
            
            st.markdown(f"**{title}**")
            st.caption(f"📰 {source} | 📅 {published[:16] if published else 'N/A'}")
            
            # Metrics row
            met_col1, met_col2, met_col3, met_col4 = st.columns(4)
            with met_col1:
                st.metric("Relevance", f"{relevance:.0%}")
            with met_col2:
                st.metric("Importance", f"{importance:.0%}")
            with met_col3:
                st.metric("Market Impact", f"{market_impact:.0%}")
            with met_col4:
                st.metric("Sentiment", f"{sentiment_score:+.2f}")
            
            # Summary
            summary = article.get("summary", "")
            if summary:
                st.write(summary[:300] + ("..." if len(summary) > 300 else ""))
            
            # Entities
            entities = []
            if article.get("companies"):
                entities.extend([f"🏢 {c.get('name', '')}" for c in article["companies"][:3]])
            if article.get("tickers"):
                entities.extend([f"📈 ${t}" for t in article["tickers"][:3]])
            if article.get("people"):
                entities.extend([f"👤 {p.get('name', '')}" for p in article["people"][:2]])
            
            if entities:
                st.caption(" | ".join(entities))
            
            # Events
            events = article.get("events", [])
            if events:
                event_strs = [f"{e.get('event_type', '').replace('_', ' ').title()} ({e.get('confidence', 0):.0%})" for e in events[:3]]
                st.caption("Events: " + ", ".join(event_strs))
            
            # Read more link
            url = article.get("url")
            if url:
                st.link_button("📖 Read Full Article", url)
        
        st.divider()


def render_news_timeline(articles: List[Dict[str, Any]]):
    """Render interactive news timeline."""
    st.markdown("### News Timeline")
    
    if not articles:
        st.info("No articles to display")
        return
    
    # Prepare data for timeline
    timeline_data = []
    for a in articles:
        try:
            pub_date = datetime.fromisoformat(a.get("published_at", "").replace("Z", "+00:00"))
            timeline_data.append({
                "Date": pub_date,
                "Title": a.get("title", "Untitled")[:80],
                "Source": a.get("source", "Unknown"),
                "Sentiment": a.get("sentiment", {}).get("label", "neutral").capitalize(),
                "Sentiment Score": a.get("sentiment", {}).get("score", 0),
                "Importance": a.get("importance_score", 0),
                "Market Impact": a.get("market_impact_score", 0),
                "Relevance": a.get("relevance_score", 0),
                "URL": a.get("url", "")
            })
        except:
            continue
    
    if not timeline_data:
        st.info("No valid timeline data")
        return
    
    df = pd.DataFrame(timeline_data)
    df = df.sort_values("Date")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        min_date = df["Date"].min().date()
        max_date = df["Date"].max().date()
        start_date = st.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
    
    # Filter by date
    mask = (df["Date"].dt.date >= start_date) & (df["Date"].dt.date <= end_date)
    df_filtered = df[mask]
    
    # Plotly timeline
    fig = px.scatter(
        df_filtered,
        x="Date",
        y="Importance",
        color="Sentiment",
        size="Market Impact",
        hover_data=["Title", "Source", "Relevance", "Sentiment Score"],
        color_discrete_map={
            "Positive": "#059669",
            "Negative": "#dc2626",
            "Neutral": "#6b7280"
        },
        title="News Timeline: Importance vs Time (Size = Market Impact)"
    )
    
    fig.update_layout(
        height=500,
        xaxis_title="Date",
        yaxis_title="Importance Score",
        hovermode="closest"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Article count over time
    daily_counts = df_filtered.groupby(df_filtered["Date"].dt.date).size().reset_index(name="Count")
    daily_counts.columns = ["Date", "Article Count"]
    
    fig2 = px.bar(
        daily_counts,
        x="Date",
        y="Article Count",
        title="Daily Article Volume"
    )
    fig2.update_layout(height=300)
    st.plotly_chart(fig2, use_container_width=True)


def render_news_sentiment(articles: List[Dict[str, Any]], summary: Dict[str, Any]):
    """Render news sentiment analysis."""
    st.markdown("### News Sentiment Analysis")
    
    # Overall sentiment from summary
    if summary:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            overall = summary.get("overall_sentiment", "Neutral")
            st.metric("Overall Sentiment", overall)
        with col2:
            score = summary.get("sentiment_score", 0)
            st.metric("Sentiment Score", f"{score:+.2f}")
        with col3:
            dist = summary.get("sentiment_distribution", {})
            st.metric("Positive", dist.get("positive", 0))
        with col4:
            st.metric("Negative", dist.get("negative", 0))
    
    # Sentiment distribution chart
    sentiments = [a.get("sentiment", {}).get("label", "neutral").capitalize() for a in articles if a.get("sentiment")]
    if sentiments:
        sent_counts = pd.Series(sentiments).value_counts()
        
        fig = px.pie(
            values=sent_counts.values,
            names=sent_counts.index,
            title="Sentiment Distribution",
            color=sent_counts.index,
            color_discrete_map={
                "Positive": "#059669",
                "Negative": "#dc2626",
                "Neutral": "#6b7280"
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Sentiment over time
    sentiment_data = []
    for a in articles:
        if a.get("sentiment"):
            try:
                pub_date = datetime.fromisoformat(a.get("published_at", "").replace("Z", "+00:00"))
                sentiment_data.append({
                    "Date": pub_date,
                    "Score": a.get("sentiment", {}).get("score", 0),
                    "Label": a.get("sentiment", {}).get("label", "neutral").capitalize(),
                    "Title": a.get("title", "")[:50]
                })
            except:
                continue
    
    if sentiment_data:
        df_sent = pd.DataFrame(sentiment_data)
        df_sent = df_sent.sort_values("Date")
        
        fig = px.scatter(
            df_sent,
            x="Date",
            y="Score",
            color="Label",
            hover_data=["Title"],
            color_discrete_map={
                "Positive": "#059669",
                "Negative": "#dc2626",
                "Neutral": "#6b7280"
            },
            title="Sentiment Score Over Time"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Rolling average
        df_sent["Rolling Avg"] = df_sent["Score"].rolling(window=5, min_periods=1).mean()
        fig2 = px.line(
            df_sent,
            x="Date",
            y=["Score", "Rolling Avg"],
            title="Sentiment Trend (with 5-article rolling average)"
        )
        fig2.update_layout(height=300)
        st.plotly_chart(fig2, use_container_width=True)
    
    # Key drivers
    if summary and "top_events" in summary:
        st.markdown("### Key Events Driving Sentiment")
        for event in summary["top_events"][:10]:
            event_type = event.get("event_type", "").replace("_", " ").title()
            confidence = event.get("confidence", 0)
            with st.expander(f"{event_type} (Confidence: {confidence:.0%})"):
                st.write(f"**Source:** {event.get('source', 'Unknown')}")
                st.write(f"**Article:** {event.get('article_title', 'N/A')}")
                st.write(f"**Published:** {event.get('published_at', 'N/A')}")
                if event.get("details"):
                    st.json(event["details"])


def render_source_breakdown(articles: List[Dict[str, Any]]):
    """Render source credibility and breakdown."""
    st.markdown("### Source Analysis")
    
    # Source counts
    source_counts = {}
    for a in articles:
        src = a.get("source", "Unknown")
        source_counts[src] = source_counts.get(src, 0) + 1
    
    if not source_counts:
        st.info("No source data available")
        return
    
    # Source distribution
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Bar chart
        df_sources = pd.DataFrame(list(source_counts.items()), columns=["Source", "Count"])
        df_sources = df_sources.sort_values("Count", ascending=True)
        
        fig = px.bar(
            df_sources,
            x="Count",
            y="Source",
            orientation="h",
            title="Articles by Source"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Credibility scores
        st.markdown("#### Source Credibility Scores")
        for src in sorted(source_counts.keys()):
            count = source_counts[src]
            credibility = get_source_credibility(src)
            st.progress(credibility, text=f"{src}: {credibility:.0%} ({count} articles)")
    
    # Source reliability table
    st.markdown("#### Source Details")
    source_details = []
    for src, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        credibility = get_source_credibility(src)
        tier = get_source_tier(src)
        source_details.append({
            "Source": src,
            "Articles": count,
            "Credibility": f"{credibility:.0%}",
            "Tier": tier,
            "Share": f"{count/len(articles)*100:.1f}%"
        })
    
    df_sources = pd.DataFrame(source_details)
    st.dataframe(df_sources, use_container_width=True, hide_index=True)


def render_related_companies(articles: List[Dict[str, Any]], summary: Dict[str, Any]):
    """Render related companies analysis."""
    st.markdown("### Related Companies")
    
    # From summary
    if summary and "related_companies" in summary:
        related = summary["related_companies"]
        if related:
            df_companies = pd.DataFrame([
                {
                    "Company": c.get("name", "Unknown"),
                    "Ticker": c.get("ticker", "N/A"),
                    "Mentions": c.get("mention_count", 0),
                    "Primary": "⭐" if c.get("is_primary") else "",
                    "Avg Sentiment": f"{c.get('sentiment', 0):+.2f}" if c.get("sentiment") else "N/A",
                    "Sources": len(c.get("sources", [])),
                }
                for c in related[:20]
            ])
            
            st.dataframe(df_companies, use_container_width=True, hide_index=True)
    
    # Company co-mentions network
    st.markdown("#### Company Co-Mentions")
    company_pairs = defaultdict(int)
    for a in articles:
        companies = [c.get("name", "") for c in a.get("companies", []) if c.get("name")]
        for i, c1 in enumerate(companies):
            for c2 in companies[i+1:]:
                pair = tuple(sorted([c1, c2]))
                company_pairs[pair] += 1
    
    if company_pairs:
        top_pairs = sorted(company_pairs.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Create network visualization data
        nodes = set()
        edges = []
        for (c1, c2), count in top_pairs:
            nodes.add(c1)
            nodes.add(c2)
            edges.append({"source": c1, "target": c2, "weight": count})
        
        # Simple network display
        st.markdown("**Top Company Co-Mentions:**")
        for (c1, c2), count in top_pairs[:10]:
            st.write(f"🔗 **{c1}** ↔ **{c2}** — {count} co-mentions")


def get_source_credibility(source: str) -> float:
    """Get credibility score for a news source."""
    tier_1 = {
        "reuters": 1.0, "bloomberg": 1.0, "financial_times": 0.95,
        "wall_street_journal": 0.95, "newsapi": 0.9
    }
    tier_2 = {
        "cnbc": 0.85, "marketwatch": 0.8, "benzinga": 0.75,
        "seeking_alpha": 0.7, "yahoo_finance": 0.7
    }
    tier_3 = {
        "finnhub": 0.7, "alpha_vantage": 0.7, "google_news": 0.6, "unknown": 0.5
    }
    
    src_lower = source.lower().replace(" ", "_")
    if src_lower in tier_1:
        return tier_1[src_lower]
    if src_lower in tier_2:
        return tier_2[src_lower]
    if src_lower in tier_3:
        return tier_3[src_lower]
    return 0.5


def get_source_tier(source: str) -> str:
    """Get tier label for a news source."""
    tier_1 = {"reuters", "bloomberg", "financial_times", "wall_street_journal", "newsapi"}
    tier_2 = {"cnbc", "marketwatch", "benzinga", "seeking_alpha", "yahoo_finance"}
    tier_3 = {"finnhub", "alpha_vantage", "google_news", "unknown"}
    
    src_lower = source.lower().replace(" ", "_")
    if src_lower in tier_1:
        return "Tier 1 (Primary)"
    if src_lower in tier_2:
        return "Tier 2 (Major)"
    if src_lower in tier_3:
        return "Tier 3 (Other)"
    return "Tier 3 (Other)"


# Add news tab to main dashboard
def add_news_tab_to_dashboard():
    """Integration point for adding news tab to main dashboard."""
    # This function documents where to add the news tab in dashboard/app.py
    # In display_results() function, add "News Intelligence" to tab_names
    # Then add corresponding render_news_dashboard_tab() call
    pass


# API endpoints for news data (to be added to api/main.py)
"""
@router.post("/news/aggregate")
async def aggregate_news(request: NewsAggregateRequest):
    \"\"\"Aggregate news for a company.\"\"\"
    aggregator = NewsAggregator()
    try:
        enrichments = await aggregator.aggregate(
            company=request.company,
            ticker=request.ticker,
            lookback_hours=request.lookback_hours,
            max_articles=request.max_articles,
            min_relevance=request.min_relevance
        )
        
        # Extract intelligence
        intelligence = CompanyNewsIntelligence()
        results = []
        for e in enrichments:
            intel = await intelligence.extract_intelligence(e.article)
            results.append(intel)
        
        # Summarize
        company_intel = {}
        # ... aggregate by company
        
        summarizer = NewsSummarizer()
        summary = await summarizer.summarize(
            [e.article for e in enrichments],
            results,
            company_intel,
            request.lookback_hours
        )
        
        return {
            "articles": [e.article.model_dump() for e in enrichments],
            "summary": summary.model_dump(),
            "company_intelligence": {k: v.to_dict() for k, v in company_intel.items()}
        }
    finally:
        await aggregator.close()
"""