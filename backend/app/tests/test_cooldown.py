from datetime import datetime, timedelta, timezone
from app.engines.claim_lock import (
    claim_allowed, lock_payload, release_payload, release_if_expired,
    cooldown_deadline, in_cooldown, parse_ts,
)
from app.modules.cooldown import project_row, rules_projection

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
CD = 600  # cooldown seconds

# --- 冷却判定 ---

def test_claim_blocked_during_cooldown_open():
    until = cooldown_deadline(NOW, CD)
    r = claim_allowed("open", None, NOW + timedelta(seconds=1), None, until)
    assert r["ok"] is False and r["reason"] == "cooldown"

def test_claim_blocked_during_cooldown_released():
    until = cooldown_deadline(NOW, CD)
    r = claim_allowed("released", None, NOW + timedelta(seconds=CD - 1), None, until)
    assert r["ok"] is False and r["reason"] == "cooldown"

def test_claim_allowed_after_cooldown_ends():
    until = cooldown_deadline(NOW, CD)
    r = claim_allowed("released", None, NOW + timedelta(seconds=CD), None, until)
    assert r["ok"] is True

def test_claim_allowed_without_cooldown():
    assert claim_allowed("open", None, NOW, None, None)["ok"] is True

def test_fulfilled_never_claimable_even_with_cooldown_value():
    until = cooldown_deadline(NOW, CD)
    r = claim_allowed("fulfilled", "alice", NOW, None, until)
    assert r["ok"] is False and r["reason"] == "already_fulfilled"

def test_in_cooldown_boundary():
    until = cooldown_deadline(NOW, CD)
    assert in_cooldown(until, NOW + timedelta(seconds=CD - 1)) is True
    assert in_cooldown(until, NOW + timedelta(seconds=CD)) is False
    assert in_cooldown(None, NOW) is False

# --- 释放写截止 ---

def test_manual_release_stamps_deadline_from_release_moment():
    p = release_payload(NOW, CD, status="released")
    assert p["status"] == "released"
    assert p["cooldown_until"] == (NOW + timedelta(seconds=CD)).isoformat()
    assert p["claimer"] is None and p["claimed_at"] is None and p["expires_at"] is None

def test_ttl_release_also_stamps_deadline():
    expired = (NOW - timedelta(seconds=1)).isoformat()
    p = release_if_expired("claimed", expired, NOW, CD)
    assert p["status"] == "open"
    assert p["cooldown_until"] == (NOW + timedelta(seconds=CD)).isoformat()

def test_ttl_release_not_due_writes_nothing():
    future = (NOW + timedelta(hours=1)).isoformat()
    assert release_if_expired("claimed", future, NOW, CD) is None

def test_claim_clears_stored_deadline():
    p = lock_payload("bob", NOW, 3600)
    assert p["cooldown_until"] is None

def test_consecutive_releases_single_fresh_deadline():
    # first release stamps D1; reclaim clears it; second release stamps D2
    # from the second release moment — one deadline at any time, never two
    r1 = release_payload(NOW, CD)
    t1 = NOW + timedelta(seconds=CD + 1)
    claim = lock_payload("alice", t1, 3600)
    assert claim["cooldown_until"] is None  # D1 gone on reclaim
    t2 = t1 + timedelta(seconds=30)
    r2 = release_payload(t2, CD)
    assert r2["cooldown_until"] == (t2 + timedelta(seconds=CD)).isoformat()
    assert parse_ts(r2["cooldown_until"]) > parse_ts(r1["cooldown_until"])

# --- 投影分源 ---

def test_projection_uses_row_deadline_not_current_setting():
    # row stamped with old 600s setting; settings later changed to 10s —
    # projection must show the row's stored deadline, never recompute
    stored = cooldown_deadline(NOW, 600)
    row = {"id": 1, "status": "released", "cooldown_until": stored}
    out = project_row(row, NOW + timedelta(seconds=30))
    assert out["cooldown_until"] == stored
    assert out["cooldown_active"] is True
    assert out["cooldown_remaining_seconds"] == 570

def test_projection_expired_deadline_inactive_but_preserved():
    stored = cooldown_deadline(NOW, CD)
    row = {"id": 1, "status": "open", "cooldown_until": stored}
    out = project_row(row, NOW + timedelta(seconds=CD + 5))
    assert out["cooldown_until"] == stored
    assert out["cooldown_active"] is False
    assert out["cooldown_remaining_seconds"] == 0

def test_projection_no_deadline():
    out = project_row({"id": 1, "status": "open", "cooldown_until": None}, NOW)
    assert out["cooldown_active"] is False and out["cooldown_remaining_seconds"] == 0

def test_rules_projection_lists_current_seconds():
    r = rules_projection(600)
    assert r["cooldown_seconds"] == 600 and "cooldown" in r
