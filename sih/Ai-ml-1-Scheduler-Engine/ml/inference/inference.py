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

# Trained offline and served read-only: a freshly built one has no weights and cannot act, so
# "no compatible model" is an error for these rather than a cue to start a cold online learner.
OFFLINE_POLICIES = ("dqn", "ppo")


class NoCompatibleModelError(LookupError):
    """No registered model of this algorithm fits the request's band count."""

    def __init__(self, policy: str, num_bands: int, scenario_id: str | None) -> None:
        self.policy = policy
        self.num_bands = num_bands
        self.scenario_id = scenario_id
        where = f"scenario {scenario_id} ({num_bands} bands)" if scenario_id else f"{num_bands} bands"
        super().__init__(
            f"no trained {policy} model is registered for {where}; "
            f"train one with POST /internal/train for a {num_bands}-band scenario"
        )


class InferenceEngine:
    """Serves scan decisions and applies online learning updates."""

    def __init__(self, registry: ModelRegistry | None = None, max_sessions: int = 64) -> None:
        self.registry = registry or ModelRegistry()
        self.max_sessions = max_sessions
        # (simulation_id, policy) -> (agent, resolved model_id, what the session was built for)
        self._sessions: OrderedDict[tuple[str, str], tuple[Agent, str, tuple]] = OrderedDict()
        self._model_cache: dict[str, Agent] = {}
        self._decisions: dict[str, dict[str, Any]] = {}
        # Decision ids already learned from, so a retried /learn is acknowledged once, not
        # applied twice. Bounded: only recent retries matter.
        self._consumed: OrderedDict[str, None] = OrderedDict()
        self._lock = threading.Lock()

    # -- session management -----------------------------------------------------------------

    def _session(
        self,
        simulation_id: str,
        policy: str,
        num_bands: int,
        model_id: str | None,
        scenario_id: str | None = None,
    ):
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
        # A session serves exactly the request it was built for. A different band count, pinned
        # model or scenario under the same simulation id is a different run configuration: reusing
        # the old agent while reporting the newly requested model id misattributed every decision.
        built_for = (num_bands, model_id, scenario_id)
        with self._lock:
            entry = self._sessions.get(key)
            if entry is not None and entry[2] == built_for:
                self._sessions.move_to_end(key)
                return entry[0], entry[1]

            agent, resolved = self._build(policy, num_bands, model_id, scenario_id)
            self._sessions[key] = (agent, resolved, built_for)
            self._sessions.move_to_end(key)
            while len(self._sessions) > self.max_sessions:
                evicted, _ = self._sessions.popitem(last=False)
                log.info("evicted inference session", extra={"simulation_id": evicted[0]})
            return agent, resolved

    def _load(self, model_id: str) -> Agent:
        cached = self._model_cache.get(model_id)
        agent = cached if cached is not None else self.registry.load_agent(model_id)
        self._model_cache.setdefault(model_id, agent)
        return agent

    def _build(
        self,
        policy: str,
        num_bands: int,
        model_id: str | None,
        scenario_id: str | None = None,
    ) -> tuple[Agent, str]:
        """The agent for a new session: a named model, else the best registered fit, else cold.

        Model choice used to be "the one active model of this algorithm". Activation is per
        algorithm, but weights are sized to a band count, so one active DQN could serve only the
        scenarios with its band count: on every other scenario DQN/PPO crashed (HTTP 500), the
        Backend fell back to round-robin for the whole run, and the result was byte-identical to
        the baseline -- presented as a real DQN measurement. ``ModelRegistry.resolve`` now picks a
        band-compatible model per request, preferring one trained on the requested scenario.
        """
        import copy

        if model_id is not None:
            pinned = self.registry.get(model_id)          # KeyError -> 404 at the API
            if pinned.algorithm != policy:
                raise ValueError(
                    f"model {model_id} is a {pinned.algorithm} model; it cannot serve {policy}"
                )
            agent = self._load(model_id)
            if agent.num_bands != num_bands:
                # An explicit pin is an operator's instruction; quietly serving something else
                # would misattribute every metric of the run. Fail loudly instead.
                raise ValueError(
                    f"model {model_id} was trained for {agent.num_bands} bands, "
                    f"but this simulation has {num_bands}"
                )
            # Serve a copy so two simulations sharing a model do not learn into each other.
            return copy.deepcopy(agent), model_id

        chosen = self.registry.resolve(policy, num_bands, scenario_id)
        if chosen is not None:
            agent = self._load(chosen.model_id)
            if agent.num_bands == num_bands:
                return copy.deepcopy(agent), chosen.model_id
            log.warning(
                "registry band count disagrees with the checkpoint; not serving it",
                extra={"model_id": chosen.model_id, "model_num_bands": agent.num_bands,
                       "requested_num_bands": num_bands},
            )

        if policy in OFFLINE_POLICIES:
            raise NoCompatibleModelError(policy, num_bands, scenario_id)

        # Nothing registered fits: a cold online learner. This is a legitimate mode, not a
        # fallback -- the bandit is designed to adapt from scratch within a single simulation,
        # and index/ctmc are fully specified by their derived constants.
        agent = _cold_agent(policy, num_bands, scenario_id)
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
        scenario_id: str | None = None,
    ) -> tuple[Action, str, str]:
        """``POST /internal/decide`` -> ``(action, model_id, decision_id)``."""
        contract_state = state.model_dump()
        num_bands = len(contract_state["bands"])
        agent, resolved_model = self._session(
            simulation_id, policy, num_bands, model_id, scenario_id
        )

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
        scanned_bands: list[int] | None = None,
        detected_bands: list[int] | None = None,
    ) -> bool:
        """``POST /internal/learn``.

        The reward arrives pre-computed from the Backend (Equation 10.1); this service consumes
        it and never recomputes it. A no-op for policies that do not learn online.

        The step's raw outcome goes to ``Agent.observe`` first, exactly as
        ``ml/evaluation/runner.py`` does it. That call was missing here, and it is the ONLY way the
        index policy updates its occupancy belief, revisit ages and kernel evidence -- so every
        Backend-served index run used a permanently cold belief with deadlines that never advanced.
        """
        with self._lock:
            if decision_id in self._consumed:
                # A retry of a learn we already applied (e.g. after an ambiguous HTTP timeout).
                # Acknowledge it -- the Backend's intent is satisfied -- but never apply it twice.
                return True
            record = self._decisions.pop(decision_id, None)
            if record is not None and record["simulation_id"] != simulation_id:
                # A decision id from another simulation: applying it would teach one simulation's
                # learner with another's step. Leave it for its real owner and refuse.
                self._decisions[decision_id] = record
                log.warning("learn with a decision id owned by another simulation",
                            extra={"simulation_id": simulation_id, "decision_id": decision_id})
                return False
            if record is not None:
                policy = record["policy"]
            else:
                # The Backend may call learn for a decision we no longer hold (log truncation).
                # The request itself carries the state, action and reward, so learning from it is
                # still correct -- provided there is exactly one session it can belong to.
                candidates = [k for k in self._sessions if k[0] == simulation_id]
                if len(candidates) != 1:
                    log.info("learn for unknown decision", extra={"simulation_id": simulation_id,
                                                                 "decision_id": decision_id})
                    return False
                policy = candidates[0][1]
            entry = self._sessions.get((simulation_id, policy))
            if entry is not None:
                self._consumed[decision_id] = None
                while len(self._consumed) > 100 * self.max_sessions:
                    self._consumed.popitem(last=False)
        if entry is None:
            return False
        agent = entry[0]

        info = _step_outcome(next_state, scanned_bands, detected_bands, agent.num_bands)
        if info is not None:
            agent.observe(info)

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


def _cold_agent(policy: str, num_bands: int, scenario_id: str | None) -> Agent:
    """A fresh agent for a request no registered model fits.

    The index policy's constants (receiver width K, detector ROC, revisit deadlines) must come
    from the receiver it drives, exactly as ``IndexAgent.from_scenario`` does for evaluation; a
    bare constructor assumed K=1 and default detector probabilities against a K=2 receiver. Every
    scenario A-G shares one receiver, and a custom simulation reuses it too, so a non-synthetic
    scenario id borrows D's receiver with the request's band count.
    """
    if policy == "index":
        from ml.agents.index_agent import IndexAgent  # noqa: PLC0415
        from ml.model_registry import SYNTHETIC_SCENARIOS  # noqa: PLC0415
        from ml.utils.config import load_scenario  # noqa: PLC0415

        cfg = dict(load_scenario(scenario_id if scenario_id in SYNTHETIC_SCENARIOS else "D"))
        cfg["bands"] = num_bands
        return IndexAgent.from_scenario(cfg)
    return build_agent(policy, num_bands)


def _step_outcome(
    next_state: StateVector | None,
    scanned_bands: list[int] | None,
    detected_bands: list[int] | None,
    num_bands: int,
) -> dict | None:
    """The ``info`` dict ``Agent.observe`` takes, from the learn request.

    Explicit ``scanned_bands``/``detected_bands`` win. Without them the outcome is recovered from
    ``next_state``, which the Backend's StateBuilder updates deterministically: a scanned band's
    ``time_since_last_scan`` is reset to 0 (every other band ages to >= 1), and a scanned band's
    ``consecutive_misses`` is reset to 0 on a hit and incremented on a miss.
    """
    if scanned_bands is not None:
        scanned = [int(b) for b in scanned_bands if 0 <= int(b) < num_bands]
        scanned_set = set(scanned)
        detected = [int(b) for b in (detected_bands or []) if int(b) in scanned_set]
        return {"scanned_bands": scanned, "detected_bands": detected}
    if next_state is None:
        return None
    bands = next_state.bands
    scanned = [b.band_id for b in bands if b.time_since_last_scan == 0]
    detected = [b.band_id for b in bands if b.time_since_last_scan == 0 and b.consecutive_misses == 0]
    return {"scanned_bands": scanned, "detected_bands": detected}
