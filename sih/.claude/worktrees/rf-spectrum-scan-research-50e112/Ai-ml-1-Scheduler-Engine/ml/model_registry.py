"""Model registry -- registration, versioning, activation and rollback (Ai-ml-1 Level 5).

Every trained model is registered with its algorithm, hyperparameters, training-data seed range
and evaluation metrics (PRD Section 10.4). Checkpoints live under ``ml/checkpoints/`` -- gitignored,
mounted as a Docker volume shared with the Backend.

Activation is per-algorithm: promoting a bandit model deactivates the previous active bandit but
leaves an active Q-Learning model alone, exactly as ``/internal/models/{id}/activate`` specifies
("deactivates previous active model of same algorithm").

The index is one JSON file rewritten atomically. At this scale that is the right call: it is
inspectable by hand during a demo, diffable, and has no service to keep running.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ml.agents.base import Agent
from ml.contract import ModelMetadata, new_model_id

# Overridable so the Docker volume mount (and test isolation) can point elsewhere.
DEFAULT_ROOT = Path(os.environ.get("ML_CHECKPOINT_DIR") or Path(__file__).resolve().parent / "checkpoints")


class ModelRegistry:
    """Versioned store of trained scheduler models."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root else DEFAULT_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self._lock = threading.Lock()
        if not self.index_path.exists():
            self._write({})

    # -- storage --------------------------------------------------------------------------

    def _read(self) -> dict[str, dict]:
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write(self, index: dict[str, dict]) -> None:
        # Write-then-rename: a crash mid-write leaves the previous index intact rather than a
        # truncated one, which would lose every registered model.
        fd, tmp = tempfile.mkstemp(dir=str(self.root), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, sort_keys=True, default=str)
            os.replace(tmp, self.index_path)
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
        with self._lock:
            index = self._read()
            model_id = new_model_id(algorithm)
            version = 1 + sum(1 for m in index.values() if m["algorithm"] == algorithm)

            checkpoint = self.root / f"{model_id}{_suffix_for(algorithm)}"
            agent.save(checkpoint)

            meta = ModelMetadata(
                model_id=model_id,
                algorithm=algorithm,
                scenario=scenario,
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

    # -- lifecycle ------------------------------------------------------------------------

    def activate(self, model_id: str) -> ModelMetadata:
        with self._lock:
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
        with self._lock:
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
        raise ValueError(f"cannot load algorithm {algorithm!r}")


def _suffix_for(algorithm: str) -> str:
    if algorithm == "q_learning":
        return ".json"
    if algorithm in ("dqn", "ppo"):
        return ".zip"
    return ".npz"


def _without_checkpoint(record: dict) -> dict:
    return {k: v for k, v in record.items() if k != "checkpoint"}
