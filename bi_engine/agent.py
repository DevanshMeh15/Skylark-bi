import re
import pandas as pd
from bi_engine.analytics_engine import AnalyticsEngine
from bi_engine.leadership_brief import LeadershipBriefGenerator

class BIAgent:
    """
    Business Intelligence Agent for Skylark Drones.
    Interprets founder queries, handles ambiguity with clarifying questions,
    queries Monday.com data cross-boards, and provides contextual insights with data quality caveats.
    """

    def __init__(self, df_deals: pd.DataFrame, df_wo: pd.DataFrame, deals_quality: dict = None, wo_quality: dict = None):
        self.df_deals = df_deals
        self.df_wo = df_wo
        self.deals_quality = deals_quality or {}
        self.wo_quality = wo_quality or {}

    def _extract_sector(self, query: str) -> str:
        q = query.lower()
        if 'renewables' in q or 'energy' in q or 'solar' in q or 'wind' in q:
            return 'Renewables'
        if 'mining' in q:
            return 'Mining'
        if 'railway' in q or 'railways' in q:
            return 'Railways'
        if 'powerline' in q or 'power' in q:
            return 'Powerline'
        if 'construction' in q:
            return 'Construction'
        if 'others' in q:
            return 'Others'
        if 'dsp' in q:
            return 'DSP'
        return None

    def _extract_quarter(self, query: str) -> str:
        q = query.upper()
        match = re.search(r'Q[1-4](\s*20\d\d)?', q)
        if match:
            return match.group(0).replace(' ', '')
        return None

    def answer_query(self, query: str) -> dict:
        q_lower = query.lower().strip()
        sector = self._extract_sector(q_lower)
        quarter = self._extract_quarter(query)

        # 1. Check for Ambiguous / Vague Queries
        if q_lower in ['hi', 'hello', 'hey', 'help', 'how are we doing', 'status', 'overview', 'summary']:
            return {
                "type": "clarification",
                "answer": "👋 Hello! I am your Monday.com Business Intelligence Agent. I can help you analyze pipeline health, revenue collections, sector performance, and operational metrics.\n\nTo give you the most precise insights, could you clarify what area you'd like to focus on?",
                "clarifying_questions": [
                    "📈 **Pipeline & Sales**: How is our pipeline looking for the Renewables or Mining sector this quarter?",
                    "💰 **Revenue & Collections**: What is our total collected revenue vs unbilled work orders?",
                    "📊 **Sectoral Performance**: Which sector has the highest conversion rate and pipeline value?",
                    "⚙️ **Operations**: How many work orders are completed, ongoing, or paused?",
                    "📋 **Leadership Update**: Can you prepare a leadership update brief for the founder?"
                ],
                "caveats": []
            }

        # 2. Leadership Update Request
        if 'leadership' in q_lower or 'founder update' in q_lower or 'executive brief' in q_lower or 'board report' in q_lower:
            brief_data = LeadershipBriefGenerator.generate_brief(self.df_deals, self.df_wo, sector=sector, quarter=quarter)
            return {
                "type": "leadership_brief",
                "answer": brief_data["report_md"],
                "data": brief_data["summary_dict"],
                "caveats": self.deals_quality.get("warnings", []) + self.wo_quality.get("warnings", [])
            }

        # 3. Cross-Board Specific Deal Search
        deal_match = re.search(r'(?:deal|project|client)\s+([a-zA-Z0-9\s]+)', q_lower)
        if deal_match and not any(k in q_lower for k in ['pipeline', 'revenue', 'sector', 'operations', 'summary']):
            search_term = deal_match.group(1).strip()
            cross_data = AnalyticsEngine.query_cross_board_deal(self.df_deals, self.df_wo, search_term)
            if cross_data["matching_deals"] or cross_data["matching_work_orders"]:
                ans = f"### 🔍 Cross-Board Search Results for '{search_term.title()}'\n\n"
                if cross_data["matching_deals"]:
                    ans += "**Found Deals:**\n"
                    for d in cross_data["matching_deals"]:
                        val_str = f"₹{d['Deal_Value']:,.2f}" if pd.notnull(d['Deal_Value']) else "Not Specified"
                        ans += f"- **{d['Deal Name']}**: Status `{d['Deal Status']}`, Stage `{d['Deal Stage']}`, Value: `{val_str}`, Sector: `{d['Sector_Normalized']}`\n"
                if cross_data["matching_work_orders"]:
                    ans += "\n**Found Work Orders:**\n"
                    for w in cross_data["matching_work_orders"]:
                        ans += f"- **{w['Deal name masked']}** (Client: `{w['Customer Name Code']}`): Execution `{w['Execution_Status_Clean']}`, Billed: `₹{w['Billed_Incl_GST']:,.2f}`, Collected: `₹{w['Collected_Incl_GST']:,.2f}`\n"
                return {
                    "type": "deal_search",
                    "answer": ans,
                    "data": cross_data,
                    "caveats": []
                }

        # 4. Pipeline & Sales Queries
        if any(k in q_lower for k in ['pipeline', 'funnel', 'deals', 'win rate', 'closure', 'conversion']):
            summary = AnalyticsEngine.get_pipeline_summary(self.df_deals, sector=sector, quarter=quarter)
            sector_name = sector or "All Sectors"
            quarter_name = quarter or "All Quarters"
            
            ans = f"### 📈 Pipeline Health ({sector_name} | {quarter_name})\n\n"
            ans += f"- **Total Deals**: **{summary['total_deals']}** ({summary['open_deals_count']} Open, {summary['won_deals_count']} Won, {summary['dead_deals_count']} Dead)\n"
            ans += f"- **Total Pipeline Value**: **₹{summary['total_pipeline_value']:,.2f}**\n"
            ans += f"- **Weighted Pipeline Value**: **₹{summary['weighted_pipeline_value']:,.2f}**\n"
            ans += f"- **Average Deal Size**: **₹{summary['avg_deal_value']:,.2f}**\n"
            ans += f"- **Historical Win Rate**: **{summary['win_rate_pct']}%**\n\n"
            ans += "**Key Insights**:\n"
            if summary['won_deals_count'] > 0:
                ans += f"• Secured {summary['won_deals_count']} deals worth ₹{AnalyticsEngine.get_revenue_summary(self.df_deals, self.df_wo, sector=sector)['won_deals_value']:,.2f}.\n"
            ans += f"• Currently {summary['open_deals_count']} active opportunities in pipeline awaiting closure."

            caveats = self.deals_quality.get("warnings", [])
            return {
                "type": "pipeline",
                "answer": ans,
                "data": summary,
                "caveats": caveats
            }

        # 5. Revenue & Cash Collections Queries
        if any(k in q_lower for k in ['revenue', 'billed', 'collected', 'collection', 'ar', 'receivable', 'money', 'unbilled', 'gst']):
            summary = AnalyticsEngine.get_revenue_summary(self.df_deals, self.df_wo, sector=sector, quarter=quarter)
            sector_name = sector or "All Sectors"
            quarter_name = quarter or "All Quarters"
            
            ans = f"### 💰 Revenue & Cash Collection Summary ({sector_name} | {quarter_name})\n\n"
            ans += f"- **Total Billed Value**: **₹{summary['total_billed_value']:,.2f}**\n"
            ans += f"- **Cash Collected**: **₹{summary['total_collected_value']:,.2f}**\n"
            ans += f"- **Outstanding Receivables (AR)**: **₹{summary['outstanding_receivables']:,.2f}**\n"
            ans += f"- **Unbilled Work Orders**: **₹{summary['unbilled_work_orders_value']:,.2f}**\n"
            ans += f"- **Collection Efficiency**: **{summary['collection_efficiency_pct']}%**\n\n"
            ans += "**Key Insights**:\n"
            ans += f"• **Cash Realization**: We have collected {summary['collection_efficiency_pct']}% of total billed invoices.\n"
            ans += f"• **Billing Gap**: There is ₹{summary['unbilled_work_orders_value']:,.2f} in executed work orders pending billing generation."

            caveats = self.wo_quality.get("warnings", [])
            return {
                "type": "revenue",
                "answer": ans,
                "data": summary,
                "caveats": caveats
            }

        # 6. Operational Metrics Queries
        if any(k in q_lower for k in ['operation', 'operational', 'execution', 'work order', 'ongoing', 'completed', 'paused', 'delivery']):
            summary = AnalyticsEngine.get_operational_summary(self.df_wo, sector=sector, quarter=quarter)
            sector_name = sector or "All Sectors"
            quarter_name = quarter or "All Quarters"

            ans = f"### ⚙️ Operational Execution Summary ({sector_name} | {quarter_name})\n\n"
            ans += f"- **Total Work Orders**: **{summary['total_work_orders']}**\n"
            ans += f"- **Completed Projects**: **{summary['completed_count']}** ({summary['completion_rate_pct']}%)\n"
            ans += f"- **Ongoing Projects**: **{summary['ongoing_count']}**\n"
            ans += f"- **Paused / Struck Projects**: **{summary['paused_count']}**\n"
            ans += f"- **Pending Start**: **{summary['not_started_count']}**\n\n"
            ans += "**Key Insights**:\n"
            ans += f"• Execution team has successfully completed {summary['completion_rate_pct']}% of tracked work orders.\n"
            if summary['paused_count'] > 0:
                ans += f"• 🚨 Attention needed: {summary['paused_count']} work orders are paused/struck."

            return {
                "type": "operations",
                "answer": ans,
                "data": summary,
                "caveats": self.wo_quality.get("warnings", [])
            }

        # 7. Sector Comparison & Performance Queries
        if any(k in q_lower for k in ['sector', 'sectoral', 'industry', 'renewables', 'mining', 'railways', 'best performing']):
            sec_df = AnalyticsEngine.get_sector_performance(self.df_deals, self.df_wo)
            ans = f"### 📊 Sectoral Performance Breakdown\n\n"
            ans += "Here is the performance cross-analyzed across Deals and Work Orders:\n\n"
            
            top_sec = sec_df.iloc[0]
            ans += f"🥇 **Top Sector by Pipeline**: **{top_sec['Sector']}** (₹{top_sec['Pipeline Value (₹)']:,.2f} Pipeline, {top_sec['Won Deals']} Won Deals)\n\n"
            
            ans += "| Sector | Deals | Pipeline Value (₹) | Won Deals | Work Orders | Billed (₹) | Collected (₹) | Completion % |\n"
            ans += "|---|---|---|---|---|---|---|---|\n"
            for _, r in sec_df.iterrows():
                ans += f"| **{r['Sector']}** | {r['Deals Count']} | ₹{r['Pipeline Value (₹)']:,.2f} | {r['Won Deals']} | {r['Work Orders']} | ₹{r['Billed Value (₹)']:,.2f} | ₹{r['Collected Value (₹)']:,.2f} | {r['Execution Completion Rate (%)']}% |\n"

            return {
                "type": "sector",
                "answer": ans,
                "data": sec_df.to_dict('records'),
                "caveats": self.deals_quality.get("warnings", [])
            }

        # 8. Fallback General BI Answer
        summary_pipe = AnalyticsEngine.get_pipeline_summary(self.df_deals, sector=sector)
        summary_rev = AnalyticsEngine.get_revenue_summary(self.df_deals, self.df_wo, sector=sector)
        ans = f"### 📊 Business Overview\n\n"
        ans += f"Here is a quick snapshot of overall telemetry:\n"
        ans += f"- **Pipeline Value**: ₹{summary_pipe['total_pipeline_value']:,.2f} ({summary_pipe['total_deals']} Deals)\n"
        ans += f"- **Won Deals Value**: ₹{summary_rev['won_deals_value']:,.2f}\n"
        ans += f"- **Billed Value**: ₹{summary_rev['total_billed_value']:,.2f} | **Collected**: ₹{summary_rev['total_collected_value']:,.2f}\n"
        ans += f"- **Unbilled Work Orders**: ₹{summary_rev['unbilled_work_orders_value']:,.2f}\n\n"
        ans += "Feel free to ask specific questions about pipeline, revenue, operational delivery, or request a full leadership update!"
        
        return {
            "type": "general",
            "answer": ans,
            "data": {},
            "caveats": self.deals_quality.get("warnings", []) + self.wo_quality.get("warnings", [])
        }
