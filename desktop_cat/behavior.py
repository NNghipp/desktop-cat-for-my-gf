"""Pure state machine. Time is supplied by the caller, never read globally."""

from enum import StrEnum
import random

from .settings import Settings


class State(StrEnum):
    WALK = "walk"
    EAT = "eat"
    SLEEP = "sleep"
    WAKE = "wake"
    ANGRY = "angry"


class Behavior:
    def __init__(self, settings: Settings, wake_seconds: float,
                 rng: random.Random | None = None):
        self.settings = settings
        self.wake_seconds = wake_seconds
        self.rng = rng if rng is not None else random.Random()
        self.next_rest = State.EAT
        self.angry_after_wake = False
        self.state = State.WALK
        self.elapsed = 0.0
        self.duration = self._duration(State.WALK)

    def _duration(self, state: State) -> float:
        s = self.settings
        match state:
            case State.WALK:
                return self.rng.uniform(s.walk_min, s.walk_max)
            case State.EAT:
                return s.eat_seconds
            case State.SLEEP:
                return self.rng.uniform(s.sleep_min, s.sleep_max)
            case State.WAKE:
                return self.wake_seconds
            case State.ANGRY:
                return s.angry_seconds

    def _enter(self, state: State) -> None:
        self.state = state
        self.elapsed = 0.0
        self.duration = self._duration(state)

    def restart_walk(self) -> None:
        self.next_rest = State.EAT
        self.angry_after_wake = False
        self._enter(State.WALK)

    def click(self) -> None:
        if self.state == State.ANGRY:
            return  # Do not let repeated clicks indefinitely restart anger.
        if self.state == State.SLEEP:
            self.angry_after_wake = True
            self._enter(State.WAKE)
        elif self.state == State.WAKE:
            self.angry_after_wake = True
        else:
            self._enter(State.ANGRY)

    def _finish(self) -> None:
        match self.state:
            case State.WALK:
                self._enter(self.next_rest)
            case State.EAT:
                self.next_rest = State.SLEEP
                self._enter(State.WALK)
            case State.SLEEP:
                self._enter(State.WAKE)
            case State.WAKE:
                if self.angry_after_wake:
                    self.angry_after_wake = False
                    self._enter(State.ANGRY)
                else:
                    self.restart_walk()
            case State.ANGRY:
                self.restart_walk()

    def advance(self, seconds: float, *, frozen: bool = False) -> float:
        """Advance through boundaries; return seconds actually spent walking."""
        if frozen or seconds <= 0:
            return 0.0
        walking = 0.0
        while seconds > 1e-10:
            step = min(seconds, self.duration - self.elapsed)
            if self.state == State.WALK:
                walking += step
            self.elapsed += step
            seconds -= step
            if self.elapsed >= self.duration - 1e-10:
                self._finish()
        return walking


def move_within_bounds(x: float, direction: int, distance: float,
                       left: float, right: float) -> tuple[float, int]:
    """Reflect at either edge, also handling a desktop smaller than the pet."""
    span = right - left
    if span <= 0:
        return left, direction
    x = max(left, min(x, right))
    phase = (x - left) if direction > 0 else 2 * span - (x - left)
    phase = (phase + distance) % (2 * span)
    if phase < span:
        return left + phase, 1
    return right - (phase - span), -1
