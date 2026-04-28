"""Thin case/run wrapper around the inherited ask council flow."""

from datetime import datetime
import uuid

from .config import RESPONDENT_MODEL_ALIASES, SYNTHESIZER_MODEL_ALIAS
from .council import run_full_council
from .run_storage import save_run_record
from .schemas.case import CaseInput
from .schemas.run import RunRecord


def new_run_id() -> str:
    """Generate a stable run identifier for one case execution."""
    return f"run_{uuid.uuid4().hex}"


def ask_case_from_message(
    user_message: str,
    case_id: str | None = None,
    title: str | None = None,
) -> CaseInput:
    """Convert the legacy message shape into an ask case input."""
    return CaseInput(
        id=case_id,
        case_type="ask",
        title=title,
        task=user_message,
        respondent_aliases=list(RESPONDENT_MODEL_ALIASES),
        synthesizer_alias=SYNTHESIZER_MODEL_ALIAS,
    )


async def run_ask_case(case_input: CaseInput, run_id: str | None = None) -> RunRecord:
    """Run the existing ask council flow and return a persisted run record."""
    run_id = run_id or new_run_id()
    created_at = datetime.utcnow().isoformat()
    errors: list[str] = []

    try:
        stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
            case_input.task
        )
        status = "completed"
    except Exception as exc:
        stage1_results = []
        stage2_results = []
        stage3_result = None
        metadata = {}
        status = "failed"
        errors.append(str(exc))

    record = RunRecord(
        run_id=run_id,
        case_id=case_input.id,
        case_type=case_input.case_type,
        input=case_input,
        status=status,
        created_at=created_at,
        completed_at=datetime.utcnow().isoformat(),
        independent_responses=stage1_results,
        peer_reviews=stage2_results,
        aggregate_rankings=metadata.get("aggregate_rankings"),
        synthesis=stage3_result,
        errors=errors,
    )
    save_run_record(record)
    return record
