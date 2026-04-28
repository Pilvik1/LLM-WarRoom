"""Storage helpers for case run artifacts."""

import json
from pathlib import Path
from typing import Any

from .schemas.run import RunRecord


RUNS_DIR = Path("data/runs")


def save_run_record(record: RunRecord) -> Path:
    """Persist a run record to data/runs/<run_id>/run.json."""
    run_dir = RUNS_DIR / record.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "run.json"
    data = _normalize_run_dict(_dump_record(record))
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    _write_summary(run_dir, data)
    return path


def load_run_record(run_id: str) -> dict[str, Any]:
    """Load data/runs/<run_id>/run.json as a dictionary."""
    path = RUNS_DIR / run_id / "run.json"
    if not path.exists():
        raise FileNotFoundError(f"Run artifact not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_decision_record(run_id: str, decision: dict[str, Any]) -> Path:
    """Persist a deterministic decision to data/runs/<run_id>/decision.json."""
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "decision.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2)
    run_path = run_dir / "run.json"
    if run_path.exists():
        with run_path.open("r", encoding="utf-8") as f:
            run_data = json.load(f)
    else:
        run_data = _run_from_decision(decision)
    outputs = run_data.setdefault("outputs", _outputs_for(run_data))
    outputs["decision"] = decision
    run_data["artifact_paths"] = _artifact_paths_for(run_data)
    run_data["artifact_paths"]["decision_json"] = str(path)
    run_data = _normalize_run_dict(run_data)
    with run_path.open("w", encoding="utf-8") as f:
        json.dump(run_data, f, indent=2)
    _write_summary(run_dir, run_data)
    return path


def _dump_record(record: RunRecord) -> dict[str, Any]:
    if hasattr(record, "model_dump"):
        return record.model_dump(mode="json")
    return record.dict()


def _normalize_run_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Return the current normalized artifact shape with legacy fields intact."""
    normalized = dict(data)
    outputs = _outputs_for(normalized)
    normalized["outputs"] = outputs
    normalized["provider_metadata"] = _provider_metadata_for(normalized, outputs)
    normalized["artifact_paths"] = _artifact_paths_for(normalized)
    return normalized


def _outputs_for(data: dict[str, Any]) -> dict[str, Any]:
    outputs = {
        key: value
        for key, value in (data.get("outputs") or {}).items()
        if _has_output(value)
    }
    for key in (
        "independent_responses",
        "peer_reviews",
        "evaluations",
        "critiques",
        "comparisons",
        "advisor_responses",
        "aggregate_rankings",
        "framed_question",
        "verdict",
        "synthesis",
    ):
        value = data.get(key)
        if _has_output(value):
            outputs[key] = value
    if "decision" in data and "decision" not in outputs:
        outputs["decision"] = data["decision"]
    return outputs


def _has_output(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _provider_metadata_for(
    data: dict[str, Any],
    outputs: dict[str, Any],
) -> dict[str, Any]:
    input_data = data.get("input") or {}
    metadata: dict[str, Any] = {
        "respondent_aliases": input_data.get("respondent_aliases") or [],
        "synthesizer_alias": input_data.get("synthesizer_alias"),
        "responses": [],
        "fallbacks": [],
    }

    for item in _iter_output_items(outputs):
        if not isinstance(item, dict):
            continue
        item_metadata = item.get("metadata") or {}
        if not item_metadata:
            continue
        response_metadata = {
            "id": item.get("id"),
            "alias": item.get("alias") or item_metadata.get("requested_alias"),
            "display_name": item_metadata.get("display_name") or item.get("display_name"),
            "actual_display_name": item_metadata.get("actual_display_name") or item.get("actual_display_name"),
            "technical_name": item_metadata.get("technical_name") or item.get("technical_name"),
            "requested_alias": item_metadata.get("requested_alias"),
            "requested_provider": item_metadata.get("requested_provider"),
            "requested_model": item_metadata.get("requested_model"),
            "actual_alias": item_metadata.get("actual_alias"),
            "actual_provider": item_metadata.get("actual_provider"),
            "actual_model": item_metadata.get("actual_model"),
            "fallback_used": item_metadata.get("fallback_used"),
            "fallback_reason": item_metadata.get("fallback_reason"),
            "attempted_aliases": item_metadata.get("attempted_aliases"),
            "latency_ms": item_metadata.get("latency_ms"),
            "usage": item_metadata.get("usage"),
            "error": item_metadata.get("error"),
        }
        metadata["responses"].append(response_metadata)
        if response_metadata.get("fallback_used") or response_metadata.get("fallback_reason"):
            metadata["fallbacks"].append(response_metadata)
    return metadata


def _iter_output_items(outputs: dict[str, Any]):
    for key in (
        "independent_responses",
        "peer_reviews",
        "evaluations",
        "critiques",
        "comparisons",
        "advisor_responses",
        "verdict",
    ):
        value = outputs.get(key)
        if isinstance(value, list):
            yield from value
    synthesis = outputs.get("synthesis")
    if isinstance(synthesis, dict):
        yield synthesis
    verdict = outputs.get("verdict")
    if isinstance(verdict, dict):
        yield verdict


def _artifact_paths_for(data: dict[str, Any]) -> dict[str, str]:
    run_id = data.get("run_id")
    if not run_id:
        return {}
    paths = {
        "run_json": str(RUNS_DIR / run_id / "run.json"),
        "summary_md": str(RUNS_DIR / run_id / "summary.md"),
    }
    decision_path = RUNS_DIR / run_id / "decision.json"
    if decision_path.exists() or data.get("case_type") == "decide" or data.get("decision"):
        paths["decision_json"] = str(decision_path)
    return paths


def _run_from_decision(decision: dict[str, Any]) -> dict[str, Any]:
    created_at = decision.get("created_at")
    return {
        "run_id": decision["run_id"],
        "case_id": None,
        "case_type": "decide",
        "status": "completed",
        "created_at": created_at,
        "completed_at": created_at,
        "input": {
            "source_run_id": (decision.get("source_artifacts") or {}).get("source_run_id"),
            "evaluation_payload": (decision.get("source_artifacts") or {}).get("evaluation_payload"),
            "thresholds": decision.get("thresholds") or {},
            "rules": decision.get("rules") or {},
        },
        "decision": decision,
        "errors": [],
    }


def _write_summary(run_dir: Path, data: dict[str, Any]) -> Path:
    path = run_dir / "summary.md"
    path.write_text(_summary_markdown(data), encoding="utf-8")
    return path


def _summary_markdown(data: dict[str, Any]) -> str:
    input_data = data.get("input") or {}
    outputs = data.get("outputs") or {}
    provider_metadata = data.get("provider_metadata") or {}
    task = input_data.get("task") or "(no task recorded)"

    lines = [
        f"# Run {data.get('run_id')}",
        "",
        f"- case_type: {data.get('case_type')}",
        f"- status: {data.get('status')}",
        f"- task: {task}",
        "",
        "## Models",
    ]
    aliases = provider_metadata.get("respondent_aliases") or []
    lines.append(f"- respondents: {', '.join(aliases) if aliases else 'none recorded'}")
    lines.append(f"- synthesizer: {provider_metadata.get('synthesizer_alias') or 'none recorded'}")

    fallbacks = provider_metadata.get("fallbacks") or []
    lines.extend(["", "## Fallback Notes"])
    if fallbacks:
        for item in fallbacks:
            lines.append(
                f"- {item.get('requested_alias') or item.get('alias')}: "
                f"{item.get('fallback_reason') or 'fallback used'}"
            )
    else:
        lines.append("- none recorded")

    lines.extend(["", "## Summary"])
    decision = outputs.get("decision")
    if isinstance(decision, dict):
        lines.append(f"- decision: {decision.get('decision')}")
        lines.append(f"- deterministic: {decision.get('deterministic')}")
        lines.append(f"- reason: {decision.get('reason')}")
    elif isinstance(outputs.get("verdict"), dict):
        lines.append(_first_paragraph(outputs["verdict"].get("response") or "No verdict text recorded."))
    elif isinstance(outputs.get("synthesis"), dict):
        lines.append(_first_paragraph(outputs["synthesis"].get("response") or "No synthesis text recorded."))
    else:
        lines.append("No synthesis or decision recorded.")

    return "\n".join(lines).rstrip() + "\n"


def _first_paragraph(text: str, limit: int = 1200) -> str:
    paragraph = (text or "").strip().split("\n\n", 1)[0].strip()
    if len(paragraph) > limit:
        return paragraph[: limit - 3].rstrip() + "..."
    return paragraph or "No synthesis text recorded."
