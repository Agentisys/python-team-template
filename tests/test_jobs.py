import pytest

from team_utils.jobs import run_job


def test_success_returns_zero_and_logs_finished(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")
    assert run_job("unit_test_job", lambda: None) == 0
    messages = [r.getMessage() for r in caplog.records]
    assert "job started" in messages
    assert "job finished" in messages


def test_failure_returns_one_and_logs_traceback(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")

    def boom() -> None:
        raise ValueError("bad input")

    assert run_job("unit_test_job", boom) == 1
    failed = [r for r in caplog.records if r.getMessage() == "job failed"]
    assert failed, "expected a 'job failed' log record"
    assert failed[0].exc_info is not None


def test_writes_log_file(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    from team_utils.config import get_settings

    get_settings.cache_clear()
    run_job("file_job", lambda: None)
    assert (tmp_path / "file_job.log").read_text(encoding="utf-8").count("job finished") == 1
