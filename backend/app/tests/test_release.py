from datetime import datetime, timedelta, timezone
from app.engines.claim_lock import lock_payload
from app.engines.release import release_payload

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

def test_release_payload_clears_lock_and_stamps_deadline():
    p = release_payload(NOW, 3600)
    assert p["status"] == "released"
    assert p["claimer"] is None and p["claimed_at"] is None and p["expires_at"] is None
    assert p["cooldown_until"] == (NOW + timedelta(seconds=3600)).isoformat()

def test_deadline_uses_seconds_in_effect_at_release_instant():
    p1 = release_payload(NOW, 3600)
    p2 = release_payload(NOW, 60)
    assert p1["cooldown_until"] == (NOW + timedelta(hours=1)).isoformat()
    assert p2["cooldown_until"] == (NOW + timedelta(minutes=1)).isoformat()

def test_consecutive_releases_leave_single_deadline():
    # 同一愿望连续两次释放：行上只有一份截止，第二次整体覆盖第一次，
    # 不得出现交叉重叠的双截止。
    row = {"status": "claimed", "claimer": "alice", "cooldown_until": None}
    r1 = release_payload(NOW, 3600)
    row.update(r1)
    assert row["cooldown_until"] == r1["cooldown_until"]

    later = NOW + timedelta(hours=2)  # 第一次冷却结束后重新认领
    row.update(lock_payload("bob", later, 86400))
    assert row["cooldown_until"] is None  # 认领清掉旧截止

    r2 = release_payload(later + timedelta(hours=1), 3600)
    row.update(r2)
    assert row["cooldown_until"] == r2["cooldown_until"]
    assert row["cooldown_until"] != r1["cooldown_until"]
    assert "cooldown_until_2" not in row and list(row).count("cooldown_until") == 1

def test_zero_seconds_cooldown_is_immediately_over():
    p = release_payload(NOW, 0)
    assert p["cooldown_until"] == NOW.isoformat()
