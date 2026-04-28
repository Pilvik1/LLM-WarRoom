"""Run record schemas."""

from typing import Any

from pydantic import BaseModel, Field

from .case import CaseInput


class RunRecord(BaseModel):
    """Persistent summary of one case execution."""

    run_id: str
    case_id: str | None = None
    case_type: str
    input: CaseInput
    status: str
    created_at: str
    completed_at: str | None = None
    independent_responses: list[Any] = Field(default_factory=list)
    peer_reviews: list[Any] = Field(default_factory=list)
    evaluations: list[Any] = Field(default_factory=list)
    critiques: list[Any] = Field(default_factory=list)
    comparisons: list[Any] = Field(default_factory=list)
    advisor_responses: list[Any] = Field(default_factory=list)
    aggregate_rankings: list[Any] | dict[str, Any] | None = None
    framed_question: str | None = None
    verdict: dict[str, Any] | None = None
    synthesis: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)
