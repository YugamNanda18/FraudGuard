# FraudAI Agent — Project Instructions

## Project
FraudAI Agent: Level 3 agentic AI platform for banking fraud detection and AI red teaming in FinTech.

## Architecture
- 6 agents: Donna (router), Harvey (transaction fraud), Louis (AML/KYC), Jessica (fraud intel), Mike (red teaming), Rachel (data engineering)
- LangGraph orchestration, RAG with BOE legal data, sandboxed execution
- API (FastAPI) + Web chat (Next.js)

## Stack
- Python 3.11+, LangGraph, LangChain, ChromaDB
- LLM: Anthropic Claude API (complex agents) + local model (routing/simple queries)
- No GPT/Gemini/external models

## Conventions
- Formatter: ruff
- Type checking: mypy (strict)
- Tests: pytest, minimum 80% coverage
- Commits: conventional commits (feat/fix/refactor/docs/test)
- Language: code in English, docs in Spanish

## Directory structure
- `src/fraudai/agents/` — Agent definitions and prompts
- `src/fraudai/tools/` — Tool implementations for agent execution
- `src/fraudai/rag/` — RAG pipeline and retrieval
- `src/fraudai/ingestion/` — BOE download and processing
- `src/fraudai/api/` — FastAPI endpoints
- `src/fraudai/core/` — Config, logging, security
- `docs/` — Requirements, ADRs, runbooks
- `tests/` — pytest tests with fixtures in tests/fixtures/

## Security
- All code execution in sandboxed Docker containers
- Tenant isolation mandatory
- Red teaming tools require explicit user confirmation
- No secrets in code — use environment variables
