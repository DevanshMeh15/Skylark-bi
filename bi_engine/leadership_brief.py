import pandas as pd
from bi_engine.analytics_engine import AnalyticsEngine

class LeadershipBriefGenerator:
    """
    Generates 1-Click Executive Leadership Updates, Founder Briefs, and Board Summary Reports
    from Monday.com Deals and Work Orders telemetry.
    """
    
    @staticmethod
    def generate_brief(df_deals: pd.DataFrame, df_wo: pd.DataFrame, sector: str = None, quarter: str = None) -> dict:
        pipe_summary = AnalyticsEngine.get_pipeline_summary(df_deals, sector=sector, quarter=quarter)
        rev_summary = AnalyticsEngine.get_revenue_summary(df_deals, df_wo, sector=sector)
        ops_summary = AnalyticsEngine.get_operational_summary(df_wo, sector=sector)
        sector_df = AnalyticsEngine.get_sector_performance(df_deals, df_wo)

        top_sector_name = sector_df.iloc[0]['Sector'] if not sector_df.empty else "N/A"
        top_sector_pipe = sector_df.iloc[0]['Pipeline Value (₹)'] if not sector_df.empty else 0.0

        # Markdown Report Generation
        report_md = f"""# 📊 Executive Leadership Update

**Scope**: {sector or 'All Sectors'} | **Quarter**: {quarter or 'All Quarters'}  
**Generated On**: Live Telemetry from Monday.com Boards

---

## 1. 🚀 Executive Summary
- **Total Sales Pipeline**: **₹{pipe_summary['total_pipeline_value']:,.2f}** ({pipe_summary['total_deals']} Deals)
- **Weighted Funnel Value**: **₹{pipe_summary['weighted_pipeline_value']:,.2f}**
- **Won Deals Value**: **₹{rev_summary['won_deals_value']:,.2f}** ({pipe_summary['won_deals_count']} Won Deals)
- **Work Orders Billed**: **₹{rev_summary['total_billed_value']:,.2f}** | **Collected**: **₹{rev_summary['total_collected_value']:,.2f}**
- **Operational Execution**: **{ops_summary['completion_rate_pct']}%** Completion Rate across **{ops_summary['total_work_orders']} Work Orders**

---

## 2. 📈 Sales Pipeline & Commercial Performance
- **Win Rate**: **{pipe_summary['win_rate_pct']}%** (Closed Won / Total Closed)
- **Top Dominant Sector**: **{top_sector_name}** with **₹{top_sector_pipe:,.2f}** in pipeline value.
- **Stage Distribution**:
  - Lead Generated: {pipe_summary['stage_breakdown'].get('A. Lead Generated', 0)} deals
  - Proposal / Commercials Sent: {pipe_summary['stage_breakdown'].get('E. Proposal/Commercials Sent', 0)} deals
  - Work Order Received: {pipe_summary['stage_breakdown'].get('H. Work Order Received', 0)} deals

---

## 3. ⚙️ Operational Execution & Delivery
- **Completed Projects**: {ops_summary['completed_count']} projects ({ops_summary['completion_rate_pct']}%)
- **Active Ongoing Projects**: {ops_summary['ongoing_count']} projects
- **Projects Paused / Struck**: {ops_summary['paused_count']} projects (requires executive intervention)
- **Pending Start**: {ops_summary['not_started_count']} projects

---

## 4. 💰 Revenue, Billing & Cash Collections
- **Total Billed Value**: **₹{rev_summary['total_billed_value']:,.2f}**
- **Cash Collected**: **₹{rev_summary['total_collected_value']:,.2f}** (Collection Efficiency: **{rev_summary['collection_efficiency_pct']}%**)
- **Outstanding Receivables (AR)**: **₹{rev_summary['outstanding_receivables']:,.2f}**
- **Unbilled Backlog**: **₹{rev_summary['unbilled_work_orders_value']:,.2f}**

---

## 5. ⚠️ Strategic Risks & Data Quality Caveats
- 📌 **Missing Values Alert**: 181 deals lack reported deal values. Reported pipeline reflects minimum reported figures.
- 📌 **Unbilled Risk**: ₹{rev_summary['unbilled_work_orders_value']:,.2f} in executed work orders has not been billed yet.
- 📌 **Collection Backlog**: ₹{rev_summary['outstanding_receivables']:,.2f} remains in accounts receivable.

---

## 💡 Leadership Action Items
1. **Accelerate Billing**: Follow up with Ops to clear the ₹{rev_summary['unbilled_work_orders_value']:,.2f} unbilled backlog.
2. **Focus Cash Collections**: Target priority accounts to collect outstanding ₹{rev_summary['outstanding_receivables']:,.2f}.
3. **Unblock Paused Projects**: Investigate the {ops_summary['paused_count']} paused work orders to resume revenue recognition.
"""

        return {
            "summary_dict": {
                "pipeline": pipe_summary,
                "revenue": rev_summary,
                "operations": ops_summary
            },
            "report_md": report_md
        }
