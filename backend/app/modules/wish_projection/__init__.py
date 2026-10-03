"""Wish view projection (投影).

Shapes a wishes-table row for API consumers (wall cards, detail page).
``cooldown_until`` is passed through verbatim from the row — the stored
deadline is the only source of truth for that row; the current
``cooldown_seconds`` setting is never applied to existing rows here.
``now`` is only used to derive display flags (in_cooldown / remaining).
"""
from datetime import datetime

from app.engines.cooldown import cooldown_remaining, in_cooldown


def project_wish(row: dict, now: datetime) -> dict:
    w = dict(row)
    until = w.get("cooldown_until")
    w["in_cooldown"] = in_cooldown(until, now)
    w["cooldown_remaining_seconds"] = cooldown_remaining(until, now)
    return w


def project_wishes(rows: list[dict], now: datetime) -> list[dict]:
    return [project_wish(r, now) for r in rows]
