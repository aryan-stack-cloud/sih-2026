// s02 - the real hardware limit: the receiver hears a narrow window of the spectrum (>=10x narrower than
// the band it guards; 2 of 16 bands in our simulator) -> "we can make it smarter".
const tB = K.cue("s02_2"), tSt = K.cue("s02_5");
const tWin = tB + 2.0;    // "...a narrow slice"
const tTen = tB + 3.15;   // ">=10x narrower" (problem statement, shown)
const tSim = tB + 4.3;    // our simulator: 2 of 16 bands

// the real receiver
K.cam(tl, "#s02-B", 0, tSt, { s: 1.0 }, { s: 1.035, y: -6 });
K.tagIn(tl, "#s02-tag1", 0.1);
tl.fromTo("#s02-bar", { scaleX: 0 }, { scaleX: 1, duration: 0.6, ease: "power3.out", transformOrigin: "0% 50%" }, 0);
tl.fromTo(["#s02-ant", "#s02-rx", "#s02-lap"], { y: 80, opacity: 0 }, { y: 0, opacity: 1, duration: 0.45, ease: "back.out(1.7)", stagger: 0.14 }, 0.15);
tl.fromTo(["#s02-l-ant", "#s02-l-rx", "#s02-l-lap"], { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.3, stagger: 0.14 }, 0.5);
tl.fromTo(["#s02-cable1", "#s02-cable2"], { attr: { "stroke-dasharray": "0 1400" } }, { attr: { "stroke-dasharray": "1400 0" }, duration: 0.7, ease: "power1.inOut" }, 0.4);
tl.fromTo("#s02-ant", { scale: 1 }, { scale: 1.03, duration: 0.3, yoyo: true, repeat: 7, ease: "sine.inOut", immediateRender: false }, 0.85);
for (let i = 1; i <= 6; i++) tl.fromTo("#s02-rx-rx-led-" + i, { opacity: 0.35 }, { opacity: 1, duration: 0.15, yoyo: true, repeat: 9, ease: "none" }, 0.75 + i * 0.07);

// the "beam" of the receiver: a narrow window on the wide spectrum
tl.fromTo("#s02-win", { opacity: 0, scale: 1.6 }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)" }, tWin);
tl.fromTo("#s02-cone", { opacity: 0 }, { opacity: 1, duration: 0.35 }, tWin);
K.pop(tl, "#s02-ib", tWin + 0.35);
tl.to("#s02-rx-rx-dial-needle", { rotation: 40, svgOrigin: "194 267", duration: 0.9, ease: "sine.inOut", yoyo: true, repeat: 3 }, tWin);

// "at least ten times narrower": ruler of 10 equal slices
K.popOut(tl, "#s02-ib", tTen - 0.05);
tl.fromTo("#s02-bracket", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.3 }, tTen);
tl.fromTo("#s02-ticks .tick", { scaleY: 0, opacity: 0 }, { scaleY: 1, opacity: 0.9, duration: 0.18, stagger: 0.04, ease: "back.out(2)" }, tTen + 0.1);
K.pop(tl, "#s02-ten", tTen + 0.3);
tl.fromTo("#s02-src", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.3 }, tTen + 0.2);

// our simulator: 16 bands, hear 2 at a time
K.tagOut(tl, "#s02-tag1", tSim - 0.1);
K.tagIn(tl, "#s02-tag2", tSim + 0.1);
tl.to("#s02-src", { opacity: 0, duration: 0.2 }, tSim);
tl.to(["#s02-bar", "#s02-ticks", "#s02-bracket", "#s02-win", "#s02-ten"], { opacity: 0, duration: 0.22 }, tSim);
tl.set("#s02-bands-wrap", { opacity: 1 }, tSim);
tl.fromTo("#s02-bands .band", { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.28, ease: "back.out(2)", stagger: 0.02 }, tSim + 0.05);
tl.fromTo("#s02-win2", { opacity: 0, scale: 1.4 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)" }, tSim + 0.4);
tl.fromTo("#s02-bands .band .lit", { opacity: 0 }, { opacity: 0.9, duration: 0.2 }, tSim + 0.45);
tl.to("#s02-cone", { attr: { points: "578,364 758,364 1050,672 900,672" }, duration: 0.35, ease: "power2.out" }, tSim + 0.4);
K.pop(tl, "#s02-two", tSim + 0.55);

// statement card
K.statement(tl, "#s02-st", tSt - 0.05, K.dur("s02_5") + 0.3);
tl.set("#s02-B", { opacity: 0 }, tSt + 0.2);
tl.fromTo("#s02-st2", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2.2)" }, tSt + 0.48 * K.dur("s02_5"));
K.tagOut(tl, "#s02-tag2", tSt - 0.1);
