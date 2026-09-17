# SIH26055 — Complete solution specification
## Search–Confirm–Track (SCT): a closed-loop ES receiver scheduler for the no-prior-intelligence case

Companion to `2026-09-11-smart-scan-strategy-design.md`, which holds the literature review and the
argument for this shape. **This document is the solution itself**: formal model, derived
constants, exact algorithms, stated guarantees, measurement protocol and build order. Everything
here is specified tightly enough to implement without further design decisions.

Scope: simulation-only. No RF hardware, no real interception, no jamming, no weapon control.

**Every numeric claim in this document is reproducible.** Run `verify_solution_constants.py` beside
this file, which recomputes the detection table of §4.3.1, the deadline and feasibility figures of
§5, the hopper probabilities of §8.2, and the three-gap statistics of §6.3. Standard library only,
no dependencies. If a number here and a number it prints ever disagree, the script is right.

---

## 0. The solution in one page

The problem statement asks for a scheduler that beats open-loop sweeping when you have **no
reliable prior intelligence**. The literature says that in that regime nothing deterministic beats
random (Clarkson & Pollington 2007), and that fixed-period sweeps can be **permanently blind** to
perfectly healthy emitters (Kelly, Noone & Perkins 1996). So a scheduler that is only "smarter
about where to look" is answering the wrong question.

SCT answers the right one. It is a **rate-normalised index policy over per-band Bayesian beliefs**,
executed under **hard revisit deadlines derived from intercept-time theory**, with **golden-ratio
phase dithering** that makes synchronisation lockout impossible, and a **randomised floor** that
bounds worst-case behaviour against emitters no model can predict.

Five claims, each earned in a numbered section below:

| # | Claim | Where |
|---|---|---|
| G1 | Every band is revisited within a deadline derived from the worst-case intercept-time requirement, so no emitter class can be starved. | §5, §9 |
| G2 | Synchronisation lockout occurs with probability zero, and phase coverage is maximally uniform (three-gap theorem). | §6 |
| G3 | Against an arbitrary, even adversarial, emitter, expected intercept time is at most `1/ρ` times the randomised floor's. Degradation is graceful, never catastrophic. | §7 |
| G4 | Where the two-state occupancy model holds, the policy coincides with the Whittle index policy for restless bandits with reset, which is optimal for stochastically identical arms. | §4 |
| G5 | The dwell-length decision resolves the sensitivity-versus-coverage trade-off automatically, because the index is a value **rate**, not a value. | §4.3 |

None of the five is available from a reward-shaped bandit or a model-free deep network. That is
the whole reason for this architecture.

---

## 1. Formal system model

### 1.1 Time

| Symbol | Meaning | Value used |
|---|---|---|
| `Δ` | slot, the minimum dwell quantum | 10 ms |
| `m` | dwell length in slots, `m ∈ M` | `M = {1, 2, 4, 8}` |
| `δ(i→j)` | retune dead time between bands | `δ₀ + δ₁·|f_i − f_j|`, `δ₀ = 2 ms`, `δ₁ = 0.2 ms/GHz` |
| `T_ep` | episode length | 60 s = 6000 slots |

`Δ = 10 ms` is not arbitrary. It is the minimum dwell at which a receiver can collect enough
consecutive pulses to measure PRI and identify an emitter across a realistic threat set, and it is
the value Winsor & Hughes derive for the same reason.

The retune cost being frequency-dependent matters: it gives the index a physical reason to prefer
nearby bands, so locally sweep-like behaviour **emerges** rather than being hard-coded.

### 1.2 Spectrum and receiver

`N` bands of width `B`. Total surveillance bandwidth `W = N·B`. Receiver instantaneous bandwidth
`K·B` with `K/N ≤ 0.1`, per the problem statement's "at least an order lower".

Three receiver modes, all supported by the same index:

| Mode | Physical analogue | Action space | Selection rule |
|---|---|---|---|
| `contiguous` | single scanning superheterodyne | window start `w ∈ {1..N}`, wrapping | sliding-window max of index sum, `O(N)` |
| `channelized` | FFT / digital channelised receiver | any `K`-subset | top-`K` index, `O(N log K)` |
| `multi_receiver` | `R` independent tuners | `R` windows | greedy assignment with retune costs |

The existing engine already implements `contiguous`, which is the honest default for a swept
superhet. `channelized` is the DLRL quad-digital-receiver analogue.

### 1.3 Emitters

Emitter `e` is a tuple `(F_e, T_e, τ_e, φ_e, PRI_e, PW_e, γ_e, θ_e, class_e)`:

- `F_e` set of bands it may occupy; `f_e(t)` the occupied band at slot `t`
- `T_e` antenna scan period, `τ_e` illumination time toward the receiver, `φ_e` scan phase
- `PRI_e` pulse repetition interval, `PW_e` pulse width
- `γ_e` post-detection SNR at the receiver, `θ_e` bearing
- `class_e ∈ {surveillance, acquisition, track, illuminator, seeker}`

The five behaviour classes in the contract map onto this cleanly:

| `behavior_class` | Realisation | Notes |
|---|---|---|
| `fixed` | `w_e(t) ≡ 1`, `|F_e| = 1` | tracker or illuminator, continuous. Trivial to intercept once found. |
| `periodic` | `w_e(t) = 1[((t−φ_e) mod T_e) < τ_e]` | circular-scan search radar. **The synchronisation-trap class.** |
| `agile` | `f_e(t)` hops over `F_e` every `T_hop` | frequency-hopping. See §8.2 for why fast hoppers are easier than slow ones. |
| `random` | Gilbert–Elliott chain `(p₀₁, p₁₀)` | the model our belief tracker is exactly matched to |
| `intermittent` | bursty on/off, heavy-tailed idle | the pop-up-threat class |

Ground truth occupancy `O_i(t) = 1` iff some emitter illuminates band `i` at slot `t`.

### 1.4 The three conditions for a *useful* intercept

This is where most treatments of the problem stop one condition short.

1. **Frequency coincidence.** `i ∈ A_t` and `f_e(t) = i`.
2. **Temporal coincidence.** `w_e(t) = 1` for at least the minimum coincidence duration `d`.
3. **Energy.** Detection statistic exceeds threshold, which happens with probability `P_d(m, γ_e)`.

The problem statement's "two dimensional search problem" is conditions 1 and 2. Condition 3 is the
sensitivity axis, and it is coupled to the schedule through dwell length. **Ignoring condition 3
is what lets a scheduler report a good intercept rate while producing intercepts too short to
identify anything.** SCT charges for it explicitly.

Minimum coincidence duration: `d_i = n_p · PRI_max(i)` with `n_p = 5`. A dwell shorter than `d_i`
yields at most a *detection*, never an *identification*, and the index gives it partial credit
only.

---

## 2. Detection model — figures of merit as derived physics

Energy detection over `N_s = m·Δ·B` complex samples. Under the Gaussian approximation valid for
`N_s > 50`:

```
P_fa(λ)     = Q( (λ − N_s σ²) / (σ² √(2 N_s)) )
P_d(λ, γ)   = Q( (λ − N_s σ²(1+γ)) / (σ²(1+γ) √(2 N_s)) )
```

Eliminating the threshold gives the operating relation the whole system uses:

```
P_d(m, γ) = Q( ( Q⁻¹(P_fa) − γ √(N_s / 2) ) / (1 + γ) ),      N_s = m · Δ · B
```

Three consequences, all of which the scheduler must respect:

1. **`P_fa` is a design input, not an output.** Fix `P_fa` at the mission requirement, e.g. `10⁻³`.
   The threshold follows. This answers the statement's "Receiver Sensitivity and threshold
   detection performance" bullet with a curve rather than a number.
2. **`P_d` is a sigmoid in `√m`.** The integrated deflection grows like `√N_s`, so `P_d` sits near
   zero, then rises sharply, then saturates. Doubling the dwell buys `√2` in deflection, which is
   worth a great deal in the rising region and nothing at either end. This is the sensitivity axis
   of the trade-off, and §4.3.1 shows why its shape matters more than its slope.
3. **Sensitivity and coverage are in direct competition**, because `m` slots spent here are `m`
   slots not spent elsewhere. §4.3 resolves this without a tuning constant.

The existing engine already scales effective SNR by `√(observe_ms / step_ms)`, which is the same
relation. Good; keep it, and make `P_fa` the configured quantity.

**On `N_s`.** Written as `m·Δ·B` this is the raw complex-sample count, which for a 250 MHz analysis
bandwidth and a 10 ms slot is 2.5 million, and the matching per-sample `γ` is correspondingly tiny
because a microsecond pulse occupies a vanishing fraction of the dwell. Carrying both extremes
through the simulation is numerically pointless. Parameterise instead by the **effective number of
independent integration samples per slot**, `n_eff`, with `γ` the dwell-averaged post-detection
SNR, so `N_s = n_eff · m`. Then `n_eff` and `γ` are the two knobs a scenario sets, and they mean
something a radar engineer can argue with. The worked figures throughout this document use
`n_eff = 100`.

**Reporting rule that must not drift.** `P_d` is counted over *all* band-slots where `O_i(t) = 1`,
so an active band never looked at is a false negative. `P_fa` is counted over *scanned* band-slots
only, because an unscanned band cannot raise an alarm. The asymmetry is deliberate: it is the only
counting convention under which a scheduler that stares at one band forever does not report a
perfect `P_d`.

---

## 3. Belief state

Four estimators per band. All are `O(1)` per update except the periodicity refit, which runs only
when a band produces a new detection, so at most `K` refits per epoch.

### 3.1 Occupancy belief with imperfect sensing

Two-state chain per band, transition matrix `P⁽ⁱ⁾ = [[p₀₀, p₀₁], [p₁₀, p₁₁]]`.
Belief `ω_i(t) = P(O_i(t) = 1 | all observations up to t)`.

**Predict**, every slot, for every band:

```
ω_i(t+1 | t) = ω_i(t)·p₁₁⁽ⁱ⁾ + (1 − ω_i(t))·p₀₁⁽ⁱ⁾
```

**Correct**, only for scanned bands, using the detector's own `P_d` and `P_fa`:

```
detection:     ω ←  ω·P_d       / ( ω·P_d       + (1−ω)·P_fa     )
no detection:  ω ←  ω·(1−P_d)   / ( ω·(1−P_d)   + (1−ω)·(1−P_fa) )
```

This is the exact POMDP belief update. It is worth stating why it matters: a naive implementation
sets `ω ← 1` on detection and `ω ← 0` on a miss, which silently assumes a perfect sensor and makes
the scheduler over-confident exactly where false alarms are most damaging. With imperfect sensing
the update is a **soft** reset, and the amount of reset is governed by the detector's own ROC. The
two models are consistent by construction.

Repeated non-detection drives `ω` toward the chain's stationary value `p₀₁/(p₀₁+p₁₀)`, not to
zero. That is correct and it is what keeps the scheduler from writing a band off permanently.

**Learning `P⁽ⁱ⁾`.** Dirichlet(1,1) priors over each row. Sufficient statistics updated from
belief-weighted transitions, with a forgetting factor `κ = 0.995` per slot so the estimate tracks
a non-stationary environment. Every `H = 200` slots, run five Baum-Welch iterations per band over
the retained observation window. Cost is negligible and it runs on the slow loop, off the
per-decision critical path.

### 3.2 Period and phase posterior — using hits *and* misses

The problem statement says "The model should then be trained based on hits and misses." Almost
every implementation uses only hits. Using misses is both free and much more informative, because
a look that found nothing at time `t` **rules out** every `(T, φ)` pair that predicted activity at
`t`. That is the single biggest accuracy lever in the whole estimator.

Let the record for band `i` be `{(t_k, z_k)}` over scanned slots, `z_k ∈ {0,1}` the detection
outcome. Hypothesise a periodic emitter with period `T`, phase `φ`, duty `u = τ/T`. Predicted
illumination:

```
w_k(T, φ, u) = 1[ ((t_k − φ) mod T) / T  <  u ]
```

Log-likelihood over the whole record, hits and misses alike:

```
ℓ(T,φ,u) = Σ_k  z_k · log[ w_k·P_d + (1−w_k)·P_fa ]
              + (1−z_k) · log[ w_k·(1−P_d) + (1−w_k)·(1−P_fa) ]
```

Grid: `T` log-spaced over `[T_min, T_max] = [0.5 s, 30 s]`, 200 points, because scan rates of
interest span roughly 2 rpm to 120 rpm and log-uniform is the right prior over a rate.
`φ` on 64 points per candidate `T`. `u ∈ {0.002, 0.005, 0.01, 0.02, 0.05, 0.1}`.

Posterior `p(T, φ, u | data) ∝ exp(ℓ) · prior`. Marginalise for `p(T | data)`.

**Report the top `J = 3` modes with weights, never the argmax.** With sparse sampling, `T`, `T/2`
and `T/3` are genuinely confusable, and a point estimate cannot express "it is either 6 rpm or
12 rpm and I cannot yet tell", which is the true state after three intercepts. Downstream, §6
needs the full posterior anyway.

Cost: incremental. Adding one look is one multiply per grid cell, `200 × 64 × 6 = 76,800`
multiplies, sub-millisecond in NumPy, and only for bands that were scanned.

Derived quantities exported for the synchronisation guard:

```
α = R_i / T̂        period ratio for planned revisit R_i
ε = (τ̂ + mΔ − 2d_i) / T̂    tolerance
```

### 3.3 Change detection

Bayesian online changepoint detection (Adams & MacKay) on the Bernoulli detection stream per band,
hazard rate `1/500` slots. Output `ν_i(t) = P(changepoint within last H slots)`.

On a fired changepoint: reset that band's period posterior to prior, halve the confidence, and
raise the exploration mixing fraction (§7). **This is the only component in the system that reacts
to novelty**, and novelty is precisely what the problem statement says open loop fails at:
"not giving time to new or threatening ones."

### 3.4 Threat score, learned rather than labelled

"Absence of prior reliable intelligence" means there is no threat emitter list. Threat must be
inferred from what the collected PDWs reveal about emitter *character*:

| Feature | Source | Threat direction |
|---|---|---|
| PRF | `1/PRI` from SDIF histogram on the pulse train | higher is more threatening |
| PRI stagger / jitter | SDIF residual structure | agility indicates ECCM, raises threat |
| Pulse width | PDW | shorter indicates fire control |
| Duty cycle toward receiver | `τ̂/T̂` from §3.2 | higher indicates tracking, not searching |
| Revisit interval | `T̂` | shorter indicates tracking |
| Frequency agility | band-set entropy | raises threat |
| Amplitude trend | PDW amplitude over time | rising indicates closing |

Gradient-boosted tree over these seven features, trained offline on Turing **stare-mode** data
where emitter labels exist, applied online to whatever has been collected. Output `R_i ∈ [0,1]`,
the band's threat weight, mixed with a uniform prior weighted by evidence count so an unobserved
band is neither favoured nor penalised.

Doctrinally this is the standard distinction: a slow circular scan with long revisit is
surveillance, a short revisit with high duty cycle and high PRF is acquisition or track. It is
what lets the scheduler "not lose time to nonthreatening emitters", which is the statement's
literal complaint.

**Note on deinterleaving.** Several emitters can share a band. Before per-emitter periodicity is
meaningful, cluster detections into emitter tracks on `(RF, PW, AoA)`. Angle of arrival is in the
PDW, which makes co-band separation genuinely tractable. This is the same task the Turing
Deinterleaving Challenge poses, so the dataset supplies both the training data and a public metric.

---

## 4. The index

### 4.1 Why an index at all

Scanning a band reveals its state and resets the belief; not scanning lets belief drift toward
stationarity. That is exactly the **restless bandit with reset** structure, which Liu, Weber and
Zhao proved indexable with a closed-form Whittle index, equivalent to the myopic policy, and
optimal for stochastically identical arms. Liu and Zhao give the closed form for Gilbert-Elliott
channels with a *semi-universal* structure that does not require knowing the transition
probabilities.

Practically this buys three things a learned policy cannot: it is `O(N)`, it is near-optimal with a
proof attached, and every decision decomposes into named terms you can put on a slide.

Honesty about scope: the exact closed form is proved for identical arms with perfect sensing. Our
arms are heterogeneous and our sensing is imperfect. SCT therefore uses a **Whittle-style index
that reduces to the exact Whittle index in that special case** and is computed by one-step
lookahead otherwise. That is the standard and defensible construction, and it should be described
that way rather than overclaimed.

### 4.2 The index, term by term

For band `i`, candidate dwell `m`, at slot `t`:

```
                w_v · R_i · ω_i(t) · P_d(m, γ̂_i) · U_i(m)  +  w_I · ΔH_i(t,m)  +  w_n · ν_i(t)  +  w_D · κ_i(t)
I_i(t, m)  =   ────────────────────────────────────────────────────────────────────────────────────────────────
                                              m·Δ  +  δ(a_{t−1} → i)
```

**Correction, forced by measurement.** An earlier draft of this document put the deadline term
outside the division, on the argument that a constraint multiplier is not value. Implementation
rejected that. The value terms carry units of "per second"; a bare barrier is dimensionless. The
barrier therefore only outbid value in the last few percent before the deadline, far too late to
drain a queue of stale bands through a receiver that serves one at a time, and staleness overran a
29-slot deadline by ten slots. Dividing it too makes the whole index one rate, the barrier begins
winning at roughly 40% of the deadline, and coverage stays ahead. It still dominates any finite
value, because the barrier diverges. `tests/test_index_agent.py` pins the guarantee down.

| Term | Meaning | Why it is there |
|---|---|---|
| `R_i` | learned threat weight, §3.4 | "give time to threatening ones" |
| `ω_i(t)` | occupancy belief, §3.1 | expected value of a look |
| `P_d(m, γ̂_i)` | detection probability at this dwell, §2 | couples sensitivity into scheduling |
| `U_i(m)` | identification credit: `1` if `mΔ ≥ d_i`, else `mΔ/d_i` | a hit too short to identify is worth less |
| `ΔH_i(t,m)` | expected entropy reduction of `ω_i` | principled exploration, replaces ε-greedy |
| `ν_i(t)` | changepoint probability, §3.3 | pays for novelty |
| `κ_i(t)` | deadline pressure, §5 | the coverage guarantee |
| denominator | dwell plus retune time | makes the whole thing a **rate** |

### 4.3 Why the denominator is the key design decision

Dividing by elapsed time turns the index into **expected value per unit of receiver time**. Three
things fall out of that single choice, and none of them needs a tuning constant:

1. **The dwell-length decision solves itself**, and it does so in a way that is worth looking at
   closely. See §4.3.1.
2. **Retune cost is priced correctly.** Switching to a distant band costs real time and is charged
   in the same units as the dwell. Locally sweep-like behaviour emerges.
3. **It is the right objective for a semi-Markov decision problem** with variable action durations.
   Maximising reward per unit time is the standard criterion; maximising reward per *decision*
   would systematically over-value long dwells.

#### 4.3.1 The optimal dwell is non-monotone in SNR

`P_d(m, γ)` is not proportional to `√m`. It is a **sigmoid in `√m`**: near zero while the
integrated deflection is below threshold, then rising sharply, then saturating at 1. Divided by a
denominator linear in `m`, the value rate therefore has an **interior maximum** whose location
depends on SNR.

Computed at `P_fa = 10⁻³`, 100 independent integration samples per slot, `Δ = 10 ms`, `δ = 5 ms`.
Rate is `P_d / (mΔ + δ)`, in units of detections per second.

| `γ` | dB | `m=1` `P_d` / rate | `m=2` `P_d` / rate | `m=4` `P_d` / rate | `m=8` `P_d` / rate | best `m` |
|---|---|---|---|---|---|---|
| 0.05 | −13 | 0.005 / 0.31 | 0.007 / 0.27 | 0.012 / 0.26 | 0.023 / 0.27 | **1** |
| 0.10 | −10 | 0.015 / 1.01 | 0.029 / 1.15 | 0.064 / 1.42 | 0.161 / 1.89 | **8** |
| 0.20 | −7 | 0.081 / 5.4 | 0.182 / 7.3 | 0.414 / 9.2 | 0.776 / 9.1 | **4** |
| 0.30 | −5 | 0.228 / 15.2 | 0.472 / 18.9 | 0.812 / 18.1 | 0.987 / 11.6 | **2** |
| 0.50 | −3 | 0.617 / 41.1 | 0.899 / 35.9 | 0.996 / 22.1 | 1.000 / 11.8 | **1** |
| 1.00 | 0 | 0.977 / 65.1 | 1.000 / 40.0 | 1.000 / 22.2 | 1.000 / 11.8 | **1** |

The optimal dwell **peaks at marginal SNR and falls away on both sides**. Three regimes:

- **Strong signal**, `γ ≳ −4 dB`: one slot suffices. Longer dwells buy nothing and cost coverage.
- **Marginal signal**, `−11 dB ≲ γ ≲ −6 dB`: long dwells pay. Integration is what lifts the signal
  over the threshold, so eight slots can be worth eight times the time.
- **Hopeless signal**, `γ ≲ −12 dB`: back to one slot. Integration over the available dwell range
  cannot rescue it, so spending eight slots is throwing away coverage for nothing.

That third regime is the one a hand-tuned rule always gets wrong, and it is exactly the behaviour
you want: **the scheduler declines to keep digging for a signal it cannot reach.** No reward weight
produces this. It falls out of the rate normalisation for free, and it is claim **G5**.

Operationally, `γ̂_i` is not known before the first detection in a band. Use the belief-weighted
expectation over the SNR posterior, which is broad early and sharpens with evidence. Early in a
mission the expectation sits in the marginal regime, so the scheduler naturally starts with longer
dwells and shortens them as it learns which bands are loud.

The comparison with our current reward function is stark. Equation 10.1 pays a fixed `w1` per
detection regardless of how long the dwell took, so it cannot express "this detection cost me eight
slots and that one cost me one." The rate normalisation is what makes the trade-off visible to the
scheduler at all.

### 4.4 Selection

- `contiguous`: choose window start `w` maximising `Σ_{i ∈ window(w)} I_i(t,m)` over `w` and `m`.
  Sliding-window sum, `O(N·|M|)`.
- `channelized`: top-`K` by index.
- Any band with `τ_i(t) ≥ D_i` is forced into the action set before value maximisation runs.
  Deadlines bind first. Always.

---

## 5. Deriving the revisit deadline `D_i`

This is the fix for the coverage loss documented in `IMPLEMENTATION.md`, and it is derived from
intercept-time theory rather than picked.

Suppose band `i` may hold a periodic emitter with scan period `T ≤ T_max` and illumination time
`τ_ill`. If we revisit with interval `R` and dwell `mΔ`, and the periods are **not** commensurate,
each look hits the illumination window with probability approximately `(τ_ill + mΔ)/T`. So

```
E[looks to intercept]  ≈  T / (τ_ill + mΔ)
E[time to intercept]   ≈  R · T / (τ_ill + mΔ)
```

Impose the mission requirement `E[time to intercept] ≤ T_req` for the worst case `T = T_max`:

```
                τ_ill + m·Δ
D_i  =  T_req · ───────────
                   T_max
```

**Worked example, and these are the numbers to put in the report.**

| Quantity | Value |
|---|---|
| Slowest search radar of interest | 3 rpm, so `T_max` = 20 s |
| Beamwidth | 1.5°, so `τ_ill` = (1.5/360)·20 s = 83 ms |
| Dwell | `mΔ` = 10 ms |
| Worst-case intercept requirement `T_req` | 60 s |
| **Derived deadline `D_i`** | 60 · (0.083 + 0.010) / 20 = **280 ms** |

Now check it is affordable. With `N = 16` and `K = 2`, one full coverage cycle is 8 dwells. At
10 ms dwell plus about 5 ms retune, that is 120 ms.

| Budget line | Value |
|---|---|
| Guaranteed coverage cycle | 120 ms |
| Deadline | 280 ms |
| **Fraction of receiver time committed to coverage** | **43%** |
| **Fraction free for threat-driven scheduling** | **57%** |

That single table is the answer to "how do you get both speed and selectivity". You do not choose
between them. You **buy the coverage guarantee at a computed price** and spend the remainder on
value. If a scenario makes the price exceed 100%, the system says so explicitly rather than
silently starving bands, and the operator can relax `T_req` or add a receiver. That is an
engineering answer, not a hyperparameter.

Deadline pressure as a barrier function, with `s = τ_i(t)/D_i`:

```
κ_i(t)  =  w_D · s^p / (1 − s),     p = 2,     and a hard override at s ≥ 1
```

`κ → ∞` as `s → 1`, so no band can be starved even before the hard override fires. This is
claim **G1**.

### 5.1 Per-band deadlines, and the mistake to avoid

`D_i` must be computed from **band `i`'s own** estimated `T_max` and `τ_ill`, never from a global
worst case. Getting this wrong produces nonsense, and it is worth showing the nonsense so nobody
reintroduces it.

Take a tracker requiring `T_req = 2 s`. Plug in the *global* `T_max = 20 s` and you get
`D_i = 9.3 ms`, which demands a coverage cycle 13 times faster than the receiver can physically
sweep. The requirement looks impossible.

It is not impossible. It is the wrong `T_max`. A tracker does not have a 20 s scan period. Two
cases:

| Tracker type | `T` | `τ_ill` | `D_i` at `T_req = 2 s` | Feasible? |
|---|---|---|---|---|
| Continuous illuminator (`fixed` class) | — | continuous | `≈ T_req` = 2 s | trivially |
| Sector scan, `T = 1 s`, 30° sector | 1 s | 83 ms | 2·(0.083+0.010)/1 = **186 ms** | yes, 120 ms cycle fits |

Clarkson makes the same point: non-scanning emitters are trivial to intercept and are not the
interesting case. The scheduler's job on a continuous illuminator is to look once; the hard case is
always the narrow-beam scanner.

### 5.2 The feasibility condition, which is also a receiver sizing formula

A guaranteed coverage cycle takes `(N/K)·(Δ + δ)` seconds. The deadlines are satisfiable only if

```
(N / K) · (Δ + δ)   ≤   min_i D_i
```

Rearranged, this sizes the receiver:

```
K   ≥   N · (Δ + δ) / min_i D_i
```

| Scenario | `N` | `min D_i` | Required `K` |
|---|---|---|---|
| Demo configuration | 16 | 186 ms | 1.29 → **2** |
| Wideband, 250 MHz channels over 2–18 GHz | 64 | 186 ms | 5.16 → **6** |
| Same, relaxed to 60 s search requirement | 64 | 280 ms | 3.43 → **4** |

This is a genuine deliverable in its own right. **The design does not just schedule a given
receiver; it tells you how much receiver you need** for a stated threat set and a stated
worst-case intercept requirement. If the condition fails, the system reports it rather than
silently starving bands, and the operator's options are explicit: more receivers, wider
instantaneous bandwidth, shorter dwell, or a relaxed `T_req`. That is an engineering answer, not a
hyperparameter.

Threat priority therefore acts on **both** terms of the index, the value numerator and the
deadline, which is what "give time to threatening ones" should actually mean.

---

## 6. Synchronisation: the failure open loop cannot see, and the fix

### 6.1 The trap, restated exactly

With `α = R/T` the period ratio, `β` the normalised relative phase and
`ε = (τ_ill + mΔ − 2d)/T` the tolerance, an intercept of duration `d` requires integers `p, q`:

```
| q·α − p + β |  ≤  ε / 2
```

**Synchronisation:** if `α = h/k` is rational and `ε < 1/k`, there exist relative phases `β` for
which no `(p,q)` satisfies the inequality. Intercept time is **infinite**. A working receiver
sweeps forever past a working emitter and never sees it.

This is not exotic. Clarkson's own worked example has an emitter at `α = 1/21` that is invisible to
a 1 s sweep until the dwell in that band is raised to 438.8 ms. Winsor & Hughes observed the
signature empirically: their channel sweep's probability of intercept was flat with respect to
observation period, meaning extra time bought nothing, because the schedule was locked out.

**A round-robin scheduler cannot detect that this is happening to it.** It reports a clean sweep
and a `P_d` of zero, indistinguishable from an empty band. That is the demonstration that should
open the presentation.

### 6.2 Detection

Given the planned revisit `R_i`, dwell `m`, and the period posterior `{(T̂_j, π_j)}`:

```
for each candidate T̂_j:
    α_j = R_i / T̂_j
    ε_j = (τ̂_j + m·Δ − 2·d_i) / T̂_j
    expand α_j as a continued fraction (Euclid), take convergents h_l/k_l with k_l ≤ k_max = 50
    risk_j = 1  if  ∃ l :  |α_j − h_l/k_l| < 1/(k_l · k_max)   and   ε_j < 1/k_l
sync_risk_i = Σ_j π_j · risk_j
```

Continued fractions are the right tool because the convergents are exactly the best rational
approximations to `α`, which is the Diophantine result of Clarkson, Perkins and Mareels.

### 6.3 The fix: golden-ratio phase dithering

Two escapes exist. Use both, in this order.

**Escape 1, extend the dwell.** Since `ε ≥ 1/k` removes the lockout, and `ε` is linear in `m`:

```
m·Δ  ≥  T̂/k  −  τ̂  +  2·d_i
```

Take this route when the band is high-threat and the extra dwell is affordable.

**Escape 2, move the ratio onto a noble number.**

A correction, again forced by measurement. An earlier draft proposed dithering the *interval*:

```
R_i[n]  =  R̄_i · ( 1 + η · ( {n · g}  −  ½ ) )
```

That does not work, and the reason is worth keeping. The partial sums of a centred low-discrepancy
sequence stay O(log n), so the accumulated timing perturbation never reaches a full emitter period.
The receiver keeps landing near the same few phases. Measured against a two-second emitter at a
one-second revisit, 200 dithered looks left 42% of the phase circle uncovered, which is a lockout
by another name. `tests/test_sync_guard.py` encodes that negative result so it is not quietly
"fixed" back.

Breaking a lockout means moving the **ratio**, not jittering the interval. Choose the revisit so
that the period ratio is a **noble number**: one whose continued fraction ends in all ones. Two
families cover both regimes,

```
R = T̂ · (m + f)          when the revisit is comparable to or longer than the emitter period
R = T̂ / (m + f)          when it is much shorter, the usual case for a fast sweep
```

with `f` either `g = (√5 − 1)/2 = 0.6180339887…` or its reflection `1 − g`, and `m` the integer
that lands `R` closest to the target without exceeding the band's revisit deadline. The deadline is
a hard cap: the coverage guarantee outranks the lockout fix, and a revisit past the deadline is not
a fix.

Noble ratios are the right target for three reasons that stack:

1. **Aperiodicity.** `g` is irrational, so `α` is never a fixed rational and synchronisation has
   measure zero. The lockout is gone with probability 1.
2. **Maximally uniform phase coverage.** By the **three-gap theorem**, the points
   `{g}, {2g}, …, {ng}` partition the circle into at most three distinct gap lengths, for *every*
   `n`, not just for special values. Verified directly:

   | `n` revisits | distinct gap lengths | smallest gap | uniform spacing would be |
   |---|---|---|---|
   | 5 | 2 | 0.146 | 0.200 |
   | 10 | 3 | 0.056 | 0.100 |
   | 20 | 3 | 0.034 | 0.050 |
   | 50 | 3 | 0.013 | 0.020 |

   The smallest gap stays at roughly 0.68 of the uniform spacing at every prefix length. No
   sequence does better, and a pseudorandom dither does considerably worse, because random points
   clump.
3. **Most robust choice of irrational.** A noble number's continued fraction ends in all ones,
   which makes it the worst approximable by rationals. Since the synchronisation condition of §6.1
   is precisely a statement about good rational approximation, a noble ratio sits as far as it is
   possible to sit from every synchronisation condition at once. That is not a coincidence; it is
   the same continued-fraction machinery viewed from the other side.

   Worth noting: the golden constant itself is one noble number among many, and a revisit that has
   to fit under a tight deadline lands on a different one. What the guard needs is the *property*,
   not the constant, so that is what the implementation asserts. A 280 ms revisit against a 20 s
   emitter lands on a ratio whose continued fraction is `[0; 71, 1, 1, 1, …]`.

**Where this is wired.** The interval dither is kept, but only for what it genuinely provides:
arrival times an adversary watching our schedule cannot predict. The lockout-breaking job belongs
to `golden_revisit`, and the *aperiodicity* of the overall visit pattern is provided by the
randomised floor of §7, which needs no period estimate at all. That last point matters
operationally: at a cold start there is no period posterior to move the ratio onto, and the floor
is what keeps the scheduler out of a lockout until there is.

And, unlike a pseudorandom dither, it is **deterministic and reproducible**, which the project's
seed-based reproducibility requirement needs.

This is claim **G2**, and it is the single most defensible algorithmic contribution in the
solution. It is also the direct, literal answer to the problem statement's line: *"approaches to
intercept a periodic scan receiver optimally should be outlined."*

---

## 7. The randomised floor

### 7.1 Why a floor is mandatory, not optional

Clarkson and Pollington proved that against emitters with **unknown parameters**, no deterministic
search strategy outperforms a random one. SIH26055 is explicitly that regime. Any system claiming
to beat random on genuine unknowns is exploiting learned structure or reporting a lucky seed.

The correct engineering response is not to argue with the theorem. It is to **carry the random
strategy as a floor** and let learning operate strictly above it.

### 7.2 Construction

Mix, at each decision epoch, with probability `ρ(t)`:

- **With probability `ρ`:** draw the next band from a continuous-time Markov chain over
  *uncharacterised* bands, configured per El-Mahassni and Howard, whose expected intercept time
  approaches linearity in emitter scan period fastest and **smoothly**, without the abrupt spikes
  deterministic sweeps exhibit at rational period ratios.
- **With probability `1 − ρ`:** follow the index.

The contrast is the whole argument: a periodic sweep is usually better than random **and
occasionally infinite**. The CTMC is never better than the tuned index on structured emitters and
never catastrophic on anything.

### 7.3 Annealing `ρ`

```
ρ(t)  =  ρ_min  +  (1 − ρ_min) · exp( − (1/N) Σ_i conf_i(t) / κ_ρ )      ρ_min = 0.10,  κ_ρ = 0.3
```

with `conf_i` the band's aggregate model confidence: posterior mass on the top period mode, times
occupancy-kernel evidence count, normalised.

Behaviour, which is exactly the operational profile the problem statement describes:

| Phase | `ρ` | Behaviour |
|---|---|---|
| `t = 0`, zero prior intelligence | `≈ 1` | pure randomised coverage; the SIH26055 opening condition |
| structure accumulating | annealing | index takes over band by band |
| changepoint fires | spikes back up | re-explores after a mode change |
| steady state | `ρ_min = 0.10` | never drops to zero; the floor is permanent |

Keeping `ρ_min > 0` is what makes the guarantee hold for the whole mission rather than only at the
start.

### 7.4 The guarantee

Because a fraction `ρ_min` of looks always follows the CTMC, and the CTMC's expected intercept time
against any emitter with illumination fraction `u` is finite and linear in `T`, the mixed policy's
expected intercept time is at most `1/ρ_min = 10×` the CTMC's, for **any** emitter, including one
designed adversarially against our learned models. Degradation is graceful and bounded. This is
claim **G3**.

---

## 8. Two cases worth getting right

### 8.1 The pop-up threat

A tracker illuminates in a band the value-greedy policy had written off. Three mechanisms catch it,
in ascending order of speed:

1. The **deadline** `D_i` forces a look within 280 ms regardless of belief.
2. The **occupancy belief** drifts back toward stationarity rather than to zero, so the band never
   becomes worthless.
3. The **changepoint detector** fires on the first anomalous detection and boosts `ρ` plus that
   band's novelty term.

A contextual bandit with a soft latency penalty has none of these. It has a number that says
"looking here is low value", and nothing that says "you are no longer entitled to that opinion."

### 8.2 The frequency-agile hopper, and why fast hoppers are *easier* than slow ones

The DRDO Smart Communication Jammer System requirement cites radios hopping up to **2000 hops/s**,
so 0.5 ms per hop. Our slot is 10 ms, so a single one-slot dwell spans about 20 hops.

If the emitter hops uniformly over `|F|` bands, the probability that a dwell of `m` slots on a
given band sees it at least once is

```
P(see it)  =  1 − (1 − 1/|F|)^{ m·Δ / T_hop }
```

Computed at `m = 1`, `Δ = 10 ms`:

| Hop rate | `|F|` | Hops per dwell | `P(see it \| right band)` |
|---|---|---|---|
| 2000 /s | 16 | 20.0 | **0.725** |
| 2000 /s | 32 | 20.0 | 0.470 |
| 200 /s | 16 | 2.0 | 0.121 |
| 50 /s | 16 | 0.5 | 0.032 |
| 20 /s | 16 | 0.2 | **0.013** |

The intuition most audiences arrive with is inverted. **The 2000 hops/s radio is 56 times easier to
intercept than the 20 hops/s one**, because a single dwell averages over twenty hops and the
emitter's own agility guarantees it visits our band. The genuinely hard case is a hopper whose hop
interval is comparable to or longer than the dwell, where each look is one Bernoulli trial at
`1/|F|`.

Two design consequences:

- For bands flagged agile, the occupancy model tracks the **hop-averaged duty cycle**, not phase.
  Phase estimation on a fast hopper is meaningless and would produce confident nonsense.
- `ρ` stays high for agile bands, because the CTMC floor is the right tool when there is no
  exploitable phase structure.

This also reframes the SCJS threat figure usefully. A 2000 hops/s radio is hard to *jam* and hard
to *follow*, but it is not hard to *find*. Those are different problems and the presentation should
say so.

---

## 9. The complete algorithm

```
INITIALISE
  for each band i:
     ω_i ← stationary prior 0.5 ;  P⁽ⁱ⁾ ← Dirichlet(1,1)
     period posterior ← log-uniform over [0.5 s, 30 s]
     R_i ← threat-weight prior (uniform) ;  D_i ← T_req·(τ_ill+Δ)/T_max
     τ_i ← 0 ;  n_i ← 0            # slots since last look, revisit counter
  ρ ← 1.0

EVERY DECISION EPOCH t
  # ---- 1. belief propagation, O(N)
  for each band i:  ω_i ← ω_i·p₁₁ + (1−ω_i)·p₀₁ ;  τ_i ← τ_i + 1

  # ---- 2. periodicity + novelty (cached; refit only bands with new detections)
  (T̂_i, φ̂_i, û_i, conf_i, ν_i) ← Ai-ml-2 batch predict

  # ---- 3. hard deadline override
  forced ← { i : τ_i ≥ D_i }
  if |forced| ≥ K:  A_t ← K oldest members of forced ;  goto EXECUTE

  # ---- 4. randomised floor
  if Bernoulli(ρ):
      A_t ← draw from CTMC restricted to { i : conf_i < conf_min }
      goto EXECUTE

  # ---- 5. index
  for each band i, each dwell m ∈ M:
      I_i(m) ← [ w_v·R_i·ω_i·P_d(m,γ̂_i)·U_i(m) + w_I·ΔH_i(m) + w_n·ν_i ]
                 / ( m·Δ + δ(a_{t−1}→i) )
                 + w_D · s_i² / (1 − s_i)          with s_i = τ_i / D_i
  A_t, m_t ← argmax over window position (contiguous) or top-K (channelized)
  A_t ← A_t ∪ forced

  # ---- 6. synchronisation guard
  for each i ∈ A_t:
      R̄_i ← running mean revisit interval of band i
      if sync_risk(R̄_i, m_t, posterior_i) > 0.2:
          if band i is high threat and budget allows:
              m_t ← smallest m with m·Δ ≥ T̂_i/k − τ̂_i + 2·d_i          # extend dwell
          else:
              schedule next revisit at R̄_i·(1 + η·({n_i·g} − ½))       # golden dither
      n_i ← n_i + 1

EXECUTE
  tune to A_t ; dwell m_t·Δ ; collect PDWs ; run detector at threshold λ(P_fa)
  for each i ∈ A_t:
      ω_i ← Bayes update with (P_d, P_fa) ;  τ_i ← 0
      push (t, z_i) to Ai-ml-2 ;  update changepoint detector
      if detection: deinterleave PDWs → tracks → PRI → threat features → update R_i

SLOW LOOP, every H = 200 slots
  Baum-Welch refit of P⁽ⁱ⁾ with forgetting factor κ
  recompute D_i from updated threat class
  re-anneal ρ from mean confidence
```

**Complexity per epoch:** `O(N·|M|)` for the index, `O(N)` for belief propagation, `O(N)` for the
contiguous window scan. At `N = 64`, `|M| = 4` that is 256 index evaluations, microseconds. The
measured 6.6 ms p95 for `/internal/decide` is dominated by HTTP and pydantic, and this design does
not change that. NFR-002's 50 ms budget is not at risk.

---

## 10. Learning: exactly three things, and no more

| What is learned | How | Why not deep RL |
|---|---|---|
| Occupancy kernels `P⁽ⁱ⁾` | online counting plus periodic Baum-Welch | this is literally "trained based on hits and misses" |
| Period, phase, duty posteriors | grid likelihood over hits **and** misses, §3.2 | closed-form, calibrated, explainable |
| Threat score `R_i` | gradient-boosted trees on PDW features, trained on Turing stare mode | supervised, auditable, small |
| The seven scalars `w_v, w_I, w_n, w_D, ρ_min, κ_ρ, η` | CMA-ES **directly on the evaluation metric** | seven numbers, minutes to train, cannot diverge |

The last row is the one to defend loudly. We do **not** tune a proxy reward and hope it correlates
with the metric. We optimise the seven index weights against the graded objective itself, a
weighted combination of censored intercept time, high-priority detection rate and worst-case
intercept time. There is no reward-shaping guesswork anywhere in the system, and there is no
hyperparameter whose value we cannot explain.

**The existing deep-RL work stays.** Bandit, Q-learning, DQN and PPO remain as comparison arms, not
as the answer. "We match model-free deep RL while remaining fully explainable and carrying four
guarantees" is a considerably stronger claim to a DRDO reviewer than "we trained a DQN", and it is
the claim the 2025 IEEE Double-DQN receiver-scheduling paper cannot make.

An optional V2 stretch: a **learned residual index** in the NeurWIN / DeepTOP style, where the
network outputs an *index* rather than an action, so deadlines still bind and the decomposition
still renders. That is the only place a neural network is warranted here.

---

## 11. Measurement protocol

### 11.1 Definitions, fixed

An **activation run** is a maximal interval `[s, e]` over which emitter `e` illuminates band `i`
continuously. A run is **intercepted** if some slot in `[s, e]` had `i ∈ A_t` and a detection.

| Metric | Definition |
|---|---|
| `P_d` | detections / (band, slot) pairs with `O_i(t)=1`, over **all** bands |
| `P_fa` | false detections / **scanned** (band, slot) pairs with `O_i(t)=0` |
| Run intercept rate | runs intercepted / runs occurring |
| `AIT` raw | mean over **intercepted** runs of `t_first − s` |
| `AIT` censored | mean over **all** runs, unintercepted runs charged `T_ep − s` |
| Interception ratio | emitters intercepted at least once / emitters present |
| HPDR | `P_d` restricted to emitters of track, illuminator or seeker class |
| Scan efficiency | dwells yielding ≥1 true detection / dwells |
| Intercept time **error** | mean `|predicted next-active-window start − actual|` |
| Correct-prediction rate | dwells placed on a predicted window that detected / dwells so placed |
| **Phase-independent `P_I`** | sweep each emitter's `φ_e` over `G = 64` values, rerun, report fraction of phases with ≥1 intercept |
| **Worst-case intercept time** | `max` over emitters of censored intercept time |

**Report raw and censored AIT side by side, always.** Raw AIT is conditioned on detection
succeeding, so a policy that intercepts *more* runs posts a *worse* raw AIT, because the extra
runs it caught are the hard, late ones the weaker policy missed entirely. Read alone, raw AIT ranks
the better policy lower. This is already documented in `IMPLEMENTATION.md` and it must not be
allowed to go stale.

The last two rows are the ones that make the comparison survive scrutiny. Phase-independent `P_I`
is Winsor and Hughes' construction and it removes the lucky-seed objection completely. Worst-case
intercept time is Clarkson's min-max criterion, and it is the metric an evaluator actually cares
about: a good mean is worthless if you never saw the one tracker that mattered.

### 11.2 Baseline ladder

| Arm | Strategy | Role |
|---|---|---|
| B1 | round-robin full-band sweep | the incumbent open-loop system |
| B2 | sweep restricted to occupied bands | a deliberately unfair, stronger baseline |
| B3 | uniform random band selection | naive stochastic control |
| B4 | optimally configured CTMC | the theoretical floor, §7 |
| B5 | GA-optimised offline schedule, **given the full emitter list** | oracle upper bound |
| — | SCT | ours |

**The result that matters is SCT versus B5.** We approach an oracle that was handed the threat
emitter list, without being handed the threat emitter list. That is the claim, and the ladder is
what earns the right to make it. B4 is the claim's honesty check: if SCT ever falls below B4 on an
unstructured scenario, something is wrong and we say so.

### 11.3 Scenario suite

Six scenarios, each engineered to break something specific.

| ID | Scenario | Parameters | Breaks | Expected result |
|---|---|---|---|---|
| S1 | **Synchronisation trap** | emitter `T = 2.0 s`, sweep period exactly `1.0 s`, `τ_ill = 40 ms`, so `α = 1/2`, `ε < 1/2` | B1, B2, any fixed-period schedule | Baseline `P_d ≈ 0` **indefinitely**; SCT intercepts within one dithered revisit |
| S2 | **Cold start** | zero prior, emitter count unknown, 16 bands, 12 emitters | anything assuming a threat list | `ρ` starts at 1, anneals; SCT ≈ B4 early, exceeds it by mid-episode |
| S3 | **Pop-up threat** | seeker activates at `t = T_ep/2` in the band with lowest observed activity | value-greedy bandit | SCT detects within `D_i`; bandit's latency is unbounded |
| S4 | **Chatty decoy** | one harmless emitter at 60% duty in band 3, one seeker at 2% duty in band 11 | reward-greedy anything | The statement's literal complaint. SCT's threat weight declines the bait. |
| S5 | **Fast hopper** | 2000 hops/s over 16 bands, per the SCJS figure | learned models generally | Falls to the CTMC floor; bounded, and see §8.2 |
| S6 | **Beam-agile multifunction** | non-periodic illumination, interleaved search and track dwells | periodicity estimation | Confidence stays low, `ρ` stays high, **no false confidence** |

Every arm sees identical spectrum per seed. Five seeds minimum, `T_ep = 6000` slots. Seed and full
config logged per experiment.

S1 is the presentation opener. A baseline that sweeps flawlessly and reports zero detections for
sixty seconds, next to SCT intercepting in under a second, makes the entire argument in one slide
without a word of explanation.

---

## 12. Build plan

### 12.1 Ai-ml-1 Scheduler Engine

| # | Module | New or changed | Depends on |
|---|---|---|---|
| 1 | `ml/belief/occupancy.py` | new. Gilbert-Elliott belief with imperfect-sensing update, §3.1 | — |
| 2 | `ml/belief/kernel_learning.py` | new. Dirichlet counts plus Baum-Welch, forgetting factor | 1 |
| 3 | `ml/scheduling/deadlines.py` | new. `D_i` from §5, per-band, threat-aware | — |
| 4 | `ml/agents/index_agent.py` | new. `policy_type: "index"`, §4 | 1, 3 |
| 5 | `ml/scheduling/sync_guard.py` | new. Continued fractions, risk test, golden dither, §6 | Ai-ml-2 fields |
| 6 | `ml/agents/ctmc_floor.py` | new. Also serves as baseline arm B4, §7 | — |
| 7 | `ml/threat/classifier.py` | new. GBT over PDW features, §3.4 | Turing stare mode |
| 8 | `ml/tuning/cmaes.py` | new. Seven weights against the graded metric, §10 | 4 |
| 9 | `ml/agents/ga_oracle.py` | new. Baseline arm B5, Winsor & Hughes' method | — |
| 10 | `ml/environments/receiver.py` | changed. Make `P_fa` the configured quantity, derive threshold, §2 | — |
| 11 | existing bandit / Q-learning / DQN / PPO | **unchanged, retained** as comparison arms | — |

### 12.2 Ai-ml-2 Periodicity Estimator

| # | Work |
|---|---|
| 1 | Replace point-estimate period with the grid likelihood of §3.2, using hits **and** misses |
| 2 | Return top-`J = 3` period modes with weights, not an argmax |
| 3 | Phase posterior and next-active-window prediction from the joint |
| 4 | Bayesian online changepoint detection per band, §3.3 |
| 5 | Export `α`, `ε`, `sync_risk`, `changepoint_flag` so Ai-ml-1's guard can act |
| 6 | Keep the batch endpoint. It is already the right shape and the caching note still holds. |

### 12.3 Backend

| # | Work |
|---|---|
| 1 | Carry `revisit_deadline`, `staleness_ratio`, `threat_score`, `occupancy_belief`, `sync_risk` in the `StateVector` |
| 2 | Log the per-term index decomposition on every decision, for the explainability panel and audit |
| 3 | Implement phase-independent `P_I` (a `G = 64` phase sweep harness) and worst-case intercept time |
| 4 | Add the six scenarios of §11.3 as configurations |
| 5 | Add a Turing scan-mode replay source alongside the synthetic generator |

### 12.4 Frontend

| # | Work |
|---|---|
| 1 | Waterfall: overlay the chosen window and dwell length on the truth spectrum |
| 2 | **Index decomposition panel**: stacked bar of the six terms for the current decision. This is the credibility moment of the demo. |
| 3 | Phase-sweep `P_I` chart, SCT against all five baseline arms |
| 4 | Scenario S1 view: baseline flatlining beside SCT intercepting |

### 12.5 Order of work

1. **Deadlines and staleness** (Ai-ml-1 #3, Backend #1). Fixes the losing metric first.
2. **Occupancy belief and the index policy** (Ai-ml-1 #1, #2, #4).
3. **Synchronisation guard, golden dither, scenario S1** (Ai-ml-1 #5, Backend #4). Small, and it is
   the demo.
4. **Ai-ml-2 posterior and changepoint** (all of §12.2).
5. **CTMC floor and adaptive `ρ`**, scenario S2 (Ai-ml-1 #6).
6. **Threat classifier**, scenario S4 (Ai-ml-1 #7).
7. **Baseline arms B4, B5, phase-independent `P_I`** (Ai-ml-1 #9, Backend #3).
8. **Index decomposition panel** (Frontend #2).
9. **CMA-ES weight tuning**, full six-scenario sweep, final numbers (Ai-ml-1 #8).

Steps 1 through 3 alone move the current result from *losing on the problem statement's primary
objective* to *winning it with a coverage guarantee and a synchronisation proof*. Everything after
step 3 is margin, and can be dropped under time pressure in reverse order.

---

## 13. Contract changes

Additive only. No endpoint removed, no existing field changes meaning, so the four folders can
adopt independently. Make the change in `API_CONTRACT.md` first, then propagate to all four copies
in the same commit.

1. `policy_type` enum gains `index` and `ctmc`.
2. `StateVector.bands[]` gains `revisit_deadline`, `staleness_ratio`, `threat_score`,
   `occupancy_belief`, `sync_risk`.
3. Ai-ml-2 `predict/batch` response gains `period_modes` (array of `{period, weight, phase, duty}`,
   length ≤ 3), `alpha`, `epsilon`, `sync_risk`, `changepoint_flag`.
4. `/internal/decide` response gains optional `index_breakdown` with the six named terms and the
   chosen `dwell_slots`.
5. Metrics payloads gain `pi_phase_independent` and `worst_case_intercept_time`, and retain
   `ait_censored` alongside `ait`.

---

## 14. Parameter reference

| Symbol | Meaning | Default | Source |
|---|---|---|---|
| `Δ` | slot / minimum dwell | 10 ms | Winsor & Hughes minimum dwell |
| `M` | dwell options in slots | {1, 2, 4, 8} | design |
| `δ₀, δ₁` | retune dead time | 2 ms, 0.2 ms/GHz | synthesiser settling |
| `n_p` | pulses needed to identify | 5 | Clarkson's `d` |
| `P_fa` | target false-alarm rate | 10⁻³ | mission requirement |
| `n_eff` | effective independent integration samples per slot | 100 | §2 |
| `T_req` | worst-case intercept requirement | 60 s search / 2 s track | mission requirement |
| `T_max` | slowest scan period of interest | 20 s (3 rpm) | Wiley, slowest search radars |
| `D_i` | derived revisit deadline | 280 ms at defaults | §5 |
| `p` | barrier exponent | 2 | design |
| `g` | golden ratio conjugate | 0.6180339887 | §6.3 |
| `η` | dither amplitude | 0.15 | design |
| `k_max` | max convergent denominator tested | 50 | §6.2 |
| `ρ_min` | permanent randomised floor | 0.10 | §7.3 |
| `κ_ρ` | `ρ` annealing rate | 0.3 | tuned by CMA-ES |
| `κ` | kernel forgetting factor | 0.995 / slot | design |
| `H` | slow-loop period | 200 slots | design |
| `J` | period modes retained | 3 | §3.2 |
| `G` | phases in the `P_I` sweep | 64 | §11.1 |
| `w_v, w_I, w_n, w_D` | index weights | tuned per scenario class | §10 |

---

## 15. What this solution does not claim

Stated first, rather than extracted under questioning.

- **It does not beat random against a genuinely adversarial, genuinely unpredictable emitter.**
  Clarkson and Pollington proved that cannot be done. SCT's response is a bounded fallback (§7.4),
  not a contradiction of the theorem.
- **The exact Whittle-index optimality proof covers identical arms with perfect sensing.** Our
  index reduces to it in that case and is a one-step-lookahead approximation otherwise. This is
  standard practice and should be described as such.
- **The threat classifier is only as good as the PDWs collected.** In the first seconds of a cold
  start it contributes nothing, which is correct behaviour and is why `ρ` starts at 1.
- **Everything is simulated.** No RF hardware, no real interception, no jamming, no weapon control.
  If a code path would touch a radio or a capture device, that is out of scope by design.

What SCT does claim is narrower and true: real emitters display structure most of the time; SCT
finds and exploits that structure online with no prior intelligence, never drops below a provable
random floor when structure is absent, cannot be locked out by synchronisation, cannot starve a
band, and explains every decision it makes as six named numbers.
