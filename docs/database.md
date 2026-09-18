# Database schema

Core tables: `users`, `documents`, `document_chunks`, `queries`, `responses`, `sources`, `reports`, `evaluation_runs`, `evaluation_results`, `business_metrics`, `search_events`.

Relationships: Document 1—N Chunks; Query 1—1 Response; Response 1—N Sources; EvaluationRun 1—N Results.

Tables are created with SQLAlchemy `Base.metadata.create_all` on startup. Seed data loads the demo user, quarterly metrics, and markdown knowledge base.
