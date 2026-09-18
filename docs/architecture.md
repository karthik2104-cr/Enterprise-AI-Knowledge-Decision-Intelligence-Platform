# Architecture

```mermaid
flowchart TD
  User --> React
  React --> FastAPI
  FastAPI --> Orchestrator
  Orchestrator --> Planner
  Orchestrator --> Retrieval
  Orchestrator --> Tools
  Orchestrator --> RAG
  Orchestrator --> Verifier
  Retrieval --> Keyword
  Retrieval --> Semantic
  Keyword --> RRF
  Semantic --> RRF
  RRF --> Rerank
  Tools --> SafeMetrics
  Tools --> Calc
  RAG --> LLM
  LLM --> Structured
  Structured --> Verifier
  Verifier --> Postgres
  Structured --> React
```

The backend is a modular FastAPI application. `LLMProvider` and `EmbeddingProvider` isolate model implementations. PostgreSQL (Compose) or SQLite (local/tests) stores documents, chunks, JSON vectors, queries, responses, sources, reports, and evaluation results.

**Mock mode** is the default so tests and demos run without API keys. It is not equivalent to a hosted LLM.
