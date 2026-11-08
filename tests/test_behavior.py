from dataclasses import replace
import random

import pytest

from desktop_cat.behavior import Behavior, State, move_within_bounds
from desktop_cat.settings import Settings


@pytest.fixture
def cat():
    settings = replace(Settings(), walk_min=2, walk_max=2, eat_seconds=1,
                       sleep_min=3, sleep_max=3, angry_seconds=2)
    return Behavior(settings, wake_seconds=1, rng=random.Random(0))


def test_complete_autonomous_cycle(cat):
    for seconds, state in [(2, State.EAT), (1, State.WALK), (2, State.SLEEP),
                           (3, State.WAKE), (1, State.WALK), (2, State.EAT)]:
        cat.advance(seconds)
        assert cat.state == state
        assert cat.elapsed == pytest.approx(0)


def test_elapsed_time_and_walking_distance_cross_boundaries(cat):
    assert cat.advance(6) == pytest.approx(4)
    assert cat.state == State.SLEEP
    assert cat.elapsed == pytest.approx(1)


@pytest.mark.parametrize("state_time", [0, 2.2, 3.5])
def test_click_interrupts_walk_or_eat(cat, state_time):
    cat.advance(state_time)
    cat.click()
    assert cat.state == State.ANGRY
    cat.advance(2)
    assert cat.state == State.WALK
    assert cat.next_rest == State.EAT


def test_click_while_asleep_wakes_before_anger(cat):
    cat.advance(5)
    assert cat.state == State.SLEEP
    cat.click()
    assert cat.state == State.WAKE
    cat.advance(0.4)
    cat.click()
    assert cat.elapsed == pytest.approx(0.4)
    cat.advance(0.6)
    assert cat.state == State.ANGRY
    cat.advance(2)
    assert cat.state == State.WALK


def test_repeated_clicks_do_not_extend_anger(cat):
    cat.click()
    for _ in range(20):
        cat.click()
        cat.advance(0.1)
    assert cat.state == State.WALK


def test_pause_does_not_consume_time(cat):
    cat.advance(0.5)
    assert cat.advance(100, frozen=True) == 0
    assert cat.elapsed == 0.5
    assert cat.state == State.WALK


def test_drag_restarts_cycle_even_during_sleep(cat):
    cat.advance(5.5)
    cat.restart_walk()
    assert cat.state == State.WALK
    assert cat.elapsed == 0
    assert cat.next_rest == State.EAT


@pytest.mark.parametrize("x,direction,distance,left,right,expected", [
    (90, 1, 20, 0, 100, (90, -1)),
    (10, -1, 20, 0, 100, (10, 1)),
    (20, 1, 470, 0, 100, (90, 1)),
    (-40, 1, 10, 0, 100, (10, 1)),
    (10, 1, 20, 50, 50, (50, 1)),
    (-100, -1, 30, -200, -50, (-130, -1)),
])
def test_motion_edges(x, direction, distance, left, right, expected):
    assert move_within_bounds(x, direction, distance, left, right) == expected
