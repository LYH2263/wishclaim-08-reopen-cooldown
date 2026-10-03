from datetime import datetime, timedelta, timezone
from app.engines.cooldown import in_cooldown, cooldown_remaining, parse_ts

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

def test_no_deadline_means_no_cooldown():
    assert in_cooldown(None, NOW) is False
    assert cooldown_remaining(None, NOW) == 0

def test_future_deadline_is_active():
    until = (NOW + timedelta(minutes=10)).isoformat()
    assert in_cooldown(until, NOW) is True
    assert cooldown_remaining(until, NOW) == 600

def test_past_deadline_is_over():
    until = (NOW - timedelta(seconds=1)).isoformat()
    assert in_cooldown(until, NOW) is False
    assert cooldown_remaining(until, NOW) == 0

def test_deadline_exactly_now_is_over():
    assert in_cooldown(NOW.isoformat(), NOW) is False

def test_parse_ts_accepts_z_and_naive():
    a = parse_ts("2026-01-01T12:00:00Z")
    b = parse_ts("2026-01-01T12:00:00")
    assert a == b == NOW
