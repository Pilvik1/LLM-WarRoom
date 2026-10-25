from backend.council import calculate_aggregate_rankings, parse_ranking_from_text


def test_parse_ranking_accepts_only_known_labels():
    text = "Analysis\nFINAL RANKING:\nResponse B\nResponse A\nResponse Z"
    assert parse_ranking_from_text(text, ["Response A", "Response B"]) == [
        "Response B",
        "Response A",
    ]


def test_aggregate_rankings_average_valid_votes():
    rankings = [
        {"parsed_ranking": ["Response A", "Response B"]},
        {"parsed_ranking": ["Response B", "Response A"]},
    ]
    result = calculate_aggregate_rankings(
        rankings,
        {"Response A": "Model A", "Response B": "Model B"},
    )
    assert [item["average_rank"] for item in result] == [1.5, 1.5]
