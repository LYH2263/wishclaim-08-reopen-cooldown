"""Claim mutex + TTL release for wishes."""
from datetime import datetime, timedelta

from app.engines.cooldown import in_cooldown, parse_ts  # noqa: F401  (parse_ts re-exported)
from app.engines.release import release_payload


def claim_allowed(status: str, claimer: str | None, now: datetime, expires_at: str | None,
                  cooldown_until: str | None = None) -> dict:
    """Only open wishes (or expired locks) can be claimed; cooldown blocks."""
    if status == "fulfilled":
        return {"ok": False, "reason": "already_fulfilled"}
    if in_cooldown(cooldown_until, now):
        return {"ok": False, "reason": "cooldown"}
    if status == "claimed" and claimer:
        if expires_at and parse_ts(expires_at) <= now:
            return {"ok": True, "reason": "ttl_expired_reclaim"}
        return {"ok": False, "reason": "locked"}
    if status in ("open", "released"):
        return {"ok": True, "reason": ""}
    return {"ok": False, "reason": "bad_status"}


def lock_payload(claimer: str, now: datetime, ttl_seconds: int) -> dict:
    """A fresh claim also clears any stale cooldown deadline, so a claimed
    row never shows a leftover cooldown_until from a previous release."""
    exp = now + timedelta(seconds=ttl_seconds)
    return {
        "status": "claimed",
        "claimer": claimer,
        "claimed_at": now.isoformat(),
        "expires_at": exp.isoformat(),
        "cooldown_until": None,
    }


def release_if_expired(status: str, expires_at: str | None, now: datetime,
                       cooldown_seconds: int = 0) -> dict | None:
    """TTL auto-release enters cooldown exactly like a manual release."""
    if status != "claimed" or not expires_at:
        return None
    if parse_ts(expires_at) <= now:
        return release_payload(now, cooldown_seconds)
    return None
