# 🛸 Skylark Drones - Monday.com Business Intelligence Agent

An intelligent, resilient Business Intelligence AI Agent designed for founders and executives to query real-world messy data across **Monday.com Deals and Work Orders boards**.

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12-green.svg)
![Monday.com](https://img.shields.io/badge/Monday.com-GraphQL%20v2-purple.svg)

---

## 🌟 Key Features

1. **🔌 Monday.com Integration (Dual-Mode)**
   - Connects dynamically to Monday.com GraphQL API v2 (`https://api.monday.com/v2`).
   - Includes a automated setup script (`scripts/setup_monday.py`) to create and populate Monday.com boards programmatically.
   - Includes an in-memory dynamic GraphQL fallback engine for instant evaluation without pre-configured API tokens.

2. **🛡️ Data Resilience & Data Quality Engine**
   - **Header Sanitization**: Filters out duplicate header rows (`Deal Stage == 'Deal Stage'`).
   - **Sector Normalization**: Standardizes messy sector names (`Mining`, `Renewables`, `Railways`, `Powerline`, `Construction`, `Others`, `DSP`).
   - **Currency & Numeric Cleaning**: Safe float parsing for masked deal values, billed amounts, collected cash, and outstanding receivables.
   - **Data Quality Caveats**: Transparently surfaces missing value counts, coverage rates, and operational warnings to the user.

3. **💬 Conversational Founder BI Assistant**
   - Natural language query understanding for pipeline health, revenue collections, sector performance, and operational metrics.
   - Ambiguity detection with automated clarifying questions when queries are vague.
   - Cross-board querying linking Deals and Work Orders on deal names and client codes.

4. **📄 1-Click Executive Leadership Brief Generator**
   - Synthesizes cross-board telemetry into board-ready leadership updates.
   - Covers Executive Summary, Commercial Pipeline, Operational Delivery, Cash Realization, Strategic Risks, and Actionable Next Steps.
   - Markdown export functionality.

---

## 🏗️ Architecture Overview

```
skylar-bi-agent/
├── app.py                          # Streamlit UI Application (Conversational Chat + Visual Analytics)
├── monday_integration/
│   ├── monday_client.py            # Monday.com GraphQL v2 API Client & Fallback Engine
├── data_resilience/
│   ├── resilience_engine.py        # Data Resilience, Cleaning, Sector Normalization, & Data Quality Audit
├── bi_engine/
│   ├── analytics_engine.py         # Cross-board BI & Metric Calculation Engine
│   ├── agent.py                    # Conversational BI Agent & Intent Parser
│   ├── leadership_brief.py         # Executive Leadership Brief Generator
├── scripts/
│   ├── setup_monday.py             # Script to populate Monday.com boards via GraphQL API
├── Deal funnel Data.xlsx           # Deals dataset
├── Work_Order_Tracker Data.xlsx    # Work Orders dataset
├── DECISION_LOG.md                 # Decision Log (Assumptions, Trade-offs, Leadership Update interpretation)
├── README.md                       # Documentation & Setup Guide
└── requirements.txt                # Python Dependencies
```

---

## ⚙️ Monday.com Configuration & Board Setup Guide

### Option 1: Automatic Setup via Script (Recommended for Live Monday.com Workspaces)
To import `Deal funnel Data.xlsx` and `Work_Order_Tracker Data.xlsx` directly into your Monday.com workspace:

1. Obtain your Monday.com API Token from **Monday.com -> Developer -> My Tokens**.
2. Run the automated setup script:
   ```bash
   python scripts/setup_monday.py --token YOUR_MONDAY_API_TOKEN
   ```
3. The script will create **"Skylark Deals Funnel"** and **"Skylark Work Order Tracker"** boards on Monday.com and output their Board IDs.
4. Set the environment variables in a `.env` file or directly in the UI drawer:
   ```env
   MONDAY_API_TOKEN=your_token_here
   MONDAY_DEALS_BOARD_ID=your_deals_board_id
   MONDAY_WORK_ORDERS_BOARD_ID=your_work_orders_board_id
   ```

### Option 2: Instant Evaluation Mode (No Monday.com Token Required)
If no API token is supplied, the agent automatically runs in **Emulated GraphQL API Mode**, dynamically serving board schemas and item records from the datasets out-of-the-box.

---

## 🚀 Local Installation & Running Guide

### Prerequisites
- Python 3.10+
- `pip`

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone <repository-url>
cd skylar-bi-agent
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run the Streamlit BI Application
```bash
streamlit run app.py
```
Open browser at `http://localhost:8501`.

---

## 🤖 AI Tools Used & Rationale

- **Google Antigravity Agentic IDE & Gemini 3.6 Flash**: Used for rapid pair programming, data schema analysis, resilience engine design, and automated testing.
- **Pandas & Altair**: Used for high-performance tabular data processing, cross-board joins, and interactive data visualizations.

---

## 📄 Decision Log & Trade-offs
For detailed explanations of key assumptions, technical trade-offs, handling messy data, and the interpretation of leadership updates, please refer to [DECISION_LOG.md](DECISION_LOG.md).
