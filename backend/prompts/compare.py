"""Prompt builders for compare cases."""

from typing import Any

from ..schemas.case import CaseInput


def build_comparer_prompt(case: CaseInput) -> str:
    """Build the independent comparer prompt for one compare case."""
    candidate_ids = [candidate["id"] for candidate in case.candidates]
    context_text = f"\nAdditional context:\n{case.context.strip()}\n" if case.context else ""

    return f"""You are an independent comparer. Compare the candidates against the task.

Rank candidate IDs only. Do not rank model names, provider names, aliases, titles, or descriptions. Use only these candidate IDs in rankings: {", ".join(candidate_ids)}.

Task:
{case.task}
{context_text}
Criteria:
{_format_criteria(case.criteria)}

Candidates:
{_format_candidates(case)}

Return plain markdown with these sections:

## Per-candidate assessment
For each candidate ID, assess strengths, weaknesses, risks, and fit for the task.

## Tradeoff table
Provide a markdown table comparing the candidate IDs across the most important tradeoffs.

## Ranked recommendation
Explain the ranking briefly using candidate IDs only.

## Disagreement notes
Identify where reasonable evaluators might disagree.

FINAL RANKING:
List candidate IDs from best to worst, one per line. Each line must contain only one candidate ID from the allowed list. Do not include titles, model names, bullets, numbers, or explanations in this section."""


def build_compare_synthesis_prompt(
    case: CaseInput,
    comparisons: list[dict[str, Any]],
    aggregate_rankings: list[dict[str, Any]],
) -> str:
    """Build the synthesizer prompt for independent comparisons."""
    candidate_ids = [candidate["id"] for candidate in case.candidates]
    context_text = f"\nAdditional context:\n{case.context.strip()}\n" if case.context else ""
    comparisons_text = "\n\n".join(
        [
            f"Comparer: {item.get('display_name') or item.get('alias') or 'Unknown'}\n"
            f"Parsed ranking: {', '.join(item.get('parsed_ranking') or []) or 'none'}\n"
            f"Comparison:\n{item.get('comparison', '')}"
            for item in comparisons
        ]
    )
    aggregate_text = "\n".join(
        [
            f"- {item['candidate_id']}: average_rank={item['average_rank']}, rankings_count={item['rankings_count']}"
            for item in aggregate_rankings
        ]
    ) or "- No parseable rankings."

    return f"""You are synthesizing independent candidate comparisons.

Rank candidate IDs only. Do not rank model names, provider names, aliases, titles, or descriptions. Use only these candidate IDs in rankings: {", ".join(candidate_ids)}.

Task:
{case.task}
{context_text}
Criteria:
{_format_criteria(case.criteria)}

Candidates:
{_format_candidates(case)}

Aggregate parsed rankings:
{aggregate_text}

Independent comparisons:
{comparisons_text}

Return plain markdown with these sections:

## Per-candidate assessment
Synthesize the assessment for each candidate ID.

## Tradeoff table
Provide a markdown table comparing candidate IDs across key tradeoffs.

## Ranked recommendation
Give a final ranked recommendation using candidate IDs only, and briefly explain why.

## Disagreement synthesis
Synthesize major disagreements, uncertainties, and cases where the ranking could change.

FINAL RANKING:
List candidate IDs from best to worst, one per line. Each line must contain only one candidate ID from the allowed list. Do not include titles, model names, bullets, numbers, or explanations in this section."""


def _format_candidates(case: CaseInput) -> str:
    return "\n\n".join(
        [
            f"Candidate ID: {candidate['id']}\nTitle: {candidate['title']}\nContent:\n{candidate['content']}"
            for candidate in case.candidates
        ]
    )


def _format_criteria(criteria: list[str]) -> str:
    if not criteria:
        return "- No explicit criteria provided; compare against the task."
    return "\n".join(f"- {criterion}" for criterion in criteria)
