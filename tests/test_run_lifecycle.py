import asyncio

import pytest

import backend.main as main
import backend.run_storage as run_storage
from backend.schemas.case import CaseInput


@pytest.mark.asyncio
async def test_background_run_can_be_cancelled(tmp_path, monkeypatch):
    monkeypatch.setattr(run_storage, "RUNS_DIR", tmp_path / "runs")
    main._RUN_TASKS.clear()

    async def wait_forever(case_input, run_id=None):
        await asyncio.Event().wait()

    monkeypatch.setattr(main, "run_war_room_case", wait_forever)
    case = CaseInput(
        case_type="council",
        task="test cancellation",
        preset_snapshot={"id": "test"},
    )

    started = main._schedule_run(case, "council")
    cancelled = await main.cancel_run(started["run_id"])

    assert started["status"] == "running"
    assert cancelled["status"] == "cancelled"
    assert cancelled["stage_events"][-1] == {"stage": "run", "status": "cancelled"}


@pytest.mark.asyncio
async def test_retry_uses_prior_input_and_creates_new_run(tmp_path, monkeypatch):
    monkeypatch.setattr(run_storage, "RUNS_DIR", tmp_path / "runs")
    main._RUN_TASKS.clear()

    async def wait_forever(case_input, run_id=None):
        await asyncio.Event().wait()

    monkeypatch.setattr(main, "run_ask_case", wait_forever)
    original = main._schedule_run(CaseInput(case_type="ask", task="retry me"), "ask")
    await main.cancel_run(original["run_id"])

    retried = await main.retry_run(original["run_id"])

    assert retried["run_id"] != original["run_id"]
    assert retried["input"]["task"] == "retry me"
    assert retried["status"] == "running"
    await main.cancel_run(retried["run_id"])
