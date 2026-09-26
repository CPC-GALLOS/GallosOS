"""Interrupted transitions remain latched after daemon restart."""

from daemon.src.transition_record import read_record, write_record


def test_pending_transition_recovers_as_error(tmp_path, monkeypatch):
    monkeypatch.setattr("daemon.src.transition_record.RECORD", tmp_path / "state.json")
    write_record("Default", "Contest", "pending", "")
    record = read_record()
    assert record == {
        "mode": "Default",
        "target_mode": "Contest",
        "transition_status": "error",
        "last_error": "Transition interrupted by daemon restart",
    }
