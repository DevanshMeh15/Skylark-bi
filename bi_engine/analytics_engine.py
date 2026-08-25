import pandas as pd
import numpy as np

class AnalyticsEngine:
    """
    Business Intelligence Analytics Engine providing cross-board queries, pipeline health,
    revenue breakdown, sector performance, and operational execution metrics.
    """
    
    @staticmethod
    def get_pipeline_summary(df_deals: pd.DataFrame, sector: str = None, quarter: str = None) -> dict:
        df = df_deals.copy()
        
        if sector and sector.lower() != 'all':
            df = df[df['Sector_Normalized'].str.lower() == sector.lower()]
            
        if quarter and quarter.lower() != 'all':
            df = df[df['Quarter'].astype(str).str.upper().str.contains(quarter.upper(), na=False)]

        total_deals = len(df)
        total_val = df['Deal_Value'].sum(min_count=1)
        total_val = float(total_val) if pd.notnull(total_val) else 0.0
        
        weighted_val = df['Weighted_Deal_Value'].sum(min_count=1)
        weighted_val = float(weighted_val) if pd.notnull(weighted_val) else 0.0
        
        won_deals = df[df['Deal Status'].astype(str).str.lower() == 'won']
        dead_deals = df[df['Deal Status'].astype(str).str.lower() == 'dead']
        open_deals = df[df['Deal Status'].astype(str).str.lower() == 'open']
        
        closed_count = len(won_deals) + len(dead_deals)
        win_rate = (len(won_deals) / closed_count * 100.0) if closed_count > 0 else 0.0

        stage_breakdown = df['Deal Stage'].value_counts().to_dict()
        status_breakdown = df['Deal Status'].value_counts().to_dict()

        return {
            "total_deals": total_deals,
            "open_deals_count": len(open_deals),
            "won_deals_count": len(won_deals),
            "dead_deals_count": len(dead_deals),
            "total_pipeline_value": total_val,
            "weighted_pipeline_value": weighted_val,
            "avg_deal_value": (total_val / max(total_deals, 1)),
            "win_rate_pct": round(win_rate, 1),
            "stage_breakdown": stage_breakdown,
            "status_breakdown": status_breakdown,
            "sector": sector or "All Sectors",
            "quarter": quarter or "All Quarters"
        }

    @staticmethod
    def get_revenue_summary(df_deals: pd.DataFrame, df_wo: pd.DataFrame, sector: str = None, quarter: str = None) -> dict:
        deals_df = df_deals.copy()
        wo_df = df_wo.copy()

        if sector and sector.lower() != 'all':
            deals_df = deals_df[deals_df['Sector_Normalized'].str.lower() == sector.lower()]
            wo_df = wo_df[wo_df['Sector_Normalized'].str.lower() == sector.lower()]

        if quarter and quarter.lower() != 'all':
            deals_df = deals_df[deals_df['Quarter'].astype(str).str.upper().str.contains(quarter.upper(), na=False)]
            wo_df = wo_df[wo_df['Quarter'].astype(str).str.upper().str.contains(quarter.upper(), na=False)]

        won_deals_val = deals_df[deals_df['Deal Status'].astype(str).str.lower() == 'won']['Deal_Value'].sum()

        wo_total_excl = wo_df['Amount_Excl_GST'].sum()
        wo_total_incl = wo_df['Amount_Incl_GST'].sum()
        billed_val = wo_df['Billed_Incl_GST'].sum()
        collected_val = wo_df['Collected_Incl_GST'].sum()
        receivable_val = wo_df['Amount_Receivable'].sum()
        unbilled_val = wo_df['Unbilled_Excl_GST'].sum()

        collection_efficiency = (collected_val / billed_val * 100.0) if billed_val > 0 else 0.0

        return {
            "won_deals_value": float(won_deals_val),
            "wo_contracted_value_excl_gst": float(wo_total_excl),
            "wo_contracted_value_incl_gst": float(wo_total_incl),
            "total_billed_value": float(billed_val),
            "total_collected_value": float(collected_val),
            "outstanding_receivables": float(receivable_val),
            "unbilled_work_orders_value": float(unbilled_val),
            "collection_efficiency_pct": round(collection_efficiency, 1),
            "sector": sector or "All Sectors",
            "quarter": quarter or "All Quarters"
        }

    @staticmethod
    def get_sector_performance(df_deals: pd.DataFrame, df_wo: pd.DataFrame) -> pd.DataFrame:
        sectors = sorted(list(set(df_deals['Sector_Normalized'].dropna()).union(set(df_wo['Sector_Normalized'].dropna()))))
        
        rows = []
        for sec in sectors:
            if sec == "Unspecified / General" and len(sectors) > 1:
                continue
            d_sec = df_deals[df_deals['Sector_Normalized'] == sec]
            w_sec = df_wo[df_wo['Sector_Normalized'] == sec]

            d_count = len(d_sec)
            pipe_val = d_sec['Deal_Value'].sum()
            won_count = len(d_sec[d_sec['Deal Status'].astype(str).str.lower() == 'won'])

            wo_count = len(w_sec)
            billed_val = w_sec['Billed_Incl_GST'].sum()
            collected_val = w_sec['Collected_Incl_GST'].sum()
            completed_wo = len(w_sec[w_sec['Execution_Status_Clean'] == 'Completed'])
            exec_rate = (completed_wo / max(wo_count, 1) * 100.0) if wo_count > 0 else 0.0

            rows.append({
                "Sector": sec,
                "Deals Count": d_count,
                "Pipeline Value (₹)": float(pipe_val),
                "Won Deals": won_count,
                "Work Orders": wo_count,
                "Billed Value (₹)": float(billed_val),
                "Collected Value (₹)": float(collected_val),
                "Execution Completion Rate (%)": round(exec_rate, 1)
            })

        res_df = pd.DataFrame(rows)
        return res_df.sort_values(by="Pipeline Value (₹)", ascending=False).reset_index(drop=True)

    @staticmethod
    def get_operational_summary(df_wo: pd.DataFrame, sector: str = None, quarter: str = None) -> dict:
        wo_df = df_wo.copy()
        if sector and sector.lower() != 'all':
            wo_df = wo_df[wo_df['Sector_Normalized'].str.lower() == sector.lower()]
        if quarter and quarter.lower() != 'all':
            wo_df = wo_df[wo_df['Quarter'].astype(str).str.upper().str.contains(quarter.upper(), na=False)]

        total_wo = len(wo_df)
        exec_counts = wo_df['Execution_Status_Clean'].value_counts().to_dict()
        
        completed_count = exec_counts.get("Completed", 0)
        ongoing_count = exec_counts.get("Ongoing", 0)
        paused_count = exec_counts.get("Paused", 0)
        not_started_count = exec_counts.get("Not Started", 0)

        completion_pct = (completed_count / max(total_wo, 1) * 100.0)

        return {
            "total_work_orders": total_wo,
            "completed_count": completed_count,
            "ongoing_count": ongoing_count,
            "paused_count": paused_count,
            "not_started_count": not_started_count,
            "completion_rate_pct": round(completion_pct, 1),
            "status_breakdown": exec_counts,
            "sector": sector or "All Sectors",
            "quarter": quarter or "All Quarters"
        }

    @staticmethod
    def query_cross_board_deal(df_deals: pd.DataFrame, df_wo: pd.DataFrame, search_term: str) -> dict:
        term = search_term.lower().strip()
        
        deals_match = df_deals[df_deals['Deal Name'].astype(str).str.lower().str.contains(term, na=False)]
        wo_match = df_wo[df_wo['Deal name masked'].astype(str).str.lower().str.contains(term, na=False)]

        deal_records = deals_match[['Deal Name', 'Owner code', 'Deal Status', 'Deal Stage', 'Deal_Value', 'Sector_Normalized', 'Quarter']].to_dict('records')
        wo_records = wo_match[['Deal name masked', 'Customer Name Code', 'Execution_Status_Clean', 'Amount_Incl_GST', 'Billed_Incl_GST', 'Collected_Incl_GST', 'Amount_Receivable']].to_dict('records')

        return {
            "search_term": search_term,
            "matching_deals": deal_records,
            "matching_work_orders": wo_records
        }
