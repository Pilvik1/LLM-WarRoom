"""Deterministic decide mode."""

from datetime import datetime
from typing import Any, Literal
import re

from .case_runner import new_run_id
from .run_storage import load_run_record, save_decision_record


Decision = Literal["accepted", "revision_required", "rejected", "no_decision"]


RECOMMENDATION_RE = re.compile(
    r"\b(accept|accepted|revise|revision_required|revision required|reject|rejected|uncertain)\b",
    re.IGNORECASE,
)
CONFIDENCE_RE = re.compile(r"\b(low|medium|high)\b", re.IGNORECASE)


def run_decide_case(
    source_run_id: str | None = None,
    evaluation_payload: dict[str, Any] | None = None,
    thresholds: dict[str, Any] | None = None,
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply deterministic rules and persist decision.json."""
    thresholds = thresholds or {}
    rules = rules or {}
    source_artifacts = _source_artifacts(source_run_id, evaluation_payload)
    observed = _observed(source_artifacts, evaluation_payload)
    decision, reason = _decide(observed, thresholds, rules)

    run_id = source_run_id or new_run_id()
    record = {
        "run_id": run_id,
        "case_type": "decide",
        "decision": decision,
        "deterministic": True,
        "reason": reason,
        "thresholds": thresholds,
        "rules": rules,
        "observed_scores": observed.get("scores", {}),
        "observed_recommendations": observed.get("recommendations", {}),
        "observed_confidence": observed.get("confidence", {}),
        "source_artifacts": source_artifacts,
        "created_at": datetime.utcnow().isoformat(),
        "artifact": {
            "path": f"data/runs/{run_id}/decision.json",
            "format": "decision.json",
        },
    }
    save_decision_record(run_id, record)
    return record


def _source_artifacts(
    source_run_id: str | None,
    evaluation_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    if source_run_id:
        artifacts["source_run_id"] = source_run_id
        artifacts["run"] = load_run_record(source_run_id)
        artifacts["run_path"] = f"data/runs/{source_run_id}/run.json"
    if evaluation_payload is not None:
        artifacts["evaluation_payload"] = evaluation_payload
    return artifacts


def _observed(
    source_artifacts: dict[str, Any],
    evaluation_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = evaluation_payload or {}
    run = source_artifacts.get("run") or {}
    scores = _extract_scores(payload)
    scores.update({key: value for key, value in _extract_scores(run).items() if key not in scores})

    text_items = _evaluation_texts(payload) + _evaluation_texts(run)
    recommendations = _count_recommendations(text_items)
    confidence = _count_confidence(text_items)

    return {
        "scores": scores,
        "recommendations": recommendations,
        "confidence": confidence,
    }


def _extract_scores(data: dict[str, Any]) -> dict[str, float]:
    scores: dict[str, float] = {}
    outputs = data.get("outputs")
    if isinstance(outputs, dict):
        scores.update(_extract_scores(outputs))

    for key in ("scores", "observed_scores"):
        raw_scores = data.get(key)
        if isinstance(raw_scores, dict):
            _merge_numeric_scores(scores, raw_scores)

    for key in ("criteria_scores", "scorecard"):
        raw_scores = data.get(key)
        if isinstance(raw_scores, dict):
            _merge_numeric_scores(scores, raw_scores, prefix="criteria.")

    numeric_score = data.get("score")
    if isinstance(numeric_score, int | float):
        scores.setdefault("overall", float(numeric_score))
    return scores


def _merge_numeric_scores(
    scores: dict[str, float],
    raw_scores: dict[str, Any],
    prefix: str = "",
) -> None:
    for key, value in raw_scores.items():
        if isinstance(value, int | float):
            scores[f"{prefix}{key}"] = float(value)
        elif isinstance(value, dict):
            _merge_numeric_scores(scores, value, prefix=f"{prefix}{key}.")


def _evaluation_texts(data: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    outputs = data.get("outputs")
    if isinstance(outputs, dict):
        texts.extend(_evaluation_texts(outputs))

    for key in ("evaluations", "critiques"):
        items = data.get(key)
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                for text_key in ("evaluation", "critique", "response", "raw_output"):
                    text = item.get(text_key)
                    if isinstance(text, str) and text.strip():
                        texts.append(text)
                        break
    synthesis = data.get("synthesis")
    if isinstance(synthesis, dict):
        text = synthesis.get("response") or synthesis.get("raw_output")
        if isinstance(text, str) and text.strip():
            texts.append(text)
    return texts


def _count_recommendations(texts: list[str]) -> dict[str, Any]:
    counts = {"accept": 0, "revise": 0, "reject": 0, "uncertain": 0}
    for text in texts:
        match = RECOMMENDATION_RE.search(text)
        if not match:
            continue
        normalized = match.group(1).lower().replace(" ", "_")
        if normalized in ("accept", "accepted"):
            counts["accept"] += 1
        elif normalized in ("revise", "revision_required"):
            counts["revise"] += 1
        elif normalized in ("reject", "rejected"):
            counts["reject"] += 1
        elif normalized == "uncertain":
            counts["uncertain"] += 1
    total = sum(counts.values())
    ratios = {
        key: (value / total if total else 0.0)
        for key, value in counts.items()
    }
    return {"counts": counts, "ratios": ratios, "total": total}


def _count_confidence(texts: list[str]) -> dict[str, Any]:
    counts = {"low": 0, "medium": 0, "high": 0}
    for text in texts:
        match = CONFIDENCE_RE.search(text)
        if match:
            counts[match.group(1).lower()] += 1
    return {"counts": counts, "total": sum(counts.values())}


def _decide(
    observed: dict[str, Any],
    thresholds: dict[str, Any],
    rules: dict[str, Any],
) -> tuple[Decision, str]:
    scores = observed.get("scores", {})
    score_key = rules.get("score_key", "overall")
    score = scores.get(score_key)

    if score is not None:
        criterion_decision = _criterion_decision(scores, thresholds, rules)
        if criterion_decision:
            return criterion_decision

        reject_below = thresholds.get("reject_below_score")
        accept_min = thresholds.get("accept_min_score")
        revision_min = thresholds.get("revision_min_score")

        if isinstance(reject_below, int | float) and score < float(reject_below):
            return "rejected", f"{score_key} score {score:g} is below reject_below_score {float(reject_below):g}"
        if isinstance(accept_min, int | float) and score >= float(accept_min):
            return "accepted", f"{score_key} score {score:g} meets accept_min_score {float(accept_min):g}"
        if isinstance(revision_min, int | float) and score >= float(revision_min):
            return "revision_required", f"{score_key} score {score:g} meets revision_min_score {float(revision_min):g}"
        return "no_decision", f"{score_key} score {score:g} did not match any configured threshold"

    recommendation_decision = _recommendation_decision(observed, thresholds)
    if recommendation_decision:
        return recommendation_decision

    if not thresholds:
        return "no_decision", "No thresholds or rules were provided"
    return "no_decision", f"No numeric score found for score_key '{score_key}' and no recommendation rule matched"


def _criterion_decision(
    scores: dict[str, float],
    thresholds: dict[str, Any],
    rules: dict[str, Any],
) -> tuple[Decision, str] | None:
    min_score = rules.get("require_all_criteria_at_least")
    if min_score is None:
        min_score = thresholds.get("per_criterion_min_score")
    if not isinstance(min_score, int | float):
        return None

    criterion_scores = {
        key: value
        for key, value in scores.items()
        if key.startswith("criteria.")
    }
    if not criterion_scores:
        return None

    failing = {
        key: value
        for key, value in criterion_scores.items()
        if value < float(min_score)
    }
    if not failing:
        return None

    decision = "rejected" if rules.get("reject_if_any_criterion_below") else "revision_required"
    reason = (
        f"Criteria below {float(min_score):g}: "
        + ", ".join(f"{key}={value:g}" for key, value in sorted(failing.items()))
    )
    return decision, reason


def _recommendation_decision(
    observed: dict[str, Any],
    thresholds: dict[str, Any],
) -> tuple[Decision, str] | None:
    recommendations = observed.get("recommendations", {})
    total = recommendations.get("total", 0)
    if not total:
        return None

    ratios = recommendations.get("ratios", {})
    rules = [
        ("min_reject_ratio", "reject", "rejected"),
        ("min_accept_ratio", "accept", "accepted"),
        ("min_revision_ratio", "revise", "revision_required"),
    ]
    for threshold_key, recommendation_key, decision in rules:
        threshold = thresholds.get(threshold_key)
        ratio = ratios.get(recommendation_key, 0.0)
        if isinstance(threshold, int | float) and ratio >= float(threshold):
            return (
                decision,
                f"{recommendation_key} recommendation ratio {ratio:g} meets {threshold_key} {float(threshold):g}",
            )
    return None
