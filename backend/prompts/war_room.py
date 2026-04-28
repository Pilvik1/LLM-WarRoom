"""Prompt builders for War Room cases."""

from typing import Any

from ..schemas.case import CaseInput


INFERRED_CRITERIA = [
    "usefulness",
    "differentiation",
    "feasibility",
    "downside risk",
    "upside potential",
    "speed to validate",
    "next-step clarity",
]


ADVISORS = [
    {
        "name": "Contrarian",
        "description": (
            "Actively looks for what is wrong, missing, fragile, risky, or likely "
            "to fail. Not pessimistic for its own sake; the job is to catch "
            "failure modes and hidden downside."
        ),
    },
    {
        "name": "First Principles Thinker",
        "description": (
            "Strips the problem down to what is actually being solved. Challenges "
            "assumptions, reframes the question, and identifies if the user is "
            "asking the wrong question."
        ),
    },
    {
        "name": "Expansionist",
        "description": (
            "Looks for upside, leverage, adjacent opportunities, hidden potential, "
            "and how the idea could become bigger or more valuable if it works."
        ),
    },
    {
        "name": "Outsider",
        "description": (
            "Assumes no insider context. Looks at clarity, positioning, obvious "
            "confusion, missing explanation, and whether the idea makes sense to "
            "someone fresh."
        ),
    },
    {
        "name": "Executor",
        "description": (
            "Focuses on feasibility, sequencing, implementation, cost, time, "
            "operational friction, and the first concrete step."
        ),
    },
]


def build_framing_prompt(case: CaseInput) -> str:
    """Build an optional LLM framing prompt for a War Room case."""
    return f"""Convert this raw War Room input into a neutral framed question.

Include:
- core decision/question
- relevant context
- stakes
- constraints/criteria
- candidate artifact/options if provided
- missing context or assumptions

Do not add a recommendation at the framing stage.

Raw input:
{_format_case(case)}
"""


def build_deterministic_framed_question(case: CaseInput) -> str:
    """Build neutral framing without spending a model call."""
    sections = [
        ("Core decision/question", case.task),
        ("Relevant context", case.context or "No extra context provided. Advisors should state assumptions explicitly."),
        ("Stakes", case.stakes),
        ("Criteria" if case.criteria else "Inferred criteria", _format_criteria(case)),
        ("Candidate artifact", case.subject_text or None),
        ("Candidate options", _format_candidates(case) if case.candidates else None),
        (
            "Missing context or assumptions",
            "Advisors should identify missing context, state assumptions explicitly, and avoid pretending uncertain facts are known.",
        ),
    ]
    return "\n\n".join(
        f"## {title}\n{value.strip()}"
        for title, value in sections
        if value and value.strip()
    )


def build_advisor_prompt(
    case: CaseInput,
    framed_question: str,
    advisor: dict[str, str],
) -> str:
    """Build one independent advisor prompt."""
    return f"""You are the {advisor["name"]} advisor in a War Room.

Lens:
{advisor["description"]}

Framed question:
{framed_question}

Your job:
- Lean fully into this perspective.
- Be direct, specific, and non-generic.
- If criteria were inferred, use them lightly, not mechanically.
- Explicitly state assumptions when context is missing.
- Avoid generic startup advice.
- Keep the response concise and distinct from the other advisor lenses.
- Avoid hedging.
- Do not write a preamble.
- Target 150-300 words.

Produce the most useful pressure-test from this lens.
"""


def build_peer_review_prompt(
    case: CaseInput,
    framed_question: str,
    anonymized_responses: list[dict[str, str]],
) -> str:
    """Build the anonymized War Room peer-review prompt."""
    responses = "\n\n".join(
        f"{item['label']}:\n{item['response']}" for item in anonymized_responses
    )
    return f"""Review these anonymized War Room advisor responses.

Framed question:
{framed_question}

Responses:
{responses}

Answer only these:
1. Which response is strongest and why?
2. Which response has the biggest blind spot and what is it?
3. What did all responses miss?

Refer only to Response A/B/C/D/E labels. Do not rank by model names, advisor names, provider names, or aliases. Keep under 200 words if possible.
"""


def build_verdict_prompt(
    case: CaseInput,
    framed_question: str,
    advisor_responses: list[dict[str, Any]],
    peer_reviews: list[dict[str, Any]],
) -> str:
    """Build the final War Room verdict prompt."""
    advisors = "\n\n".join(
        f"{item.get('advisor_name')}:\n{item.get('response', '')}"
        for item in advisor_responses
    )
    reviews = "\n\n".join(
        f"{item.get('id', 'peer_review')}:\n{item.get('review', '')}"
        for item in peer_reviews
    )
    return f"""Synthesize this War Room into a final verdict.

Framed question:
{framed_question}

Advisor responses:
{advisors}

Peer reviews:
{reviews or "No peer reviews were collected."}

Use this exact output structure:
## Where the War Room Agrees
## Where the War Room Clashes
## Blind Spots the War Room Caught
## The Recommendation
## The One Thing to Do First

Instructions:
- Be clear and actionable.
- Do not smooth over genuine disagreement.
- Give a real recommendation, not vague "it depends."
- The chairman/synthesizer may disagree with the majority if the reasoning supports it.
- The one thing to do first must be a single concrete next action.
"""


def _format_case(case: CaseInput) -> str:
    return "\n\n".join(
        item
        for item in [
            f"Task:\n{case.task}",
            f"Context:\n{case.context}" if case.context else "",
            f"Stakes:\n{case.stakes}" if case.stakes else "",
            f"Criteria:\n{_format_criteria(case)}",
            f"Candidate artifact:\n{case.subject_text}" if case.subject_text else "",
            f"Candidate options:\n{_format_candidates(case)}" if case.candidates else "",
        ]
        if item
    )


def _format_criteria(case: CaseInput) -> str:
    if not case.criteria:
        return "\n".join(f"- {item}" for item in INFERRED_CRITERIA)
    return "\n".join(f"- {item}" for item in case.criteria)


def _format_candidates(case: CaseInput) -> str:
    return "\n\n".join(
        f"Candidate {candidate.get('id')} - {candidate.get('title')}\n{candidate.get('content')}"
        for candidate in case.candidates
    )
