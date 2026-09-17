"""Low-latency decision path backing ``/internal/decide`` (Ai-ml-1 Level 4).

Budget: < 50 ms per decision for bandit/Q-Learning, < 150 ms for DQN (NFR-002). Nothing on this
path touches disk, and models are cached after first load.

STATE OWNERSHIP. The Backend owns simulation state; we are stateless with respect to it. Every
``/internal/decide`` call carries the full StateVector, so a decision is a pure function of the
request plus the model. What we *do* keep per ``(simulation_id, policy)`` is the online-learning
agent instance, because the contract has the Backend call ``/internal/learn`` after every step --
the bandit's per-band estimates are built up over a simulation and must survive between calls.
Those sessions are evicted by ``reset(simulation_id)`` and bounded by ``max_sessions``.

We never call Ai-ml-2. ``periodicity_phase`` and ``periodicity_confidence`` arrive already merged
into the StateVector by the Backend's StateBuilder (API_CONTRACT.md Section 0).
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any

import numpy as np

from ml.agents.base import Agent
from ml.agents.factory import build_agent
from ml.contract import Action, StateVector, new_decision_id
from ml.environments.action_space import ActionSpaceSpec
from ml.environments.state import StateBuilder
from ml.model_registry import ModelRegistry
from ml.utils.logging import get_logger

log = get_logger(__name__)


class InferenceEngine:
    """Serves scan decisions and applies online learning updates."""

    def __init__(self, registry: ModelRegistry | None = None, max_sessions: int = 64) -> None:
        self.registry = registry or ModelRegistry()
        self.max_sessions = max_sessions
        # (simulation_id, policy) -> (agent, resolved model_id)
        self._sessions: OrderedDict[tuple[str, str], tuple[Agent, str]] = OrderedDict()
        self._model_cache: dict[str, Agent] = {}
        self._decisions: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    # -- session management -----------------------------------------------------------------

    def _session(self, simulation_id: str, policy: str, num_bands: int, model_id: str | None):
        """Get or create the agent serving one simulation under one policy.

        The resolved ``model_id`` is stored WITH the session rather than re-resolved per call.
        Two reasons, and the second is why this is not merely an optimisation:

        * Resolving it per call meant reading and JSON-parsing the registry index off disk on
          every decision -- a filesystem hit on the NFR-002 critical path, which is worth about
          10 ms per decide over HTTP. An in-process test client hides this; a real socket does not.
        * A session's decisions should be attributed to the model that session is actually
          running. If an operator activates a new model mid-simulation, re-resolving would start
          reporting the new ``model_id`` for decisions still being made by the old agent. New
          activations correctly apply to new sessions.
        """
        key = (simulation_id, policy)
        with self._lock:
            entry = self._sessions.get(key)
            if entry is not None and entry[0].num_bands == num_bands:
                self._sessions.move_to_end(key)
                agent, resolved = entry
                return agent, (model_id or resolved)

            agent, resolved = self._build(policy, num_bands, model_id)
            self._sessions[key] = (agent, resolved)
            self._sessions.move_to_end(key)
            while len(self._sessions) > self.max_sessions:
                evicted, _ = self._sessions.popitem(last=False)
                log.info("evicted inference session", extra={"simulation_id": evicted[0]})
            return agent, resolved

    def _build(self, policy: str, num_bands: int, model_id: str | None) -> tuple[Agent, str]:
        """Load a registered model if one is named or active, else a fresh online learner."""
        target = model_id
        if target is None:
            active = self.registry.active_model(policy)
            target = active.model_id if active else None

        if target is not None:
            cached = self._model_cache.get(target)
            agent = cached if cached is not None else self.registry.load_agent(target)
            self._model_cache.setdefault(target, agent)
            # Serve a copy so two simulations sharing a model do not learn into each other.
            import copy

            return copy.deepcopy(agent), target

        # No registered model: a cold online learner. This is a legitimate mode, not a
        # fallback -- the bandit is designed to adapt from scratch within a single simulation.
        agent = build_agent(policy, num_bands)
        agent.start_episode(0)
        return agent, f"online_{policy}"

    def reset(self, simulation_id: str) -> int:
        """Drop every session for a simulation. Called when the Backend resets a simulation."""
        with self._lock:
            keys = [k for k in self._sessions if k[0] == simulation_id]
            for k in keys:
                del self._sessions[k]
            stale = [d for d, rec in self._decisions.items() if rec["simulation_id"] == simulation_id]
            for d in stale:
                del self._decisions[d]
        return len(keys)

    # -- the contract operations -------------------------------------------------------------

    def decide(
        self,
        simulation_id: str,
        state: StateVector,
        policy: str,
        model_id: str | None = None,
    ) -> tuple[Action, str, str]:
        """``POST /internal/decide`` -> ``(action, model_id, decision_id)``."""
        contract_state = state.model_dump()
        num_bands = len(contract_state["bands"])
        agent, resolved_model = self._session(simulation_id, policy, num_bands, model_id)

        vector = StateBuilder.from_contract(contract_state).to_vector()
        # explore=False: a live simulation is not a training run. Exploration during deployment
        # would make the Backend's metrics non-reproducible for the same seed (NFR-006).
        action_index = agent.select_action(vector, explore=False)

        spec = ActionSpaceSpec(num_bands=num_bands)
        action = Action(**spec.to_contract(action_index))
        decision_id = new_decision_id()

        with self._lock:
            self._decisions[decision_id] = {
                "simulation_id": simulation_id,
                "policy": policy,
                "action": action_index,
                "state": vector,
            }
            # Bound the decision log; only the most recent are ever learned against.
            if len(self._decisions) > 10 * self.max_sessions:
                for stale in list(self._decisions)[: len(self._decisions) // 2]:
                    del self._decisions[stale]

        return action, resolved_model, decision_id

    def learn(
        self,
        simulation_id: str,
        decision_id: str,
        state: StateVector,
        action: Action,
        reward: float,
        next_state: StateVector | None = None,
    ) -> bool:
        """``POST /internal/learn``.

        The reward arrives pre-computed from the Backend (Equation 10.1); this service consumes
        it and never recomputes it. A no-op for policies that do not learn online.
        """
        record = self._decisions.pop(decision_id, None)
        policy = record["policy"] if record else None
        if policy is None:
            # The Backend may call learn for a decision we no longer hold (restart, eviction).
            # Fall back to the only session for this simulation, if there is exactly one.
            with self._lock:
                candidates = [k for k in self._sessions if k[0] == simulation_id]
            if len(candidates) != 1:
                log.info("learn for unknown decision", extra={"simulation_id": simulation_id,
                                                             "decision_id": decision_id})
                return False
            policy = candidates[0][1]

        with self._lock:
            entry = self._sessions.get((simulation_id, policy))
        if entry is None:
            return False
        agent = entry[0]

        state_vec = (
            record["state"] if record else StateBuilder.from_contract(state.model_dump()).to_vector()
        )
        next_vec = (
            StateBuilder.from_contract(next_state.model_dump()).to_vector()
            if next_state is not None
            else state_vec
        )
        agent.learn(
            np.asarray(state_vec),
            int(action.next_band) % agent.num_bands,
            float(reward),
            np.asarray(next_vec),
            done=False,
        )
        return True

    # -- introspection ------------------------------------------------------------------------

    def session_count(self) -> int:
        return len(self._sessions)

    def describe_session(self, simulation_id: str, policy: str) -> dict | None:
        entry = self._sessions.get((simulation_id, policy))
        return entry[0].describe() if entry else None
