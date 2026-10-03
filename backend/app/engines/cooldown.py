"""Cooldown determination for released wishes (冷却判定).

Pure functions over a row's stored ``cooldown_until`` timestamp. The
deadline is always read from the row itself — never recomputed from the
current ``cooldown_seconds`` setting — so changing the setting never
rewrites history.
"""
from datetime import datetime, timezone


def parse_ts(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def in_cooldown(cooldown_until: str | None, now: datetime) -> bool:
    """True while the row's stored cooldown deadline is still in the future."""
    if not cooldown_until:
        return False
    return parse_ts(cooldown_until) > now


def cooldown_remaining(cooldown_until: str | None, now: datetime) -> int:
    """Whole seconds left on the row's cooldown, floored at 0."""
    if not cooldown_until:
        return 0
    left = (parse_ts(cooldown_until) - now).total_seconds()
    return max(0, int(left))
