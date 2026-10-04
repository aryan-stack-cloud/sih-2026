"""The two agent-side shaping terms (ml/agents/shaping.py): efficiency (detected share of the window) and coverage (staleness)."""

import numpy as np
import pytest

from ml.agents.shaping import (
    RewardShaping,
    hit_share,
    staleness_from_ages,
    staleness_from_observation,
)


def _observation(n=8, ages=None, tuned=()):
    obs = np.zeros(8 * n + 2)
    for band, age in (ages or {}).items():
        obs[band * 7 + 0] = age
    for band in tuned:
        obs[7 * n + band] = 1.0
    return obs


def test_hit_share_is_detected_over_scanned_and_zero_without_a_scan():
    assert hit_share({}) == 0.0
    assert hit_share({"scanned_bands": [], "detected_bands": []}) == 0.0
    assert hit_share({"scanned_bands": [3, 4], "detected_bands": [3]}) == 0.5
    assert hit_share({"scanned_bands": [3, 4], "detected_bands": [3, 4]}) == 1.0


def test_staleness_from_ages_caps_at_32_steps():
    assert staleness_from_ages([0, 16, 64], [1, 2]) == pytest.approx((0.5 + 1.0) / 2)
    assert staleness_from_ages([5], []) == 0.0


def test_staleness_from_observation_reads_the_executed_window():
    obs = _observation(ages={3: 0.25, 4: 0.75}, tuned=(3, 4))
    assert staleness_from_observation(obs, 3, 8) == pytest.approx(0.5)


def test_staleness_from_observation_wraps_and_defaults_to_one_band_without_a_tuned_block():
    obs = _observation(ages={7: 1.0, 0: 0.0}, tuned=(7, 0))
    assert staleness_from_observation(obs, 7, 8) == pytest.approx(0.5)
    assert staleness_from_observation(_observation(ages={3: 0.25}), 3, 8) == pytest.approx(0.25)


def test_reward_shaping_adds_both_terms_and_is_inactive_by_default():
    obs = _observation(ages={3: 0.25, 4: 0.75}, tuned=(3, 4))
    shaping = RewardShaping(eff_beta=4.0, cov_beta=2.0)
    shaping.observe({"scanned_bands": [3, 4], "detected_bands": [3, 4]})
    assert shaping.active
    assert shaping.shape(1.0, obs, 3, 8) == pytest.approx(1.0 + 4.0 * 1.0 + 2.0 * 0.5)
    off = RewardShaping()
    off.observe({"scanned_bands": [3, 4], "detected_bands": [3, 4]})
    assert not off.active
    assert off.shape(1.0, obs, 3, 8) == 1.0


def test_reward_shaping_uses_only_the_latest_observed_outcome():
    shaping = RewardShaping(eff_beta=2.0)
    obs = _observation(tuned=(0, 1))
    shaping.observe({"scanned_bands": [0, 1], "detected_bands": [0, 1]})
    shaping.observe({"scanned_bands": [0, 1], "detected_bands": []})
    assert shaping.shape(0.0, obs, 0, 8) == 0.0
