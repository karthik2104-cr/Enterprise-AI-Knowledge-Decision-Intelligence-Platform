from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from app.core.config import get_settings


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    name = "mock"

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        header = system_prompt.strip().upper()
        if header.startswith("PLANNER"):
            return self._plan(user_prompt)
        if header.startswith("VERIFIER"):
            return self._verify(user_prompt)
        return self._answer(user_prompt)

    def _plan(self, user_prompt: str) -> dict[str, Any]:
        text = user_prompt.lower()
        tools: list[str] = []
        intent = "document_qa"
        if any(w in text for w in ["revenue", "expense", "kpi", "employee count", "headcount", "quarter", "q2", "q3", "metric"]):
            tools.append("query_database")
            intent = "structured_data"
        if any(w in text for w in ["compare", "vs", "versus", "difference", "delta", "changed"]):
            tools.append("calculate_metric")
            if "report" in text or "q2" in text or "q3" in text:
                tools.append("compare_documents")
            intent = "comparison"
        if "report" in text or "executive summary" in text or "generate a" in text:
            tools.append("generate_report")
            intent = "report"
        if any(w in text for w in ["policy", "compliance", "leave", "security", "procurement", "handbook", "benefit"]):
            tools.append("search_documents")
            if intent == "structured_data":
                intent = "hybrid_analysis"
            elif intent not in {"comparison", "report"}:
                intent = "document_qa"
        if not tools:
            tools = ["search_documents"]
        if "search_documents" not in tools and intent in {"document_qa", "hybrid_analysis", "comparison", "report"}:
            tools.insert(0, "search_documents")
        unique = list(dict.fromkeys(tools))
        return {
            "intent": intent,
            "tools": unique,
            "rationale": "Selected tools from question cues (mock planner).",
            "needs_documents": "search_documents" in unique or "compare_documents" in unique,
            "needs_database": "query_database" in unique,
        }

    def _answer(self, user_prompt: str) -> dict[str, Any]:
        evidence_block = _extract_between(user_prompt, "EVIDENCE:", "DATABASE:")
        db_block = _extract_between(user_prompt, "DATABASE:", "QUESTION:")
        question = _extract_between(user_prompt, "QUESTION:", "END.")
        if not question:
            question = user_prompt[-400:]
        question = _extract_between(user_prompt, "QUESTION:", "END.")
        qtokens = set(re.findall(r"[a-z0-9]{4,}", question.lower()))
        snippets: list[str] = []
        for block in re.split(r"\n(?=\[\d+\])", evidence_block):
            block = block.strip()
            if not block.startswith("["):
                continue
            body = block.split(":", 1)[-1].strip() if ":" in block else block
            snippets.append(re.sub(r"\s+", " ", body)[:600])
        if qtokens:
            ranked = []
            for snip in snippets:
                overlap = len(qtokens.intersection(set(re.findall(r"[a-z0-9]{4,}", snip.lower()))))
                ranked.append((overlap, snip))
            ranked.sort(key=lambda x: x[0], reverse=True)
            snippets = [s for ov, s in ranked if ov > 0][:4] or [s for _, s in ranked[:2]]
        facts: list[Any] = []
        try:
            raw = db_block.split("NOTES:")[0].strip()
            loaded = json.loads(raw) if raw and raw not in {"(none)", ""} else []
            if isinstance(loaded, list):
                facts = loaded
        except Exception:
            facts = []
        if not snippets and not facts:
            return {
                "answer": "I couldn't find sufficient evidence in the available knowledge base to answer this reliably.",
                "confidence": 0.15,
                "claims": [],
                "uncertainty": ["No supporting evidence was retrieved."],
            }
        parts: list[str] = []
        claims: list[dict[str, Any]] = []
        for row in facts:
            if isinstance(row, dict) and row.get("metric"):
                text = f"{row.get('period')} {row.get('metric')} was {row.get('value')} {row.get('unit')}."
                parts.append(text)
                claims.append({"text": text, "evidence": []})
            elif isinstance(row, dict) and "comparison" in row:
                cmp = row["comparison"]
                op = cmp.get("operation")
                if op == "pct_change":
                    text = f"The value changed by {cmp.get('value')}% from {cmp.get('left')} to {cmp.get('right')}."
                else:
                    text = f"The calculated {op} from {cmp.get('left')} to {cmp.get('right')} is {cmp.get('value')}."
                parts.append(text)
                claims.append({"text": text, "evidence": []})
        for snip in snippets[:2]:
            for sentence in _relevant_sentences(snip, qtokens):
                parts.append(sentence)
                claims.append({"text": sentence[:400], "evidence": []})
        answer = " ".join(dict.fromkeys(parts))[:1400]
        return {
            "answer": answer,
            "confidence": 0.78 if facts or snippets else 0.2,
            "claims": claims[:6],
            "uncertainty": [],
        }

    def _verify(self, user_prompt: str) -> dict[str, Any]:
        return {"status": "reviewed", "notes": "Heuristic verification applied in mock mode."}


def _relevant_sentences(text: str, qtokens: set[str], limit: int = 2) -> list[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        return [text[:280]]
    scored: list[tuple[int, str]] = []
    for sentence in sentences:
        overlap = len(qtokens.intersection(set(re.findall(r"[a-z0-9]{4,}", sentence.lower()))))
        if overlap:
            scored.append((overlap, sentence))
    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [s for _, s in scored[:limit]]
    return picked or sentences[:limit]


class OpenAILLMProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, timeout: int):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._fallback = MockLLMProvider()

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.api_key:
            return self._fallback.complete_json(system_prompt, user_prompt)
        try:
            import httpx

            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:
            return self._fallback.complete_json(system_prompt, user_prompt)


def _extract_between(text: str, start: str, end: str) -> str:
    lower = text
    i = lower.find(start)
    if i < 0:
        return ""
    j = lower.find(end, i + len(start))
    if j < 0:
        return lower[i + len(start) :].strip()
    return lower[i + len(start) : j].strip()


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider.lower() == "openai":
        return OpenAILLMProvider(settings.llm_api_key, settings.llm_model, settings.llm_timeout_seconds)
    return MockLLMProvider()


def safe_parse_json(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"\{.*\}", raw, re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return {}
        return {}
