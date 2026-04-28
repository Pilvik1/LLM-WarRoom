"""Critique case runner."""

from datetime import datetime
from typing import Any

from .case_runner import new_run_id
from .config import RESPONDENT_MODEL_ALIASES, SYNTHESIZER_MODEL_ALIAS
from .prompts.critique import build_critic_prompt, build_critique_synthesis_prompt
from .providers.model_registry import (
    complete_aliases_parallel,
    complete_with_alias,
    display_model,
    response_metadata,
)
from .run_storage import save_run_record
from .schemas.case import CaseInput
from .schemas.run import RunRecord


async def run_critique_case(
    case_input: CaseInput,
    run_id: str | None = None,
) -> RunRecord:
    """Run independent critiques, synthesize them, and persist the run."""
    run_id = run_id or new_run_id()
    created_at = datetime.utcnow().isoformat()
    errors: list[str] = []

    respondent_aliases = case_input.respondent_aliases or list(RESPONDENT_MODEL_ALIASES)
    synthesizer_alias = case_input.synthesizer_alias or SYNTHESIZER_MODEL_ALIAS
    case_input.respondent_aliases = list(respondent_aliases)
    case_input.synthesizer_alias = synthesizer_alias

    critiques: list[dict[str, Any]] = []
    synthesis: dict[str, Any] | None = None
    status = "completed"

    try:
        critic_prompt = build_critic_prompt(case_input)
        responses = await complete_aliases_parallel(
            respondent_aliases,
            user_prompt=critic_prompt,
        )
        for alias, response in responses.items():
            metadata = response_metadata(response)
            content = response.content.strip()
            critiques.append(
                {
                    "id": f"crit_{len(critiques) + 1:03d}",
                    "alias": alias,
                    "display_name": metadata.get("display_name"),
                    "technical_name": metadata.get("technical_name"),
                    "model": display_model(response),
                    "critique": content or f"Error: {response.error}",
                    "raw_output": response.content,
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

        synthesis_prompt = build_critique_synthesis_prompt(case_input, critiques)
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
            "metadata": synthesis_metadata,
            "requested_alias": synthesis_metadata.get("requested_alias"),
            "requested_provider": synthesis_metadata.get("requested_provider"),
            "requested_model": synthesis_metadata.get("requested_model"),
            "actual_provider": synthesis_metadata.get("actual_provider"),
            "actual_model": synthesis_metadata.get("actual_model"),
            "fallback_used": synthesis_metadata.get("fallback_used"),
            "fallback_reason": synthesis_metadata.get("fallback_reason"),
        }

        if not critiques:
            status = "failed"
            errors.append("No critic responses were collected")
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
        critiques=critiques,
        synthesis=synthesis,
        errors=errors,
    )
    save_run_record(record)
    return record
