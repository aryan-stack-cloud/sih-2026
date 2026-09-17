# Smart Scan Strategy for Electronic Warfare — research findings and solution design

Problem statement: **SIH26055**, DRDO / Dept. of Defence Production (iDEX), Category Software.
Deliverable named by the portal: *"Machine learning based Electronic Support (ES) receiver
scheduler software."*

Scope reminder, unchanged: simulation-only. No real RF hardware, no interception of real signals,
no jamming, no weapon control.

Status: this document is the **design spec**. It supersedes nothing in `API_CONTRACT.md`; where it
requires a contract change, that change is listed explicitly in §9.

---

## 1. What the problem actually is

Strip the prose off the problem statement and three constraints remain.

1. **Two-dimensional search.** An intercept happens only when the receiver is tuned to the right
   band *at the right time*. Frequency alone is not enough. The statement says this outright:
   "Interception of signals is a two dimensional search problem since it involves adjusting
   receiver's frequency at correct time."
2. **Bandwidth deficit of at least one order.** Instantaneous bandwidth `K` bands out of `N` total,
   with `K/N ≤ 0.1`. Every step is an allocation decision under scarcity.
3. **No prior reliable intelligence.** The official objective line is "in the absence of prior
   reliable intelligence of emitters and their operating characteristics." This is the part that
   kills most naive solutions, and it is the part every published optimisation method assumes away.

The stated failure of the incumbent (open loop) is not that it is slow. It is that it is
*indiscriminate*: "may lose time to nonthreatening emitters by not giving time to new or
threatening ones." So the objective is **not** "scan faster". It is **allocate scarce look-time by
threat value while still guaranteeing coverage of the unknown**.

Those two halves pull in opposite directions. That tension is the whole problem, and §4 explains
why our current build sits on the wrong side of it.

---

## 2. Research findings

### 2.1 The classical intercept-theory chain

The ES scan-scheduling literature is small and highly specific. It runs like this.

| Work | Contribution that matters to us |
|---|---|
| Richards 1948; Miller & Schwarz 1953; Friedman 1954 | Coincidence of periodic pulse trains. The mathematical primitive. |
| Stein & Johansen 1958 | Coincidence among **random** pulse trains. The stochastic counterpart. |
| Self & Smith 1985, *Intercept time and its prediction*, IEE Proc. 132F | The **window function** model. An intercept requires simultaneous coincidence of every window: emitter spatial, emitter frequency, receiver spatial, receiver frequency. |
| Clarkson, Perkins & Mareels 1996, IEEE Trans. Inf. Theory 42(3) | First intercept time is a **Diophantine approximation** problem. Solved by continued-fraction convergents of the ratio of the two periods. |
| Kelly, Noone & Perkins 1996, IEEE Trans. AES 32(1) | **Synchronisation.** For certain period ratios the two windows *never* coincide. Intercept time is infinite. Deliberate jitter removes it. |
| Clarkson 2003, 2004, 2011 | Min-max intercept-time optimisation over sweep period **and** per-band dwell, via a Farey-series partition of the parameter plane. |
| Clarkson & Pollington 2007, IEEE Trans. AES 43 | **Performance limit.** Against emitters with unknown parameters, no deterministic search strategy beats a random one. |
| El-Mahassni & Howard 2005, IEE Proc. RSN | An optimally configured **continuous-time Markov chain** random strategy makes expected intercept time approach linearity in emitter scan period fastest and *smoothly*, without the abrupt spikes other strategies show. |
| Winsor & Hughes 2012, IET RSN | Genetic-algorithm optimised **aperiodic** dwell sequence. Phase-independent `P_I` computed by cross-correlating window functions. |
| Apfeld, Charlish & Koch, 2016 onward (Fraunhofer FKIE) | **Adaptive** scheduling: online autocorrelation estimate of emitter scan period drives dwell placement; revisit and dwell chosen per band by quality-of-service resource management under a receiver-time budget. |
| Clarkson 2019, IET RSN | Extension to **beam-agile** (multifunction, electronically scanned) radar, where the illumination pattern is not periodic at all. |
| IEEE 2025, *Machine Learning-based Receiver Scheduling for Electronic Support* | Model-free **Double DQN** receiver scheduler aimed at periodic-scan emitters. This is the current state of the art and the thing we must be measurably better than, or measurably more defensible than. |

### 2.2 The four results that determine our design

**(a) The intercept inequality and the synchronisation trap.** Following Clarkson, let the emitter
have scan period `T₁`, illumination time `τ₁`, phase `φ₁`; let the receiver have sweep period `T₂`,
dwell `τ₂`, phase `φ₂`. Define

```
α = T₂ / T₁                      period ratio
β = (φ₂ − φ₁) / T₁               normalised relative phase
ε = (τ₁ + τ₂ − 2d) / T₁          tolerance, with d the minimum coincidence duration
```

An intercept of at least duration `d` occurs whenever, for integers `p, q`,

```
| qα − p + β |  ≤  ε / 2
```

**Synchronisation occurs when `α` is rational, `α = h/k`, and `ε < 1/k`.** In that case there exist
relative phases for which the inequality is *never* satisfied. A perfectly healthy receiver sweeps
forever and never sees a perfectly healthy emitter. This is not a rare pathology; Clarkson's own
worked example has an emitter with `α = 1/21` that is invisible to a 1-second sweep until the dwell
in that band is raised to 438.8 ms.

Two escapes exist and we use both:
- lengthen the dwell in that band until `ε ≥ 1/k`, or
- **dither** the revisit interval so the receiver window is aperiodic and `α` is never a fixed
  rational.

**(b) Aperiodic beats periodic, and short dwells beat long ones.** Winsor & Hughes optimised the
dwell *sequence* rather than just the sweep period, and measured phase-independent `P_I` by sliding
the emitter and receiver windows across each other over all phase offsets. Their headline numbers,
at 10 ms dwell and a 60 s observation window against ten scanning radars:

| Strategy | Phase-independent `P_I` |
|---|---|
| GA-optimised aperiodic dwell sequence | 94.7% |
| Sweep of the 10 occupied channels only | 58.0% |
| Full 64-channel band sweep | 46.7% |

They also observed that the channel sweep's `P_I` was *independent of observation period*, which
they attribute to exactly the synchronisation limit above. Optimised aperiodic sequences are
immune to it by construction.

**(c) Against the unknown, random is the floor and nothing deterministic beats it.** This is
Clarkson & Pollington's result, and it is the single most important finding for SIH26055, because
SIH26055 is explicitly the no-prior-intelligence case. It has a sharp consequence: **any scheduler
that claims to beat random against genuinely unknown emitters is either exploiting learned
structure or is fooling itself on a lucky seed.** Our design therefore makes the split explicit. We
learn structure where structure exists, and we fall back to a provably-good randomised sweep where
it does not.

**(d) The decision problem has a name: restless bandit with reset.** Each band is a slowly-evolving
Markov process. Looking at a band reveals its state and *resets* the receiver's belief; not looking
lets belief drift toward the stationary distribution. Liu, Weber & Zhao (CDC-ECC 2011) prove this
class is **indexable** and give the **Whittle index in closed form**, and Liu & Zhao (IEEE Trans.
Inf. Theory 2010) give the closed-form index for Gilbert-Elliott channels with a *semi-universal*
structure that does not require knowing the transition probabilities. For `K` simultaneous looks,
the index policy is simply "activate the top `K` indices." That is a near-optimal, `O(N)`,
fully interpretable scheduler. It is the right spine for this system.

### 2.3 Data available

- **Turing Synthetic Radar Dataset** (Alan Turing Institute, Apache 2.0, ~70 GB). 6,000 pulse
  trains, ~4 billion pulses, 0–18 GHz, up to 90 emitters per train. Five-dimensional PDWs: time of
  arrival, centre frequency, pulse width, angle of arrival, amplitude. Crucially it ships **two
  receiver modes**: *stare* (full-spectrum ground truth, ~3.8 billion pulses) and *scan* (a
  sweeping receiver, ~282 million pulses). Stare mode is our ground-truth oracle; scan mode is the
  incumbent open-loop baseline, already generated for us. That pairing is a gift and we should
  build the whole evaluation around it.
- **JC Wise radar emitter database** for realistic PRF, PRI agility, stagger, hop intervals and
  antenna scan rates (circular, sector, raster) when configuring synthetic emitters.
- DRDO-side grounding, for the report: Defence Science Journal work on sub-Nyquist Pisarenko
  spectrum sensing, adaptive covariance-matrix sensing, cooperative double-threshold energy
  detection; the DLRL digital-receiver ELINT configuration paper; the *Modelling Radar-ECCM*
  monograph; Samyukta and the Smart Communication Jammer System as deployment context.

---

## 3. Where the state of the art stops

Every optimisation method above (Clarkson, Winsor & Hughes, and to a lesser degree Apfeld) requires
a **threat emitter list with known parameters**, and optimises **offline, pre-mission**. Winsor &
Hughes say so plainly: their genetic algorithm takes many generations and is intended to be run
before the mission.

SIH26055 asks for the opposite: **no reliable prior, decide online**. Nobody in that literature
solves that case, and the 2025 Double-DQN paper solves it by throwing away the theory entirely,
which buys performance at the cost of any ability to explain or bound behaviour.

**The gap we fill is the middle: an online scheduler that recovers the structure the offline
methods assume, uses it while it is valid, and falls back to a provably-bounded randomised strategy
when it is not.** That is the contribution, and it is defensible in front of a DRDO reviewer in a
way that "we trained a DQN" is not.

---

## 4. The problem with what we have built so far

From `Ai-ml-1-Scheduler-Engine/IMPLEMENTATION.md`, scenario B, five seeds, 1000 steps:

| Metric | round-robin | bandit |
|---|---|---|
| Pd | 0.1067 | **0.3454** |
| High-priority detection rate | 0.1014 | **0.3748** |
| Scan efficiency | 0.198 | **0.573** |
| Run intercept rate | **0.413** | 0.174 |
| Censored average intercept time | **587.8** | 826.1 |

The bandit wins on detection density and loses on coverage. The problem statement's primary
objective is "minimise intercept time and ensure a high interception rate." **On the objective the
problem statement names as primary, our ML scheduler currently loses to the baseline it is supposed
to beat.** A DRDO evaluator reading our own implementation notes will find this in a minute.

This is not a bug and it is not a tuning failure. It is structural, and the theory explains it
exactly:

- The reward is a single scalar that pays per detection. A scalar reward that pays for detections
  buys *density*: camp on the busiest bands.
- Intercept time and interception ratio are **coverage** objectives with deadline structure. They
  are not obtainable from a density reward by reweighting. The `w5_redundant` sweep in
  `IMPLEMENTATION.md` shows exactly this: it walks the frontier monotonically, trading Pd for
  coverage. There is no weight that gets both, because the two live on a Pareto frontier.
- And a policy that camps on busy bands is precisely the failure the problem statement complains
  about, only with the sign flipped. Open loop loses time to non-threatening emitters by treating
  all bands equally. A density-greedy bandit loses time to non-threatening emitters by *preferring
  the chatty ones*. A high-duty-cycle decoy is the ideal bait for it.

The fix is not a better reward. It is a **different decision architecture**: a coverage guarantee
expressed as a hard constraint, with value maximisation happening inside that constraint.

---

## 5. The solution

**Name:** Search–Confirm–Track index scheduler (SCT). One sentence: *a threat-weighted Whittle-style
index over per-band Bayesian beliefs, executed under hard revisit deadlines derived from
intercept-time theory, with a dithered randomised floor that guarantees worst-case performance
against emitters we know nothing about.*

Five blocks.

### Block 1 — Receiver and detection model

Makes the problem statement's figures of merit **derived physics rather than invented parameters**.

- Energy detection over a dwell of `N` samples. Threshold `λ` set from a target `P_fa` through the
  chi-square (Gaussian for large `N`) tail; `P_d` then follows from post-detection SNR along the
  ROC curve. This directly answers the statement's "Receiver Sensitivity and threshold detection
  performance" bullet, and it means `P_d` and `P_fa` are not free knobs we can quietly tune to make
  a slide look good.
- **Minimum coincidence duration `d`.** A dwell is only useful if it collects enough consecutive
  pulses to measure PRI and identify the emitter. Set `d = n_pulses × PRI_max(band)`. This is
  Clarkson's `d` in the intercept inequality, and it turns dwell time from a free variable into a
  constrained one. Typically `n_pulses = 3` to `5`.
- Retune dead time between dwells is charged explicitly against the budget. Winsor & Hughes'
  finding that short dwells raise `P_I` only holds until retune overhead dominates; the model has
  to show where that knee is.
- Both `K > 1` (simultaneous bands) and multi-receiver are supported, because the index policy
  extends to top-`K` selection with no change.

### Block 2 — Per-band belief state

Three cheap recursive estimators per band. All are `O(1)` per update.

**(a) Occupancy HMM.** Two-state Gilbert-Elliott chain, idle/active, per band. Transition matrix
estimated online with Dirichlet-smoothed counts, refined by Baum-Welch over the sparse observation
record. Yields `ω_i(t) = P(band i active now | history)`. Scanning band `i` resets `ω_i` to the
observation; not scanning drifts it toward stationarity. This is the reset structure that makes the
Whittle index available in closed form.

**(b) Period and phase posterior.** For bands showing repeated activity, estimate emitter scan
period `T₁` and phase `φ₁` from a gappy, irregularly-sampled intercept series. Use a
Lomb-Scargle periodogram (built for uneven sampling) plus a folded-phase histogram, and report a
**posterior over `(T₁, φ₁)` with a confidence**, not a point estimate. This is Ai-ml-2's real job,
and it is a genuine upgrade from mean inter-arrival: a point estimate cannot express "it is either
6 rpm or 12 rpm and I cannot yet tell," which is the state you are actually in after three
intercepts.

**(c) Change detector.** Per-band CUSUM or Bayesian online changepoint detection on the detection
rate. Fires when a new emitter appears or a known one changes mode. **This is the component that
serves "new or threatening" emitters, which is the problem statement's explicit complaint about
open loop.** Nothing else in the system reacts to novelty.

### Block 3 — The index

For each band `i` and candidate dwell `τ`, one scalar. Structured as a Whittle index, meaning: the
subsidy for *not* looking at which you would be indifferent between looking and not.

```
I_i(t, τ) =   w_thr  · P_threat(i) · ω_i(t) · P_d(τ, SNR_i)     expected threat-weighted hit value
            + w_inf  · ΔH_i(t)                                   information gain, pays for exploring
            + w_nov  · Novelty_i(t)                              changepoint bonus
            + w_stale· g( τ_since_i(t) / D_i )                   staleness pressure, hard at D_i
            − w_cost · c(current band → i)                       retune cost
```

Two parts of this are load-bearing.

**The revisit deadline `D_i` is a hard constraint, not a penalty.** `g(·)` diverges as
`τ_since_i → D_i`, so no band can be starved. `D_i` is not hand-tuned. It is derived from
Clarkson's min-max intercept-time construction: the revisit interval that bounds worst-case
intercept time for the slowest-scanning emitter plausibly present in band `i`. Before we have any
evidence about a band, `D_i` takes the conservative value implied by the slowest search radar we
would ever care about, around 3 rpm, so a 20 s observation floor. **This constraint is the direct
structural fix for the run-intercept-rate and censored-AIT losses in §4.**

**`P_threat(i)` is learned, not labelled.** "Absence of prior reliable intelligence" means we do not
get a threat emitter list. We infer threat from observable emitter character in the PDWs we do
collect: high PRF, narrow beamwidth, short revisit and continuous illumination indicate a tracker,
illuminator or missile seeker; slow circular scan with long revisit indicates surveillance. That is
a small supervised classifier over PDW-derived features, trainable on Turing stare-mode data where
the emitter labels exist. It is what lets the scheduler "not lose time to nonthreatening emitters."

### Block 4 — Randomisation floor

Two things a deterministic index provably cannot do.

**(a) Anti-synchronisation guard.** Before committing revisit interval `R_i`, test Clarkson's
condition against the current period posterior: if `α = R_i / T̂₁` sits near a rational `h/k` with
tolerance `ε < 1/k`, the schedule is in a lockout and will never intercept that emitter. Respond by
either extending the dwell until `ε ≥ 1/k`, or dithering `R_i` by a few percent so the receiver
window is aperiodic. **This is the specific, literal answer to the problem statement's line
"approaches to intercept a periodic scan receiver optimally should be outlined."** It is also the
most under-appreciated result in the whole area and will land well in a review.

**(b) Minimax floor via an optimally configured CTMC.** Reserve a fraction `ρ` of dwells for a
randomised coverage sweep over bands that are not yet characterised, drawn from the
continuous-time Markov chain configuration of El-Mahassni & Howard, whose expected intercept time
approaches linearity in emitter scan period fastest and without the abrupt spikes deterministic
sweeps show. `ρ` is adaptive:

- `ρ → 1` at mission start. Zero prior intelligence, which is exactly the SIH26055 opening
  condition.
- `ρ` decays as bands acquire confident occupancy models.
- `ρ` spikes back up when the change detector fires or when a band's model starts mispredicting.

This gives us a **worst-case guarantee against a perfectly adversarial frequency-agile emitter**
that no learned policy can offer, and it is the honest response to Clarkson & Pollington's
impossibility result rather than a claim to have beaten it.

### Block 5 — Learning, confined to where it earns its place

Do **not** learn the raw band choice with a deep network. Learn three narrow things.

1. **The occupancy transition kernels**, online, from hits and misses. This is literally what the
   problem statement asks for: "The model should then be trained based on hits and misses."
2. **The six index weights and the exploration fraction `ρ`**, by CMA-ES or Bayesian optimisation
   on the simulator, per scenario class. Seven numbers. Trains in minutes, is stable, cannot
   diverge, and every learned value is human-readable and can be defended line by line.
3. **A learned residual index** (NeurWIN / DeepTOP style: the network outputs an *index*, not an
   action) as the V2 stretch. This is the only place a neural network is warranted, and even there
   the output stays interpretable and the hard deadlines still bind.

The existing DQN and PPO agents stay in the repository as comparison arms. They are how we show
the index scheduler matches or beats model-free deep RL while remaining explainable. That is a
stronger story than shipping the DQN as the answer.

### The loop, concretely

Per decision epoch:

1. Drift beliefs for unscanned bands; reset belief for the band just scanned.
2. Ai-ml-2 batch-predicts `(T̂₁, φ̂₁, confidence)` for all bands in one call.
3. Compute `I_i(t, τ)` for every band and each candidate dwell length.
4. Force to the top any band with `τ_since_i ≥ D_i`. Deadlines bind before value maximisation.
5. With probability `ρ`, draw the next band from the CTMC over uncharacterised bands instead.
6. Run the anti-synchronisation guard; dither the dwell or revisit if it trips.
7. Select the top `K` bands by index. Execute. Observe.
8. Feed the outcome to the HMM, the period posterior and the change detector.

---

## 6. Evaluation design

The problem statement lists its own figures of merit. Map them exactly, and add the two that make
the comparison honest.

| Statement's metric | How we compute it |
|---|---|
| `P_d`, `P_fa` | From the detector ROC. `P_d` over all band-steps, so an unvisited active band is a false negative. `P_fa` over scanned band-steps only. The asymmetry is deliberate and must stay documented. |
| Receiver sensitivity, threshold performance | The ROC sweep itself: `P_d` against SNR at fixed `P_fa`, and the threshold-vs-`P_fa` curve. |
| Average intercept rate | Activation runs intercepted, divided by activation runs occurring. |
| Average intercept time | Reported **censored**: undetected runs charged the full episode. Raw AIT is conditioned on detection succeeding and therefore ranks the better policy lower, which we already found the hard way. Report both, label both. |
| Average intercept **time error** | Absolute error between predicted next-active window and the true one. This is Ai-ml-2's own accuracy and belongs on its own axis. |
| Average reward / cost function | The index's realised value, decomposed per term, so the demo can show *why* a band was chosen. |
| Percentage of correct predictions | Hit rate of dwells placed on a predicted active window. |
| Interception ratio | Distinct emitters intercepted at least once, divided by emitters present. |

Two additions that are not optional:

- **Phase-independent `P_I`.** Sweep each emitter's initial phase across its full range and report
  the fraction of phases yielding at least one intercept inside the observation window. This is
  Winsor & Hughes' method and it is what removes the "you got a lucky seed" objection. It is the
  metric that makes a "we beat open loop" claim survive scrutiny.
- **Worst-case intercept time over emitters.** Clarkson's min-max criterion. A DRDO reviewer does
  not care about your mean if you never saw the one tracker that mattered.

**Baseline ladder.** Five arms, in increasing strength:

1. Round-robin full-band sweep. The incumbent.
2. Channel sweep restricted to occupied bands. A stronger, slightly unfair baseline.
3. Uniform random band selection.
4. Optimally configured CTMC random. The theoretical floor from §2.2(c).
5. GA-optimised offline schedule computed **with full prior knowledge of every emitter**. This is
   the oracle upper bound.

The money result is arm 5 versus SCT: *we approach an oracle that was given the threat emitter
list, without being given the threat emitter list.* That is the claim worth making, and the
baseline ladder is what earns the right to make it.

**Scenarios.** Six, each designed to break something.

| Scenario | What it breaks | Expected story |
|---|---|---|
| Synchronisation trap: emitter scan period an exact rational multiple of the sweep period | Round-robin, and any fixed-period schedule | Baseline `P_d` near zero indefinitely; the anti-sync dither intercepts within one revisit. The most striking demo in the set. |
| Cold start, zero prior, unknown emitter count | Everything that assumes a threat list | Shows `ρ` starting at 1 and annealing as structure is found |
| Pop-up threat at `t = T/2` in an abandoned band | Density-greedy bandit | Deadline `D_i` plus changepoint detector catch it; the bandit does not |
| Chatty harmless decoy with high duty cycle | Reward-greedy anything | The problem statement's exact complaint. Threat-weighted index declines the bait. |
| Frequency-agile hopper, up to ~2000 hops/s | Learned models generally | Falls back to the CTMC floor; bounded, not catastrophic |
| Beam-agile multifunction radar, non-periodic illumination | Periodicity estimation | Confidence stays low, `ρ` stays high, no false confidence. Matches Clarkson 2019. |

Reproducibility rules stay as they are: identical scenario, identical seed, all arms, seed and
config logged per experiment.

---

## 7. Why this wins the argument, not just the metric

Four things a reviewer will test, and the answer to each.

- **"Where is your prior intelligence coming from?"** It is not. `ρ = 1` at start and the CTMC floor
  is provably good against the unknown. Everything learned is learned in-mission.
- **"What stops it starving a band?"** A hard revisit deadline derived from min-max intercept-time
  theory, not a soft penalty weight. It binds before value maximisation.
- **"Why should I trust a neural network with my spectrum?"** You do not have to. The scheduler is
  an index with six named terms, and the demo shows the decomposition for every decision. The
  neural arm exists only as a comparison, and the deep-RL arms are in the repo to be beaten or
  matched.
- **"How do I know this is not overfitted to your simulator?"** Turing scan mode is a
  third-party-generated open-loop receiver trace with stare-mode ground truth beside it. We
  evaluate against it, not only against our own generator.

And the honest limitation, stated first rather than extracted: **against a genuinely adversarial,
genuinely unpredictable emitter, no scheduler beats randomised search.** That is Clarkson &
Pollington, it is a theorem, and our design does not claim to break it. What we claim is that real
emitters are not adversarial most of the time, and that the moment they display any structure we
exploit it, while never dropping below the random floor when they do not. That framing turns an
apparent weakness into evidence that we read the literature.

---

## 8. How we build it

The four-folder split in `API_CONTRACT.md` survives intact. The work lands as follows.

### Ai-ml-1 — Scheduler Engine (owned in this repo)

| Step | Work | Notes |
|---|---|---|
| 1 | Per-band occupancy HMM with online kernel estimation | New module. Replaces the bandit's per-band scalar estimates. |
| 2 | Whittle-style index with the six terms of §5 Block 3 | New policy, registered as `policy_type: "index"` |
| 3 | Hard revisit deadlines `D_i` derived from min-max theory | The §4 fix. Highest priority item in the whole plan. |
| 4 | Anti-synchronisation guard and dither | Small, self-contained, high demo value |
| 5 | CTMC randomised floor with adaptive `ρ` | Also becomes baseline arm 4 |
| 6 | Threat classifier over PDW features | Trained on Turing stare mode |
| 7 | CMA-ES weight tuning per scenario class | Replaces reward-weight hand-tuning |
| 8 | Keep bandit, Q-learning, DQN, PPO as comparison arms | No deletion. They are the evidence. |
| 9 | GA offline oracle | Baseline arm 5. Winsor & Hughes' method. |

### Ai-ml-2 — Periodicity Estimator

| Step | Work |
|---|---|
| 1 | Replace point-estimate period with a `(T₁, φ₁)` **posterior** plus calibrated confidence |
| 2 | Lomb-Scargle periodogram for unevenly sampled intercept series |
| 3 | Folded-phase histogram for phase recovery |
| 4 | CUSUM / Bayesian online changepoint detection per band |
| 5 | Expose `α`, `ε` and a synchronisation-risk flag so Ai-ml-1's guard can act on them |

The existing batch endpoint stays; the response gains fields (§9).

### Backend

| Step | Work |
|---|---|
| 1 | Carry `D_i` deadlines and staleness in the `StateVector` |
| 2 | Log the per-term index decomposition per decision, for the explainability panel |
| 3 | Implement the censored-AIT, phase-independent `P_I` and worst-case-intercept-time metrics |
| 4 | Add the six scenarios of §6 as configurations |
| 5 | Add a Turing scan-mode replay source alongside the synthetic generator |

### Frontend

| Step | Work |
|---|---|
| 1 | Waterfall stays; overlay the chosen band and dwell on the truth spectrum |
| 2 | **Index decomposition panel**: for the current decision, a stacked bar of the six terms. This is the credibility moment of the demo. |
| 3 | Phase-sweep `P_I` plot, our policy against all five baseline arms |
| 4 | Synchronisation-trap scenario view, showing the baseline flatlining and SCT intercepting |

### Suggested order

1. Deadlines and staleness (§8 Ai-ml-1 step 3). Fixes the losing metric first.
2. Index policy and HMM beliefs (steps 1–2).
3. Anti-synchronisation guard plus the synchronisation-trap scenario. Small, and it is the demo.
4. Ai-ml-2 posterior and changepoint.
5. CTMC floor, adaptive `ρ`, cold-start scenario.
6. Threat classifier, decoy scenario.
7. Baseline ladder arms 4 and 5, phase-independent `P_I`.
8. Frontend explainability panel.
9. Weight tuning, full six-scenario sweep, final numbers.

Items 1 through 3 alone convert the current result from "loses on the primary objective" to "wins
on the primary objective with a provable coverage guarantee." Everything after that is margin.

---

## 9. Required contract changes

To be made in `API_CONTRACT.md` first, then propagated to all four copies in one commit.

1. `policy_type` enum gains `index`. Existing values unchanged.
2. `StateVector.bands[]` gains `revisit_deadline`, `staleness_ratio`, `threat_score`,
   `occupancy_belief`, `sync_risk`.
3. Ai-ml-2's `predict/batch` response gains `period_posterior` (a small set of candidate periods
   with weights), `phase_confidence`, `alpha`, `epsilon`, `sync_risk`, and `changepoint_flag`.
4. `/internal/decide` response gains an optional `index_breakdown` object, six named terms, for the
   explainability panel and the decision log.
5. Metrics payloads gain `pi_phase_independent`, `worst_case_intercept_time`, and keep
   `ait_censored` alongside `ait`.

No endpoint is removed and no existing field changes meaning, so the four folders can adopt these
independently.

---

## 10. Corrections to the current submission material

Three things in the existing deck that will cost marks:

1. The theme is listed as **"Clean & Green Technology."** The official problem statement lists the
   theme as **Robotics and Drones**. Fix before submission.
2. The references slide lists three entries pointing at the same DOI (`rsn2.12337`) under different
   titles. A reviewer who clicks two of them will notice. Replace with the §2.1 chain, which is the
   actual literature for this problem.
3. The technical-approach slide leads with "Contextual Multi-Armed Bandit." Given §4, lead with the
   index scheduler and coverage guarantee instead, and keep the bandit as a comparison arm.

---

## 11. Open questions for the team

1. Is `K`, the receiver's instantaneous bandwidth in bands, fixed at 2, or should the scenarios
   sweep it? The index policy handles any `K` unchanged, but the story differs at `K = 1`.
2. Do we commit to Turing scan-mode replay as a primary evaluation source, or keep it as a
   secondary validation? It is 70 GB and that is a real logistics cost for a demo machine.
3. How much of the deep-RL work do we present? The recommendation is: present it as a comparison
   arm we match while staying explainable, not as the headline.
