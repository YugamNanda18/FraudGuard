<p align="center">
  <img src="assets/logo.png" alt="FraudGuard AI Logo" width="180" />
</p>

<h1 align="center">🛡️ FraudGuard AI</h1>

<p align="center">
  <strong>Autonomous Multi-Agent Intelligence Engine for FinTech Fraud Detection, AML/KYC Compliance & AI System Red Teaming</strong>
</p>

<p align="center">
  <a href="https://github.com/YugamNanda18/FraudGuard"><img src="https://img.shields.io/badge/Status-Production--Ready-brightgreen?style=for-the-badge&logo=shield" alt="Status" /></a>
  <a href="https://github.com/YugamNanda18/FraudGuard"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://github.com/YugamNanda18/FraudGuard"><img src="https://img.shields.io/badge/LangGraph-0.3+-blueviolet?style=for-the-badge&logo=langchain&logoColor=white" alt="LangGraph" /></a>
  <a href="https://github.com/YugamNanda18/FraudGuard"><img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://github.com/YugamNanda18/FraudGuard"><img src="https://img.shields.io/badge/Next.js-14+-000000?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js" /></a>
  <a href="https://github.com/YugamNanda18/FraudGuard"><img src="https://img.shields.io/badge/Qdrant-Vector_DB-E0234E?style=for-the-badge&logo=qdrant&logoColor=white" alt="Qdrant" /></a>
  <a href="https://github.com/YugamNanda18/FraudGuard"><img src="https://img.shields.io/badge/Docker-Sandboxed-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Sandbox" /></a>
  <a href="https://github.com/YugamNanda18/FraudGuard"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License" /></a>
</p>

<p align="center">
  <a href="#-executive-summary">Executive Summary</a> •
  <a href="#-specialized-agent-swarm">Agent Swarm</a> •
  <a href="#-system-architecture">Architecture</a> •
  <a href="#-tech-stack--ecosystem">Tech Stack</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-project-structure">Structure</a> •
  <a href="#-documentation-center">Docs</a> •
  <a href="#-testing--quality">Testing</a>
</p>

---

## 📌 Executive Summary

**FraudGuard AI** is an advanced, **Level 3 Autonomous Multi-Agent AI Platform** built to revolutionize fraud investigation, regulatory compliance, and security red-teaming for banking and modern financial services.

Unlike traditional static rule engines or basic LLM text generators, **FraudGuard** deploys specialized, autonomous agents that actively **execute code, compute transaction metrics, query hybrid vector stores, generate official Suspicious Activity Reports (SAR), and execute security red-teaming attacks** inside ephemeral, sandboxed Docker containers.

```
                  ┌─────────────────────────────────────────┐
                  │          📥 User Query / Stream         │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │    🧠 Router Agent (Donna Paulsen)      │
                  └──────┬─────────────┬─────────────┬──────┘
                         │             │             │
        ┌────────────────┴┐           │           ┌─┴───────────────┐
        ▼                 ▼           ▼           ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───┐ ┌───────────────┐ ┌───────────────┐
│  📊 Harvey    │ │   ⚖️ Louis    │ │   │ │   ⚡ Mike     │ │   📈 Rachel   │
│  Transaction  │ │   AML/KYC     │ │...│ │  Red Teaming  │ │ Data Pipelines│
│  Fraud & Risk │ │  Compliance   │ │   │ │ (HITL Gated)  │ │   ETL Engine  │
└───────┬───────┘ └───────┬───────┘ └───┘ └───────┬───────┘ └───────┬───────┘
        │                 │                       │                 │
        └─────────────────┴───────────┬───────────┴─────────────────┘
                                      │
                                      ▼
                  ┌─────────────────────────────────────────┐
                  │  🔒 Sandboxed Execution & Tool Engine   │
                  └─────────────────────────────────────────┘
```

---

## 🤖 Specialized Agent Swarm

The platform mimics an elite, multi-disciplinary financial investigation firm. Six domain-tailored agents collaborate seamlessly under a unified conversational state machine:

| Agent Icon | Agent Name | Core Domain | Specialty & Capabilities | Tooling & Action Output |
| :---: | :--- | :--- | :--- | :--- |
| 👑 | **Donna Paulsen** | Router & Intent Routing | Real-time intent classification, session context retention, specialized dispatch | Dynamic state graph router |
| 🎯 | **Harvey Specter** | Transaction Fraud | Anomaly detection, velocity scoring, transaction risk classification | Python pandas/scikit analysis sandbox |
| ⚖️ | **Louis Litt** | Regulatory & AML/KYC | Spanish BOE & EU legal compliance, SAR generation, legal article citation | Hybrid Vector RAG (Qdrant + BM25) |
| 🕸️ | **Jessica Pearson** | Fraud Intelligence | Graph network analysis, identity resolution, syndicate tracking | NetworkX graph visualization & clustering |
| 🛡️ | **Mike Ross** | AI Red Teaming | LLM vulnerability analysis, prompt injection testing, adversarial attacks | Sandboxed red-teaming (HITL Gated) |
| ⚡ | **Rachel Zane** | Data Engineering | ETL pipeline generation, data quality auditing, feature store extraction | Automated feature engineering scripts |

---

## 🏗️ System Architecture

<p align="center">
  <img src="docs/architecture/system-architecture.svg" alt="FraudGuard System Architecture" width="850" />
</p>

### Key Architectural Highlights

* 🔄 **LangGraph Orchestration**: Stateful agent orchestration managing multi-turn dialog context and agent hand-offs.
* 📚 **Hybrid Search RAG Pipeline**: Combines dense vector embeddings (**BGE-M3**, 1024-dim) with sparse lexical search (**BM25**) over 35,000+ legal documents from the BOE (*Boletín Oficial del Estado*).
* 🐳 **Zero-Trust Ephemeral Sandboxing**: Isolated Docker runtime environment (`cap_drop=ALL`, memory limits, read-only rootfs) preventing unauthorized side-effects.
* ⚡ **3-Tier Fallback LLM Routing**: Ultra-low latency routing through **Groq (Llama-3)** $\rightarrow$ **Anthropic Claude 3.5** $\rightarrow$ **Local Ollama** fallback.
* 🛡️ **Human-in-the-Loop (HITL)**: Mandatory confirmation step before executing red-teaming probes or external system modifications.

---

## 🛠️ Tech Stack & Ecosystem

```
┌────────────────────────────────────────────────────────────────────────┐
│                          FRAUDGUARD TECH STACK                         │
├───────────────────┬────────────────────────────────────────────────────┤
│ Orchestration    │ LangGraph 0.3+, LangChain Core                      │
│ LLM Engines       │ Groq (Llama-3 70B), Anthropic Claude 3.5, Ollama   │
│ Vector Database   │ Qdrant Vector Engine (Hybrid Dense + Sparse BM25)  │
│ Embeddings        │ BGE-M3 Multilingual (1024-dimensional)             │
│ Backend API       │ FastAPI, Python 3.11+, Uvicorn, Pydantic v2        │
│ Web Dashboard     │ Next.js 14, React 18, Tailwind CSS                 │
│ Execution Engine  │ Docker Engine with custom seccomp & cap_drop       │
│ Observability     │ Prometheus Metrics, Grafana Dashboards             │
│ Database Storage  │ SQLite (Session History & Audit), Qdrant (Vectors) │
└───────────────────┴────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 📋 Prerequisites

Ensure you have the following installed on your host machine:

* **Docker & Docker Compose** (v24.0+)
* **Python** (v3.11+)
* **Node.js** (v20+) & **pnpm** / **npm**
* **Groq API Key** ([Get your key here](https://console.groq.com))

---

### 1️⃣ Clone & Configure Environment

```bash
git clone https://github.com/YugamNanda18/FraudGuard.git
cd FraudGuard

# Create your local environment file
cp .env.example .env
```

Edit your `.env` file to add your credentials:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
LLM_PROVIDER=groq
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

---

### 2️⃣ Launch Infrastructure Services

Start the vector storage and local fallback services:

```bash
docker compose up -d
```

---

### 3️⃣ Setup & Launch Backend Engine

Using `uv` (recommended) or standard `pip`:

```bash
# Install dependencies using uv package manager
uv sync --dev

# Run the FastAPI server
uv run python -m uvicorn fraudai.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

---

### 4️⃣ Launch Next.js Dashboard

```bash
cd frontend
pnpm install
pnpm dev
```

---

### 5️⃣ Access Services

| Component | Target URL | Description |
| :--- | :--- | :--- |
| 🖥️ **Web Dashboard** | `http://localhost:3000` | Next.js 14 Interactive Multi-Agent UI |
| 📖 **FastAPI Docs** | `http://localhost:8000/docs` | Swagger OpenAPI Endpoint Documentation |
| 🗄️ **Qdrant Dashboard** | `http://localhost:6333/dashboard` | Vector Database Management Console |
| 📊 **Prometheus** | `http://localhost:9090` | System Metrics & Metrics Collector |
| 📈 **Grafana** | `http://localhost:3000` | Operational Monitoring Dashboard |

---

## 📂 Project Structure

```bash
FraudGuard/
├── 📁 src/fraudai/             # Core Backend Source Code
│   ├── 📁 agents/              # 6 Agent definitions, prompts, & LangGraph workflow
│   ├── 📁 api/                 # FastAPI routes, JWT auth, middleware, & sessions
│   ├── 📁 core/                # Configuration, logging, database, & telemetry
│   ├── 📁 evaluation/          # RAGAS benchmarks & evaluation suites
│   ├── 📁 ingestion/           # Legal corpus scraper, parser, & chunking engine
│   ├── 📁 rag/                 # Retriever, BM25/BGE hybrid rankers, & prompts
│   └── 📁 tools/               # Sandboxed Docker tools & python scripts
├── 📁 frontend/                # Next.js 14 Web Application Dashboard
├── 📁 monitoring/              # Prometheus alerts & Grafana dashboard specs
├── 📁 docs/                    # Technical spec, ADRs, & runbooks
├── 📁 tests/                   # 480+ unit, integration, & smoke test cases
├── 📄 Dockerfile               # Production Docker container image
├── 📄 docker-compose.yml       # Infrastructure orchestration file
└── 📄 pyproject.toml           # Python project definition & hatch setup
```

---

## 📜 Documentation Center

Detailed system specifications and architecture decisions are available in the `docs/` folder:

| Document Title | Description |
| :--- | :--- |
| 📑 [System Requirements (F0)](docs/F0_requirements.md) | Full functional, non-functional, and ML specifications |
| 🏛️ [Architecture Decisions (F0.5)](docs/F0.5_ADRs.md) | 6 Architectural Decision Records (ADRs) |
| 📋 [Product Backlog (F0.5)](docs/F0.5_backlog.md) | 74 User stories organized into 8 development sprints |
| 📊 [Technical Spec & Baselines (F2)](docs/F2_spec.md) | Performance metrics, SLAs, & fairness evaluation standards |
| 🔌 [API Reference Manual (F6)](docs/F6_api_reference.md) | Comprehensive endpoint definitions with cURL examples |
| 🚀 [Deployment Guide (F6)](docs/F6_deployment_guide.md) | Enterprise production deployment instructions |
| 🛠️ [Operations Runbook (F6)](docs/F6_runbook.md) | Troubleshooting guides, incident response, & scaling |

---

## 🧪 Testing & Quality Assurance

FraudGuard comes equipped with an extensive test suite covering unit, integration, and live smoke tests:

```bash
# Run complete unit & integration test suite (480+ tests)
uv run pytest tests/ -v

# Generate HTML code coverage report
uv run pytest tests/ --cov=fraudai --cov-report=html

# Execute live system smoke testing script
./scripts/smoke-test.sh
```

---

## 👤 Author & Maintainer

<table align="center">
  <tr>
    <td align="center">
      <a href="https://github.com/YugamNanda18">
        <img src="https://github.com/YugamNanda18.png" width="100px;" alt="Yugam Nanda"/><br />
        <sub><b>Yugam Nanda</b></sub>
      </a><br />
      <a href="https://github.com/YugamNanda18/FraudGuard" title="Project Lead">💻 Lead Architect & Developer</a>
    </td>
  </tr>
</table>

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
