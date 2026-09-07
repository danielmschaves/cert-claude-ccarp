"""The exam clock. Monotonic, and each warning fires once."""

from ccarp.timer import Timer


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def test_counts_down():
    clock = FakeClock()
    t = Timer(120, clock)
    assert t.remaining == 7200
    clock.advance(600)
    assert t.remaining == 6600
    assert not t.expired


def test_expires_and_never_goes_negative():
    clock = FakeClock()
    t = Timer(120, clock)
    clock.advance(7300)
    assert t.expired
    assert t.remaining == 0.0


def test_each_warning_fires_exactly_once():
    clock = FakeClock()
    t = Timer(120, clock)
    assert t.due_warning() is None
    clock.advance(7200 - 1800)          # 30 minutes left
    assert t.due_warning() == 30
    assert t.due_warning() is None      # not again
    clock.advance(1200)                 # 10 minutes left
    assert t.due_warning() == 10


def test_remaining_is_formatted_for_the_question_header():
    clock = FakeClock()
    t = Timer(120, clock)
    clock.advance(7200 - 125)
    assert t.format_remaining() == "2:05"
