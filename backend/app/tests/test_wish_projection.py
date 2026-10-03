from datetime import datetime, timedelta, timezone
from app.modules.wish_projection import project_wish, project_wishes

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

def row(**kw):
    base = {"id": 1, "title": "t", "note": "", "status": "released", "claimer": None,
            "claimed_at": None, "expires_at": None, "cooldown_until": None, "data_quality": "clean"}
    base.update(kw)
    return base

def test_projection_passes_row_deadline_through_verbatim():
    until = (NOW + timedelta(minutes=30)).isoformat()
    w = project_wish(row(cooldown_until=until), NOW)
    # 行截止是投影的唯一来源：原样透出，绝不按现行秒重算
    assert w["cooldown_until"] == until
    assert w["in_cooldown"] is True
    assert w["cooldown_remaining_seconds"] == 1800

def test_projection_does_not_recompute_from_current_seconds():
    # 旧行按当时 3600 秒写死截止；即便现行秒已改成 60，投影也不得改动行截止
    old_until = (NOW + timedelta(seconds=3600)).isoformat()
    w = project_wish(row(cooldown_until=old_until), NOW)
    assert w["cooldown_until"] == old_until
    assert w["cooldown_remaining_seconds"] == 3600

def test_projection_marks_expired_cooldown_inactive():
    until = (NOW - timedelta(seconds=5)).isoformat()
    w = project_wish(row(cooldown_until=until), NOW)
    assert w["cooldown_until"] == until  # 截止仍原样展示
    assert w["in_cooldown"] is False
    assert w["cooldown_remaining_seconds"] == 0

def test_fulfilled_row_has_no_cooldown():
    w = project_wish(row(status="fulfilled", cooldown_until=None), NOW)
    assert w["in_cooldown"] is False
    assert w["cooldown_remaining_seconds"] == 0

def test_projection_does_not_mutate_input_and_batches():
    rows = [row(id=1), row(id=2, cooldown_until=(NOW + timedelta(seconds=10)).isoformat())]
    out = project_wishes(rows, NOW)
    assert [w["id"] for w in out] == [1, 2]
    assert out[0]["in_cooldown"] is False and out[1]["in_cooldown"] is True
    assert "in_cooldown" not in rows[0]  # 原行未被污染
