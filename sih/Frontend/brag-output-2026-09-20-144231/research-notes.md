# Research notes — PUSHPAK explainer

## What the repository says

The solution design describes interception as a two-dimensional coincidence problem: the receiver must be tuned to the right frequency at the same time an emitter illuminates that frequency. It also names the synchronization trap: periodic receiver and emitter schedules can miss one another indefinitely. The SCT proposal responds with per-band beliefs, hard revisit deadlines, phase dithering, and a randomized floor.

The frontend product document adds the demo story: press **Run the demo**, watch the live waterfall, and compare policies on computed simulation metrics. It explicitly scopes the system to simulation-only operation.

## External research used for visual framing

Clarkson, “Sensor scheduling for electronic support to intercept beam-agile radar,” IET Radar, Sonar & Navigation (2019):

https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/iet-rsn.2018.5668

The paper's abstract and introduction describe the receiver searching across RF bands, periodic illumination, and the failure mode where the receiver is tuned to the wrong band every time the emitter illuminates. That maps directly to the 2D frequency/time scene and the 3D-style phase-lock loop in this video.

No external footage or copyrighted animation was imported. The visuals are authored as deterministic SVG/CSS/GSAP motion so the explanation stays specific to PUSHPAK and avoids implying real-world collection.
