"""Model registry -- registration, versioning, activation and rollback (Ai-ml-1 Level 5).

Every trained model is registered with its algorithm, hyperparameters, training-data seed range
and evaluation metrics (PRD Section 10.4). Checkpoints live under ``ml/checkpoints/`` -- gitignored,
mounted as a Docker volume shared with the Backend.

Activation is per-algorithm: promoting a bandit model deactivates the previous active bandit but
leaves an active Q-Learning model alone, exactly as ``/internal/models/{id}/activate`` specifies
("deactivates previous active model of same algorithm").

Activation alone cannot serve seven scenarios, though: a model's weights are sized to the band
count it was trained on (16, 24 or 32 here), so one active DQN can only ever serve the scenarios
with that band count. ``resolve`` is what the inference engine calls instead -- it picks, per
request, the best registered model whose band count fits, preferring one trained on the requested
scenario. Every record carries ``num_bands`` for this (older records are backfilled).

The index is one JSON file rewritten atomically. At this scale that is the right call: it is
inspectable by hand during a demo, diffable, and has no service to keep running.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

from ml.agents.base import Agent
from ml.contract import ModelMetadata, new_model_id

# Overridable so the Docker volume mount (and test isolation) can point elsewhere.
DEFAULT_ROOT = Path(os.environ.get("ML_CHECKPOINT_DIR") or Path(__file__).resolve().parent / "checkpoints")

# The PRD Section 13 scenarios. Anything else in a record's `scenario` (e.g. "turing-replay") was
# trained on a different data source and is only served when nothing synthetic fits.
SYNTHETIC_SCENARIOS = frozenset("ABCDEFG")


class ModelRegistry:
    """Versioned store of trained scheduler models."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root else DEFAULT_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self._lock_path = self.root / "index.lock"
        self._thread_lock = threading.Lock()
        if not self.index_path.exists():
            with self._lock():
                if not self.index_path.exists():
                    self._write({})

    # -- storage --------------------------------------------------------------------------

    @contextmanager
    def _lock(self):
        """Exclusive access to the index, across threads AND processes.

        The service, the training CLI and parallel training jobs all register into the same
        index. A thread lock alone let two processes each read the index, add their own model and
        write it back -- the second write silently dropping the first registration (6 writers x 5
        registrations kept as few as 5 of 30).

        An OS byte-range lock on a file that is never deleted, rather than a create-exclusive lock
        file: on Windows a lock file being deleted refuses re-creation with PermissionError, and the
        OS releases this kind of lock by itself if its holder dies, so it cannot go stale.
        """
        with self._thread_lock:
            with open(self._lock_path, "a+b") as handle:
                _acquire_file_lock(handle, timeout_s=60.0)
                try:
                    yield
                finally:
                    _release_file_lock(handle)

    def _read(self) -> dict[str, dict]:
        try:
            text = _retry_on_sharing_violation(
                lambda: self.index_path.read_text(encoding="utf-8"))
            return json.loads(text)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write(self, index: dict[str, dict]) -> None:
        # Write-then-rename: a crash mid-write leaves the previous index intact rather than a
        # truncated one, which would lose every registered model.
        fd, tmp = tempfile.mkstemp(dir=str(self.root), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, sort_keys=True, default=str)
            _retry_on_sharing_violation(lambda: os.replace(tmp, self.index_path))
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    # -- registration ---------------------------------------------------------------------

    def register(
        self,
        agent: Agent,
        algorithm: str,
        scenario: str | None = None,
        hyperparams: dict[str, Any] | None = None,
        seed_range: list[int] | None = None,
        metrics: dict[str, Any] | None = None,
        activate: bool = False,
    ) -> ModelMetadata:
        """Persist a trained agent and record its metadata."""
        with self._lock():
            index = self._read()
            model_id = new_model_id(algorithm)
            version = 1 + sum(1 for m in index.values() if m["algorithm"] == algorithm)

            checkpoint = self.root / f"{model_id}{_suffix_for(algorithm)}"
            agent.save(checkpoint)

            meta = ModelMetadata(
                model_id=model_id,
                algorithm=algorithm,
                scenario=scenario,
                num_bands=int(agent.num_bands),
                version=version,
                active=False,
                created_at=datetime.now(timezone.utc).isoformat(),
                hyperparams=hyperparams or (agent.hyperparams() if hasattr(agent, "hyperparams") else {}),
                seed_range=seed_range,
                metrics=metrics or {},
            )
            record = meta.model_dump()
            record["checkpoint"] = str(checkpoint.name)
            index[model_id] = record
            self._write(index)

        if activate:
            return self.activate(model_id)
        return meta

    # -- queries --------------------------------------------------------------------------

    def list(self, algorithm: str | None = None, active: bool | None = None) -> list[ModelMetadata]:
        records = list(self._read().values())
        if algorithm is not None:
            records = [r for r in records if r["algorithm"] == algorithm]
        if active is not None:
            records = [r for r in records if bool(r["active"]) is bool(active)]
        records.sort(key=lambda r: r["created_at"], reverse=True)
        return [ModelMetadata(**_without_checkpoint(r)) for r in records]

    def get(self, model_id: str) -> ModelMetadata:
        record = self._read().get(model_id)
        if record is None:
            raise KeyError(model_id)
        return ModelMetadata(**_without_checkpoint(record))

    def checkpoint_path(self, model_id: str) -> Path:
        record = self._read().get(model_id)
        if record is None:
            raise KeyError(model_id)
        return self.root / record["checkpoint"]

    def active_model(self, algorithm: str) -> ModelMetadata | None:
        found = self.list(algorithm=algorithm, active=True)
        return found[0] if found else None

    def resolve(
        self, algorithm: str, num_bands: int, scenario_id: str | None = None
    ) -> ModelMetadata | None:
        """The model that should serve ``algorithm`` on a ``num_bands``-band scenario.

        Only band-count-compatible models are candidates. Among them, in order:

        1. one trained on the requested scenario -- the active one if that is it, else the newest;
        2. the algorithm's active model (an operator's explicit choice), from another scenario;
        3. the newest model trained on any synthetic scenario A-G;
        4. the newest of whatever is left (e.g. a Turing-replay model).

        ``None`` means nothing registered fits, and the caller decides what that means: a cold
        online learner is a real policy for the bandit, but a DQN with no weights cannot act.
        """
        candidates = [
            r for r in self._read().values()
            if r["algorithm"] == algorithm and self._record_bands(r) == int(num_bands)
        ]
        if not candidates:
            return None

        def rank(record: dict) -> tuple:
            same_scenario = scenario_id is not None and record.get("scenario") == scenario_id
            return (
                same_scenario,
                bool(record.get("active")),
                record.get("scenario") in SYNTHETIC_SCENARIOS,
                record.get("created_at", ""),
            )

        best = max(candidates, key=rank)
        return ModelMetadata(**_without_checkpoint(best))

    def backfill_num_bands(self) -> int:
        """Record ``num_bands`` on every record registered before it was stored. Idempotent."""
        with self._lock():
            index = self._read()
            changed = 0
            for record in index.values():
                if record.get("num_bands") is None:
                    bands = self._record_bands(record)
                    if bands is not None:
                        record["num_bands"] = bands
                        changed += 1
            if changed:
                self._write(index)
        return changed

    def _record_bands(self, record: dict) -> int | None:
        """A record's band count: stored, else from its scenario, else from the checkpoint."""
        if record.get("num_bands") is not None:
            return int(record["num_bands"])
        scenario = record.get("scenario")
        if scenario in SYNTHETIC_SCENARIOS:
            from ml.utils.config import load_scenario

            return int(load_scenario(scenario)["bands"])
        try:
            # SB3 checkpoints carry a sidecar with the band count; far cheaper than loading torch.
            sidecar = (self.root / record["checkpoint"]).with_suffix(".meta.json")
            if sidecar.exists():
                stored = json.loads(sidecar.read_text(encoding="utf-8")).get("num_bands")
                if stored is not None:
                    return int(stored)
            return int(self.load_agent(record["model_id"]).num_bands)
        except Exception:  # noqa: BLE001 - an unreadable checkpoint is simply not a candidate
            return None

    # -- lifecycle ------------------------------------------------------------------------

    def activate(self, model_id: str) -> ModelMetadata:
        with self._lock():
            index = self._read()
            if model_id not in index:
                raise KeyError(model_id)
            algorithm = index[model_id]["algorithm"]
            for mid, record in index.items():
                if record["algorithm"] == algorithm:
                    record["active"] = mid == model_id
            self._write(index)
            return ModelMetadata(**_without_checkpoint(index[model_id]))

    def update_metrics(self, model_id: str, metrics: dict[str, Any]) -> ModelMetadata:
        with self._lock():
            index = self._read()
            if model_id not in index:
                raise KeyError(model_id)
            index[model_id]["metrics"] = metrics
            self._write(index)
            return ModelMetadata(**_without_checkpoint(index[model_id]))

    def load_agent(self, model_id: str, **kwargs) -> Agent:
        """Rehydrate a registered model into a ready-to-serve agent."""
        meta = self.get(model_id)
        path = self.checkpoint_path(model_id)
        algorithm = meta.algorithm

        if algorithm == "bandit":
            from ml.agents.bandit_agent import BanditAgent

            return BanditAgent.load(path, **kwargs)
        if algorithm == "q_learning":
            from ml.agents.q_learning_agent import QLearningAgent

            return QLearningAgent.load(path, **kwargs)
        if algorithm in ("dqn", "ppo"):
            from ml.agents.dqn_agent import DeepRLAgent

            return DeepRLAgent.load(path, algorithm=algorithm, **kwargs)
        if algorithm == "baseline":
            from ml.agents.baseline_scanner import BaselineScanner

            return BaselineScanner.load(path, **kwargs)
        if algorithm == "index":
            from ml.agents.index_agent import IndexAgent

            return IndexAgent.load(path, **kwargs)
        if algorithm == "ctmc":
            from ml.agents.ctmc_floor import CTMCFloorAgent

            return CTMCFloorAgent.load(path, **kwargs)
        raise ValueError(f"cannot load algorithm {algorithm!r}")


if os.name == "nt":
    import msvcrt

    def _acquire_file_lock(handle, timeout_s: float) -> None:
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if time.monotonic() > deadline:
                    raise TimeoutError(f"model registry lock {handle.name} is held") from None
                time.sleep(0.01)

    def _release_file_lock(handle) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _acquire_file_lock(handle, timeout_s: float) -> None:  # noqa: ARG001 - blocks until free
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

    def _release_file_lock(handle) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


_T = TypeVar("_T")


def _retry_on_sharing_violation(op: Callable[[], _T], attempts: int = 50) -> _T:
    """Retry an index read or replace that Windows refused because another process had it open.

    Windows will not replace (or, briefly, read) a file another process holds open, and reports
    it as PermissionError; the other process's open lasts microseconds, so a short retry is the
    whole fix. On POSIX the first attempt always succeeds.
    """
    for attempt in range(attempts):
        try:
            return op()
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.02)
    raise AssertionError("unreachable")


def _suffix_for(algorithm: str) -> str:
    if algorithm == "q_learning":
        return ".json"
    if algorithm in ("dqn", "ppo"):
        return ".zip"
    return ".npz"


def _without_checkpoint(record: dict) -> dict:
    return {k: v for k, v in record.items() if k != "checkpoint"}
