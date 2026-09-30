"""Sliding-window rate limiter, thread-safe.

Beschermt de Gemini-key op een publieke URL: per sessie en globaal per proces.
Op Cloud Run geldt de globale limiet per instantie (zie DEPLOY.md).
"""
from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable


class SlidingWindowLimiter:
    def __init__(self, max_calls: int, window_s: float, clock: Callable[[], float] = time.monotonic) -> None:
        if max_calls <= 0 or window_s <= 0:
            raise ValueError("max_calls en window_s moeten groter dan 0 zijn")
        self.max_calls = max_calls
        self.window_s = window_s
        self._clock = clock
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        while self._calls and now - self._calls[0] >= self.window_s:
            self._calls.popleft()

    def _check(self, now: float) -> tuple[bool, int]:
        self._prune(now)
        if len(self._calls) < self.max_calls:
            return True, 0
        return False, max(1, math.ceil(self.window_s - (now - self._calls[0])))

    def peek(self) -> tuple[bool, int]:
        """Zou een call nu mogen? Verbruikt niets."""
        with self._lock:
            return self._check(self._clock())

    def try_acquire(self) -> tuple[bool, int]:
        """(toegelaten, retry_after_s). Een toegelaten call telt mee."""
        with self._lock:
            now = self._clock()
            ok, retry = self._check(now)
            if ok:
                self._calls.append(now)
            return ok, retry


def acquire_both(session: SlidingWindowLimiter, global_: SlidingWindowLimiter) -> tuple[bool, int]:
    """Beide limieten moeten toelaten. Een geweigerde call verbruikt van geen van beide.

    De sessie wordt eerst gecheckt, zodat één gebruiker na zijn eigen limiet geen
    globaal budget meer opsoupeert.
    """
    ok, retry = session.peek()
    if not ok:
        return False, retry
    ok, retry = global_.try_acquire()
    if not ok:
        return False, retry
    session.try_acquire()
    return True, 0
