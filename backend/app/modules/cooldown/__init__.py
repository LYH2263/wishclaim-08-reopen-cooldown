"""Cooldown projection: what wall cards / detail / rules display.

Two separate sources, never mixed:
- a row's deadline comes only from that row's stored `cooldown_until`
  (stamped at release time); it is never recomputed from settings;
- the current cooldown seconds come only from the `settings` table
  and appear on the rules page, not on any row.
"""
from app.engines.claim_lock import in_cooldown, parse_ts

def project_row(row: dict, now) -> dict:
    """Attach display fields sourced solely from the row's stored deadline."""
    out = dict(row)
    until = row.get("cooldown_until")
    out["cooldown_active"] = in_cooldown(until, now)
    out["cooldown_remaining_seconds"] = (
        max(0, int((parse_ts(until) - now).total_seconds())) if until else 0
    )
    return out

def project_rows(rows: list[dict], now) -> list[dict]:
    return [project_row(r, now) for r in rows]

def rules_projection(cooldown_seconds: int) -> dict:
    """Rules-page entries: the *current* setting, independent of any row."""
    return {
        "cooldown": "释放后进入冷却，冷却期内不可认领，冷却结束可再次认领",
        "cooldown_seconds": cooldown_seconds,
    }
