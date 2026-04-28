"""War Room case runner."""

import asyncio
from datetime import datetime
from typing import Any

from .case_runner import new_run_id
from .config import RESPONDENT_MODEL_ALIASES, REVIEWER_MODEL_ALIASES, SYNTHESIZER_MODEL_ALIAS
from .prompts.war_room import (
    ADVISORS,
    build_advisor_prompt,
    build_deterministic_framed_question,
    build_peer_review_prompt,
    build_verdict_prompt,
)
from .providers.model_registry import complete_with_alias, display_model, response_metadata
from .run_storage import save_run_record
from .schemas.case import CaseInput
from .schemas.run import RunRecord


async def run_war_room_case(
    case_input: CaseInput,
    run_id: str | None = None,
) -> RunRecord:
    """Run five advisor lenses, anonymized peer review, and final verdict."""
    run_id = run_id or new_run_id()
    created_at = datetime.utcnow().isoformat()
    errors: list[str] = []

    respondent_aliases = case_input.respondent_aliases or list(RESPONDENT_MODEL_ALIASES)
    synthesizer_alias = case_input.synthesizer_alias or SYNTHESIZER_MODEL_ALIAS
    if not respondent_aliases:
        respondent_aliases = [synthesizer_alias]
    case_input.respondent_aliases = list(respondent_aliases)
    case_input.synthesizer_alias = synthesizer_alias

    framed_question = build_deterministic_framed_question(case_input)
    advisor_responses: list[dict[str, Any]] = []
    peer_reviews: list[dict[str, Any]] = []
    verdict: dict[str, Any] | None = None
    status = "completed"

    try:
        advisor_tasks = [
            _run_advisor(
                alias=respondent_aliases[index % len(respondent_aliases)],
                advisor=advisor,
                framed_question=framed_question,
                case_input=case_input,
                index=index,
            )
            for index, advisor in enumerate(ADVISORS)
        ]
        advisor_responses = await asyncio.gather(*advisor_tasks)
        for item in advisor_responses:
            if item.get("error"):
                errors.append(f"{item.get('advisor_name')}: {item.get('error')}")

        usable_advisors = [item for item in advisor_responses if (item.get("raw_output") or "").strip()]
        if not usable_advisors:
            status = "failed"
            errors.append("No advisor responses were collected")
        else:
            anonymized = _anonymize(usable_advisors)
            reviewer_aliases = list(REVIEWER_MODEL_ALIASES or respondent_aliases)
            peer_prompt = build_peer_review_prompt(case_input, framed_question, anonymized)
            peer_tasks = [
                _run_peer_review(alias=alias, prompt=peer_prompt, index=index)
                for index, alias in enumerate(reviewer_aliases)
            ]
            peer_reviews = await asyncio.gather(*peer_tasks)
            for item in peer_reviews:
                if item.get("error"):
                    errors.append(f"{item.get('id')}: {item.get('error')}")

            verdict_prompt = build_verdict_prompt(
                case_input,
                framed_question,
                usable_advisors,
                peer_reviews,
            )
            verdict_response = await complete_with_alias(
                synthesizer_alias,
                user_prompt=verdict_prompt,
            )
            verdict_metadata = response_metadata(verdict_response)
            verdict_content = verdict_response.content.strip()
            verdict = {
                "id": "war_room_verdict",
                "alias": synthesizer_alias,
                "display_name": verdict_metadata.get("display_name"),
                "actual_display_name": verdict_metadata.get("actual_display_name"),
                "technical_name": verdict_metadata.get("technical_name"),
                "model": display_model(verdict_response),
                "response": verdict_content or f"Error: {verdict_response.error}",
                "raw_output": verdict_response.content,
                "metadata": verdict_metadata,
                "requested_alias": verdict_metadata.get("requested_alias"),
                "requested_provider": verdict_metadata.get("requested_provider"),
                "requested_model": verdict_metadata.get("requested_model"),
                "actual_provider": verdict_metadata.get("actual_provider"),
                "actual_model": verdict_metadata.get("actual_model"),
                "fallback_used": verdict_metadata.get("fallback_used"),
                "fallback_reason": verdict_metadata.get("fallback_reason"),
            }
            if verdict_response.error:
                errors.append(f"verdict: {verdict_response.error}")
                if status != "failed":
                    status = "partial"
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
        framed_question=framed_question,
        advisor_responses=advisor_responses,
        peer_reviews=peer_reviews,
        verdict=verdict,
        errors=errors,
    )
    save_run_record(record)
    return record


async def _run_advisor(
    alias: str,
    advisor: dict[str, str],
    framed_question: str,
    case_input: CaseInput,
    index: int,
) -> dict[str, Any]:
    prompt = build_advisor_prompt(case_input, framed_question, advisor)
    response = await complete_with_alias(alias, user_prompt=prompt)
    metadata = response_metadata(response)
    content = response.content.strip()
    return {
        "id": f"advisor_{index + 1:03d}",
        "advisor_name": advisor["name"],
        "advisor_description": advisor["description"],
        "alias": alias,
        "display_name": metadata.get("display_name"),
        "actual_display_name": metadata.get("actual_display_name"),
        "technical_name": metadata.get("technical_name"),
        "model": display_model(response),
        "response": content or f"Error: {response.error}",
        "raw_output": response.content,
        "metadata": metadata,
        "requested_alias": metadata.get("requested_alias"),
        "requested_provider": metadata.get("requested_provider"),
        "requested_model": metadata.get("requested_model"),
        "actual_provider": metadata.get("actual_provider"),
        "actual_model": metadata.get("actual_model"),
        "fallback_used": metadata.get("fallback_used"),
        "fallback_reason": metadata.get("fallback_reason"),
        "anonymous_label": _label_for_index(index),
        "error": response.error,
    }


async def _run_peer_review(alias: str, prompt: str, index: int) -> dict[str, Any]:
    response = await complete_with_alias(alias, user_prompt=prompt)
    metadata = response_metadata(response)
    content = response.content.strip()
    return {
        "id": f"peer_review_{index + 1:03d}",
        "alias": alias,
        "display_name": metadata.get("display_name"),
        "actual_display_name": metadata.get("actual_display_name"),
        "technical_name": metadata.get("technical_name"),
        "model": display_model(response),
        "review": content or f"Error: {response.error}",
        "raw_output": response.content,
        "metadata": metadata,
        "requested_alias": metadata.get("requested_alias"),
        "requested_provider": metadata.get("requested_provider"),
        "requested_model": metadata.get("requested_model"),
        "actual_provider": metadata.get("actual_provider"),
        "actual_model": metadata.get("actual_model"),
        "fallback_used": metadata.get("fallback_used"),
        "fallback_reason": metadata.get("fallback_reason"),
        "error": response.error,
    }


def _anonymize(advisor_responses: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Use deterministic Response A-E mapping and preserve it in artifacts."""
    anonymized = []
    for index, item in enumerate(advisor_responses):
        label = _label_for_index(index)
        item["anonymous_label"] = label
        anonymized.append(
            {
                "label": label,
                "advisor_response_id": item.get("id"),
                "advisor_name": item.get("advisor_name"),
                "response": item.get("response", ""),
            }
        )
    return anonymized


def _label_for_index(index: int) -> str:
    return f"Response {chr(ord('A') + index)}"
