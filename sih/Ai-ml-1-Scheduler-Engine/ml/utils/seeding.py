"""Seeding helpers.

NFR-006 requires that, given an identical seed and configuration, simulator output is
bit-for-bit reproducible. Section 13 additionally requires that baseline and ML runs of the
same scenario see the *identical* spectrum, so the comparison isolates the policy.

Both fall out of one rule: derive independent generator streams from a single seed, one per
concern, so that changing the policy cannot perturb the world.

    seed + 0  ground truth (emitter placement + activity table)
    seed + 1  detection noise
    seed + 2  agent exploration
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

GROUND_TRUTH_STREAM = 0
NOISE_STREAM = 1
POLICY_STREAM = 2


@dataclass(frozen=True)
class SeedBundle:
    """The three independent generators a simulation run needs."""

    seed: int
    ground_truth: np.random.Generator
    noise: np.random.Generator
    policy: np.random.Generator


def make_generator(seed: int, stream: int) -> np.random.Generator:
    """A generator for one concern, independent of every other stream from the same seed."""
    return np.random.default_rng([int(seed), int(stream)])


def make_seed_bundle(seed: int) -> SeedBundle:
    return SeedBundle(
        seed=int(seed),
        ground_truth=make_generator(seed, GROUND_TRUTH_STREAM),
        noise=make_generator(seed, NOISE_STREAM),
        policy=make_generator(seed, POLICY_STREAM),
    )
