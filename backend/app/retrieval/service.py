from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.models import Document, DocumentChunk
from app.providers.embeddings import cosine_similarity, get_embedding_provider, tokenize

TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass
class Hit:
    document_id: str
    document_name: str
    chunk_id: str
    page: Optional[int]
    section: Optional[str]
    content: str
    score: float
    retrieval_method: str
    department: Optional[str] = None
    doc_type: Optional[str] = None
    year: Optional[int] = None

    def snippet(self, n: int = 280) -> str:
        text = " ".join(self.content.split())
        return text[:n] + ("…" if len(text) > n else "")


def _load_chunks(db: Session, filters: dict[str, Any] | None = None) -> list[tuple[Document, DocumentChunk]]:
    q = db.query(DocumentChunk, Document).join(Document, DocumentChunk.document_id == Document.id)
    q = q.filter(Document.status == "indexed")
    filters = filters or {}
    if filters.get("document_type"):
        q = q.filter(Document.doc_type == filters["document_type"])
    if filters.get("department"):
        q = q.filter(Document.department == filters["department"])
    if filters.get("year"):
        q = q.filter(Document.year == int(filters["year"]))
    rows = q.all()
    if filters.get("section"):
        section = str(filters["section"]).lower()
        rows = [r for r in rows if r[0].section and section in r[0].section.lower()]
    return [(doc, chunk) for chunk, doc in rows]


def keyword_search(db: Session, query: str, filters: dict[str, Any] | None = None, top_k: int = 8) -> list[Hit]:
    pairs = _load_chunks(db, filters)
    q_tokens = tokenize(query)
    if not q_tokens or not pairs:
        return []
    df: dict[str, int] = {}
    docs_tokens: list[list[str]] = []
    for _, chunk in pairs:
        toks = tokenize(chunk.content)
        docs_tokens.append(toks)
        for tok in set(toks):
            df[tok] = df.get(tok, 0) + 1
    n = len(pairs)
    k1, b = 1.5, 0.75
    avgdl = sum(len(t) for t in docs_tokens) / max(n, 1)
    hits: list[Hit] = []
    for (doc, chunk), toks in zip(pairs, docs_tokens):
        tf: dict[str, int] = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        for qt in q_tokens:
            if qt not in tf:
                continue
            idf = math.log(1 + (n - df.get(qt, 0) + 0.5) / (df.get(qt, 0) + 0.5))
            freq = tf[qt]
            denom = freq + k1 * (1 - b + b * len(toks) / max(avgdl, 1))
            score += idf * (freq * (k1 + 1)) / denom
        if score > 0:
            hits.append(_hit(doc, chunk, score, "keyword"))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]


def semantic_search(db: Session, query: str, filters: dict[str, Any] | None = None, top_k: int = 8) -> list[Hit]:
    pairs = _load_chunks(db, filters)
    if not pairs:
        return []
    qvec = get_embedding_provider().embed(query)
    hits: list[Hit] = []
    for doc, chunk in pairs:
        try:
            vec = json.loads(chunk.embedding_json)
        except Exception:
            vec = []
        score = cosine_similarity(qvec, vec)
        if score > 0.05:
            hits.append(_hit(doc, chunk, score, "semantic"))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]


def hybrid_search(db: Session, query: str, filters: dict[str, Any] | None = None, top_k: int | None = None) -> list[Hit]:
    """Merge lexical and semantic lists with reciprocal rank fusion (not raw-score mixing)."""
    settings = get_settings()
    k = top_k or settings.retrieval_top_k
    kw = keyword_search(db, query, filters, top_k=k * 2)
    sem = semantic_search(db, query, filters, top_k=k * 2)
    kw_ids = {h.chunk_id for h in kw}
    sem_ids = {h.chunk_id for h in sem}
    rrf: dict[str, float] = {}
    docs: dict[str, Hit] = {}
    for rank, hit in enumerate(kw, start=1):
        rrf[hit.chunk_id] = rrf.get(hit.chunk_id, 0.0) + 1.0 / (60 + rank)
        docs[hit.chunk_id] = hit
    for rank, hit in enumerate(sem, start=1):
        rrf[hit.chunk_id] = rrf.get(hit.chunk_id, 0.0) + 1.0 / (60 + rank)
        docs[hit.chunk_id] = hit
    hits: list[Hit] = []
    for chunk_id, score in rrf.items():
        base = docs[chunk_id]
        if chunk_id in kw_ids and chunk_id in sem_ids:
            method = "hybrid"
        elif chunk_id in kw_ids:
            method = "keyword"
        else:
            method = "semantic"
        hits.append(Hit(**{**base.__dict__, "score": round(score, 4), "retrieval_method": method}))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[: k * 2]


def rerank(query: str, hits: list[Hit], top_k: int | None = None) -> list[Hit]:
    settings = get_settings()
    k = top_k or settings.rerank_top_k
    if not hits:
        return []
    q_tokens = set(tokenize(query))
    raw_scores = [hit.score for hit in hits]
    lo, hi = min(raw_scores), max(raw_scores)
    span = hi - lo or 1.0
    ranked: list[Hit] = []
    for hit in hits:
        overlap = len(q_tokens.intersection(set(tokenize(hit.content))))
        coverage = overlap / max(len(q_tokens), 1)
        title_bonus = 0.08 if any(t in hit.document_name.lower() for t in q_tokens) else 0.0
        length_penalty = 0.02 if len(hit.content) < 80 else 0.0
        norm = (hit.score - lo) / span
        score = 0.4 * norm + 0.5 * coverage + title_bonus - length_penalty
        ranked.append(
            Hit(**{**hit.__dict__, "score": round(score, 4), "retrieval_method": f"{hit.retrieval_method}+rerank"})
        )
    ranked.sort(key=lambda h: h.score, reverse=True)
    return ranked[:k]


def retrieve(db: Session, query: str, filters: dict[str, Any] | None = None) -> list[Hit]:
    hits, _, _ = retrieve_with_timing(db, query, filters)
    return hits


def retrieve_with_timing(
    db: Session, query: str, filters: dict[str, Any] | None = None
) -> tuple[list[Hit], float, float]:
    import time

    started = time.perf_counter()
    candidates = hybrid_search(db, query, filters)
    retrieval_ms = (time.perf_counter() - started) * 1000
    started_rerank = time.perf_counter()
    ranked = rerank(query, candidates)
    rerank_ms = (time.perf_counter() - started_rerank) * 1000
    return ranked, retrieval_ms, rerank_ms


def _hit(doc: Document, chunk: DocumentChunk, score: float, method: str) -> Hit:
    return Hit(
        document_id=doc.id,
        document_name=doc.title,
        chunk_id=chunk.id,
        page=chunk.page,
        section=chunk.section,
        content=chunk.content,
        score=round(float(score), 4),
        retrieval_method=method,
        department=doc.department,
        doc_type=doc.doc_type,
        year=doc.year,
    )


def score_explanation(method: str, score: float) -> str:
    if method.startswith("semantic"):
        kind = "semantic similarity (cosine)"
    elif method.startswith("keyword"):
        kind = "keyword relevance (BM25-style)"
    elif "hybrid" in method:
        kind = "hybrid reciprocal-rank fusion, then reranked"
    else:
        kind = "relevance after reranking"
    return f"{kind}: {score:.3f} (ranking signal, not a calibrated probability)"
