"""
setup_monday.py
Production-grade initial setup utility script to programmatically create Deals and Work Orders boards on Monday.com,
create explicit typed columns (Text, Numbers, Date), normalize messy dates/currencies,
handle rate-limiting with exponential backoff retries, and output detailed row-level audit logs.

Usage:
    python scripts/setup_monday.py --token YOUR_MONDAY_API_TOKEN
"""

import argparse
import os
import sys
import time
import json
import re
import pandas as pd
import requests

MONDAY_API_URL = "https://api.monday.com/v2"

def execute_query(query: str, variables: dict, token: str, max_retries: int = 5) -> dict:
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "API-Version": "2023-10"
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(MONDAY_API_URL, json=payload, headers=headers, timeout=15)
            if response.status_code in [429, 500, 502, 503, 504]:
                wait_time = 2 ** attempt
                print(f"   [API Throttled/Server Error {response.status_code}] Retrying in {wait_time}s... (Attempt {attempt}/{max_retries})")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            res_json = response.json()
            if "errors" in res_json and res_json["errors"]:
                err_msg = str(res_json["errors"])
                if "complexity" in err_msg.lower() or "limit" in err_msg.lower():
                    time.sleep(2 * attempt)
                    continue
                print(f"   [GraphQL Error]: {err_msg}")
            return res_json or {}
        except requests.RequestException as req_err:
            if attempt == max_retries:
                print(f"[HTTP Request Error after {max_retries} attempts]: {req_err}")
                raise
            time.sleep(2 ** attempt)
        except Exception as gen_err:
            if attempt == max_retries:
                print(f"[Unexpected Error after {max_retries} attempts]: {gen_err}")
                raise
            time.sleep(2 ** attempt)
    return {}

def create_board(board_name: str, token: str, workspace_id: str = None) -> str:
    query = """
    mutation ($name: String!, $kind: BoardKind!, $workspace_id: ID) {
      create_board (board_name: $name, board_kind: $kind, workspace_id: $workspace_id) {
        id
      }
    }
    """
    vars = {"name": board_name, "kind": "public", "workspace_id": workspace_id if workspace_id else None}
    res = execute_query(query, vars, token)
    data = res.get("data") or {}
    board_id = (data.get("create_board") or {}).get("id")
    print(f"[OK] Created Board '{board_name}' (ID: {board_id})")
    return board_id

def create_column(board_id: str, title: str, col_type: str, token: str) -> str:
    query = """
    mutation ($board_id: ID!, $title: String!, $col_type: ColumnType!) {
      create_column (board_id: $board_id, title: $title, column_type: $col_type) {
        id
        title
      }
    }
    """
    vars = {"board_id": board_id, "title": title, "col_type": col_type}
    res = execute_query(query, vars, token)
    data = res.get("data") or {}
    col_id = (data.get("create_column") or {}).get("id")
    print(f"   Created column '{title}' ({col_type}) -> ID: {col_id}")
    return col_id

def create_item(board_id: str, item_name: str, column_values: dict, token: str):
    query = """
    mutation ($board_id: ID!, $item_name: String!, $column_values: JSON!) {
      create_item (board_id: $board_id, item_name: $item_name, column_values: $column_values) {
        id
      }
    }
    """
    vars = {
        "board_id": board_id,
        "item_name": str(item_name),
        "column_values": json.dumps(column_values)
    }
    return execute_query(query, vars, token)

def parse_date_safely(val):
    if pd.isna(val):
        return None
    try:
        dt = pd.to_datetime(val, format='mixed', errors='coerce')
        if pd.notnull(dt):
            return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    return None

def parse_number_safely(val):
    if pd.isna(val):
        return None
    try:
        val_str = str(val).replace(',', '').replace('$', '').replace('₹', '').replace('%', '').strip().lower()
        
        multiplier = 1.0
        if 'cr' in val_str or 'crore' in val_str:
            multiplier = 1e7
            val_str = re.sub(r'[a-z\s]', '', val_str)
        elif 'lakh' in val_str or 'lac' in val_str or val_str.endswith('l'):
            multiplier = 1e5
            val_str = re.sub(r'[a-z\s]', '', val_str)
        elif 'k' in val_str or 'thousand' in val_str:
            multiplier = 1e3
            val_str = re.sub(r'[a-z\s]', '', val_str)
            
        return float(val_str) * multiplier
    except Exception:
        return None

def find_exact_or_substring_col(df: pd.DataFrame, exact_title: str, fallback_keywords: list) -> str:
    for c in df.columns:
        if str(c).strip().lower() == exact_title.lower():
            return c
    for c in df.columns:
        c_clean = str(c).strip().lower()
        if all(kw.lower() in c_clean for kw in fallback_keywords):
            return c
    return None

def auto_detect_headers(file_path: str) -> pd.DataFrame:
    try:
        df_first = pd.read_excel(file_path, header=None, nrows=3)
        first_row_str = ' '.join([str(x) for x in df_first.iloc[0].tolist()]).lower()
        if 'deal' not in first_row_str and 'customer' not in first_row_str and 'serial' not in first_row_str:
            return pd.read_excel(file_path, header=1)
        return pd.read_excel(file_path, header=0)
    except Exception:
        return pd.read_excel(file_path)

def setup_boards(token: str, workspace_id: str = None):
    print("=== Starting Production-Grade Monday.com Board Setup & Data Import ===\n", flush=True)
    
    audit_log = {
        "deals_success": 0, "deals_failed": 0,
        "wo_success": 0, "wo_failed": 0,
        "errors": []
    }

    # -------------------------------------------------------------
    # 1. DEALS BOARD CREATION
    # -------------------------------------------------------------
    deals_path = "Deal funnel Data.xlsx"
    deals_board_id = None
    if os.path.exists(deals_path):
        df_deals = auto_detect_headers(deals_path)
        name_col = find_exact_or_substring_col(df_deals, 'Deal Name', ['deal', 'name']) or df_deals.columns[0]
        df_deals = df_deals[df_deals[name_col].notnull() & (df_deals[name_col].astype(str).str.strip().str.lower() != 'deal name')]

        deals_board_id = create_board("Skylark Deals Funnel", token, workspace_id)
        time.sleep(1)

        # Create Typed Columns (Closure Probability as 'text' to preserve High/Medium/Low/percentages)
        c_owner = create_column(deals_board_id, "Owner Code", "text", token)
        c_client = create_column(deals_board_id, "Client Code", "text", token)
        c_status = create_column(deals_board_id, "Deal Status", "text", token)
        c_stage = create_column(deals_board_id, "Deal Stage", "text", token)
        c_value = create_column(deals_board_id, "Masked Deal Value", "numbers", token)
        c_sector = create_column(deals_board_id, "Sector Service", "text", token)
        c_prob = create_column(deals_board_id, "Closure Probability", "text", token) # TEXT type for High/Med/Low
        c_date_close = create_column(deals_board_id, "Tentative Close Date", "date", token)
        c_date_close_a = create_column(deals_board_id, "Close Date (A)", "date", token)
        c_date_created = create_column(deals_board_id, "Created Date", "date", token)
        c_product = create_column(deals_board_id, "Product Deal", "text", token)
        time.sleep(1)

        # Precise Column resolution
        col_owner = find_exact_or_substring_col(df_deals, 'Owner code', ['owner'])
        col_client = find_exact_or_substring_col(df_deals, 'Client Code', ['client'])
        col_status = find_exact_or_substring_col(df_deals, 'Deal Status', ['status'])
        col_stage = find_exact_or_substring_col(df_deals, 'Deal Stage', ['stage'])
        col_value = find_exact_or_substring_col(df_deals, 'Masked Deal value', ['masked', 'value'])
        col_sector = find_exact_or_substring_col(df_deals, 'Sector/service', ['sector'])
        col_prob = find_exact_or_substring_col(df_deals, 'Closure Probability', ['probability'])
        col_t_close = find_exact_or_substring_col(df_deals, 'Tentative Close Date', ['tentative'])
        col_close_a = find_exact_or_substring_col(df_deals, 'Close Date (A)', ['close date'])
        col_created = find_exact_or_substring_col(df_deals, 'Created Date', ['created date'])
        col_product = find_exact_or_substring_col(df_deals, 'Product deal', ['product'])

        print(f"\n[Importing] {len(df_deals)} deals into Monday.com...")
        for idx, (_, row) in enumerate(df_deals.iterrows()):
            item_name = str(row.get(name_col, "Untitled Deal")).strip()
            col_vals = {}
            
            try:
                if col_owner and pd.notnull(row.get(col_owner)) and c_owner:
                    col_vals[c_owner] = str(row[col_owner]).strip()

                if col_client and pd.notnull(row.get(col_client)) and c_client:
                    col_vals[c_client] = str(row[col_client]).strip()

                if col_status and pd.notnull(row.get(col_status)) and c_status:
                    col_vals[c_status] = str(row[col_status]).strip()

                if col_stage and pd.notnull(row.get(col_stage)) and c_stage:
                    col_vals[c_stage] = str(row[col_stage]).strip()

                if col_value and pd.notnull(row.get(col_value)) and c_value:
                    num = parse_number_safely(row[col_value])
                    if num is not None:
                        col_vals[c_value] = num

                if col_sector and pd.notnull(row.get(col_sector)) and c_sector:
                    col_vals[c_sector] = str(row[col_sector]).strip()

                if col_prob and pd.notnull(row.get(col_prob)) and c_prob:
                    col_vals[c_prob] = str(row[col_prob]).strip() # Preserves High/Medium/Low & percentages

                if col_t_close and pd.notnull(row.get(col_t_close)) and c_date_close:
                    dt_iso = parse_date_safely(row[col_t_close])
                    if dt_iso:
                        col_vals[c_date_close] = {"date": dt_iso}

                if col_close_a and pd.notnull(row.get(col_close_a)) and c_date_close_a:
                    dt_iso = parse_date_safely(row[col_close_a])
                    if dt_iso:
                        col_vals[c_date_close_a] = {"date": dt_iso}

                if col_created and pd.notnull(row.get(col_created)) and c_date_created:
                    dt_iso = parse_date_safely(row[col_created])
                    if dt_iso:
                        col_vals[c_date_created] = {"date": dt_iso}

                if col_product and pd.notnull(row.get(col_product)) and c_product:
                    col_vals[c_product] = str(row[col_product]).strip()

                create_item(deals_board_id, item_name, col_vals, token)
                audit_log["deals_success"] += 1
            except Exception as e:
                audit_log["deals_failed"] += 1
                audit_log["errors"].append(f"Deals Row {idx+2} ({item_name}): {e}")

            time.sleep(0.08)
            if (idx + 1) % 50 == 0 or (idx + 1) == len(df_deals):
                print(f"   Processed {idx + 1}/{len(df_deals)} deals...")

        print(f"[OK] Deals Board import complete! ({audit_log['deals_success']} succeeded, {audit_log['deals_failed']} failed)\n")

    # -------------------------------------------------------------
    # 2. WORK ORDERS BOARD CREATION
    # -------------------------------------------------------------
    wo_path = "Work_Order_Tracker Data.xlsx"
    wo_board_id = None
    if os.path.exists(wo_path):
        df_wo = auto_detect_headers(wo_path)
        name_col = find_exact_or_substring_col(df_wo, 'Deal name masked', ['deal', 'name']) or df_wo.columns[0]
        df_wo = df_wo[df_wo[name_col].notnull() & (df_wo[name_col].astype(str).str.strip().str.lower() != 'deal name masked')]

        wo_board_id = create_board("Skylark Work Order Tracker", token, workspace_id)
        time.sleep(1)

        # Create Typed Columns
        w_cust = create_column(wo_board_id, "Customer Name Code", "text", token)
        w_exec = create_column(wo_board_id, "Execution Status", "text", token)
        w_sec = create_column(wo_board_id, "Sector", "text", token)
        w_amt_excl = create_column(wo_board_id, "Amount Excl GST", "numbers", token)
        w_amt_incl = create_column(wo_board_id, "Amount Incl GST", "numbers", token)
        w_billed_excl = create_column(wo_board_id, "Billed Value Excl GST", "numbers", token)
        w_billed_incl = create_column(wo_board_id, "Billed Value Incl GST", "numbers", token)
        w_collected = create_column(wo_board_id, "Collected Amount Incl GST", "numbers", token)
        w_receivable = create_column(wo_board_id, "Amount Receivable", "numbers", token)
        w_unbilled_incl = create_column(wo_board_id, "Amount To Be Billed Incl GST", "numbers", token)
        w_po_date = create_column(wo_board_id, "Date of PO LOI", "date", token)
        w_start_date = create_column(wo_board_id, "Probable Start Date", "date", token)
        w_end_date = create_column(wo_board_id, "Probable End Date", "date", token)
        w_billing_stat = create_column(wo_board_id, "Billing Status", "text", token)
        w_collection_stat = create_column(wo_board_id, "Collection Status", "text", token)
        time.sleep(1)

        col_cust = find_exact_or_substring_col(df_wo, 'Customer Name Code', ['customer'])
        col_exec = find_exact_or_substring_col(df_wo, 'Execution Status', ['execution', 'status'])
        col_sec = find_exact_or_substring_col(df_wo, 'Sector', ['sector'])
        
        # Precise GST Column Matching
        col_excl = find_exact_or_substring_col(df_wo, 'Amount in Rupees (Excl of GST) (Masked)', ['amount', 'excl'])
        col_incl = find_exact_or_substring_col(df_wo, 'Amount in Rupees (Incl of GST) (Masked)', ['amount', 'incl'])
        col_billed_excl = find_exact_or_substring_col(df_wo, 'Billed Value in Rupees (Excl of GST.) (Masked)', ['billed', 'excl'])
        col_billed_incl = find_exact_or_substring_col(df_wo, 'Billed Value in Rupees (Incl of GST.) (Masked)', ['billed', 'incl'])
        col_collected = find_exact_or_substring_col(df_wo, 'Collected Amount in Rupees (Incl of GST.) (Masked)', ['collected'])
        col_receivable = find_exact_or_substring_col(df_wo, 'Amount Receivable (Masked)', ['receivable'])
        col_unbilled_incl = find_exact_or_substring_col(df_wo, 'Amount to be billed in Rs. (Incl. of GST) (Masked)', ['to be billed', 'incl'])
        
        col_po_date = find_exact_or_substring_col(df_wo, 'Date of PO/LOI', ['po/loi'])
        col_start_date = find_exact_or_substring_col(df_wo, 'Probable Start Date', ['start date'])
        col_end_date = find_exact_or_substring_col(df_wo, 'Probable End Date', ['end date'])
        col_billing_stat = find_exact_or_substring_col(df_wo, 'Billing Status', ['billing status'])
        col_collection_stat = find_exact_or_substring_col(df_wo, 'Collection status', ['collection status'])

        print(f"\n[Importing] {len(df_wo)} work orders into Monday.com...")
        for idx, (_, row) in enumerate(df_wo.iterrows()):
            item_name = str(row.get(name_col, "Untitled WO")).strip()
            col_vals = {}

            try:
                if col_cust and pd.notnull(row.get(col_cust)) and w_cust:
                    col_vals[w_cust] = str(row[col_cust]).strip()

                if col_exec and pd.notnull(row.get(col_exec)) and w_exec:
                    col_vals[w_exec] = str(row[col_exec]).strip()

                if col_sec and pd.notnull(row.get(col_sec)) and w_sec:
                    col_vals[w_sec] = str(row[col_sec]).strip()

                if col_billing_stat and pd.notnull(row.get(col_billing_stat)) and w_billing_stat:
                    col_vals[w_billing_stat] = str(row[col_billing_stat]).strip()

                if col_collection_stat and pd.notnull(row.get(col_collection_stat)) and w_collection_stat:
                    col_vals[w_collection_stat] = str(row[col_collection_stat]).strip()

                # Numeric Column Parsing
                num_pairs = [
                    (col_excl, w_amt_excl), (col_incl, w_amt_incl),
                    (col_billed_excl, w_billed_excl), (col_billed_incl, w_billed_incl),
                    (col_collected, w_collected), (col_receivable, w_receivable),
                    (col_unbilled_incl, w_unbilled_incl)
                ]
                for col_ref, target_cid in num_pairs:
                    if col_ref and pd.notnull(row.get(col_ref)) and target_cid:
                        num = parse_number_safely(row[col_ref])
                        if num is not None:
                            col_vals[target_cid] = num

                # Dates
                for date_ref, target_cid in [(col_po_date, w_po_date), (col_start_date, w_start_date), (col_end_date, w_end_date)]:
                    if date_ref and pd.notnull(row.get(date_ref)) and target_cid:
                        dt_iso = parse_date_safely(row[date_ref])
                        if dt_iso:
                            col_vals[target_cid] = {"date": dt_iso}

                create_item(wo_board_id, item_name, col_vals, token)
                audit_log["wo_success"] += 1
            except Exception as e:
                audit_log["wo_failed"] += 1
                audit_log["errors"].append(f"WorkOrders Row {idx+2} ({item_name}): {e}")

            time.sleep(0.08)
            if (idx + 1) % 50 == 0 or (idx + 1) == len(df_wo):
                print(f"   Processed {idx + 1}/{len(df_wo)} work orders...")

        print(f"[OK] Work Orders Board import complete! ({audit_log['wo_success']} succeeded, {audit_log['wo_failed']} failed)\n")

    print("=" * 65)
    print("MONDAY.COM BOARD SETUP & AUDIT COMPLETE!")
    print(f"Deals Board ID: {deals_board_id}")
    print(f"Work Orders Board ID: {wo_board_id}")
    print(f"Deals Import: {audit_log['deals_success']} Success, {audit_log['deals_failed']} Failed")
    print(f"Work Orders Import: {audit_log['wo_success']} Success, {audit_log['wo_failed']} Failed")
    if audit_log["errors"]:
        print(f"Total Row Errors: {len(audit_log['errors'])}")
    print("=" * 65)
    print("\nCopy these Board IDs into your app's sidebar or .env file to connect live!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate Monday.com Boards from Skylark datasets.")
    parser.add_argument("--token", required=True, help="Monday.com API Token")
    parser.add_argument("--workspace_id", required=False, help="Monday.com Workspace ID")
    args = parser.parse_args()
    
    setup_boards(args.token, args.workspace_id)
