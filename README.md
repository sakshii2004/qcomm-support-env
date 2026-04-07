---
title: QComm Support Agent Environment
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
  - fraud-prevention
  - logistics
  - support-agent
---

# QComm Support Agent Environment: Logistics Guard

The **QComm Support Agent Environment** is a high-fidelity reinforcement learning simulation designed to train and evaluate AI agents in solving real-world Quick Commerce (QComm) customer support tickets while actively detecting and preventing fraud (Profit Leakage).

## Motivation
In the QComm industry, agents must balance **customer satisfaction** with **financial integrity**. Fraudsters often use sophisticated methods (GPS spoofing, device tampering, social engineering) to claim false refunds. This environment challenges agents to investigate evidence before making a final resolution.

---

## 🛠️ Environment Specification

### Observation Space
The `QCommSupportObservation` provides the agent with structured data across four domains:
- **`ticket_text`**: The raw customer complaint (e.g., "My order never arrived!").
- **`customer_profile`**: Historical data including `tenure_days`, `r2o_rate` (Refund-to-Order), and `device_trust`.
- **`telemetry_data`**: Deep-link logistics data (GPS coordinates of rider vs. delivery point, geofence status).
- **`merchant_stats`**: Reliability scores and incident rates for the specific store.
- **`environment_context`**: Content evidence such as photo descriptions (e.g., "leaking_milk").

### Action Space
The `QCommSupportAction` requires the agent to call investigation tools before resolving:
1. **`investigate_telemetry`**: Reveals GPS and distance data.
2. **`query_customer_history`**: Reveals tenure and trust metrics.
3. **`verify_content_evidence`**: Reveals merchant stats and photo labels.
4. **`issue_resolution`**: Resolves the ticket with a specific type:
   - `refund_source`, `partial_refund`, `replacement` (Refunds)
   - `reject`, `warn` (Soft Denials)
   - `permaban` (Hard Denial for fraud)
   - `escalate_to_human` (Fallback)

---

## 📈 Reward Logic
The reward function is meticulously shaped to encourage investigation and penalize "Profit Leakage":
- **+0.1**: For each unique investigation tool used.
- **+0.7**: For matching the "Correct Resolution" (Ground Truth).
- **-0.05**: For redundant tool calls (Inefficiency penalty).
- **-0.5**: For resolving without at least 2 investigation steps (Guessing penalty).
- **-1.0**: For issuing a refund in a clear Fraud Scenario (Critical Failure).

---

## 🎯 Task Scenarios
The environment includes 5 standardized tasks with increasing difficulty:

| Task | Difficulty | Scenario Description | Expected Resolution |
| :--- | :--- | :--- | :--- |
| 1 | **Very Easy** | Legitimate damaged item (Leaking Milk) with clear photo evidence. | `replacement` |
| 2 | **Easy** | Missing ₹20 item, suspicious customer profile (high r2o, low tenure). | `partial_refund` |
| 3 | **Medium** | Merchant fault, but customer looks like a textbook fraudster. | `partial_refund` |
| 4 | **Hard** | Empathy Trap: polite, relatable student story — but GPS is 350m off. | `reject` |
| 5 | **Very Hard** | Borderline 110m GPS offset, subtle fraud with neutral tone. | `reject` |

---

## 🚀 Setup & Usage

### Prerequisites
- Python 3.10+
- [Openenv CLI](https://github.com/meta-pytorch/openenv)
- Docker (for containerized deployment)

### Local Development
1. **Install dependencies**:
   ```bash
   pip install -e .
   ```
2. **Run the server**:
   ```bash
   uvicorn server.app:app --host 0.0.0.0 --port 8000
   ```
3. **Run the baseline inference**:
   ```bash
   export HF_TOKEN="your_token"
   python inference.py
   ```

### Docker Deployment
Build the image locally:
```bash
docker build -t qcomm-support-env .
docker run -p 8000:8000 qcomm-support-env
```

---

## 📊 Baseline Scores
*Experimental results using Qwen-2.5-7B-Instruct:*

| Task | Difficulty | Score |
| :--- | :--- | :--- |
| Task 1 | Very Easy | **1.0** |
| Task 2 | Easy | **0.8** |
| Task 3 | Medium | **0.8** |
| Task 4 | Hard | **0.0** |
| Task 5 | Very Hard | **0.0** |

**Overall Average**: 0.52/1.0
