import os
import requests
import pandas as pd

class MondayClient:
    """
    Client for Monday.com GraphQL API v2.
    Supports both live API querying and dynamic fallback to imported data schemas.
    """
    def __init__(self, api_token: str = None, deals_board_id: str = None, work_orders_board_id: str = None):
        self.api_token = api_token or os.getenv("MONDAY_API_TOKEN", "")
        self.deals_board_id = deals_board_id or os.getenv("MONDAY_DEALS_BOARD_ID", "")
        self.work_orders_board_id = work_orders_board_id or os.getenv("MONDAY_WORK_ORDERS_BOARD_ID", "")
        self.api_url = "https://api.monday.com/v2"

    def is_live_configured(self) -> bool:
        return bool(self.api_token and self.deals_board_id and self.work_orders_board_id)

    def _execute_graphql(self, query: str, variables: dict = None) -> dict:
        headers = {
            "Authorization": self.api_token,
            "Content-Type": "application/json",
            "API-Version": "2023-10"
        }
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def fetch_board_items_live(self, board_id: str) -> list[dict]:
        query = """
        query ($board_id: [ID!]) {
          boards (ids: $board_id) {
            id
            name
            columns {
              id
              title
              type
            }
            items_page (limit: 500) {
              items {
                id
                name
                column_values {
                  id
                  text
                  value
                }
              }
            }
          }
        }
        """
        data = self._execute_graphql(query, {"board_id": [board_id]})
        boards = data.get("data", {}).get("boards", [])
        if not boards:
            return []
        
        board = boards[0]
        col_map = {col["id"]: col["title"] for col in board.get("columns", [])}
        
        raw_items = board.get("items_page", {}).get("items", [])
        parsed_items = []
        for item in raw_items:
            row = {"Name": item.get("name")}
            for cv in item.get("column_values", []):
                col_title = col_map.get(cv.get("id"), cv.get("id"))
                row[col_title] = cv.get("text")
            parsed_items.append(row)
        
        return parsed_items

    def fetch_deals_board(self) -> pd.DataFrame:
        """
        Fetch Deals board either live from Monday.com GraphQL API or via resilient loader.
        """
        if self.is_live_configured():
            try:
                items = self.fetch_board_items_live(self.deals_board_id)
                if items:
                    return pd.DataFrame(items)
            except Exception as e:
                print(f"[MondayClient Warning] Live fetch failed for Deals: {e}. Falling back to dynamic board loader.")

        # Fallback dynamic loader reading Monday-imported format
        deals_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Deal funnel Data.xlsx')
        if os.path.exists(deals_path):
            return pd.read_excel(deals_path)
        raise FileNotFoundError("Deal funnel Data.xlsx not found.")

    def fetch_work_orders_board(self) -> pd.DataFrame:
        """
        Fetch Work Orders board either live from Monday.com GraphQL API or via resilient loader.
        """
        if self.is_live_configured():
            try:
                items = self.fetch_board_items_live(self.work_orders_board_id)
                if items:
                    return pd.DataFrame(items)
            except Exception as e:
                print(f"[MondayClient Warning] Live fetch failed for Work Orders: {e}. Falling back to dynamic board loader.")

        # Fallback dynamic loader reading Monday-imported format
        wo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Work_Order_Tracker Data.xlsx')
        if os.path.exists(wo_path):
            return pd.read_excel(wo_path, header=1)
        raise FileNotFoundError("Work_Order_Tracker Data.xlsx not found.")
