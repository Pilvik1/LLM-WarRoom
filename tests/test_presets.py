import pytest

import backend.preset_storage as preset_storage
from backend.schemas.preset import CouncilPreset, SeatDefinition


def _custom_preset() -> CouncilPreset:
    return CouncilPreset(
        id="my-council",
        name="My Council",
        workflow_type="council",
        seats=[
            SeatDefinition(
                id="skeptic",
                name="Skeptic",
                role_prompt="Find the strongest reason this could fail.",
                model_alias="reasoner",
            )
        ],
        reviewer_aliases=["reviewer"],
        synthesizer_alias="synthesizer",
    )


def test_custom_preset_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(preset_storage, "PRESETS_DIR", tmp_path / "presets")

    stored = preset_storage.save_preset(_custom_preset())
    restored = preset_storage.get_preset("my-council")

    assert stored.built_in is False
    assert restored is not None
    assert restored.seats[0].role_prompt.startswith("Find the strongest")
    assert restored.seats[0].model_alias == "reasoner"


def test_built_in_preset_cannot_be_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(preset_storage, "PRESETS_DIR", tmp_path / "presets")
    preset = _custom_preset().model_copy(update={"id": "general-council"})

    with pytest.raises(ValueError, match="built-in presets cannot be overwritten"):
        preset_storage.save_preset(preset)
