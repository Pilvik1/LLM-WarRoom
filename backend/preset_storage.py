"""JSON storage and built-in defaults for council presets."""

import json
import re
from pathlib import Path

from .config import (
    RESPONDENT_MODEL_ALIASES,
    REVIEWER_MODEL_ALIASES,
    SYNTHESIZER_MODEL_ALIAS,
)
from .prompts.war_room import ADVISORS
from .schemas.preset import CouncilPreset, SeatDefinition, WorkflowType


PRESETS_DIR = Path("data/presets")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def _assigned_alias(index: int) -> str:
    aliases = list(RESPONDENT_MODEL_ALIASES) or [SYNTHESIZER_MODEL_ALIAS]
    return aliases[index % len(aliases)]


def _seats(roles: list[tuple[str, str]]) -> list[SeatDefinition]:
    return [
        SeatDefinition(
            id=re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_"),
            name=name,
            role_prompt=prompt,
            model_alias=_assigned_alias(index),
        )
        for index, (name, prompt) in enumerate(roles)
    ]


def built_in_presets() -> list[CouncilPreset]:
    """Return fresh built-in presets based on the active alias configuration."""
    council_seats = [
        SeatDefinition(
            id=f"seat_{index + 1}",
            name=advisor["name"],
            role_prompt=advisor["description"],
            model_alias=_assigned_alias(index),
        )
        for index, advisor in enumerate(ADVISORS)
    ]
    ask_seats = [
        SeatDefinition(
            id=f"respondent_{index + 1}",
            name=f"Independent Respondent {index + 1}",
            role_prompt="Answer independently and prioritize correctness, clarity, and usefulness.",
            model_alias=alias,
        )
        for index, alias in enumerate(
            list(RESPONDENT_MODEL_ALIASES) or [SYNTHESIZER_MODEL_ALIAS]
        )
    ]
    compare_seats = [
        SeatDefinition(
            id=f"comparer_{index + 1}",
            name=f"Independent Comparer {index + 1}",
            role_prompt="Compare the candidates independently against the supplied criteria.",
            model_alias=alias,
        )
        for index, alias in enumerate(
            list(RESPONDENT_MODEL_ALIASES) or [SYNTHESIZER_MODEL_ALIAS]
        )
    ]
    common = {
        "reviewer_aliases": list(REVIEWER_MODEL_ALIASES),
        "synthesizer_alias": SYNTHESIZER_MODEL_ALIAS,
        "built_in": True,
    }
    return [
        CouncilPreset(
            id="general-council",
            name="General Council",
            description="Five reasoning lenses for decisions, plans, ideas, and artifacts.",
            workflow_type="council",
            seats=council_seats,
            **common,
        ),
        CouncilPreset(
            id="decision-review",
            name="Decision Review",
            description="Test a consequential choice from evidence, risk, and execution angles.",
            workflow_type="council",
            seats=_seats([
                ("Decision Analyst", "Clarify the decision, alternatives, evidence, and expected value."),
                ("Risk Officer", "Identify downside, failure modes, irreversible exposure, and safeguards."),
                ("Contrarian", "Build the strongest case against the apparent preferred option."),
                ("Operator", "Translate the decision into sequencing, ownership, and a reversible first step."),
            ]),
            **common,
        ),
        CouncilPreset(
            id="code-review",
            name="Code Review",
            description="Review an implementation for correctness, security, simplicity, and operability.",
            workflow_type="council",
            seats=_seats([
                ("Correctness Reviewer", "Find logic errors, unhandled states, broken contracts, and missing tests."),
                ("Security Reviewer", "Identify trust-boundary failures, unsafe inputs, secret exposure, and abuse paths."),
                ("Maintainer", "Reduce accidental complexity and improve readability, boundaries, and change safety."),
                ("Operator", "Assess deployment, observability, failure recovery, and runtime behavior."),
            ]),
            **common,
        ),
        CouncilPreset(
            id="investment-case",
            name="Investment Case",
            description="Pressure-test an investment thesis without hiding uncertainty.",
            workflow_type="council",
            seats=_seats([
                ("Fundamental Analyst", "Assess business quality, economics, financial evidence, and valuation drivers."),
                ("Industry Analyst", "Examine market structure, competition, bargaining power, and industry change."),
                ("Bear Case", "Build the strongest evidence-based downside case and identify thesis breakers."),
                ("Catalyst Analyst", "Identify what changes the market's view, on what timeline, and with what evidence."),
                ("Portfolio Manager", "Judge sizing, opportunity cost, risk limits, and what must be monitored."),
            ]),
            **common,
        ),
        CouncilPreset(
            id="red-team",
            name="Red Team",
            description="Attack a plan before reality gets the opportunity.",
            workflow_type="council",
            seats=_seats([
                ("Adversary", "Actively find how the plan can be exploited, defeated, or made irrelevant."),
                ("Assumption Auditor", "List hidden assumptions and identify the cheapest way to falsify each one."),
                ("Pre-mortem Lead", "Assume failure occurred and reconstruct the most plausible causal chain."),
                ("Recovery Planner", "Design mitigations, tripwires, fallbacks, and recovery actions."),
            ]),
            **common,
        ),
        CouncilPreset(
            id="multi-model-ask",
            name="Multi-model Ask",
            description="Independent answers, anonymized peer review, and synthesis.",
            workflow_type="ask",
            seats=ask_seats,
            **common,
        ),
        CouncilPreset(
            id="structured-compare",
            name="Structured Compare",
            description="Independent comparison of named options against explicit criteria.",
            workflow_type="compare",
            seats=compare_seats,
            **common,
        ),
    ]


def list_presets(workflow_type: WorkflowType | None = None) -> list[CouncilPreset]:
    presets = {preset.id: preset for preset in built_in_presets()}
    if PRESETS_DIR.exists():
        for path in sorted(PRESETS_DIR.glob("*.json")):
            try:
                preset = CouncilPreset.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            preset.built_in = False
            presets[preset.id] = preset
    values = list(presets.values())
    if workflow_type:
        values = [preset for preset in values if preset.workflow_type == workflow_type]
    return sorted(values, key=lambda preset: (not preset.built_in, preset.name.lower()))


def get_preset(preset_id: str) -> CouncilPreset | None:
    return next((preset for preset in list_presets() if preset.id == preset_id), None)


def save_preset(preset: CouncilPreset) -> CouncilPreset:
    if not _SAFE_ID.fullmatch(preset.id):
        raise ValueError("preset id may contain only letters, numbers, hyphens, and underscores")
    if any(item.id == preset.id for item in built_in_presets()):
        raise ValueError("built-in presets cannot be overwritten; save a copy with a new id")
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    stored = preset.model_copy(update={"built_in": False})
    (PRESETS_DIR / f"{stored.id}.json").write_text(
        json.dumps(stored.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return stored
