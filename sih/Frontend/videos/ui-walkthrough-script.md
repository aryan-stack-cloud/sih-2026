# UI walkthrough video script

**Target length:** about 3 minutes. **Audience:** SIH judges and first-time viewers. **Format:** screen recording with voiceover. Use the values produced during the recording; do not pre-record a claim that a policy always wins.

| Time | On screen | Voiceover |
|---|---|---|
| 0:00–0:18 | Open the Dashboard. Show the title, service indicators, and the two-band aperture. | “This is Team Pushpak’s Spectrum Scan Scheduler, a research prototype for deciding where a limited receiver listens next. In this simulation, there are many frequency bands, but the receiver can hear only two at a time. The status lights show whether the backend, scheduler, and periodicity service are connected.” |
| 0:18–0:38 | Point to Scenario, Compare against, and Speed. Select Scenario B and Bandit. | “First, I choose a scenario and the scheduling policy. Scenario B contains mostly periodic activity. Bandit is a learned policy; the fixed sweep is our reference. The speed control changes how quickly the live run plays on screen.” |
| 0:38–1:05 | Click **Run live comparison**. Keep the waterfall visible as it runs. | “Each row in this waterfall is a moment in time. Frequency bands run left to right, with the newest moment at the top. The highlighted aperture shows where the receiver listened. Activity outside that aperture passes by unheard. The policy repeatedly chooses the next place to listen.” |
| 1:05–1:28 | Scroll to the four “This run” tiles. Point to each tile. | “These four tiles summarize this one live run. Spectrum heard is the share of transmitting band moments observed. False alarms count detections where no signal was present. Listening efficiency is the share of scans spent on an active band. Interceptions counts detections made so far.” |
| 1:28–2:05 | Scroll to **Head to head**. Point to seed caption, baseline and Bandit figures, and both better and worse rows. | “The chart below is a separate test: ten matched, 80-step simulated worlds. Bandit and the fixed sweep face the same worlds, so their results can be compared fairly. The left number is the sweep; the right is Bandit. The bar and percentage show the change from the sweep. Green marks improvements and red shows where the policy did worse. This is why the live tile and chart may show different efficiency values: the tile covers one 160-step run, while the chart summarizes ten shorter runs.” |
| 2:05–2:20 | Open **Show the underlying numbers**, then point to **Replay these worlds**. | “The full table shows every metric behind the chart. The seed range identifies these simulated worlds, and Replay these worlds runs the same setup again. A new run selects new seeds, so its numbers can change.” |
| 2:20–2:48 | Click each tab briefly: Simulations, Raw stream, Experiments, Models, Health. | “The other tabs expose the test harness. Simulations creates and manages individual runs. Raw stream shows the live events and latest decision. Experiments compares several policies over chosen episodes and seeds. Models lists registered checkpoints and offers training controls. Health shows whether the connected services are responding.” |
| 2:48–3:00 | Return to Dashboard, hold on the chart and footer. | “This prototype lets us see both the scheduler’s choices and the tradeoffs in its measured results. All of these results are from simulation, not live RF hardware.” |

## Recording notes

- Run the comparison once before recording so the services and selected model are ready. Record a fresh run on camera.
- Pause or cut during the experiment calculation, but keep the same run’s tile and chart together.
- Read the actual chart values if desired; do not script fixed percentages. If the chart shows a loss, describe it plainly.
- Keep the Dashboard sample caption visible when explaining one live run versus ten comparison runs.

## Five-second lines for optional inserts

- **Hardware concept:** “An antenna receives signals, and our scheduler chooses which two frequency bands the receiver listens to.” This describes the concept only; the demonstrated system has no RF hardware.
- **Fixed sweep:** “The fixed sweep checks each frequency band in a set order, then repeats, regardless of where signals appear.”
