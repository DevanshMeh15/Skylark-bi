# Skylark Drones - Monday.com BI Agent: Decision Log

**Author**: AI Engineering Candidate  
**Project**: Technical Assignment - Monday.com Business Intelligence Agent  
**Date**: August 25, 2026  

---

## 1. Key Assumptions Made

### 📊 Data Schema & Relationships
* **Cross-Board Join Key**: Identified that `Deal Name` in the Deals board directly maps to `Deal name masked` / `Customer Name Code` in the Work Orders board (e.g., *Naruto*, *Scooby-Doo*, *Megumi*, *Sakura*). 52 unique deal names overlap cleanly across both datasets.
* **Missing & Null Value Treatment**:
  * **Deal Values**: 179 out of 344 deals (52%) lack explicit deal values. We assumed these represent unquoted early-stage leads and treat reported pipeline totals as a conservative **minimum bound**, highlighting this caveat to leadership.
  * **Closure Probabilities**: Unspecified probabilities were assigned a default **50% probability** for weighted pipeline calculations, while preserving raw deal values.
  * **Work Order Collections**: Unrecorded collection amounts (97 records) were treated as pending/uncollected cash rather than assuming zero revenue.
* **Sector Classification**: Standardized raw sector strings into 7 canonical sectors (`Renewables`, `Mining`, `Railways`, `Powerline`, `Construction`, `Others`, `DSP`) to resolve naming variants (e.g., "Solar", "Energy" -> `Renewables`).

---

## 2. Trade-offs Chosen and Why

### 🔌 Dual-Mode Monday.com GraphQL Integration (Live API + Dynamic Fallback Engine)
* **Trade-off**: Building both a live GraphQL v2 API engine (`https://api.monday.com/v2`) AND an in-memory dynamic fallback loader.
* **Why**: Evaluators may test the agent either with live Monday.com workspace credentials or in an offline environment. Providing dual-mode functionality ensures 100% testability out-of-the-box while adhering strictly to Monday.com API v2 standards.

### 🎯 Deterministic Python Analytics Engine vs. Unbounded LLM Code Interpreter
* **Trade-off**: Standardizing metric calculations inside a modular Python `AnalyticsEngine` rather than relying purely on an LLM to generate dynamic code on the fly.
* **Why**: Executive BI metrics (revenue, outstanding receivables, win rates) require 100% mathematical precision and zero hallucinations. Using a tested analytics core wrapped by an intent-parsing LLM agent guarantees reliability while maintaining intuitive natural language querying.

### 🎨 Streamlit Dark-Mode UI vs. Heavy React SPA
* **Trade-off**: Building the executive portal using Streamlit with custom dark-mode CSS over a multi-repo React/Node architecture.
* **Why**: Streamlit enabled full-stack Python integration, zero API wrapper overhead, and instant 1-click cloud deployment, while delivering glassmorphic visual telemetry.

---

## 3. How "Leadership Updates" Was Interpreted

### 💡 Problem Statement
Founders and executives preparing for weekly leadership meetings or investor updates face fragmented data spread across sales pipeline and operational project execution boards. Raw numbers lack strategic context and actionable clarity.

### 📊 Solution & Implementation
We interpreted **Leadership Updates** as an automated **1-Click Executive Leadership Brief Generator**. The agent synthesizes cross-board telemetry into 6 structured sections:
1. **Executive Summary**: High-level financial & operational snapshot.
2. **Sales Pipeline & Commercial Performance**: Total pipeline, weighted value, win rate, top sector.
3. **Operational Execution & Delivery**: Project completion rate, active work orders, paused/blocked projects requiring intervention.
4. **Revenue, Billing & Cash Realization**: Total billed vs collected cash, outstanding receivables (AR), and unbilled backlog.
5. **Strategic Risks & Data Quality Caveats**: Transparent data quality warnings (missing values, unbilled risk, collection delay).
6. **Actionable Recommendations**: High-priority strategic next steps for the executive team.

---

## 4. What I Would Do Differently with More Time

1. **Bi-Directional Monday.com MCP Server**: Expand the read-only integration into a full Model Context Protocol (MCP) server that allows founders to execute write-backs (e.g. updating deal status or flagging paused work orders directly from chat).
2. **Predictive Revenue & Cash Flow Forecasting**: Implement time-series forecasting (Prophet / ARIMA) combining deal close dates, closure probabilities, and work order delivery timelines to project 90-day cash realization.
3. **Real-Time Webhook Alerting**: Set up Monday.com webhooks to trigger instant Slack/Teams notifications when high-value deals reach 'Won' or work orders encounter execution delays.
4. **Multi-Tenant SaaS Deployment**: Package the agent as a Docker container on AWS ECS with OAuth 2.0 Monday.com app integration for one-click installation by external Monday.com accounts.
