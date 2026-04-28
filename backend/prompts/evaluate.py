"""Prompt builders for evaluate cases."""

from typing import Any

from ..schemas.case import CaseInput


def build_evaluator_prompt(case: CaseInput) -> str:
    """Build the independent evaluator prompt for one evaluate case."""
    criteria_text = _format_criteria(case.criteria)
    context_text = f"\nAdditional context:\n{case.context.strip()}\n" if case.context else ""

    return f"""You are an independent evaluator. Evaluate the candidate output against the task.

Be critical and practical. Do not be generically positive. Preserve important nuance, but call out real problems plainly.

Task:
{case.task}
{context_text}
Candidate output:
{case.candidate_output}

Criteria:
{criteria_text}

Return plain markdown with these sections:

## Overall assessment
Briefly state whether the candidate satisfies the task.

## Criteria evaluation
Evaluate against each criterion if criteria are provided. If no criteria are provided, evaluate against the task requirements.

## Strengths
List the concrete strengths.

## Weaknesses
List the concrete weaknesses.

## Risks
Identify risks, edge cases, misleading claims, or likely failure modes.

## Missing assumptions or evidence
Identify missing assumptions, evidence, context, or verification needed.

## Recommendation
Choose exactly one: accept, revise, reject, or uncertain. Explain why.

## Confidence
Choose exactly one: low, medium, or high. Explain why."""


def build_evaluation_synthesis_prompt(
    case: CaseInput,
    evaluations: list[dict[str, Any]],
) -> str:
    """Build the synthesizer prompt for independent evaluations."""
    criteria_text = _format_criteria(case.criteria)
    context_text = f"\nAdditional context:\n{case.context.strip()}\n" if case.context else ""
    evaluations_text = "\n\n".join(
        [
            f"Evaluator: {item.get('display_name') or item.get('alias') or 'Unknown'}\n"
            f"Evaluation:\n{item.get('evaluation', '')}"
            for item in evaluations
        ]
    )

    return f"""You are synthesizing independent evaluations of a candidate output.

Do not make a deterministic decision. Do not add new modes such as compare, critique, or decide. Synthesize the evaluators' judgments into a practical, critical summary.

Task:
{case.task}
{context_text}
Candidate output:
{case.candidate_output}

Criteria:
{criteria_text}

Independent evaluations:
{evaluations_text}

Return plain markdown with these sections:

## Synthesis
Summarize the main agreement and disagreement across evaluators.

## Criteria summary
Summarize performance against the criteria, or against the task if no criteria were provided.

## Key strengths
List the strongest positive points that are actually supported by the evaluations.

## Key weaknesses
List the most important weaknesses or gaps.

## Risks and missing evidence
Summarize risks, missing assumptions, and evidence still needed.

## Recommendation summary
Summarize the recommendation spread, using only accept, revise, reject, or uncertain.

## Confidence summary
Summarize confidence levels and explain what drives them."""


def _format_criteria(criteria: list[str]) -> str:
    if not criteria:
        return "- No explicit criteria provided; evaluate against the task."
    return "\n".join(f"- {criterion}" for criterion in criteria)
