from typing import Any, Optional

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class EvidenceItem(BaseModel):
    document: str
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_id: Optional[str] = None
    snippet: Optional[str] = None
    score: Optional[float] = None
    retrieval_method: Optional[str] = None
    citation_index: Optional[int] = None


class Claim(BaseModel):
    text: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    supported: bool = True


class LatencyMetrics(BaseModel):
    retrieval_ms: float = 0
    rerank_ms: float = 0
    llm_ms: float = 0
    verification_ms: float = 0
    total_ms: float = 0


class StructuredAnswer(BaseModel):
    answer: str
    confidence: float = Field(ge=0, le=1, default=0.0)
    claims: list[Claim] = Field(default_factory=list)
    sources: list[EvidenceItem] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    latency: LatencyMetrics = Field(default_factory=LatencyMetrics)
    verification: dict[str, Any] = Field(default_factory=dict)
    retrieval: dict[str, Any] = Field(default_factory=dict)
    query_id: Optional[str] = None
    response_id: Optional[str] = None


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    filters: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    document_type: Optional[str] = None
    department: Optional[str] = None
    year: Optional[int] = None
    section: Optional[str] = None
    top_k: int = Field(default=8, ge=1, le=25)


class SearchHit(BaseModel):
    document_id: str
    document_name: str
    chunk_id: str
    page: Optional[int] = None
    section: Optional[str] = None
    snippet: str
    score: float
    retrieval_method: str
    score_explanation: str


class DocumentOut(BaseModel):
    id: str
    title: str
    original_name: str
    status: str
    department: Optional[str]
    doc_type: Optional[str]
    year: Optional[int]
    chunk_count: int
    error_message: Optional[str]
    ingested_ms: Optional[int]
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ReportRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    title: Optional[str] = None


class ReportOut(BaseModel):
    id: str
    title: str
    question: str
    status: str
    content: dict[str, Any]
    created_at: Optional[str] = None


class HistoryItem(BaseModel):
    id: str
    question: str
    query_type: str
    created_at: Optional[str]
    answer_summary: Optional[str] = None
    tools_used: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    confidence: Optional[float] = None


class DashboardMetrics(BaseModel):
    documents: int
    indexed_documents: int
    questions: int
    reports: int
    searches: int
    evaluation_runs: int
    recent_activity: list[dict[str, Any]] = Field(default_factory=list)
