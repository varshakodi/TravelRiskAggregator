"""
Tiny in-process TTL (time-to-live) cache.

Why: external APIs have request budgets (AviationStack free tier is ~100
requests/MONTH; OpenSky rations anonymous credits). A TTL cache trades
freshness for budget: remember each answer for `seconds`, serve the copy
until it goes stale. Pick the TTL from the data's own tempo — aircraft
positions change in seconds, airline schedules barely change all day.

In-process on purpose: one dict in this server's memory. The moment there
are multiple server instances they'd each hold their own copy, and you'd
reach for a shared cache (Redis) — a deliberate non-problem at this scale.
"""
import functools
import time


def ttl_cache(seconds: float):
    """Memoize a function's return value per-arguments for `seconds`."""
    def decorator(fn):
        store: dict = {}  # key -> (expires_at_monotonic, value)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            hit = store.get(key)
            if hit and hit[0] > now:
                return hit[1]
            value = fn(*args, **kwargs)
            store[key] = (now + seconds, value)
            return value

        wrapper.cache_clear = store.clear  # handy for tests
        return wrapper
    return decorator
