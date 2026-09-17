# Running the system

Four services. Start them in this order — the Backend checks the two ML services on `/ready`, and
the Frontend talks only to the Backend.

| Service | Port | Folder |
|---|---|---|
| Ai-ml-1 scheduler engine | 8500 | `Ai-ml-1-Scheduler-Engine/` |
| Ai-ml-2 periodicity estimator | 8600 | `Ai-ml-2-Periodicity-Estimator/` |
| Backend | 8080 | `Backend/` |
| Frontend test harness | 5173 | `Frontend/` |

Ports are fixed by `API_CONTRACT.md` §7. Simulation-only: no real RF hardware, no interception,
no jamming, no weapon control.

---

## 1. Ai-ml-1 — scan-decision policy

```bash
cd Ai-ml-1-Scheduler-Engine && pip install -r requirements.txt
```

```bash
cd Ai-ml-1-Scheduler-Engine && uvicorn ml.api.main:app --port 8500
```

## 2. Ai-ml-2 — periodicity estimator

```bash
cd Ai-ml-2-Periodicity-Estimator && pip install -r requirements.txt
```

```bash
cd Ai-ml-2-Periodicity-Estimator && uvicorn periodicity.api.main:app --port 8600
```

## 3. Backend

```bash
cd Backend && mvn -DskipTests package
```

```bash
cd Backend && java -jar target/rf-scheduler-backend-1.0.0.jar
```

Then confirm the whole chain is wired:

```bash
curl -s localhost:8080/ready
```

Expect `"ml_scheduler":"up"` and `"ml_periodicity":"up"`. If either says `down`, the scheduler
still runs but silently degrades to round-robin — it will look like a bad policy rather than an
outage, so check this before drawing conclusions from any run.

## 4. Frontend

```bash
cd Frontend && npm install && npm run dev
```

Open <http://localhost:5173>.

---

## Known environment issue: Java 25 on Windows

On at least one Windows machine here, **JDK 25 cannot create an NIO `Selector`**, so Tomcat fails
to start with `Unable to establish loopback connection` and the Backend never binds a port. It has
nothing to do with the application code — `Selector.open()` fails in a three-line test program.

The cause is the directory the JDK uses for AF_UNIX sockets. Point it somewhere valid:

```bash
java -Djdk.net.unixdomain.tmpdir=C:/rfstmp -jar target/rf-scheduler-backend-1.0.0.jar
```

Create that directory first. If the Backend starts normally without the flag, ignore this.

---

## Databases

The default profile runs **H2 in PostgreSQL-compatibility mode**, so the stack boots with no
Docker, Postgres or Redis installed. Flyway owns the schema in both cases and the migrations are
written in SQL both engines accept.

For the PRD's real stack, run with the `docker` profile, which points at Postgres and Redis:

```bash
java -jar target/rf-scheduler-backend-1.0.0.jar --spring.profiles.active=docker
```

**This path is written but has not been run** — Docker is not installed on the development
machine used so far. Build and exercise it before relying on it.

---

## Verifying without the UI

Run each service's own suite:

```bash
cd Ai-ml-1-Scheduler-Engine && python -m pytest tests/ -q
```

```bash
cd Ai-ml-2-Periodicity-Estimator && python -m pytest tests/ -q
```

```bash
cd Backend && mvn test
```

The Backend suite includes `EndToEndSimulationTest` and `PeriodicityAcceptanceTest`, which drive
the real three-service path. They **skip rather than fail** when the ML services are not running,
so a green Backend build does not by itself prove integration — start 8500 and 8600 first if that
is what you are checking.

The headline comparison, straight from the ML side without any Backend:

```bash
cd Ai-ml-1-Scheduler-Engine && python scripts/compare.py --scenario B --policies random,baseline,bandit --episodes 20
```

---

## Known open issue: periodicity does not yet help

PRD Definition-of-Done item 8 — "periodic-emitter prediction measurably improves detection
latency on Scenario B" — is **not met**, and the reason is understood rather than mysterious.

Ai-ml-2 is told only when a detection happened, never when a band was listened to and found
silent. Without the silences it cannot separate the emitter's rhythm from the receiver's, and it
fails in one of two ways depending on who is scheduling:

- **Under the learned policy it is starved.** The bandit concentrates on a few bands, so no band
  accumulates the separated observations a period needs. Its best band reached seven activations
  against a threshold of eight, and the gaps between them traced the scheduler's revisit pattern.
- **Under the sweep it is aliased.** A round-robin run does produce confident claims on ten of
  sixteen bands, but at a period of 8 — exactly how often a stride-2 sweep over 16 bands revisits
  a band. It is measuring the scanner, not the spectrum.

The fix is a contract change: carry scanned-but-empty observations alongside detections in
`API_CONTRACT.md` §5, so the estimator can tell "I looked and it was quiet" from "I did not
look". That is the Backend owner's call and is not made here.

The acceptance test is `@Disabled` with this explanation rather than deleted, so the gap stays
visible in the suite. Everything else about Ai-ml-2 works and is tested — the estimator recovers
clean, sparse and jittered periods correctly on fixture data, and refuses to claim periodicity on
the four non-periodic emitter classes at the nominal false-positive rate.

---

## Reading the results honestly

Two things will be asked about, so know them before the demo:

**Compare policies on `ait_censored`, not `ait`.** Raw AIT averages only the activation runs a
policy actually caught, so a policy that intercepts *more* runs reports a *worse* AIT — the extra
runs it caught are the hard, late ones the weaker policy missed entirely. Censored AIT charges
undetected runs the full episode and is defined over all of them.

**The learned policy does not win everything.** It wins decisively on Pd, HPDR and scan
efficiency, and loses to the round-robin sweep on distinct-run coverage. That is a real
resource-constraint frontier: with K=2 of 16 bands you either spread thin and clip the start of
many short bursts, or concentrate and hear far more total signal. The reward weight
`w5_redundant` slides along it. Leading with this is stronger than being caught by it.
