"""Case input schemas."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CaseInput(BaseModel):
    """Minimal input shape for one WarRoom case."""

    id: str | None = None
    case_type: Literal["ask", "evaluate", "critique", "decide", "compare", "war_room"] = "ask"
    title: str | None = None
    task: str
    context: str | None = None
    stakes: str | None = None
    criteria: list[str] = Field(default_factory=list)
    candidate_output: str | None = None
    artifact: str | None = None
    candidates: list[dict[str, str]] = Field(default_factory=list)
    respondent_aliases: list[str] = Field(default_factory=list)
    synthesizer_alias: str | None = None

    @model_validator(mode="after")
    def validate_mode_inputs(self) -> "CaseInput":
        """Enforce mode-specific runtime requirements."""
        if self.case_type == "evaluate" and not (self.candidate_output or "").strip():
            raise ValueError("candidate_output is required for evaluate cases")
        if self.case_type == "critique" and not self.subject_text:
            raise ValueError("candidate_output or artifact is required for critique cases")
        if self.case_type == "compare":
            if len(self.candidates) < 2:
                raise ValueError("at least two candidates are required for compare cases")
            ids = []
            for candidate in self.candidates:
                candidate_id = (candidate.get("id") or "").strip()
                title = (candidate.get("title") or "").strip()
                content = (candidate.get("content") or "").strip()
                if not candidate_id or not title or not content:
                    raise ValueError("each compare candidate requires id, title, and content")
                ids.append(candidate_id)
            if len(ids) != len(set(ids)):
                raise ValueError("compare candidate ids must be unique")
        return self

    @property
    def subject_text(self) -> str:
        """Return the artifact text being evaluated or critiqued."""
        return (self.candidate_output or self.artifact or "").strip()
