# API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /api/health | Liveness |
| POST | /api/auth/login | JWT login |
| GET | /api/auth/me | Current user |
| POST | /api/documents | Upload |
| GET | /api/documents | List |
| GET | /api/documents/{id} | Detail + chunks |
| DELETE | /api/documents/{id} | Delete |
| POST | /api/search | Hybrid search |
| POST | /api/ask | RAG question |
| POST | /api/analyze | Analytical question |
| POST | /api/report | Generate + store report |
| GET | /api/reports | List reports |
| GET | /api/evaluation | Evaluation runs |
| POST | /api/evaluation/run | Execute golden set |
| GET | /api/evaluation/results | Per-question scores |
| GET | /api/history | Prior interactions |
| GET | /api/history/{id} | Interaction detail |
| GET | /api/dashboard | Live metrics |
