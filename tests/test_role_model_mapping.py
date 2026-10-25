import pytest

import backend.war_room_runner as runner
from backend.schemas.case import CaseInput
from backend.schemas.preset import SeatDefinition
from backend.schemas.provider import ProviderResponse


@pytest.mark.asyncio
async def test_council_routes_each_role_to_its_assigned_model(tmp_path, monkeypatch):
    aliases_seen: list[str] = []

    async def fake_complete(alias, **kwargs):
        aliases_seen.append(alias)
        return ProviderResponse(
            provider="fake",
            model=alias,
            content="Recommendation with evidence.",
            requested_alias=alias,
            requested_provider="fake",
            requested_model=alias,
            actual_provider="fake",
            actual_model=alias,
        )

    monkeypatch.setattr(runner, "complete_with_alias", fake_complete)
    monkeypatch.setattr(runner, "save_run_record", lambda record: tmp_path / "run.json")

    case = CaseInput(
        case_type="council",
        task="Should we proceed?",
        seats=[
            SeatDefinition(id="a", name="Analyst", role_prompt="Analyze", model_alias="model-a"),
            SeatDefinition(id="b", name="Skeptic", role_prompt="Challenge", model_alias="model-b"),
            SeatDefinition(id="c", name="Operator", role_prompt="Execute", model_alias="model-c"),
        ],
        reviewer_aliases=["reviewer-model"],
        synthesizer_alias="synth-model",
        preset_snapshot={"id": "test-preset"},
    )

    record = await runner.run_war_room_case(case, run_id="run-test")

    assert aliases_seen[:3] == ["model-a", "model-b", "model-c"]
    assert aliases_seen[3:] == ["reviewer-model", "synth-model"]
    assert [item["alias"] for item in record.advisor_responses] == [
        "model-a",
        "model-b",
        "model-c",
    ]
    assert record.preset_snapshot == {"id": "test-preset"}
