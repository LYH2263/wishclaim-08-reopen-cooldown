"""Release payload builder (释放写截止).

Both the manual release endpoint and the TTL sweep funnel through
``release_payload`` so every release — manual or automatic — stamps the
row with exactly one ``cooldown_until`` deadline, computed from the
cooldown seconds in effect at the release instant. A later release
overwrites the previous deadline wholesale, so a row never carries two
overlapping cooldowns.
"""
from datetime import datetime, timedelta


def release_payload(now: datetime, cooldown_seconds: int) -> dict:
    """Columns to write when a claim is released.

    Clears the lock fields and sets ``cooldown_until = now + cooldown_seconds``.
    With ``cooldown_seconds <= 0`` the deadline lands at/before ``now`` and
    the cooldown is immediately over.
    """
    return {
        "status": "released",
        "claimer": None,
        "claimed_at": None,
        "expires_at": None,
        "cooldown_until": (now + timedelta(seconds=cooldown_seconds)).isoformat(),
    }
