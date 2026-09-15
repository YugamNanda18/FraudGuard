# 🎓 FraudGuard — Live Teacher Demonstration & Evaluation Guide
> **Student / Presenter Guide**  
> **Project Name:** FraudGuard — Multi-Agent AI Banking Fraud & Compliance Platform  
> **Maintainer:** Yugam Nanda  
> **Architecture:** FastAPI (Backend) + Next.js 14 (Frontend) + LangGraph (Swarm Engine) + Qdrant (Vector RAG) + Groq AI

---

## 🎯 1-Minute Elevator Pitch (What to Say to Your Teacher)

> *"Good morning/afternoon Professor. Today I am presenting **FraudGuard**, an enterprise-grade AI multi-agent platform for financial fraud detection and banking compliance.*
>
> *Traditional fraud systems rely on simple static rules. FraudGuard uses a **swarm of 6 specialized AI agents** that work together in real-time:*
> 1. **Donna (Router):** Uses intent classification to automatically route user queries.
> 2. **Harvey (Fraud Analyst):** Analyzes transaction anomalies, velocity spikes, and fraud patterns.
> 3. **Louis (Compliance Specialist):** Reviews AML, KYC, and financial regulations (SEPBLAC/PSD2/GDPR).
> 4. **Jessica (Graph Intelligence):** Investigates money mule networks and fraud rings.
> 5. **Mike (Red Teaming Security):** Tests AI models for prompt injection and security vulnerabilities.
> 6. **Rachel (Data Engineer):** Handles vector embeddings, ETL pipelines, and RAG indexing.*
>
> *Let me demonstrate the system live."*

---

## 🚀 STEP 1: Launching the System (Fresh Start)

If the servers are not already running, open two terminal windows:

### Terminal 1: Backend API Server
```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python.exe -m uvicorn fraudai.api.app:create_app --factory --host 0.0.0.0 --port 8000
```
*(Wait until you see `Uvicorn running on http://0.0.0.0:8000`)*

### Terminal 2: Frontend Next.js Web App
```powershell
cd frontend
npm run dev
```
*(Wait until you see `Ready in ... http://localhost:3000`)*

---

## 🧪 STEP 2: Automated QA & Test Suite Verification

Show your teacher that the codebase passes rigorous automated testing with **zero failures**:

### 1. Run the Pytest Unit & Integration Suite
Open a new terminal and run:
```powershell
$env:PYTHONPATH="src"
.venv\Scripts\pytest.exe -v
```
👉 **Point out to Teacher:** *"We have 482 passing automated unit and integration tests covering vector ingestion, authentication, state routing, and prompt security."*

### 2. Run the One-Click Automated System QA Script
```powershell
.\test_demo.ps1
```
👉 **Point out to Teacher:** *"This script tests every API endpoint, authenticates via JWT, checks vector health, and executes end-to-end multi-agent routing."*

---

## 💻 STEP 3: Live Web Dashboard Demonstration (`http://localhost:3000`)

Open your browser to **`http://localhost:3000`** (or `http://localhost:3000/chat`).

### Demo 3.1: Automatic AI Routing (Donna -> Harvey)
1. In the chat input box at the bottom, type:
   ```text
   Analyze transaction TX-999 for suspicious velocity spikes.
   ```
2. Press **Enter**.
3. 👉 **Explain to Teacher:** *"Notice how Donna recognized this as a transaction anomaly prompt, automatically assigned **Harvey Specter**, and Harvey responded asking for transaction scope and velocity thresholds within 1 second."*

### Demo 3.2: Direct Agent Switching (Louis Litt - Compliance)
1. Click on **Louis** on the left sidebar menu (`Transaction analysis & anomalies / Regulatory`).
2. Type:
   ```text
   What are the AML and KYC requirements for account ACC-44821 under financial regulations?
   ```
3. Press **Enter**.
4. 👉 **Explain to Teacher:** *"Here we switched directly to Louis Litt, who acts as our legal and compliance expert for Anti-Money Laundering (AML) reporting."*

### Demo 3.3: Network Graph Investigation (Jessica Pearson)
1. Click on **Jessica** on the left sidebar.
2. Type:
   ```text
   Detect fraud ring networks and shared device clusters across accounts.
   ```
3. Press **Enter**.
4. 👉 **Explain to Teacher:** *"Jessica analyzes topological relationships, identifying shared devices, linked IPs, and money mule clusters."*

### Demo 3.4: System Health & Observability
1. Point to the **bottom-left corner** of the screen.
2. 👉 **Explain to Teacher:** *"The green **'All systems operational'** badge polls our `/api/v1/health` endpoint live to monitor Qdrant vector database connectivity and Groq LLM cluster status."*

---

## 🛠️ STEP 4: Live API & Swagger Documentation (`http://localhost:8000`)

Open your browser to **`http://localhost:8000`**.

1. 👉 **Show Root Redirect:** Point out that visiting `http://localhost:8000` automatically redirects to `/docs` (Swagger UI).
2. 👉 **Demonstrate JWT Authentication Endpoint (`/api/v1/auth/token`):**
   - Click **`POST /api/v1/auth/token`** -> **Try it out**.
   - Enter `username`: `qa_analyst`, `password`: `password123` -> **Execute**.
   - Show the returned JWT `access_token`.
3. 👉 **Show System OpenAPI Specification:** Point out the RESTful architecture adherence, Prometheus metrics integration (`/api/v1/admin/metrics`), and streaming chat routes.

---

## ❓ STEP 5: Teacher Q&A Cheat Sheet (Common Questions & Answers)

| Question | Your Answer |
| :--- | :--- |
| **Q1: How do agents communicate with each other?** | *"We use **LangGraph** to build a state machine DAG (Directed Acyclic Graph). Donna acts as the root node, classifying intent and passing shared context state to specialist nodes."* |
| **Q2: Where are documents and rules stored for AI retrieval?** | *"We use **Qdrant Vector Database** with dense embeddings. Documents like financial regulations are chunked, embedded, and queried via Retrieval-Augmented Generation (RAG)."* |
| **Q3: How do you handle security and malicious inputs?** | *"We have **Mike Ross**, a dedicated Red Teaming agent that validates prompt injections, and we enforce JWT Bearer Token authentication across all API routes."* |
| **Q4: What happens if Docker/Qdrant goes offline?** | *"The system features graceful fallback: Qdrant switches to in-memory mode, and routing falls back to deterministic keyword regex matching so service is never interrupted."* |

---

### 🎉 Demo Checklist Summary
- [x] Backend running on `http://localhost:8000` (Status: Healthy)
- [x] Frontend running on `http://localhost:3000`
- [x] Pytest suite verified (482 Passed)
- [x] Script `.\test_demo.ps1` verified
- [x] Live chat demo tested with Harvey, Louis, Jessica, and Donna

*Created for Yugam Nanda — FraudGuard Project Evaluation*
