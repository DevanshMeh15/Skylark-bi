import pandas as pd
import numpy as np
import re

class ResilienceEngine:
    """
    Data Resilience Engine for cleaning, normalizing, and auditing messy business data
    from Monday.com deals and work orders boards (supports both raw Excel and live GraphQL column names).
    """
    
    SECTOR_MAPPING = {
        'mining': 'Mining',
        'renewables': 'Renewables',
        'renewable': 'Renewables',
        'solar': 'Renewables',
        'wind': 'Renewables',
        'energy': 'Renewables',
        'railways': 'Railways',
        'railway': 'Railways',
        'powerline': 'Powerline',
        'power': 'Powerline',
        'construction': 'Construction',
        'dsp': 'DSP',
        'tender': 'Tender',
        'manufacturing': 'Manufacturing',
        'aviation': 'Aviation',
        'security': 'Security & Surveillance',
        'security and surveillance': 'Security & Surveillance',
        'others': 'Others',
        'other': 'Others'
    }

    def __init__(self):
        self.deals_quality_report = {}
        self.wo_quality_report = {}

    def normalize_sector(self, sector_raw) -> str:
        if pd.isna(sector_raw) or not str(sector_raw).strip():
            return "Unspecified / General"
        sec_str = str(sector_raw).strip().lower()
        if sec_str in ['sector/service', 'sector service', 'sector', 'nan', 'none', 'null']:
            return "Unspecified / General"
        
        for key, val in self.SECTOR_MAPPING.items():
            if key in sec_str:
                return val
        return str(sector_raw).strip().title()

    def clean_probability(self, prob_raw) -> float:
        if pd.isna(prob_raw):
            return np.nan
        prob_str = str(prob_raw).replace('%', '').strip().lower()
        if 'high' in prob_str:
            return 0.8
        if 'med' in prob_str:
            return 0.5
        if 'low' in prob_str:
            return 0.2
        try:
            val = float(prob_str)
            if val > 1.0:
                val = val / 100.0
            return max(0.0, min(1.0, val))
        except ValueError:
            return np.nan

    def clean_currency(self, val_raw) -> float:
        if pd.isna(val_raw):
            return np.nan
        if isinstance(val_raw, (int, float)):
            return float(val_raw)
        val_str = str(val_raw).replace('$', '').replace('₹', '').replace(',', '').strip()
        try:
            return float(val_str)
        except ValueError:
            return np.nan

    def _find_col(self, df: pd.DataFrame, candidates: list) -> str:
        for c in df.columns:
            c_clean = str(c).strip().lower()
            for cand in candidates:
                if cand.lower() in c_clean:
                    return c
        return None

    def clean_deals(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        df = df_raw.copy()
        
        name_col = self._find_col(df, ['deal name', 'name']) or df.columns[0]
        if name_col in df.columns:
            df['Deal Name'] = df[name_col]
            df = df[df['Deal Name'].notnull()]
            df = df[df['Deal Name'].astype(str).str.strip().str.lower() != 'deal name']

        # Flexible column resolution
        status_col = self._find_col(df, ['deal status', 'status'])
        stage_col = self._find_col(df, ['deal stage', 'stage'])
        value_col = self._find_col(df, ['masked deal value', 'value', 'amount'])
        sector_col = self._find_col(df, ['sector service', 'sector/service', 'sector'])
        prob_col = self._find_col(df, ['closure probability', 'probability'])
        owner_col = self._find_col(df, ['owner code', 'owner'])
        client_col = self._find_col(df, ['client code', 'client'])

        df['Deal Status'] = df[status_col].astype(str).str.strip() if status_col else "Open"
        df['Deal Stage'] = df[stage_col].astype(str).str.strip() if stage_col else "Unspecified"
        df['Owner code'] = df[owner_col].astype(str).str.strip() if owner_col else "Unassigned"
        df['Client Code'] = df[client_col].astype(str).str.strip() if client_col else "Unassigned"

        df['Deal_Value'] = df[value_col].apply(self.clean_currency) if value_col else np.nan
        df['Closure_Probability'] = df[prob_col].apply(self.clean_probability) if prob_col else np.nan
        df['Weighted_Deal_Value'] = df['Deal_Value'] * df['Closure_Probability'].fillna(0.5)

        df['Sector_Normalized'] = df[sector_col].apply(self.normalize_sector) if sector_col else "Unspecified / General"

        # Safe Date parsing & Quarter extraction
        clean_deals_dt_series = None
        for col in list(df.columns):
            if any(k in str(col).lower() for k in ['date', 'created', 'tentative', 'close']):
                dt_series = pd.to_datetime(df[col], format='mixed', errors='coerce')
                if dt_series.notnull().any():
                    df[f'{col}_Clean'] = dt_series
                    if clean_deals_dt_series is None:
                        clean_deals_dt_series = dt_series

        if clean_deals_dt_series is not None:
            df['Quarter'] = clean_deals_dt_series.dt.to_period('Q').astype(str).replace({'NaT': 'Unscheduled', 'nan': 'Unscheduled'})
        else:
            df['Quarter'] = "Unscheduled"

        # Audit Report
        total_rows = len(df)
        missing_val_count = df['Deal_Value'].isna().sum()
        missing_prob_count = df['Closure_Probability'].isna().sum()
        
        self.deals_quality_report = {
            "total_records": total_rows,
            "missing_deal_values": missing_val_count,
            "missing_deal_values_pct": round((missing_val_count / max(total_rows, 1)) * 100, 1),
            "missing_closure_prob": missing_prob_count,
            "missing_closure_prob_pct": round((missing_prob_count / max(total_rows, 1)) * 100, 1),
            "data_completeness_pct": round(100.0 - ((missing_val_count + missing_prob_count) / (total_rows * 2)) * 100, 1),
            "warnings": [
                f"{missing_val_count} deals ({round(missing_val_count/total_rows*100)}%) missing deal value — reported figures represent minimum bound.",
                f"{missing_prob_count} deals missing explicit closure probability — default probability 50% applied for weighted pipeline calculations."
            ]
        }

        # PyArrow safe object sanitization
        for c in df.select_dtypes(include=['object']).columns:
            df[c] = df[c].astype(str).replace({'nan': '', 'None': '', 'NaT': ''})

        return df

    def clean_work_orders(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        df = df_raw.copy()

        name_col = self._find_col(df, ['deal name masked', 'deal name', 'name']) or df.columns[0]
        if name_col in df.columns:
            df['Deal name masked'] = df[name_col]
            df = df[df['Deal name masked'].notnull()]
            df = df[df['Deal name masked'].astype(str).str.strip().str.lower() != 'deal name masked']

        cust_col = self._find_col(df, ['customer name code', 'customer'])
        exec_col = self._find_col(df, ['execution status', 'status'])
        sector_col = self._find_col(df, ['sector'])

        df['Customer Name Code'] = df[cust_col].astype(str).str.strip() if cust_col else "Unassigned"
        df['Execution Status'] = df[exec_col].astype(str).str.strip() if exec_col else "Not Specified"
        df['Sector_Normalized'] = df[sector_col].apply(self.normalize_sector) if sector_col else "Unspecified / General"

        # Financial Column Mapping (supports both raw Excel headers and Monday GraphQL titles)
        amount_mapping = {
            'Amount in Rupees (Excl of GST) (Masked)': 'Amount_Excl_GST',
            'Amount Excl GST': 'Amount_Excl_GST',
            'Amount in Rupees (Incl of GST) (Masked)': 'Amount_Incl_GST',
            'Amount Incl GST': 'Amount_Incl_GST',
            'Billed Value in Rupees (Excl of GST.) (Masked)': 'Billed_Excl_GST',
            'Billed Value Excl GST': 'Billed_Excl_GST',
            'Billed Value in Rupees (Incl of GST.) (Masked)': 'Billed_Incl_GST',
            'Billed Value Incl GST': 'Billed_Incl_GST',
            'Collected Amount in Rupees (Incl of GST.) (Masked)': 'Collected_Incl_GST',
            'Collected Amount Incl GST': 'Collected_Incl_GST',
            'Amount Receivable (Masked)': 'Amount_Receivable',
            'Amount Receivable': 'Amount_Receivable',
            'Amount to be billed in Rs. (Exl. of GST) (Masked)': 'Unbilled_Excl_GST',
            'Amount to be billed in Rs. (Incl. of GST) (Masked)': 'Unbilled_Excl_GST',
            'Amount To Be Billed': 'Unbilled_Excl_GST',
            'Amount To Be Billed Incl GST': 'Unbilled_Excl_GST'
        }

        # Initialize targets to 0.0
        target_cols = ['Amount_Excl_GST', 'Amount_Incl_GST', 'Billed_Excl_GST', 'Billed_Incl_GST', 'Collected_Incl_GST', 'Amount_Receivable', 'Unbilled_Excl_GST']
        for tc in target_cols:
            df[tc] = 0.0

        for col in df.columns:
            for orig_key, target_col in amount_mapping.items():
                if orig_key.lower() in str(col).lower():
                    s_vals = df[col].apply(self.clean_currency).fillna(0.0)
                    df[target_col] = np.maximum(df[target_col], s_vals)

        # Execution Status Normalization
        def norm_exec_status(stat_raw):
            if pd.isna(stat_raw):
                return "Not Specified"
            s = str(stat_raw).lower()
            if 'complete' in s:
                return "Completed"
            if 'ongoing' in s or 'executed' in s:
                return "Ongoing"
            if 'pause' in s or 'struck' in s:
                return "Paused"
            if 'not start' in s:
                return "Not Started"
            if 'pending' in s or 'details' in s:
                return "Pending Client Details"
            return "Other"

        df['Execution_Status_Clean'] = df['Execution Status'].apply(norm_exec_status)

        # Safe Date parsing & Quarter extraction for Work Orders
        clean_dt_series = None
        for col in list(df.columns):
            if any(k in str(col).lower() for k in ['date', 'po', 'loi', 'invoice', 'delivery', 'start']):
                dt_s = pd.to_datetime(df[col], format='mixed', errors='coerce')
                if dt_s.notnull().any():
                    df[f'{col}_Clean'] = dt_s
                    if clean_dt_series is None:
                        clean_dt_series = dt_s

        if clean_dt_series is not None:
            df['Quarter'] = clean_dt_series.dt.to_period('Q').astype(str).replace({'NaT': 'Unscheduled', 'nan': 'Unscheduled'})
        else:
            df['Quarter'] = "Unscheduled"

        # Quality Audit
        total_rows = len(df)
        missing_collected = (df['Collected_Incl_GST'] == 0.0).sum()
        
        self.wo_quality_report = {
            "total_records": total_rows,
            "zero_or_uncollected_count": missing_collected,
            "uncollected_pct": round((missing_collected / max(total_rows, 1)) * 100, 1),
            "warnings": [
                f"{missing_collected} work orders have zero or unrecorded collection figures — collection metrics reflect processed payments only."
            ]
        }

        # PyArrow safe object sanitization
        for c in df.select_dtypes(include=['object']).columns:
            df[c] = df[c].astype(str).replace({'nan': '', 'None': '', 'NaT': ''})

        return df
