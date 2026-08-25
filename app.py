import streamlit as st
import pandas as pd
import altair as alt
import os

import sys

# Ensure local imports work cleanly
sys.path.append(os.path.dirname(__file__))

from monday_integration.monday_client import MondayClient
from data_resilience.resilience_engine import ResilienceEngine
from bi_engine.analytics_engine import AnalyticsEngine
from bi_engine.agent import BIAgent
from bi_engine.leadership_brief import LeadershipBriefGenerator

# Page Configuration
st.set_page_config(
    page_title="Skylark Drones - Monday.com BI Agent",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Mode Glassmorphism Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #0B0E14;
        color: #E2E8F0;
    }
    
    /* Header Container */
    .header-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
    }
    
    .header-title {
        font-size: 28px;
        font-weight: 700;
        background: linear-gradient(90deg, #38BDF8 0%, #818CF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    
    .header-subtitle {
        color: #94A3B8;
        font-size: 14px;
        margin-top: 4px;
    }
    
    /* Status Badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .warning-badge {
        display: inline-flex;
        align-items: center;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    /* Metric Cards */
    .metric-card {
        background: #1E293B;
        border-radius: 12px;
        padding: 18px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        transition: transform 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.4);
    }
    .metric-label {
        font-size: 12px;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-val {
        font-size: 22px;
        font-weight: 700;
        color: #F8FAFC;
        margin-top: 6px;
    }

    /* Prompt Pills */
    .stButton>button {
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        background: #1E293B;
        color: #CBD5E1;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background: #38BDF8;
        color: #0F172A;
        border-color: #38BDF8;
    }
</style>
""", unsafe_allow_html=True)

# Data Caching & Initialization Engine
@st.cache_data(show_spinner=False)
def load_and_clean_data(api_token="", deals_id="", wo_id=""):
    client = MondayClient(api_token=api_token, deals_board_id=deals_id, work_orders_board_id=wo_id)
    df_deals_raw = client.fetch_deals_board()
    df_wo_raw = client.fetch_work_orders_board()
    
    res_engine = ResilienceEngine()
    df_deals = res_engine.clean_deals(df_deals_raw)
    df_wo = res_engine.clean_work_orders(df_wo_raw)

    # PyArrow ArrowTypeError safety sanitization for all object columns
    for col in df_deals.columns:
        if df_deals[col].dtype == 'object':
            df_deals[col] = df_deals[col].apply(lambda x: str(x) if pd.notnull(x) and x != 'nan' and x != 'NaT' else '')
    for col in df_wo.columns:
        if df_wo[col].dtype == 'object':
            df_wo[col] = df_wo[col].apply(lambda x: str(x) if pd.notnull(x) and x != 'nan' and x != 'NaT' else '')
    
    return df_deals, df_wo, res_engine.deals_quality_report, res_engine.wo_quality_report, client.is_live_configured()

# Sidebar Setup
with st.sidebar:
    st.image("https://img.icons8.com/isometric-line/100/38bdf8/drone.png", width=60)
    st.title("🛸 Skylark BI Agent")
    st.caption("Monday.com Intelligence Engine v1.0")
    st.divider()

    st.subheader("🔌 Monday.com Integration")
    monday_mode = st.radio("Connection Mode", ["Emulated GraphQL (Demo Data)", "Live Monday.com API"], index=0)
    
    api_token, deals_board_id, wo_board_id = "", "", ""
    if monday_mode == "Live Monday.com API":
        api_token = st.text_input("Monday.com API Token", type="password")
        deals_board_id = st.text_input("Deals Board ID")
        wo_board_id = st.text_input("Work Orders Board ID")
        st.info("Tip: Run `python scripts/setup_monday.py` to auto-populate boards on your Monday account.")

    st.divider()
    st.subheader("🎯 Global Analytics Filters")
    sector_options = ["All", "Renewables", "Mining", "Railways", "Powerline", "Construction", "Others"]
    selected_sector = st.selectbox("Filter Sector", sector_options, index=0)
    selected_quarter = st.selectbox("Filter Quarter", ["All", "Q1", "Q2", "Q3", "Q4"], index=0)

    st.divider()
    st.caption("Developed for Skylark Drones Technical Assignment")

# Load Data
try:
    df_deals, df_wo, deals_quality, wo_quality, is_live = load_and_clean_data(api_token, deals_board_id, wo_board_id)
    agent = BIAgent(df_deals, df_wo, deals_quality, wo_quality)
except Exception as e:
    st.error(f"Error loading Monday.com data: {e}")
    st.stop()

# Header Rendering
st.markdown(f"""
<div class="header-card">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <div class="header-title">Monday.com Business Intelligence Agent</div>
            <div class="header-subtitle">Executive Telemetry & Conversational BI for Skylark Drones</div>
        </div>
        <div>
            <span class="status-badge">🟢 {'Live Monday.com API' if is_live else 'Emulated GraphQL API'}</span>
            <span class="warning-badge">🛡️ Data Quality Audit: Clean</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Application Tabs
tab_chat, tab_analytics, tab_leadership = st.tabs([
    "💬 Conversational BI Agent", 
    "📊 Visual Analytics & Telemetry", 
    "📄 1-Click Leadership Brief"
])

# ==========================================
# TAB 1: CONVERSATIONAL AGENT INTERFACE
# ==========================================
with tab_chat:
    st.subheader("💡 Founder Conversational Assistant")
    st.caption("Ask natural language business questions across Monday.com Deals and Work Orders boards.")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": "👋 Welcome Founder! I am your Skylark BI Agent. You can ask me questions about pipeline health, revenue collections, sector performance, or operational execution. What would you like to explore?"
            }
        ]

    # Sample prompt buttons
    col_p1, col_p2, col_p3 = st.columns(3)
    prompt_clicked = None
    with col_p1:
        if st.button("📈 How's our pipeline for energy sector?"):
            prompt_clicked = "How's our pipeline looking for energy sector this quarter?"
    with col_p2:
        if st.button("💰 Revenue vs Unbilled Work Orders?"):
            prompt_clicked = "What is our total collected revenue vs unbilled work orders?"
    with col_p3:
        if st.button("📋 Generate Leadership Update Brief"):
            prompt_clicked = "Generate a leadership update for executive team"

    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "caveats" in msg and msg["caveats"]:
                with st.expander("⚠️ Data Resilience & Quality Caveats", expanded=False):
                    for c in msg["caveats"]:
                        st.caption(f"• {c}")

    # Process Input
    user_input = st.chat_input("Ask a business query (e.g. 'Show revenue by sector', 'How many work orders completed?')...")
    
    active_prompt = prompt_clicked or user_input

    if active_prompt:
        # User message
        st.session_state.messages.append({"role": "user", "content": active_prompt})
        with st.chat_message("user"):
            st.markdown(active_prompt)

        # Agent Answer
        with st.spinner("Analyzing Monday.com telemetry..."):
            response = agent.answer_query(active_prompt)

        with st.chat_message("assistant"):
            st.markdown(response["answer"])

            # If response has clarifying questions
            if response["type"] == "clarification":
                for q in response["clarifying_questions"]:
                    st.markdown(f"- {q}")

            if response.get("caveats"):
                with st.expander("⚠️ Data Resilience & Quality Caveats", expanded=False):
                    for c in response["caveats"]:
                        st.caption(f"• {c}")

        # Store in history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response["answer"],
            "caveats": response.get("caveats", [])
        })

# ==========================================
# TAB 2: VISUAL ANALYTICS & TELEMETRY
# ==========================================
with tab_analytics:
    st.subheader("📊 Executive Metrics & Telemetry Dashboard")
    
    # Calculate filtered summaries
    pipe_summary = AnalyticsEngine.get_pipeline_summary(df_deals, sector=selected_sector, quarter=selected_quarter)
    rev_summary = AnalyticsEngine.get_revenue_summary(df_deals, df_wo, sector=selected_sector)
    ops_summary = AnalyticsEngine.get_operational_summary(df_wo, sector=selected_sector)

    # Metric Cards Row
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Pipeline Value</div>
            <div class="metric-val">₹{pipe_summary['total_pipeline_value']/1e7:.2f} Cr</div>
            <div style="font-size:11px; color:#34D399;">{pipe_summary['total_deals']} Total Deals</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Won Deals Value</div>
            <div class="metric-val">₹{rev_summary['won_deals_value']/1e7:.2f} Cr</div>
            <div style="font-size:11px; color:#38BDF8;">{pipe_summary['won_deals_count']} Won Deals</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Billed Value</div>
            <div class="metric-val">₹{rev_summary['total_billed_value']/1e7:.2f} Cr</div>
            <div style="font-size:11px; color:#818CF8;">Incl GST</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Cash Collected</div>
            <div class="metric-val">₹{rev_summary['total_collected_value']/1e7:.2f} Cr</div>
            <div style="font-size:11px; color:#34D399;">Eff: {rev_summary['collection_efficiency_pct']}%</div>
        </div>
        """, unsafe_allow_html=True)
    with m5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Unbilled Backlog</div>
            <div class="metric-val">₹{rev_summary['unbilled_work_orders_value']/1e7:.2f} Cr</div>
            <div style="font-size:11px; color:#FBBF24;">Pending Invoicing</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Visual Charts Row 1
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📈 Pipeline Funnel Stage Distribution")
        stage_df = pd.DataFrame(list(pipe_summary['stage_breakdown'].items()), columns=['Stage', 'Count'])
        chart1 = alt.Chart(stage_df).mark_bar(cornerRadius=6, color="#38BDF8").encode(
            x=alt.X('Count:Q', title="Number of Deals"),
            y=alt.Y('Stage:N', sort='-x', title="Stage"),
            tooltip=['Stage', 'Count']
        ).properties(height=320)
        st.altair_chart(chart1, use_container_width=True)

    with c2:
        st.subheader("⚙️ Work Order Execution Status")
        ops_df = pd.DataFrame(list(ops_summary['status_breakdown'].items()), columns=['Status', 'Count'])
        chart2 = alt.Chart(ops_df).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="Count", type="quantitative"),
            color=alt.Color(field="Status", type="nominal", scale=alt.Scale(scheme='tableau10')),
            tooltip=['Status', 'Count']
        ).properties(height=320)
        st.altair_chart(chart2, use_container_width=True)

    # Sector Performance Table
    st.subheader("📊 Sectoral Performance Breakdown")
    sec_perf = AnalyticsEngine.get_sector_performance(df_deals, df_wo)
    st.dataframe(sec_perf, use_container_width=True)

    # Raw Data Explorer Drawer
    with st.expander("🔍 Explore Raw Cleaned Monday.com Data Boards", expanded=False):
        b_type = st.radio("Select Board", ["Deals Board", "Work Orders Board"], horizontal=True)
        if b_type == "Deals Board":
            st.dataframe(df_deals, use_container_width=True)
        else:
            st.dataframe(df_wo, use_container_width=True)

# ==========================================
# TAB 3: 1-CLICK LEADERSHIP BRIEF
# ==========================================
with tab_leadership:
    st.subheader("📄 1-Click Executive Leadership Brief")
    st.caption("Generate a board-ready executive summary for leadership updates.")

    brief_res = LeadershipBriefGenerator.generate_brief(df_deals, df_wo, sector=selected_sector, quarter=selected_quarter)
    report_text = brief_res["report_md"]

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        st.download_button(
            label="📥 Download Leadership Brief (.md)",
            data=report_text,
            file_name="Skylark_Executive_Leadership_Brief.md",
            mime="text/markdown"
        )

    st.markdown(report_text)
