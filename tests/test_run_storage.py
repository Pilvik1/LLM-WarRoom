import pytest

from backend.run_storage import (
    list_run_records,
    load_run_record,
    save_decision_record,
    save_run_record,
)
from backend.schemas.case import CaseInput
from backend.schemas.run import RunRecord
import backend.run_storage as run_storage


def test_run_record_survives_reload(tmp_path, monkeypatch):
    monkeypatch.setattr(run_storage, "RUNS_DIR", tmp_path / "runs")
    record = RunRecord(
        run_id="run-1",
        case_id="case-1",
        case_type="ask",
        input=CaseInput(case_type="ask", task="test task"),
        status="completed",
        created_at="2026-10-25T20:00:00",
        completed_at="2026-10-25T20:00:01",
        synthesis={"response": "answer"},
    )

    path = save_run_record(record)
    restored = load_run_record("run-1")

    assert path.exists()
    assert restored["outputs"]["synthesis"]["response"] == "answer"
    assert restored["artifact_paths"]["summary_md"].endswith("summary.md")


def test_run_history_is_newest_first_and_preserves_preset_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(run_storage, "RUNS_DIR", tmp_path / "runs")
    for index in range(2):
        save_run_record(
            RunRecord(
                run_id=f"run-{index}",
                case_type="council",
                workflow_type="council",
                input=CaseInput(
                    case_type="council",
                    task=f"task {index}",
                    preset_id="custom-council",
                ),
                status="completed",
                created_at=f"2026-10-25T20:00:0{index}+00:00",
                preset_snapshot={"id": "custom-council", "name": "Custom Council"},
            )
        )

    history = list_run_records()

    assert [item["run_id"] for item in history] == ["run-1", "run-0"]
    assert history[0]["preset_name"] == "Custom Council"


def test_run_id_cannot_escape_run_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(run_storage, "RUNS_DIR", tmp_path / "runs")
    with pytest.raises(ValueError, match="Invalid run_id"):
        save_run_record(
            RunRecord(
                run_id="../../outside",
                case_type="ask",
                input=CaseInput(case_type="ask", task="test"),
                status="running",
                created_at="2026-10-25T20:00:00+00:00",
            )
        )


def test_decision_run_id_cannot_escape_run_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(run_storage, "RUNS_DIR", tmp_path / "runs")
    with pytest.raises(ValueError, match="Invalid run_id"):
        save_decision_record("../../outside", {"decision": "GO"})
