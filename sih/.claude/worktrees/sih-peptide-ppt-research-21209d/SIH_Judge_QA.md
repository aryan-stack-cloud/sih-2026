# Judge Q&A prep — Intelligent RF Spectrum Scan Strategy

Every answer below is grounded in a number or a file that already exists in this repo. If you
cannot point at the source, do not say it.

---

## The problem statement, verbatim

Pulled from the published SIH 2026 catalogue. Know these before anything else.

| Field | Value |
|---|---|
| ID | SIH26055 |
| Title | Smart Scan strategy for Electronic Warfare |
| Organisation | DRDO |
| Department | Department of Defence Production / IDEX |
| Category | Software |
| Theme | Clean & Green Technology |
| Idea submission deadline | 20 September 2026 |

Two things follow from this.

**The Theme really is "Clean & Green Technology."** It looks wrong against an electronic-warfare
brief, and it is still what the portal says. Do not let anyone talk the team into changing it.

**DRDO wrote the brief, so expect a signals person on the panel.** The brief names its own figures
of merit by hand: probability of detection, probability of false alarm, sensitivity, average
intercept rate, average reward or cost function, percentage of correct predictions, and average
intercept time error. Slide 5's table is built from that list on purpose. It also states the
primary objective in one sentence: *a robust scheduler using machine learning to minimise
intercept time and ensure a high interception rate.* The expected solution is *machine learning
based Electronic Support receiver scheduler software.*

The brief also names the dataset it expects you to use, the Turing synthetic radar dataset. The
repo already replays it in `ml/data/turing_replay.py`. Say so.

---

## Before you open your mouth

**The first 30 seconds.** Do not start with "our project is about". Start with the picture on
slide 1: sixteen bands across, time flowing down, blue is an emitter transmitting, amber is where
our receiver actually was. Every blue cell is signal lost forever, because a receiver hears two
bands at a time and there are sixteen. Then: "that gap is the problem statement. We closed
two-thirds of it."

**Who answers what.** Agree this in advance. The playbook every SIH mentor repeats is that any
member, not just the presenter, must be able to walk a stranger through problem, solution and demo
in under two minutes. Judges test this by asking the quiet person.

**The one thing not to do.** Do not claim the learned policy beats the baseline on everything. It
does not, you know exactly where it does not, and saying so first is the strongest move in the
whole presentation.

---

## The questions a technical judge will actually ask

### 1. "Your policy catches fewer distinct bursts than a plain round-robin sweep. Isn't that a failure?"

No, and it is the most interesting result we have. With an instantaneous bandwidth of two bands
out of sixteen, a scheduler faces a genuine resource frontier. It can spread thin and clip the
*start* of many short bursts, or concentrate and hear far more total active spectrum. It cannot do
both.

The sweep takes the first option and scores 0.413 on distinct bursts caught. We take the second
and score 0.174, but we hear three times the detection rate and nearly three times the listening
efficiency.

The important part is that this is a **dial, not an accident**. The reward weight
`w5_redundant` moves along the frontier monotonically:

| `w5_redundant` | Pd | Censored AIT | Distinct bursts caught |
|---|---|---|---|
| 0.5 | 0.357 | 827 | 0.173 |
| 3.0 (our default) | 0.338 | 812 | 0.188 |
| 8.0 | 0.259 | 703 | 0.297 |
| 20.0 | 0.154 | 577 | 0.423 |

At weight 20 we match the sweep on coverage. An operator picks the point on this curve that suits
the mission. It is config, per scenario, in `ml/experiments/scenario_*.yaml`.

**This is the answer to the brief's primary objective too.** DRDO asks for a scheduler that
minimises intercept time and keeps a high interception rate. At our default weight the censored
intercept time is 826 against the sweep's 588, so we lose. At weight 20 it is 577, so we win, and
the interception ratio reaches 1.000. Do not hide the first number. Show that the frontier is
something the mission chooses rather than a wall we hit.

There is a test named `test_learned_policy_trades_run_coverage_for_density` that asserts this
weakness. If a future change accidentally fixes it, that test fails and we find out.

### 2. "Your average intercept time is worse than the baseline's. Explain."

Raw AIT is conditioned on detection succeeding — it averages only the activation runs a policy
actually caught. A policy that intercepts *more* runs posts a *worse* AIT, because the extra runs
it caught are the hard, late ones the weaker policy missed entirely. Read alone, raw AIT ranks the
better policy lower.

So we report `ait_censored` beside it, which charges every undetected run the full episode length.
That average is defined over all runs, not just the easy ones. Compare policies on the censored
number; use the raw number only to describe how fast a policy reacts when it does intercept.

We found this by measuring, not by reading the code, and both rules are pinned by tests in
`tests/test_metrics.py`.

### 3. "Why are Pd and Pfa counted over different populations? That looks like a bug."

It is deliberate, and each rule prevents a specific degenerate policy.

Pd counts every band at every step, so a band that was active and never looked at counts as a
false negative. Without that, a scanner that stared at one band forever would report a perfect Pd
— which is the exact failure this project exists to fix.

Pfa counts scanned bands only, because an unscanned band cannot raise a false alarm. Counting idle
unscanned bands as true negatives would drive Pfa to zero for every policy and make the metric
useless.

### 4. "6.6 ms sounds too good. What exactly did you measure?"

p95, measured over a real HTTP socket against `uvicorn` on port 8500 — not an in-process function
call. The budget in the requirements is 50 ms.

Be precise here, because an earlier draft of our own notes claimed 0.26 ms. That figure was the
in-process agent decision inside the evaluation loop and excluded the HTTP hop, pydantic
validation and session lookup. We corrected it. The number that matters to the backend is 6.6 ms,
because the backend pays the socket.

| Case | p50 | p95 |
|---|---|---|
| Warm, same simulation | 5.6 ms | 6.6 ms |
| New simulation id | 7.0 ms | 8.1 ms |
| First decide after boot | — | ~260 ms, once per process |

The cold start is once per process, not per simulation. We warm it at startup before a demo.

### 5. "Why a contextual bandit? Isn't deep RL the obvious choice?"

DQN and PPO are built, verified and shipped behind a flag. The bandit is the default because it
needs no pre-training, learns online from the first step, and already clears every acceptance
gate. Choosing the simplest model that passes is an engineering decision, not a limitation — and
when a judge asks whether we *could* do deep RL, the honest answer is that we did, and chose not
to switch the default without evidence it helps.

### 6. "Your own notes say the periodicity service doesn't improve anything. Why is it in the deck?"

Because the failure is diagnosed, and the diagnosis is the interesting part.

The estimator is told when a detection happened. It is never told when a band was listened to and
found silent. Without the silences it cannot separate the emitter's rhythm from the receiver's,
and it fails in one of two ways depending on who is scheduling:

- **Under the learned policy it is starved.** The bandit concentrates on a few bands, so no band
  accumulates enough separated observations. The best band reached seven activations against a
  threshold of eight.
- **Under the sweep it is aliased.** A round-robin run does produce confident claims on ten of
  sixteen bands, at a period of 8 — exactly how often a stride-2 sweep over 16 bands revisits a
  band. It is measuring the scanner, not the spectrum.

The fix is a contract change: carry scanned-but-empty observations alongside detections in
`API_CONTRACT.md` §5. That is the backend owner's call. The acceptance test is `@Disabled` with
this explanation rather than deleted, so the gap stays visible in the suite instead of quietly
going stale.

Everything else about the service works and is tested: it recovers clean, sparse and jittered
periods on fixture data, and refuses to claim periodicity on the four non-periodic emitter classes
at the nominal false-positive rate.

### 7. "How do you know your period estimates aren't just patterns in noise?"

Three corrections, each found by measurement:

- **Subharmonics.** Every divisor of the true period folds the data just as tightly. We find the
  best-scoring candidate first, then test only integer multiples of it, and take the largest that
  still folds tightly.
- **The look-elsewhere effect.** We sweep a few thousand candidate periods and keep the best.
  Scoring that winner with a plain Rayleigh p-value rated a purely *random* emitter at 0.99
  confidence. The p-value is now corrected for the number of independent trial periods searched.
- **One activation is one sample.** A receiver dwelling on an active band reports the same burst
  several steps running. Feeding those in as independent samples rated a bursty intermittent
  emitter above 95%. Detections closer together than `min_period` are now collapsed into one
  activation.

Calibration, as a measured rate rather than a claim — fraction of runs claiming confidence above
0.95:

| Emitter class | n=12 | n=20 | n=40 | n=64 |
|---|---|---|---|---|
| random | 0.04 | 0.06 | 0.01 | 0.00 |
| intermittent | 0.00 | 0.00 | 0.01 | 0.06 |
| fixed | 0.00 | 0.00 | 0.00 | 0.00 |
| **periodic, clean** | **1.00** | **1.00** | **1.00** | **1.00** |
| **periodic, jitter ±3** | 0.70 | **1.00** | **1.00** | **1.00** |

The four non-periodic classes sit at the nominal 5%. Periodic emitters are found essentially
always from about 20 activations.

### 8. "Why take the median inter-arrival time apart? That's the standard approach."

Because we do not observe the emitter. We observe our own detections of it, and the receiver is
tuned elsewhere most of the time. A period-20 emitter does not produce gaps of 20 — it produces
20, 40, 60, 100, whichever activations the scan schedule happened to catch. The median of that is
not the period, and it drifts with the *scheduler's* behaviour rather than the emitter's.

Instead we fold every timestamp onto a candidate period and measure the concentration of the
resulting phases. If the candidate is right, detections land at the same phase however many cycles
were skipped. `test_recovers_the_period_when_cycles_were_missed` asserts the naive median gives
the wrong answer and the fit gives the right one.

### 9. "Pd of 0.345 is still low in absolute terms."

It is, and the ceiling is set by physics, not by the model. Two bands of sixteen means at best we
can be listening to one eighth of the spectrum at any instant. Against that ceiling, 0.345 from a
starting point of 0.107 is the number to judge. On Scenario A, which is mostly fixed emitters,
listening efficiency reaches 0.917.

### 10. "It's all simulation. How do you know it transfers?"

We do not claim it transfers unchanged, and the scope is simulation-only by design — no RF
hardware, no interception, no jamming, no weapon control, and no code path that touches a radio.

What supports transfer is the interface. The policy consumes an abstract per-band state vector:
time since last scan, recent detection rate, consecutive misses, periodicity phase and confidence,
band priority, tuning cost. Nothing in the learning code knows it is talking to a simulator. Swap
the observation source and the agent is unchanged.

### 11. "Has this been done before?"

Yes, and we found it: US 10,523,342 B1, BAE Systems, "Autonomous reinforcement learning method of
receiver scan schedule control." Reinforcement learning on receiver scan scheduling is prior art.

What we add is the periodicity feature feeding the RL state as a predicted next-activation window
with a calibrated confidence, rather than the agent having to learn timing from reward alone — and
the honest measurement layer around it, the censored metric and the frontier dial.

Saying "nobody has done this" when a patent exists is how a team loses a technical judge. Saying
"here is the patent, and here is our delta" is how it gains one.

### 12. "What happens when an emitter changes behaviour mid-mission?"

The bandit's per-band estimates are online and updated every step, so they track drift. The
periodicity estimator keeps bounded per-band buffers, so old behaviour ages out. The agile emitter
class in the simulation exists precisely to exercise this — Scenario C is 70% frequency-agile.

### 13. "Why Java and Python rather than one stack?"

The seam is deliberate and it is in the architecture document. The Python ML ecosystem sits behind
an internal REST boundary from the Spring Boot domain layer, which keeps each side independently
testable, independently deployable, and buildable by different people in parallel. One
`API_CONTRACT.md` is copied byte-identical into all four folders. A change to any shared endpoint
is made there first and propagated in the same commit.

### 14. "Prove the numbers."

```bash
cd Ai-ml-1-Scheduler-Engine && python scripts/compare.py --scenario B --policies random,baseline,bandit --episodes 20
```

Everything is deterministic by seed, so every policy is scored on an identical spectrum. 167 tests
in the scheduler engine at 87% coverage, 77 in the estimator at 96%.

**Trap to avoid on the day:** the backend degrades silently to round-robin if the ML services are
down. Check `curl -s localhost:8080/ready` shows `"ml_scheduler":"up"` and `"ml_periodicity":"up"`
before you run anything in front of a judge, or a learned policy will look like a bad one rather
than an outage.

### 15. "How much of this did you write?"

Answer it straight, whatever the truth is. The follow-up is always "explain this file", so the
real preparation is that every member can open any file in their own area and explain why it is
shaped the way it is. Pick the two or three files you each own and be fluent in them: the reward
function, the state builder, the estimator, the scheduler client.

---

## Demo runbook

Start in this order, because the backend checks both ML services on `/ready`:

```bash
cd Ai-ml-1-Scheduler-Engine && uvicorn ml.api.main:app --port 8500
```

```bash
cd Ai-ml-2-Periodicity-Estimator && uvicorn periodicity.api.main:app --port 8600
```

```bash
cd Backend && java -jar target/rf-scheduler-backend-1.0.0.jar
```

```bash
cd Frontend && npm install && npm run dev
```

Then confirm the chain before you present:

```bash
curl -s localhost:8080/ready
```

Warm the decision path once so the ~260 ms cold start does not land in the demo. Record a backup
video locally — venue wi-fi is the single most common demo failure at these events.

**Known environment issue.** On at least one Windows machine here, JDK 25 cannot create an NIO
selector and Tomcat never binds a port. It is not application code. Point the JDK at a valid
directory for AF_UNIX sockets:

```bash
java -Djdk.net.unixdomain.tmpdir=C:/rfstmp -jar target/rf-scheduler-backend-1.0.0.jar
```

---

## Deck checklist before you submit

The deck to submit is `SIH_PUSHPAK_Idea_Presentation.pptx`. The dark-themed
`SIH_Idea_Presentation_dark_alt.pptx` carries the same content in a different skin and is kept
only as an alternative.

- [ ] Team ID filled in on slide 1. It is the only field still blank, and it comes from the portal.
- [ ] Demo-video link filled in on slide 6. The repository link is already there.
- [ ] Exported to PDF. The portal takes PDF, not PPTX.
- [ ] Still exactly 6 slides.
- [ ] Rehearsed twice against a timer.
- [ ] Submitted before **20 September 2026**, the deadline on the problem statement.

The Theme field needs no checking. "Clean & Green Technology" is what the catalogue lists for
SIH26055, odd as it looks.

One correction already applied: the earlier deck attached the same DOI, `10.1049/rsn2.12337`, to
three different references. Only the Hashmi et al. entry keeps it now. A judge who clicks two of
those and lands on the same page will doubt the whole reference list.
