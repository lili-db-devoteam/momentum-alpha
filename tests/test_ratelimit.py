import threading

import pytest

from engine.ratelimit import SlidingWindowLimiter, acquire_both


class FakeClock:
    def __init__(self):
        self.t = 1_000.0

    def __call__(self):
        return self.t


def test_allows_up_to_max_then_blocks():
    lim = SlidingWindowLimiter(3, 60, clock=FakeClock())
    assert [lim.try_acquire()[0] for _ in range(3)] == [True, True, True]
    assert lim.try_acquire() == (False, 60)


def test_window_slides():
    clock = FakeClock()
    lim = SlidingWindowLimiter(1, 60, clock=clock)
    assert lim.try_acquire() == (True, 0)
    clock.t += 59
    assert lim.try_acquire() == (False, 1)
    clock.t += 1
    assert lim.try_acquire() == (True, 0)


def test_retry_after_counts_from_oldest_call():
    clock = FakeClock()
    lim = SlidingWindowLimiter(2, 60, clock=clock)
    lim.try_acquire()
    clock.t += 30
    lim.try_acquire()
    clock.t += 10
    assert lim.try_acquire() == (False, 20)


def test_peek_does_not_consume():
    lim = SlidingWindowLimiter(1, 60, clock=FakeClock())
    assert lim.peek() == (True, 0)
    assert lim.peek() == (True, 0)
    assert lim.try_acquire() == (True, 0)
    assert lim.peek() == (False, 60)


@pytest.mark.parametrize("max_calls,window", [(0, 60), (1, 0), (-1, 60)])
def test_invalid_arguments(max_calls, window):
    with pytest.raises(ValueError):
        SlidingWindowLimiter(max_calls, window)


def test_thread_safe_never_exceeds_max():
    lim = SlidingWindowLimiter(50, 3_600)
    allowed = []
    lock = threading.Lock()

    def worker():
        for _ in range(20):
            ok, _ = lim.try_acquire()
            if ok:
                with lock:
                    allowed.append(1)

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(allowed) == 50


def test_session_limit_does_not_spend_global_budget():
    clock = FakeClock()
    session, global_ = SlidingWindowLimiter(1, 600, clock=clock), SlidingWindowLimiter(3, 3_600, clock=clock)
    assert acquire_both(session, global_) == (True, 0)
    assert acquire_both(session, global_) == (False, 600)
    assert [global_.try_acquire()[0] for _ in range(3)] == [True, True, False]


def test_global_limit_does_not_spend_session_budget():
    clock = FakeClock()
    session, global_ = SlidingWindowLimiter(2, 600, clock=clock), SlidingWindowLimiter(1, 3_600, clock=clock)
    assert acquire_both(session, global_) == (True, 0)
    assert acquire_both(session, global_) == (False, 3_600)
    assert session.peek() == (True, 0)
