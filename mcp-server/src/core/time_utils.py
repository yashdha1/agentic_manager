"""Global time strategy for all mock data and tool operations.

All timestamps in this project use UTC and the canonical format: YYYY-MM-DD HH:MM:SS.

- Use ``now()`` in tools wherever a reference to the current time is needed
  (e.g., computing lookback windows for DB queries).
- Use ``random_past()`` in seeders and dataset generators to produce realistic
  mock timestamps anchored to the recent past.
"""

import random
from datetime import UTC, datetime, timedelta

FMT = "%Y-%m-%d %H:%M:%S"


def now() -> datetime:
    """Return the current UTC datetime.

    Returns:
        Timezone-aware UTC datetime representing the current instant.
    """
    return datetime.now(UTC)


def random_past(days: int = 30) -> datetime:
    """Return a random UTC datetime within the last *days* days.

    The result is sampled uniformly over the window [now - days, now],
    at one-second granularity.

    Args:
        days: Window size in days. Defaults to 30.

    Returns:
        Timezone-aware UTC datetime somewhere in the past *days* days.
    """
    offset = random.randint(0, days * 24 * 60 * 60)
    return datetime.now(UTC) - timedelta(seconds=offset)
