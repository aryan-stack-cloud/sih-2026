"""Guard the in-process cost of a full Backend-style episode."""

import pytest

from tests.bench_episode import episode


@pytest.mark.parametrize("bands", [16, 32])
def test_2000_step_episode_fits_budget(bands):
    elapsed_seconds = episode(bands, 2000) * 2
    assert elapsed_seconds < 15, f"{bands} bands took {elapsed_seconds:.2f} s"
