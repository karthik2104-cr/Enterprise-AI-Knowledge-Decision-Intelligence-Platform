# Agent workflow

The planner classifies intent and selects tools: `search_documents`, `query_database`, `calculate_metric`, `compare_documents`, `generate_report`.

The orchestrator executes only those tools, then generates a structured answer and runs the verifier. Database access is a catalog of named metrics — the model cannot run arbitrary SQL.
