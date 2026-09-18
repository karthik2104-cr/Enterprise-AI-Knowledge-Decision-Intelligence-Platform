# Evaluation methodology

The golden set in `evaluation/dataset/golden_set.json` contains questions, expected evidence documents, expected answers, and must-include tokens.

Retrieval: Precision@K, Recall@K, MRR, NDCG@K using document-title matching.

Generation: token overlap relevance, must-include correctness, verifier groundedness, citation presence, unsupported-claim heuristic.

LLM-as-judge is optional behind the LLM provider; heuristic metrics are always computed so evaluation works in mock mode.

Measured on the six-question golden set (mock mode): Recall@5 1.0, MRR 1.0, NDCG@5 0.9866, Precision@5 0.2667, answer correctness 1.0, groundedness 1.0, citation correctness 1.0, unsupported-claim rate 0.0. Precision@5 is lower because extra documents appear in the top five; expected evidence is still retrieved (Recall@5 = 1.0).
