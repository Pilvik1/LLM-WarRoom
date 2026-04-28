"""Compare case runner."""

from collections import defaultdict
from datetime import datetime
from typing import Any
import re

from .case_runner import new_run_id
from .config import RESPONDENT_MODEL_ALIASES, SYNTHESIZER_MODEL_ALIAS
from .prompts.compare import build_compare_synthesis_prompt, build_comparer_prompt
from .providers.model_registry import (
    complete_aliases_parallel,
    complete_with_alias,
    display_model,
    response_metadata,
)
from .run_storage import save_run_record
from .schemas.case import CaseInput
from .schemas.run import RunRecord


async def run_compare_case(
    case_input: CaseInput,
    run_id: str | None = None,
) -> RunRecord:
    """Run independent comparisons, synthesize them, and persist the run."""
    run_id = run_id or new_run_id()
    created_at = datetime.utcnow().isoformat()
    errors: list[str] = []

    respondent_aliases = case_input.respondent_aliases or list(RESPONDENT_MODEL_ALIASES)
    synthesizer_alias = case_input.synthesizer_alias or SYNTHESIZER_MODEL_ALIAS
    case_input.respondent_aliases = list(respondent_aliases)
    case_input.synthesizer_alias = synthesizer_alias

    comparisons: list[dict[str, Any]] = []
    synthesis: dict[str, Any] | None = None
    aggregate_rankings: list[dict[str, Any]] = []
    status = "completed"

    try:
        comparer_prompt = build_comparer_prompt(case_input)
        responses = await complete_aliases_parallel(
            respondent_aliases,
            user_prompt=comparer_prompt,
        )
        candidate_ids = [candidate["id"] for candidate in case_input.candidates]
        for alias, response in responses.items():
            metadata = response_metadata(response)
            content = response.content.strip()
            parsed_ranking = parse_candidate_ranking(content, candidate_ids)
            comparisons.append(
                {
                    "id": f"cmp_{len(comparisons) + 1:03d}",
                    "alias": alias,
                    "display_name": metadata.get("display_name"),
                    "technical_name": metadata.get("technical_name"),
                    "model": display_model(response),
                    "comparison": content or f"Error: {response.error}",
                    "raw_output": response.content,
                    "parsed_ranking": parsed_ranking,
                    "metadata": metadata,
                    "requested_alias": metadata.get("requested_alias"),
                    "requested_provider": metadata.get("requested_provider"),
                    "requested_model": metadata.get("requested_model"),
                    "actual_provider": metadata.get("actual_provider"),
                    "actual_model": metadata.get("actual_model"),
                    "fallback_used": metadata.get("fallback_used"),
                    "fallback_reason": metadata.get("fallback_reason"),
                }
            )

        aggregate_rankings = calculate_candidate_aggregate_rankings(
            comparisons,
            case_input.candidates,
        )

        synthesis_prompt = build_compare_synthesis_prompt(
            case_input,
            comparisons,
            aggregate_rankings,
        )
        synthesis_response = await complete_with_alias(
            synthesizer_alias,
            user_prompt=synthesis_prompt,
        )
        synthesis_metadata = response_metadata(synthesis_response)
        synthesis_content = synthesis_response.content.strip()
        synthesis = {
            "alias": synthesizer_alias,
            "display_name": synthesis_metadata.get("display_name"),
            "technical_name": synthesis_metadata.get("technical_name"),
            "model": display_model(synthesis_response),
            "response": synthesis_content or f"Error: {synthesis_response.error}",
            "raw_output": synthesis_response.content,
            "parsed_ranking": parse_candidate_ranking(synthesis_content, candidate_ids),
            "metadata": synthesis_metadata,
            "requested_alias": synthesis_metadata.get("requested_alias"),
            "requested_provider": synthesis_metadata.get("requested_provider"),
            "requested_model": synthesis_metadata.get("requested_model"),
            "actual_provider": synthesis_metadata.get("actual_provider"),
            "actual_model": synthesis_metadata.get("actual_model"),
            "fallback_used": synthesis_metadata.get("fallback_used"),
            "fallback_reason": synthesis_metadata.get("fallback_reason"),
        }

        if not comparisons:
            status = "failed"
            errors.append("No comparer responses were collected")
    except Exception as exc:
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
        comparisons=comparisons,
        aggregate_rankings=aggregate_rankings,
        synthesis=synthesis,
        errors=errors,
    )
    save_run_record(record)
    return record


def parse_candidate_ranking(text: str, valid_candidate_ids: list[str]) -> list[str] | None:
    """Parse FINAL RANKING using only exact candidate IDs."""
    if "FINAL RANKING:" not in text:
        return None
    valid = set(valid_candidate_ids)
    ranking_section = text.split("FINAL RANKING:", 1)[1]
    parsed: list[str] = []
    for line in ranking_section.splitlines():
        candidate_id = line.strip()
        if not candidate_id:
            continue
        candidate_id = re.sub(r"^\d+[.)]\s*", "", candidate_id)
        candidate_id = candidate_id.strip("-* \t")
        if candidate_id in valid and candidate_id not in parsed:
            parsed.append(candidate_id)
    return parsed or None


def calculate_candidate_aggregate_rankings(
    comparisons: list[dict[str, Any]],
    candidates: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Calculate average candidate rank from parsed comparer rankings."""
    positions: dict[str, list[int]] = defaultdict(list)
    candidate_meta = {
        candidate["id"]: {"title": candidate.get("title")}
        for candidate in candidates
    }
    for comparison in comparisons:
        parsed_ranking = comparison.get("parsed_ranking") or []
        for position, candidate_id in enumerate(parsed_ranking, start=1):
            if candidate_id in candidate_meta:
                positions[candidate_id].append(position)

    aggregate = []
    for candidate_id, ranked_positions in positions.items():
        aggregate.append(
            {
                "candidate_id": candidate_id,
                "title": candidate_meta[candidate_id].get("title"),
                "average_rank": round(sum(ranked_positions) / len(ranked_positions), 2),
                "rankings_count": len(ranked_positions),
            }
        )
    aggregate.sort(key=lambda item: item["average_rank"])
    return aggregate
