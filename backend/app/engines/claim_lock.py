"""Claim mutex + TTL release + post-release cooldown for wishes."""
from datetime import datetime, timedelta, timezone

def parse_ts(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def cooldown_deadline(now: datetime, cooldown_seconds: int) -> str:
    """The stored-per-row cooldown deadline, computed once at release time."""
    return (now + timedelta(seconds=cooldown_seconds)).isoformat()

def in_cooldown(cooldown_until: str | None, now: datetime) -> bool:
    """Cooldown decision: only the row's stored deadline counts, never settings."""
    return bool(cooldown_until) and parse_ts(cooldown_until) > now

def claim_allowed(status: str, claimer: str | None, now: datetime, expires_at: str | None,
                  cooldown_until: str | None = None) -> dict:
    """Only open wishes (or expired locks) outside cooldown can be claimed."""
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
    exp = now + timedelta(seconds=ttl_seconds)
    return {
        "status": "claimed",
        "claimer": claimer,
        "claimed_at": now.isoformat(),
        "expires_at": exp.isoformat(),
        # claiming clears any prior cooldown deadline so a row never carries two
        "cooldown_until": None,
    }

def release_payload(now: datetime, cooldown_seconds: int, status: str = "released") -> dict:
    """Every release (manual or TTL) stamps the row's cooldown deadline once."""
    return {
        "status": status,
        "claimer": None,
        "claimed_at": None,
        "expires_at": None,
        "cooldown_until": cooldown_deadline(now, cooldown_seconds),
    }

def release_if_expired(status: str, expires_at: str | None, now: datetime,
                       cooldown_seconds: int = 0) -> dict | None:
    if status != "claimed" or not expires_at:
        return None
    if parse_ts(expires_at) <= now:
        return release_payload(now, cooldown_seconds, status="open")
    return None
