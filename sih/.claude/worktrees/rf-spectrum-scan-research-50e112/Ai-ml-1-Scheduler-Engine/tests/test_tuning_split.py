"""Train and hold-out seed splitting for the index tuner.

The first tuning run scored its own search seeds and reported a +1.84 improvement over a +0.41
default. That number is not a result, it is a fit: six free parameters against three episodes will
find something. A tuned configuration is only worth shipping if it beats the default on seeds the
search never saw, so the splitter is not a convenience, it is the thing that makes the search
honest.
"""

from __future__ import annotations

import pytest

from ml.tuning.objective import train_holdout_seeds

SCENARIO = {"bands": 16, "seed": 42, "seed_range": [42, 62], "episodes": 20}


def test_the_two_sets_never_overlap():
    train, holdout = train_holdout_seeds(SCENARIO, train_episodes=3, holdout_episodes=8)
    assert set(train).isdisjoint(holdout)


def test_each_set_gets_the_requested_number_of_seeds():
    train, holdout = train_holdout_seeds(SCENARIO, train_episodes=3, holdout_episodes=8)
    assert len(train) == 3
    assert len(holdout) == 8


def test_training_takes_the_scenarios_own_leading_seeds():
    """So a tuning run and an ordinary comparison at the same episode count see the same spectra."""
    train, _ = train_holdout_seeds(SCENARIO, train_episodes=3, holdout_episodes=5)
    assert train == [42, 43, 44]


def test_holdout_continues_past_the_training_seeds():
    _, holdout = train_holdout_seeds(SCENARIO, train_episodes=3, holdout_episodes=4)
    assert holdout == [45, 46, 47, 48]


def test_the_split_is_deterministic():
    first = train_holdout_seeds(SCENARIO, train_episodes=4, holdout_episodes=6)
    second = train_holdout_seeds(SCENARIO, train_episodes=4, holdout_episodes=6)
    assert first == second


def test_a_holdout_may_extend_past_the_declared_seed_range():
    """Seeds are consecutive integers; the range is a convention, not a supply limit."""
    _, holdout = train_holdout_seeds(SCENARIO, train_episodes=18, holdout_episodes=10)
    assert len(holdout) == 10
    assert max(holdout) > SCENARIO["seed_range"][1]


def test_an_empty_holdout_is_refused():
    """Tuning without validation is what produced the overfitted number in the first place."""
    with pytest.raises(ValueError):
        train_holdout_seeds(SCENARIO, train_episodes=3, holdout_episodes=0)


def test_an_empty_training_set_is_refused():
    with pytest.raises(ValueError):
        train_holdout_seeds(SCENARIO, train_episodes=0, holdout_episodes=5)
