"""
Dashboard Components - Phase 5

Streamlit dashboard components for Knowledge Graph, Portfolio, Alerts, Analytics, and Patterns.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta
from typing import Any, Optional
import json


def render_knowledge_graph_tab(kg_client) -> None:
    """Render Knowledge Graph tab in dashboard."""
    st.header("🔗 Knowledge Graph")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Graph Explorer", "🔍 Entity Search", "📈 Analytics", "⚙️ Management"
    ])
    
    with tab1:
        st.subheader("Knowledge Graph Explorer")
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            st.markdown("**Filters**")
            entity_types = st.multiselect(
                "Entity Types",
                ["Company", "Person", "Product", "Event", "Filing", "Metric", "Sector"],
                default=["Company"]
            )
            
            relationship_types = st.multiselect(
                "Relationship Types",
                ["HAS_TICKER", "LISTED_ON", "CEO_OF", "COMPETES_WITH", "PARTNERS_WITH", 
                 "HAS_METRIC", "FILED", "REPORTED_IN", "HAS_VALUE"],
                default=["HAS_TICKER", "CEO_OF", "COMPETES_WITH"]
            )
            
            max_nodes = st.slider("Max Nodes", 10, 200, 50)
            layout = st.selectbox("Layout", ["force", "hierarchical", "circular"])
            
            if st.button("🔄 Refresh Graph"):
                st.rerun()
        
        with col1:
            st.info("Knowledge Graph visualization would render here using Cytoscape.js or similar. "
                    "The graph shows entities as nodes and relationships as edges.")
            
            # Placeholder for graph visualization
            st.markdown("""
            **Graph Features:**
            - Interactive node/edge exploration
            - Click nodes to see details
            - Filter by entity/relationship type
            - Export subgraphs
            - Path finding between entities
            """)
    
    with tab2:
        st.subheader("Entity Search")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            search_query = st.text_input("Search entities...", placeholder="e.g., Apple, AAPL, Tim Cook")
        with col2:
            entity_type_filter = st.selectbox("Type", ["All", "Company", "Person", "Product", "Event"])
        
        if search_query:
            st.info(f"Searching for: {search_query}")
            # Would call kg_client.find_entities(search_query, entity_type_filter)
            st.dataframe(pd.DataFrame({
                "Entity": ["Apple Inc.", "AAPL", "Tim Cook"],
                "Type": ["Company", "Ticker", "Person"],
                "Properties": ["{'sector': 'Technology'}", "{'exchange': 'NASDAQ'}", "{'title': 'CEO'}"],
                "Confidence": [0.95, 0.99, 0.92]
            }))
    
    with tab3:
        st.subheader("Graph Analytics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Entities", "12,345")
        with col2:
            st.metric("Total Relationships", "89,234")
        with col3:
            st.metric("Graph Density", "0.023%")
        
        st.subheader("Entity Type Distribution")
        entity_data = pd.DataFrame({
            "Type": ["Company", "Person", "Filing", "Metric", "Event", "Product"],
            "Count": [3421, 892, 1567, 4321, 567, 234]
        })
        fig = px.bar(entity_data, x="Type", y="Count", title="Entities by Type")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Relationship Type Distribution")
        rel_data = pd.DataFrame({
            "Type": ["HAS_TICKER", "CEO_OF", "COMPETES_WITH", "PARTNERS_WITH", "HAS_METRIC", "FILED"],
            "Count": [3421, 215, 189, 432, 4321, 1567]
        })
        fig = px.pie(rel_data, values="Count", names="Type", title="Relationships by Type")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.subheader("Graph Management")
        
        col1, col2 = st.columns(2)
        with col1:
            st.button("🔄 Rebuild Graph Index", help="Rebuild search indexes")
            st.button("📥 Export Graph (GraphML)", help="Export as GraphML")
            st.button("📥 Export Graph (JSON)", help="Export as JSON")
        with col2:
            st.button("🧹 Clear Stale Entities", help="Remove entities not updated in 90 days")
            st.button("🔗 Rebuild Relationships", help="Recompute relationships from source data")
            st.button("📊 Generate Report", help="Generate graph health report")


def render_portfolio_tab(portfolio_client) -> None:
    """Render Portfolio Management tab."""
    st.header("💼 Portfolio Management")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", "📈 Positions", "📋 Orders", "⚖️ Risk", "🔧 Rebalance"
    ])
    
    with tab1:
        st.subheader("Portfolio Overview")
        
        # Portfolio selector
        portfolios = ["Main Portfolio", "Retirement", "Trading", "Crypto"]
        selected = st.selectbox("Select Portfolio", portfolios)
        
        # Key metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Value", "$1,234,567", "+$12,345 (1.0%)")
        with col2:
            st.metric("Cash", "$123,456", "-$5,000")
        with col3:
            st.metric("Day P&L", "+$5,432", "+0.44%")
        with col4:
            st.metric("Total P&L", "+$145,678", "+13.4%")
        with col5:
            st.metric("Sharpe Ratio", "1.34", "+0.12")
        
        # Performance chart
        st.subheader("Performance")
        dates = pd.date_range(end=datetime.today(), periods=252)
        values = np.cumsum(np.random.randn(252) * 0.01 + 0.0005) * 1000000 + 1000000
        df = pd.DataFrame({"Date": dates, "Value": values})
        fig = px.line(df, x="Date", y="Value", title="Portfolio Value")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Positions")
        
        positions_df = pd.DataFrame({
            "Symbol": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
            "Quantity": [100, 50, 25, 15, 30],
            "Avg Cost": [150.00, 280.00, 120.00, 3200.00, 250.00],
            "Current Price": [175.50, 320.25, 135.75, 3350.00, 265.00],
            "Market Value": [17550, 16012, 3393, 50250, 7950],
            "P&L": ["+2550", "+2012", "+393", "+2250", "+450"],
            "P&L %": ["+17.0%", "+14.4%", "+13.1%", "+4.7%", "+6.0%"],
            "Weight": ["18.2%", "16.6%", "3.5%", "52.0%", "8.2%"]
        })
        st.dataframe(positions_df, use_container_width=True)
    
    with tab3:
        st.subheader("Orders")
        
        tab_open, tab_history = st.tabs(["Open Orders", "History"])
        
        with tab_open:
            orders_df = pd.DataFrame({
                "Symbol": ["NVDA", "JPM"],
                "Side": ["BUY", "SELL"],
                "Type": ["LIMIT", "MARKET"],
                "Quantity": [20, 50],
                "Price": [450.00, 145.00],
                "Status": ["PENDING", "PENDING"],
                "Created": ["2024-01-15 09:30", "2024-01-15 10:15"]
            })
            st.dataframe(orders_df, use_container_width=True)
        
        with tab_history:
            hist_df = pd.DataFrame({
                "Symbol": ["AAPL", "MSFT", "GOOGL"],
                "Side": ["BUY", "BUY", "SELL"],
                "Quantity": [100, 50, 10],
                "Price": [150.00, 280.00, 135.00],
                "Filled": ["2024-01-10", "2024-01-12", "2024-01-14"],
                "P&L": ["+2550", "+2012", "-150"]
            })
            st.dataframe(hist_df, use_container_width=True)
    
    with tab4:
        st.subheader("Risk Metrics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("VaR (95%)", "-2.3%", "-0.1%")
            st.metric("CVaR (95%)", "-3.8%", "-0.2%")
            st.metric("Max Drawdown", "-12.5%", "-0.5%")
        with col2:
            st.metric("Volatility (Ann.)", "18.2%", "+0.3%")
            st.metric("Downside Vol", "12.1%", "+0.2%")
            st.metric("Sharpe Ratio", "1.34", "+0.05")
        with col3:
            st.metric("Sortino Ratio", "1.89", "+0.08")
            st.metric("Calmar Ratio", "0.87", "+0.03")
            st.metric("Sortino Ratio", "1.89", "+0.08")
        
        st.subheader("Drawdown Analysis")
        dates = pd.date_range(end=datetime.today(), periods=252)
        dd = np.abs(np.cumsum(np.random.randn(252) * 0.005) - 1)
        fig = px.area(pd.DataFrame({"Date": dates, "Drawdown": dd}), x="Date", y="Drawdown", title="Historical Drawdown")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Exposure Analysis")
        exposure_df = pd.DataFrame({
            "Sector": ["Technology", "Healthcare", "Financials", "Consumer", "Industrial", "Energy"],
            "Weight": [45.2, 18.5, 12.3, 15.6, 5.8, 2.7],
            "Benchmark": [28.5, 14.2, 11.8, 10.2, 8.1, 4.5]
        })
        fig = px.bar(exposure_df, x="Sector", y=["Weight", "Benchmark"], 
                     title="Sector Exposure vs Benchmark", barmode="group")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        st.subheader("Portfolio Rebalancing")
        
        col1, col2 = st.columns(2)
        with col1:
            strategy = st.selectbox(
                "Rebalancing Strategy",
                ["Equal Weight", "Market Cap", "Risk Parity", "Minimum Variance", "Max Sharpe"]
            )
            target_date = st.date_input("Target Date", date.today() + timedelta(days=7))
            dry_run = st.checkbox("Dry Run", value=True)
        
        with col2:
            if st.button("🔄 Generate Rebalance Plan"):
                st.success("Rebalance plan generated!")
                plan_df = pd.DataFrame({
                    "Symbol": ["AAPL", "MSFT", "GOOGL", "NVDA", "JPM"],
                    "Current Weight": [18.2, 16.6, 3.5, 52.0, 8.2],
                    "Target Weight": [20.0, 20.0, 20.0, 20.0, 20.0],
                    "Action": ["BUY", "BUY", "BUY", "SELL", "BUY"],
                    "Quantity": [10, 10, 38, -48, 60],
                    "Est. Cost": [1755, 3202, 5157, -16080, 1590]
                })
                st.dataframe(plan_df, use_container_width=True)
                
                if st.button("✅ Execute Rebalance", type="primary"):
                    st.success("Rebalance executed!")
    
    with tab2:
        st.subheader("Positions")
        
        positions_df = pd.DataFrame({
            "Symbol": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
            "Quantity": [100, 50, 25, 15, 30],
            "Avg Cost": [150.00, 280.00, 120.00, 3200.00, 250.00],
            "Current Price": [175.50, 320.25, 135.75, 3350.00, 265.00],
            "Market Value": [17550, 16012, 3393, 50250, 7950],
            "P&L": ["+2550", "+2012", "+393", "+2250", "+450"],
            "P&L %": ["+17.0%", "+14.4%", "+13.1%", "+4.7%", "+6.0%"],
            "Weight": ["18.2%", "16.6%", "3.5%", "52.0%", "8.2%"]
        })
        st.dataframe(positions_df, use_container_width=True)
    
    with tab3:
        st.subheader("Orders")
        
        tab_open, tab_history = st.tabs(["Open Orders", "History"])
        
        with tab_open:
            orders_df = pd.DataFrame({
                "Symbol": ["NVDA", "JPM"],
                "Side": ["BUY", "SELL"],
                "Type": ["LIMIT", "MARKET"],
                "Quantity": [20, 50],
                "Price": [450.00, 145.00],
                "Status": ["PENDING", "PENDING"],
                "Created": ["2024-01-15 09:30", "2024-01-15 10:15"]
            })
            st.dataframe(orders_df, use_container_width=True)
        
        with tab_history:
            hist_df = pd.DataFrame({
                "Symbol": ["AAPL", "MSFT", "GOOGL"],
                "Side": ["BUY", "BUY", "SELL"],
                "Quantity": [100, 50, 10],
                "Price": [150.00, 280.00, 135.00],
                "Filled": ["2024-01-10", "2024-01-12", "2024-01-14"],
                "P&L": ["+2550", "+2012", "-150"]
            })
            st.dataframe(hist_df, use_container_width=True)
    
    with tab4:
        st.subheader("Risk Metrics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("VaR (95%)", "-2.3%", "-0.1%")
            st.metric("CVaR (95%)", "-3.8%", "-0.2%")
            st.metric("Max Drawdown", "-12.5%", "-0.5%")
        with col2:
            st.metric("Volatility (Ann.)", "18.2%", "+0.3%")
            st.metric("Downside Vol", "12.1%", "+0.2%")
            st.metric("Sharpe Ratio", "1.34", "+0.05")
        with col3:
            st.metric("Sortino Ratio", "1.89", "+0.08")
            st.metric("Calmar Ratio", "0.87", "+0.03")
            st.metric("Sortino Ratio", "1.89", "+0.08")
        
        st.subheader("Drawdown Analysis")
        dates = pd.date_range(end=datetime.today(), periods=252)
        dd = np.abs(np.cumsum(np.random.randn(252) * 0.005) - 1)
        fig = px.area(pd.DataFrame({"Date": dates, "Drawdown": dd}), x="Date", y="Drawdown", title="Historical Drawdown")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Exposure Analysis")
        exposure_df = pd.DataFrame({
            "Sector": ["Technology", "Healthcare", "Financials", "Consumer", "Industrial", "Energy"],
            "Weight": [45.2, 18.5, 12.3, 15.6, 5.8, 2.7],
            "Benchmark": [28.5, 14.2, 11.8, 10.2, 8.1, 4.5]
        })
        fig = px.bar(exposure_df, x="Sector", y=["Weight", "Benchmark"], 
                     title="Sector Exposure vs Benchmark", barmode="group")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        st.subheader("Portfolio Rebalancing")
        
        col1, col2 = st.columns(2)
        with col1:
            strategy = st.selectbox(
                "Rebalancing Strategy",
                ["Equal Weight", "Market Cap", "Risk Parity", "Minimum Variance", "Max Sharpe"]
            )
            target_date = st.date_input("Target Date", date.today() + timedelta(days=7))
            dry_run = st.checkbox("Dry Run", value=True)
        
        with col2:
            if st.button("🔄 Generate Rebalance Plan"):
                st.success("Rebalance plan generated!")
                plan_df = pd.DataFrame({
                    "Symbol": ["AAPL", "MSFT", "GOOGL", "NVDA", "JPM"],
                    "Current Weight": [18.2, 16.6, 3.5, 52.0, 8.2],
                    "Target Weight": [20.0, 20.0, 20.0, 20.0, 20.0],
                    "Action": ["BUY", "BUY", "BUY", "SELL", "BUY"],
                    "Quantity": [10, 10, 38, -48, 60],
                    "Est. Cost": [1755, 3202, 5157, -16080, 1590]
                })
                st.dataframe(plan_df, use_container_width=True)
                
                if st.button("✅ Execute Rebalance", type="primary"):
                    st.success("Rebalance executed!")
    
    with tab2:
        st.subheader("Positions")
        
        positions_df = pd.DataFrame({
            "Symbol": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
            "Quantity": [100, 50, 25, 15, 30],
            "Avg Cost": [150.00, 280.00, 120.00, 3200.00, 250.00],
            "Current Price": [175.50, 320.25, 135.75, 3350.00, 265.00],
            "Market Value": [17550, 16012, 3393, 50250, 7950],
            "P&L": ["+2550", "+2012", "+393", "+2250", "+450"],
            "P&L %": ["+17.0%", "+14.4%", "+13.1%", "+4.7%", "+6.0%"],
            "Weight": ["18.2%", "16.6%", "3.5%", "52.0%", "8.2%"]
        })
        st.dataframe(positions_df, use_container_width=True)
    
    with tab3:
        st.subheader("Orders")
        
        tab_open, tab_history = st.tabs(["Open Orders", "History"])
        
        with tab_open:
            orders_df = pd.DataFrame({
                "Symbol": ["NVDA", "JPM"],
                "Side": ["BUY", "SELL"],
                "Type": ["LIMIT", "MARKET"],
                "Quantity": [20, 50],
                "Price": [450.00, 145.00],
                "Status": ["PENDING", "PENDING"],
                "Created": ["2024-01-15 09:30", "2024-01-15 10:15"]
            })
            st.dataframe(orders_df, use_container_width=True)
        
        with tab_history:
            hist_df = pd.DataFrame({
                "Symbol": ["AAPL", "MSFT", "GOOGL"],
                "Side": ["BUY", "BUY", "SELL"],
                "Quantity": [100, 50, 10],
                "Price": [150.00, 280.00, 135.00],
                "Filled": ["2024-01-10", "2024-01-12", "2024-01-14"],
                "P&L": ["+2550", "+2012", "-150"]
            })
            st.dataframe(hist_df, use_container_width=True)
    
    with tab4:
        st.subheader("Risk Metrics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("VaR (95%)", "-2.3%", "-0.1%")
            st.metric("CVaR (95%)", "-3.8%", "-0.2%")
            st.metric("Max Drawdown", "-12.5%", "-0.5%")
        with col2:
            st.metric("Volatility (Ann.)", "18.2%", "+0.3%")
            st.metric("Downside Vol", "12.1%", "+0.2%")
            st.metric("Sharpe Ratio", "1.34", "+0.05")
        with col3:
            st.metric("Sortino Ratio", "1.89", "+0.08")
            st.metric("Calmar Ratio", "0.87", "+0.03")
            st.metric("Sortino Ratio", "1.89", "+0.08")
        
        st.subheader("Drawdown Analysis")
        dates = pd.date_range(end=datetime.today(), periods=252)
        dd = np.abs(np.cumsum(np.random.randn(252) * 0.005) - 1)
        fig = px.area(pd.DataFrame({"Date": dates, "Drawdown": dd}), x="Date", y="Drawdown", title="Historical Drawdown")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Exposure Analysis")
        exposure_df = pd.DataFrame({
            "Sector": ["Technology", "Healthcare", "Financials", "Consumer", "Industrial", "Energy"],
            "Weight": [45.2, 18.5, 12.3, 15.6, 5.8, 2.7],
            "Benchmark": [28.5, 14.2, 11.8, 10.2, 8.1, 4.5]
        })
        fig = px.bar(exposure_df, x="Sector", y=["Weight", "Benchmark"], 
                     title="Sector Exposure vs Benchmark", barmode="group")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        st.subheader("Portfolio Rebalancing")
        
        col1, col2 = st.columns(2)
        with col1:
            strategy = st.selectbox(
                "Rebalancing Strategy",
                ["Equal Weight", "Market Cap", "Risk Parity", "Minimum Variance", "Max Sharpe"]
            )
            target_date = st.date_input("Target Date", date.today() + timedelta(days=7))
            dry_run = st.checkbox("Dry Run", value=True)
        
        with col2:
            if st.button("🔄 Generate Rebalance Plan"):
                st.success("Rebalance plan generated!")
                plan_df = pd.DataFrame({
                    "Symbol": ["AAPL", "MSFT", "GOOGL", "NVDA", "JPM"],
                    "Current Weight": [18.2, 16.6, 3.5, 52.0, 8.2],
                    "Target Weight": [20.0, 20.0, 20.0, 20.0, 20.0],
                    "Action": ["BUY", "BUY", "BUY", "SELL", "BUY"],
                    "Quantity": [10, 10, 38, -48, 60],
                    "Est. Cost": [1755, 3202, 5157, -16080, 1590]
                })
                st.dataframe(plan_df, use_container_width=True)
                
                if st.button("✅ Execute Rebalance", type="primary"):
                    st.success("Rebalance executed!")


def render_alerts_tab(alert_client) -> None:
    """Render Alerts tab."""
    st.header("🚨 Alerts & Notifications")
    
    tab1, tab2, tab3 = st.tabs(["🔔 Active Alerts", "📋 Rules", "📜 History"])
    
    with tab1:
        st.subheader("Active Alerts")
        
        # Filter controls
        col1, col2, col3 = st.columns(3)
        with col1:
            severity_filter = st.multiselect(
                "Severity", ["critical", "warning", "info"], default=["critical", "warning"]
            )
        with col2:
            status_filter = st.multiselect(
                "Status", ["active", "triggered", "acknowledged"], default=["active", "triggered"]
            )
        with col3:
            st.button("🔄 Refresh")
        
        # Alerts table
        alerts_df = pd.DataFrame({
            "Time": ["10:32", "10:15", "09:45", "09:30", "09:15"],
            "Severity": ["🔴 Critical", "🟡 Warning", "🟡 Warning", "🔵 Info", "🟡 Warning"],
            "Type": ["Price Below", "Volume Spike", "RSI Oversold", "MA Cross", "Earnings"],
            "Symbol": ["TSLA", "NVDA", "META", "AAPL", "MSFT"],
            "Message": [
                "TSLA fell below $200 threshold",
                "NVDA volume 4.2x average",
                "META RSI at 28 (oversold)",
                "AAPL 50MA crossed above 200MA",
                "MSFT earnings beat by 8%"
            ],
            "Status": ["Active", "Active", "Acknowledged", "Active", "Active"],
            "Actions": ["Ack", "Ack", "View", "Ack", "View"]
        })
        st.dataframe(alerts_df, use_container_width=True)
    
    with tab2:
        st.subheader("Alert Rules")
        
        col1, col2 = st.columns([2, 1])
        with col2:
            if st.button("➕ Create Rule", type="primary"):
                st.session_state.show_create_rule = True
        
        rules_df = pd.DataFrame({
            "Name": ["TSLA Price Alert", "NVDA Volume", "AAPL Golden Cross", "Portfolio Risk", "Earnings Alerts"],
            "Type": ["Price Below", "Volume Spike", "MA Cross", "Portfolio VaR", "Earnings"],
            "Severity": ["Warning", "Info", "Info", "Critical", "Info"],
            "Channels": ["In-App, Email", "In-App", "In-App, Slack", "In-App, Email, SMS", "In-App, Email"],
            "Status": ["Active", "Active", "Active", "Active", "Active"],
            "Last Triggered": ["2h ago", "5h ago", "1d ago", "Never", "3h ago"]
        })
        st.dataframe(rules_df, use_container_width=True)
    
    with tab3:
        st.subheader("Alert History")
        
        hist_df = pd.DataFrame({
            "Time": ["10:32", "10:15", "09:45", "09:30", "09:15", "09:00", "08:45", "08:30"],
            "Type": ["Price Below", "Volume Spike", "RSI Oversold", "MA Cross", "Earnings", "Pattern", "Volume Spike", "MA Cross"],
            "Symbol": ["TSLA", "NVDA", "META", "AAPL", "MSFT", "AMZN", "GOOGL", "NVDA"],
            "Severity": ["🔴 Critical", "🟡 Warning", "🟡 Warning", "🔵 Info", "🔵 Info", "🔵 Info", "🟡 Warning", "🔵 Info"],
            "Resolved": ["✅", "✅", "✅", "✅", "✅", "✅", "✅", "✅"],
            "Channels": ["In-App, Email", "In-App", "In-App", "In-App, Slack", "In-App, Email", "In-App", "In-App", "In-App, Slack"]
        })
        st.dataframe(hist_df, use_container_width=True)


def render_analytics_tab(analytics_client) -> None:
    """Render Analytics tab."""
    st.header("📈 Analytics & Reports")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Risk Metrics", "📈 Performance", "🔬 Factor Analysis", "🎲 Monte Carlo", "📋 Reports"
    ])
    
    with tab1:
        st.subheader("Risk Metrics")
        
        portfolio_select = st.selectbox("Portfolio", ["Main Portfolio", "Retirement", "Trading"])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("VaR (95%)", "-2.3%", "-0.1%")
            st.metric("CVaR (95%)", "-3.8%", "-0.2%")
        with col2:
            st.metric("Max Drawdown", "-12.5%", "-0.5%")
            st.metric("Volatility (Ann.)", "18.2%", "+0.3%")
        with col3:
            st.metric("Sharpe Ratio", "1.34", "+0.05")
            st.metric("Sortino Ratio", "1.89", "+0.08")
        with col4:
            st.metric("Calmar Ratio", "0.87", "+0.03")
            st.metric("Info Ratio", "0.72", "+0.08")
        
        st.subheader("VaR Breakdown")
        var_df = pd.DataFrame({
            "Confidence": ["90%", "95%", "99%", "99.9%"],
            "VaR": ["-1.8%", "-2.3%", "-3.5%", "-5.2%"],
            "CVaR": ["-2.5%", "-3.8%", "-5.8%", "-8.1%"]
        })
        st.dataframe(var_df, use_container_width=True)
        
        st.subheader("Drawdown Analysis")
        dates = pd.date_range(end=datetime.today(), periods=252)
        dd = np.abs(np.cumsum(np.random.randn(252) * 0.005) - 1)
        fig = px.area(pd.DataFrame({"Date": dates, "Drawdown": dd}), x="Date", y="Drawdown", title="Historical Drawdown")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Exposure Analysis")
        exposure_df = pd.DataFrame({
            "Sector": ["Technology", "Healthcare", "Financials", "Consumer", "Industrial", "Energy"],
            "Weight": [45.2, 18.5, 12.3, 15.6, 5.8, 2.7],
            "Benchmark": [28.5, 14.2, 11.8, 10.2, 8.1, 4.5]
        })
        fig = px.bar(exposure_df, x="Sector", y=["Weight", "Benchmark"], 
                     title="Sector Exposure vs Benchmark", barmode="group")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Performance Analytics")
        
        portfolio_select = st.selectbox("Portfolio", ["Main Portfolio", "Retirement", "Trading"])
        
        st.subheader("Returns")
        perf_data = pd.DataFrame({
            "Period": ["1D", "1W", "1M", "3M", "6M", "1Y", "YTD", "3Y", "5Y"],
            "Return": ["+0.4%", "+2.1%", "+5.2%", "+12.3%", "+18.7%", "+24.5%", "+22.1%", "+65.3%", "+134.2%"],
            "Benchmark": ["+0.2%", "+1.5%", "+3.8%", "+8.7%", "+12.3%", "+18.2%", "+15.6%", "+42.1%", "+89.4%"],
            "Excess": ["+0.2%", "+0.6%", "+1.4%", "+3.6%", "+6.4%", "+6.3%", "+6.5%", "+23.2%", "+44.8%"]
        })
        st.dataframe(perf_data, use_container_width=True)
        
        st.subheader("Rolling Returns (1Y Window)")
        dates = pd.date_range(end=datetime.today(), periods=252)
        rolling_1y = np.cumsum(np.random.randn(252) * 0.01 + 0.0005)
        fig = px.line(pd.DataFrame({"Date": dates, "Rolling 1Y": rolling_1y}), x="Date", y="Rolling 1Y", title="Rolling 1-Year Returns")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Risk-Adjusted Metrics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Sharpe Ratio", "1.34", "+0.05")
            st.metric("Sortino Ratio", "1.89", "+0.08")
        with col2:
            st.metric("Calmar Ratio", "0.87", "+0.03")
            st.metric("Information Ratio", "0.72", "+0.08")
        with col3:
            st.metric("Treynor Ratio", "0.98", "+0.04")
            st.metric("Omega Ratio", "1.67", "+0.05")
        with col4:
            st.metric("Kappa 3", "1.45", "+0.06")
            st.metric("Gain/Loss Ratio", "1.42", "+0.03")
    
    with tab3:
        st.subheader("Factor Analysis")
        
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("Model", ["Fama-French 3-Factor", "Fama-French 5-Factor", "Fama-French 5-Factor + Momentum", "Custom"])
            st.selectbox("Period", ["1M", "3M", "6M", "1Y", "3Y", "5Y", "Max"])
        with col2:
            if st.button("🔄 Run Factor Analysis"):
                with st.spinner("Running factor analysis..."):
                    import time
                    time.sleep(2)
                    st.success("Factor analysis completed!")
        
        # Factor loadings
        st.subheader("Factor Loadings")
        factor_df = pd.DataFrame({
            "Factor": ["MKT-RF", "SMB", "HML", "RMW", "CMA", "MOM"],
            "Loading": [1.08, -0.12, 0.08, 0.05, -0.03, 0.15],
            "T-Stat": [24.5, -1.8, 1.4, 0.9, -0.6, 3.2],
            "P-Value": [0.000, 0.072, 0.162, 0.368, 0.549, 0.001]
        })
        st.dataframe(factor_df, use_container_width=True)
        
        st.subheader("Factor Returns (Annualized)")
        factor_ret = pd.DataFrame({
            "Factor": ["MKT-RF", "SMB", "HML", "RMW", "CMA", "MOM"],
            "Return (%)": [8.2, 2.1, 3.8, 3.2, 2.9, 8.7],
            "Volatility (%)": [15.2, 10.8, 9.5, 8.4, 7.9, 14.2]
        })
        st.dataframe(factor_ret, use_container_width=True)
        
        st.subheader("Regression Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("R²", "0.942", "+0.012")
        with col2:
            st.metric("Adj. R²", "0.938", "+0.010")
        with col3:
            st.metric("Alpha (Ann.)", "+3.4%", "+0.8%")
        with col4:
            st.metric("Residual Vol", "4.2%", "-0.3%")
    
    with tab4:
        st.subheader("Monte Carlo Simulation")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            n_sims = st.slider("Simulations", 50, 5000, 200)
            horizon = st.slider("Horizon (days)", 30, 756, 252)
        with col2:
            if st.button("▶️ Run Simulation"):
                with st.spinner(f"Running {n_sims} simulations..."):
                    import time
                    time.sleep(2)
                    st.success("Simulation complete!")
                    st.session_state.mc_done = True
        
        if st.session_state.get("mc_done", False):
            st.subheader("Simulation Results")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Mean Final Value", "$1,245,000", "+$10,500")
            with col2:
                st.metric("Median Final Value", "$1,238,000", "+$9,200")
            with col3:
                st.metric("5th Percentile", "$1,045,000", "-$15,000")
            with col4:
                st.metric("Prob. Profit", "78.5%", "+2.3%")
            
            # Paths chart
            st.subheader("Sample Paths")
            dates = pd.date_range(start=datetime.today(), periods=252)
            paths = np.random.randn(10, 252).cumsum(axis=1) * 0.01 + 1
            paths = paths * 1000000 + 100000
            
            fig = go.Figure()
            for i, path in enumerate(paths):
                fig.add_trace(go.Scatter(x=dates, y=path, mode='lines', 
                                        name=f'Path {i+1}', opacity=0.5,
                                        line=dict(width=1)))
            fig.add_trace(go.Scatter(x=dates, y=np.median(paths, axis=0), 
                                    mode='lines', name='Median', line=dict(width=3, color='red')))
            fig.update_layout(title="Monte Carlo Paths (Sample 10)", xaxis_title="Date", yaxis_title="Portfolio Value")
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Return Distribution")
            returns = np.random.randn(200) * 0.12 + 0.18
            fig = px.histogram(returns * 100, nbins=30, title="Distribution of Annual Returns")
            fig.add_vline(x=0, line_dash="dash", line_color="red")
            fig.add_vline(x=np.percentile(returns, 5) * 100, line_dash="dash", line_color="orange", annotation_text="VaR 95%")
            st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        st.subheader("Reports")
        
        col1, col2 = st.columns([2, 1])
        with col2:
            if st.button("📄 Generate Report", type="primary"):
                st.success("Report generated!")
        
        reports = [
            {"Name": "Monthly Performance", "Type": "Performance", "Period": "Dec 2024", "Status": "Ready", "Generated": "2025-01-02"},
            {"Name": "Quarterly Risk", "Type": "Risk", "Period": "Q4 2024", "Status": "Ready", "Generated": "2025-01-03"},
            {"Name": "Factor Attribution", "Type": "Analytics", "Period": "Q4 2024", "Status": "Ready", "Generated": "2025-01-04"},
            {"Name": "Annual Review", "Type": "Comprehensive", "Period": "2024", "Status": "Generating...", "Generated": "In Progress"},
            {"Name": "Risk Budget", "Type": "Risk", "Period": "Jan 2025", "Status": "Scheduled", "Generated": "2025-01-15"},
        ]
        st.dataframe(pd.DataFrame(reports), use_container_width=True)
        
        st.subheader("Report Builder")
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("Report Type", ["Performance", "Risk", "Attribution", "Compliance", "Custom"])
            st.multiselect("Sections", ["Executive Summary", "Performance", "Risk", "Attribution", "Holdings", "Transactions", "Appendix"])
        with col2:
            st.date_input("Period Start", date.today() - timedelta(days=90))
            st.date_input("Period End", date.today())
            st.selectbox("Format", ["PDF", "HTML", "Excel", "PowerPoint"])


def render_patterns_tab(pattern_client) -> None:
    """Render Patterns tab."""
    st.header("🔍 Pattern Detection")
    
    tab1, tab2, tab3 = st.tabs(["🔍 Detect", "📚 Library", "📊 Analytics"])
    
    with tab1:
        st.subheader("Pattern Detection")
        
        col1, col2 = st.columns(2)
        with col1:
            symbol = st.text_input("Symbol", "AAPL")
            timeframe = st.selectbox("Timeframe", ["1d", "1h", "15m", "5m"])
            pattern_types = st.multiselect(
                "Pattern Types",
                ["Trend", "Seasonal", "Support/Resistance", "Reversal", "Breakout", "Volume Spike", "Cycle", "Regime Change", "Anomaly"],
                default=["Trend", "Support/Resistance", "Reversal", "Breakout"]
            )
        with col2:
            if st.button("🔍 Detect Patterns", type="primary"):
                with st.spinner("Detecting patterns..."):
                    import time
                    time.sleep(2)
                    st.success("Pattern detection complete!")
                    st.session_state.patterns_detected = True
        
        if st.session_state.get("patterns_detected", False):
            st.subheader("Detected Patterns")
            patterns_df = pd.DataFrame({
                "Type": ["Trend", "Support/Resistance", "Reversal", "Breakout"],
                "Description": ["Strong Uptrend (R²=0.92)", "Support at $145.50 (5 touches)", "Double Bottom at $142", "Bullish Breakout above $180"],
                "Confidence": ["Very High", "High", "High", "Medium"],
                "Timeframe": ["1d", "1d", "1d", "1d"],
                "Parameters": ["R²=0.92", "Level=$145.50", "Target=$165", "Vol=3.2x"]
            })
            st.dataframe(patterns_df, use_container_width=True)
    
    with tab2:
        st.subheader("Pattern Library")
        
        patterns = pd.DataFrame({
            "Type": ["Trend", "Trend", "Support/Resistance", "Reversal", "Reversal", "Breakout", "Volume Spike", "Cycle"],
            "Name": ["Strong Uptrend", "Death Cross", "Key Support", "Double Bottom", "Head & Shoulders", "Bullish Breakout", "Volume Surge", "4-Year Cycle"],
            "Symbols": ["AAPL, MSFT, NVDA", "SPY, QQQ", "AAPL, MSFT, GOOGL", "META, AMZN", "TSLA, NVDA", "NVDA, AMD", "META, NFLX", "SPY, QQQ"],
            "Confidence": ["Very High", "High", "High", "High", "Medium", "High", "Medium", "Medium"],
            "Occurrences": [45, 12, 28, 15, 8, 22, 31, 5],
            "Last Seen": ["2024-01-15", "2023-12-20", "2024-01-10", "2024-01-12", "2023-11-05", "2024-01-14", "2024-01-13", "2023-10-01"]
        })
        st.dataframe(patterns, use_container_width=True)
    
    with tab3:
        st.subheader("Pattern Analytics")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Patterns", "167", "+12")
            st.metric("Avg Confidence", "0.78", "+0.03")
            st.metric("Active Patterns", "23", "+3")
        with col2:
            # Pattern type distribution
            pt_data = pd.DataFrame({
                "Type": ["Trend", "Seasonal", "S/R", "Reversal", "Breakout", "Volume", "Cycle", "Regime", "Anomaly"],
                "Count": [45, 12, 28, 15, 22, 18, 5, 8, 12]
            })
            fig = px.bar(pt_data, x="Type", y="Count", title="Patterns by Type")
            st.plotly_chart(fig, use_container_width=True)


# Export
__all__ = [
    "render_knowledge_graph_tab",
    "render_portfolio_tab",
    "render_alerts_tab",
    "render_analytics_tab",
    "render_patterns_tab",
]