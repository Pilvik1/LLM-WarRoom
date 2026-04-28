"""Prompt builders for critique cases."""

from typing import Any

from ..schemas.case import CaseInput


def build_critic_prompt(case: CaseInput) -> str:
    """Build the independent critic prompt for one critique case."""
    criteria_text = _format_criteria(case.criteria)
    context_text = f"\nAdditional context:\n{case.context.strip()}\n" if case.context else ""

    return f"""You are an independent critic. Critique the candidate output/artifact against the task.

Be specific, practical, and direct. Do not drift into generic praise. Focus on what would help improve the artifact.

Task:
{case.task}
{context_text}
Candidate output/artifact:
{case.subject_text}

Criteria:
{criteria_text}

Return plain markdown with these sections:

## Strengths
List concrete strengths.

## Weaknesses
List concrete weaknesses.

## Hidden assumptions
Identify assumptions the artifact makes without stating or proving them.

## Risks
Identify risks, edge cases, misleading claims, or likely failure modes.

## Missing evidence
Identify evidence, citations, examples, tests, context, or verification still needed.

## Concrete improvements
List actionable improvements. Make them specific enough for a person to apply.

## Optional revised version
If a concise revision would materially help, provide one. Otherwise write: Not provided."""


def build_critique_synthesis_prompt(
    case: CaseInput,
    critiques: list[dict[str, Any]],
) -> str:
    """Build the synthesizer prompt for independent critiques."""
    criteria_text = _format_criteria(case.criteria)
    context_text = f"\nAdditional context:\n{case.context.strip()}\n" if case.context else ""
    critiques_text = "\n\n".join(
        [
            f"Critic: {item.get('display_name') or item.get('alias') or 'Unknown'}\n"
            f"Critique:\n{item.get('critique', '')}"
            for item in critiques
        ]
    )

    return f"""You are synthesizing independent critiques of a candidate output/artifact.

Do not add compare or decide behavior. Do not make a deterministic acceptance decision. Produce a practical critique synthesis that preserves important disagreements and concrete fixes.

Task:
{case.task}
{context_text}
Candidate output/artifact:
{case.subject_text}

Criteria:
{criteria_text}

Independent critiques:
{critiques_text}

Return plain markdown with these sections:

## Strengths
Synthesize the strongest supported strengths.

## Weaknesses
Synthesize the most important weaknesses.

## Hidden assumptions
Synthesize unstated assumptions the artifact appears to rely on.

## Risks
Synthesize risks and likely failure modes.

## Missing evidence
Synthesize missing evidence, context, examples, tests, or verification.

## Concrete improvements
List prioritized, actionable improvements.

## Optional revised version
If the critiques support a useful concise revision, provide one. Otherwise write: Not provided."""


def _format_criteria(criteria: list[str]) -> str:
    if not criteria:
        return "- No explicit criteria provided; critique against the task."
    return "\n".join(f"- {criterion}" for criterion in criteria)
