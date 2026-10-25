from backend.run_storage import load_run_record, save_run_record
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
