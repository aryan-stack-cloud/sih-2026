// s02 - "why not a bigger searchlight?" -> the real hardware limit -> 2 of 16 -> make it smarter
const G = "s02-g", E = "s02-e";
const tB = K.cue("s02_2"), d2 = K.dur("s02_2");
const tTen = K.cue("s02_3"), tSim = K.cue("s02_4"), tSt = K.cue("s02_5");

// Shot A: the daydream
K.cam(tl, "#s02-A", 0, tB, { s: 1 }, { s: 1.04, x: -10 });
K.idle(tl, G, 0, tB);
K.blinks(tl, G, 0, tB, 2.2);
K.rot(tl, G, "head", -8, K.cue("s02_1") + 0.1, 0.5, "sine.inOut");
K.brows(tl, G, -7, K.cue("s02_1") + 0.1);
tl.fromTo("#s02-cloud", { scale: 0.1, opacity: 0, x: -260, y: 260 }, { scale: 1, opacity: 1, x: 0, y: 0, duration: 0.55, ease: "back.out(1.6)" }, K.cue("s02_1") + 0.05);
tl.fromTo("#s02-bigbeam", { opacity: 0 }, { opacity: 1, duration: 0.5, ease: "power2.out" }, K.cue("s02_1") + 0.55);
K.pulse(tl, "#s02-bigsl", K.cue("s02_1") + 0.6, tB, 0.05, 0.8);
// the engineer walks in and bursts the bubble
tl.fromTo("#s02-e-wrap", { x: 620 }, { x: 0, duration: 0.6, ease: "power3.out" }, K.end("s02_1") - 0.2);
K.blinks(tl, E, K.end("s02_1"), tB, 2.0);
K.pop(tl, "#s02-bub-e", K.end("s02_1") + 0.2, { transformOrigin: "85% 115%" });
K.talk(tl, E, K.end("s02_1") + 0.22, K.end("s02_1") + 1.15);
K.rot(tl, E, "arm-n", -28, K.end("s02_1") + 0.2, 0.3, "back.out(2)");
K.rot(tl, E, "fore-n", -60, K.end("s02_1") + 0.25, 0.3, "back.out(2)");
tl.to("#s02-cloud", { scale: 1.15, opacity: 0, duration: 0.2, ease: "power2.in" }, K.end("s02_1") + 1.0);
K.mouth(tl, G, "o", K.end("s02_1") + 1.0);
K.brows(tl, G, 0, K.end("s02_1") + 1.0);

// Shot B: the real receiver
K.cut(tl, "#s02-B", "#s02-A", tB);
K.cam(tl, "#s02-B", tB, tSt, { s: 1.0 }, { s: 1.03, y: -6 });
K.tagIn(tl, "#s02-tag1", tB + 0.15);
tl.fromTo("#s02-bar", { scaleX: 0 }, { scaleX: 1, duration: 0.6, ease: "power3.out", transformOrigin: "0% 50%" }, tB);
tl.fromTo(["#s02-ant", "#s02-rx", "#s02-lap"], { y: 80, opacity: 0 }, { y: 0, opacity: 1, duration: 0.45, ease: "back.out(1.7)", stagger: 0.14 }, tB + 0.2);
tl.fromTo(["#s02-l-ant", "#s02-l-rx", "#s02-l-lap"], { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.3, stagger: 0.14 }, tB + 0.55);
tl.fromTo(["#s02-cable1", "#s02-cable2"], { attr: { "stroke-dasharray": "0 1400" } }, { attr: { "stroke-dasharray": "1400 0" }, duration: 0.7, ease: "power1.inOut" }, tB + 0.45);
tl.fromTo("#s02-ant", { scale: 1 }, { scale: 1.03, duration: 0.3, yoyo: true, repeat: 7, ease: "sine.inOut", immediateRender: false }, tB + 0.9);
for (let i = 1; i <= 6; i++) tl.fromTo("#s02-rx-rx-led-" + i, { opacity: 0.35 }, { opacity: 1, duration: 0.15, yoyo: true, repeat: 9, ease: "none" }, tB + 0.8 + i * 0.07);
// the "beam" of the receiver: a narrow window on the wide spectrum
const tWin = tB + 0.42 * d2;
tl.fromTo("#s02-win", { opacity: 0, scale: 1.6 }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)" }, tWin);
tl.fromTo("#s02-cone", { opacity: 0 }, { opacity: 1, duration: 0.35 }, tWin);
K.pop(tl, "#s02-ib", tWin + 0.5);
tl.to("#s02-rx-rx-dial-needle", { rotation: 40, svgOrigin: "194 267", duration: 1.2, ease: "sine.inOut", yoyo: true, repeat: 3 }, tWin);

// "at least ten times narrower": ruler of 10 equal slices
K.popOut(tl, "#s02-ib", tTen - 0.05);
tl.fromTo("#s02-bracket", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.35 }, tTen);
tl.fromTo("#s02-ticks .tick", { scaleY: 0, opacity: 0 }, { scaleY: 1, opacity: 0.9, duration: 0.2, stagger: 0.07, ease: "back.out(2)" }, tTen + 0.2);
K.pop(tl, "#s02-ten", tTen + 1.5);
tl.fromTo("#s02-src", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35 }, tTen + 0.3);

// Shot C: our simulator = 16 bands, hear 2 at a time
K.tagOut(tl, "#s02-tag1", tSim - 0.1);
K.tagIn(tl, "#s02-tag2", tSim + 0.15);
tl.to("#s02-src", { opacity: 0, duration: 0.2 }, tSim);
tl.to(["#s02-bar", "#s02-ticks", "#s02-bracket", "#s02-win", "#s02-ten"], { opacity: 0, duration: 0.25 }, tSim);
tl.set("#s02-bands-wrap", { opacity: 1 }, tSim);
tl.fromTo("#s02-bands .band", { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2)", stagger: 0.03 }, tSim + 0.05);
tl.fromTo("#s02-win2", { opacity: 0, scale: 1.4 }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)" }, tSim + 0.7);
tl.fromTo("#s02-bands .band .lit", { opacity: 0 }, { opacity: 0.9, duration: 0.2 }, tSim + 0.8);
tl.to("#s02-cone", { attr: { points: "578,364 758,364 1050,672 900,672" }, duration: 0.35, ease: "power2.out" }, tSim + 0.7);
K.pop(tl, "#s02-two", tSim + 1.3);

// Shot D: statement card
K.statement(tl, "#s02-st", tSt - 0.05, 3);
tl.set("#s02-B", { opacity: 0 }, tSt + 0.2);
tl.fromTo("#s02-st2", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2.2)" }, tSt + 0.48 * K.dur("s02_5"));
K.tagOut(tl, "#s02-tag2", tSt - 0.1);
