"""3-stage WarRoom orchestration.

The current runtime still follows the inherited llm-council ask flow:
independent responses, anonymized peer ranking, and chairman synthesis.
"""

from typing import List, Dict, Any, Tuple

from .config import (
    RESPONDENT_MODEL_ALIASES,
    REVIEWER_MODEL_ALIASES,
    SYNTHESIZER_MODEL_ALIAS,
    TITLE_MODEL_ALIAS,
)
from .providers.model_registry import (
    complete_aliases_parallel,
    complete_with_alias,
    display_model,
    display_name_for_alias,
    response_metadata,
    technical_name_for,
)


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    responses = await complete_aliases_parallel(
        RESPONDENT_MODEL_ALIASES,
        user_prompt=user_query,
    )

    # Format results
    stage1_results = []
    for alias, response in responses.items():
        content = response.content.strip()
        if content or response.error:
            metadata = response_metadata(response)
            stage1_results.append({
                "id": f"resp_{len(stage1_results) + 1:03d}",
                "response_id": f"resp_{len(stage1_results) + 1:03d}",
                "alias": alias,
                "requested_alias": metadata.get("requested_alias"),
                "requested_provider": metadata.get("requested_provider"),
                "requested_model": metadata.get("requested_model"),
                "actual_provider": metadata.get("actual_provider"),
                "actual_model": metadata.get("actual_model"),
                "display_name": metadata.get("display_name"),
                "technical_name": metadata.get("technical_name"),
                "fallback_used": metadata.get("fallback_used"),
                "fallback_reason": metadata.get("fallback_reason"),
                "model": display_model(response),
                "response": content or f"Error: {response.error}",
                "metadata": metadata,
            })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...
    valid_labels = [f"Response {label}" for label in labels]

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result.get('display_name') or result['model']
        for label, result in zip(labels, stage1_results)
    }
    label_metadata = {
        f"Response {label}": {
            **result.get("metadata", {}),
            "anonymous_label": f"Response {label}",
            "response_id": result.get("response_id"),
        }
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])
    example_ranking = "\n".join(valid_labels)

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst, one per line
- Each line should contain ONLY one of these exact labels: {", ".join(valid_labels)}
- Do not add any other text or explanations in the ranking section
- Do not use provider names, model names, aliases, or words like "free" as ranking labels

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...

FINAL RANKING:
{example_ranking}

Now provide your evaluation and ranking:"""

    responses = await complete_aliases_parallel(
        REVIEWER_MODEL_ALIASES,
        user_prompt=ranking_prompt,
    )

    # Format results
    stage2_results = []
    for alias, response in responses.items():
        full_text = response.content.strip()
        if full_text or response.error:
            metadata = response_metadata(response)
            parsed = parse_ranking_from_text(full_text, valid_labels)
            stage2_results.append({
                "id": alias,
                "alias": alias,
                "display_name": metadata.get("display_name"),
                "technical_name": metadata.get("technical_name"),
                "model": display_model(response),
                "ranking": full_text or f"Error: {response.error}",
                "parsed_ranking": parsed,
                "metadata": metadata,
            })

    return stage2_results, label_to_model, label_metadata


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"{result.get('anonymous_label', result.get('response_id', 'Response'))}: {result.get('display_name', result['model'])}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Reviewer: {result.get('display_name', result['model'])}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    # Query the chairman model
    response = await complete_with_alias(
        SYNTHESIZER_MODEL_ALIAS,
        user_prompt=chairman_prompt,
    )

    if response.error or not response.content.strip():
        # Fallback if chairman fails
        return {
            **_identity_fields(response),
            "model": display_model(response),
            "response": f"Error: Unable to generate final synthesis. {response.error or 'Empty response'}",
            "metadata": response_metadata(response),
        }

    return {
        **_identity_fields(response),
        "model": display_model(response),
        "response": response.content,
        "metadata": response_metadata(response),
    }


def parse_ranking_from_text(
    ranking_text: str,
    valid_labels: List[str] | None = None,
) -> List[str] | None:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order, or None if parsing fails
    """
    import re

    if "FINAL RANKING:" not in ranking_text:
        return None

    valid_set = set(valid_labels or [])
    ranking_section = ranking_text.split("FINAL RANKING:", 1)[1]
    matches = re.findall(r'^\s*(?:\d+\.\s*)?(Response [A-Z])\s*$', ranking_section, re.MULTILINE)
    filtered = [match for match in matches if not valid_set or match in valid_set]
    if not filtered:
        return None
    return filtered


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
    label_metadata: Dict[str, Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    label_positions = defaultdict(list)

    for ranking in stage2_results:
        parsed_ranking = ranking.get('parsed_ranking')
        if not parsed_ranking:
            continue

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                label_positions[label].append(position)

    # Calculate average position for each model
    aggregate = []
    label_metadata = label_metadata or {}
    for label, positions in label_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            metadata = label_metadata.get(label, {})
            aggregate.append({
                "label": label,
                "model": label_to_model[label],
                "display_name": metadata.get("display_name") or label_to_model[label],
                "technical_name": metadata.get("technical_name"),
                "requested_alias": metadata.get("requested_alias"),
                "requested_technical_name": metadata.get("requested_technical_name"),
                "actual_alias": metadata.get("actual_alias"),
                "fallback_used": metadata.get("fallback_used"),
                "fallback_reason": metadata.get("fallback_reason"),
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


def _identity_fields(response) -> Dict[str, Any]:
    metadata = response_metadata(response)
    return {
        "display_name": metadata.get("display_name"),
        "technical_name": metadata.get("technical_name"),
        "requested_alias": metadata.get("requested_alias"),
        "requested_provider": metadata.get("requested_provider"),
        "requested_model": metadata.get("requested_model"),
        "actual_provider": metadata.get("actual_provider"),
        "actual_model": metadata.get("actual_model"),
        "fallback_used": metadata.get("fallback_used"),
        "fallback_reason": metadata.get("fallback_reason"),
    }


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    response = await complete_with_alias(
        TITLE_MODEL_ALIAS,
        user_prompt=title_prompt,
        max_tokens=50,
    )

    if response.error or not response.content.strip():
        # Fallback to a generic title
        return "New Conversation"

    title = response.content.strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model, label_metadata = await stage2_collect_rankings(user_query, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(
        stage2_results,
        label_to_model,
        label_metadata,
    )

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "label_metadata": label_metadata,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata
