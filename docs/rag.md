# RAG pipeline

Question → plan → hybrid retrieval → context construction → LLM JSON completion → Pydantic validation → verification → persistence.

Prompts live in `/prompts` and are loaded by `app.core.prompts`. If retrieval and structured metrics are empty, the system returns a fixed insufficient-evidence message instead of guessing.
