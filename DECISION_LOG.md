# Skylark Drones - Monday.com BI Agent: Decision Log

**Author**: AI Engineering Candidate  
**Project**: Technical Assignment - Monday.com Business Intelligence Agent  
**Date**: August 25, 2026  

---

## 1. Key Assumptions Made

### Data Schema & Relationships
* **Cross-Board Join Key**: Identified that `Deal Name` in the Deals board directly maps to `Deal name masked` / `Customer Name Code` in the Work Orders board (e.g., *Naruto*, *Scooby-Doo*, *Megumi*, *Sakura*). 52 unique deal names overlap cleanly across both boards.
* **Missing & Null Values Handling**:
  * **Deal Values**: 179 out of 344 deals (52%) lack an explicit deal value. We assumed these reflect unquoted early-stage leads and treat reported pipeline totals as a conservative **minimum bound**, highlighting this caveat to leadership.
  * **Closure Probabilities**: 344 deals lacked explicit probability percentages. We assigned a default **50% probability** for weighted pipeline calculations, while preserving raw deal values.
  * **Work Order Collections**: Unrecorded collection amounts (97 records) were treated as pending/uncollected cash rather than assuming zero revenue.
* **Sector Classification**: Standardized raw sector strings into 7 canonical sectors (`Renewables`, `Mining`, `Railways`, `Powerline`, `Construction`, `Others`, `DSP`) to resolve minor naming inconsistencies (e.g., "Solar", "Energy" -> `Renewables`).

---

## 2. Technical Decisions & Trade-offs Chosen

### A. Dual-Mode Monday.com GraphQL Integration (Live API + Dynamic Fallback Engine)
* **Choice**: Implemented a dynamic `MondayClient` supporting both live Monday.com GraphQL API v2 (`https://api.monday.com/v2`) and an in-memory dynamic fallback engine.
* **Rationale**: Evaluators may test the agent either with live Monday.com workspace credentials or without local setup. Providing dual-mode functionality ensures 100% testability out-of-the-box while maintaining strict dynamic querying requirements.

### B. Python Analytics Engine vs. Unbounded LLM Code Interpreter
* **Choice**: Built a structured, deterministic `AnalyticsEngine` and `ResilienceEngine` for metric calculations, wrapped by a natural language query interpreter (`BIAgent`).
* **Rationale**: Financial and operational BI metrics (revenue, outstanding receivables, win rates) cannot afford LLM hallucinations. Standardizing calculations in tested Python engines guarantees 100% numerical precision, while the conversational agent layer delivers intuitive executive interaction.

### C. Streamlit Dark-Mode Glassmorphism UI vs. React SPA
* **Choice**: Built the frontend using Python Streamlit with custom CSS (glassmorphism theme, metric cards, Altair charts, interactive chat, and markdown exporter).
* **Rationale**: Streamlit enabled full-stack python integration within the 5-hour timeframe, avoiding API layer overhead while delivering a modern UI experience.

---

## 3. Interpretation of "Leadership Updates"

### Problem
Founders and executives preparing for weekly leadership meetings or investor updates face fragmented data spread across sales pipeline and project execution boards. Raw numbers lack strategic context.

### Solution & Implementation
We interpreted **Leadership Updates** as an automated **1-Click Executive Leadership Brief Generator**. The agent synthesizes cross-board telemetry into 5 structured sections:
1. **Executive Summary**: High-level financial & operational snapshot.
2. **Sales Pipeline & Commercial Performance**: Total pipeline, weighted value, win rate, top sector.
3. **Operational Execution & Delivery**: Project completion rate, active work orders, paused/struck projects requiring intervention.
4. **Revenue, Billing & Cash Collections**: Total billed vs collected cash, outstanding receivables (AR), and unbilled work order backlog.
5. **Strategic Risks & Data Quality Caveats**: Transparent data quality warnings (missing values, unbilled risk, collection delay).
6. **Actionable Recommendations**: 3 high-priority strategic steps for the executive team.

---

## 4. What I Would Do Differently with More Time

1. **Full Bi-Directional Monday.com MCP Server**: Expand the read-only integration into a full Model Context Protocol (MCP) server that allows founders to execute write-backs (e.g. updating deal status or flagging paused work orders directly from chat).
2. **Predictive Revenue & Cash Flow Forecasting**: Train a time-series forecasting model (Prophet / ARIMA) combining deal close dates, closure probabilities, and work order delivery timelines to project 90-day cash flow.
3. **Real-Time Webhook Alerting**: Set up Monday.com webhooks to trigger instant Slack/Teams notifications when high-value deals reach 'Won' or work orders encounter execution delays.
4. **Multi-Tenant SaaS Deployment**: Package the agent as a Dockerized container on AWS ECS/Render with OAuth 2.0 Monday.com app integration for one-click installation by external Monday.com accounts.
