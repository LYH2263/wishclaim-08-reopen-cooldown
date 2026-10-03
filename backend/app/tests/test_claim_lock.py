from datetime import datetime, timedelta, timezone
from app.engines.claim_lock import claim_allowed, lock_payload, release_if_expired

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

def test_mutex_blocks_second_claimer():
    r = claim_allowed("claimed", "alice", NOW, (NOW + timedelta(hours=1)).isoformat())
    assert r["ok"] is False and r["reason"] == "locked"

def test_ttl_allows_reclaim():
    r = claim_allowed("claimed", "alice", NOW, (NOW - timedelta(minutes=1)).isoformat())
    assert r["ok"] is True

def test_lock_payload_sets_expiry():
    p = lock_payload("bob", NOW, 3600)
    assert p["status"] == "claimed" and p["claimer"] == "bob"
    assert release_if_expired("claimed", p["expires_at"], NOW) is None

def test_cooldown_blocks_claim():
    until = (NOW + timedelta(minutes=5)).isoformat()
    r = claim_allowed("released", None, NOW, None, until)
    assert r["ok"] is False and r["reason"] == "cooldown"

def test_claim_allowed_after_cooldown_ends():
    until = (NOW - timedelta(seconds=1)).isoformat()
    r = claim_allowed("released", None, NOW, None, until)
    assert r["ok"] is True

def test_fulfilled_never_claimable_even_without_cooldown():
    r = claim_allowed("fulfilled", "alice", NOW, None, None)
    assert r["ok"] is False and r["reason"] == "already_fulfilled"

def test_lock_payload_clears_cooldown():
    p = lock_payload("bob", NOW, 3600)
    assert p["cooldown_until"] is None

def test_ttl_release_enters_cooldown():
    p = release_if_expired("claimed", (NOW - timedelta(seconds=1)).isoformat(), NOW, 120)
    assert p["status"] == "released"
    assert p["claimer"] is None and p["expires_at"] is None
    # 截止从释放瞬间（now）起算，而非从过期时刻起算
    assert p["cooldown_until"] == (NOW + timedelta(seconds=120)).isoformat()

def test_ttl_release_default_zero_cooldown():
    p = release_if_expired("claimed", (NOW - timedelta(seconds=1)).isoformat(), NOW)
    assert p["status"] == "released"
    assert p["cooldown_until"] == NOW.isoformat()
