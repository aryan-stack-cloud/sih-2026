// s08 - #4 Q-learning: a cheat sheet of situation x move; one "useless" move pays off later.
const t2 = K.cue("s08_2"), d2 = K.dur("s08_2");
K.cam(tl, "#s08-cam", 0, K.D, { s: 1.0 }, { s: 1.045, x: -10, y: 8 });
K.numcard(tl, "#s08-num", "#s08-cam", 0.05, 0.8);
tl.fromTo("#s08-nb", { y: 760, rotation: 8 }, { y: 0, rotation: -1.5, duration: 0.6, ease: "back.out(1.3)" }, 1.05);
tl.fromTo(["#s08 .chip-col", "#s08 .chip-row", "#s08 .cap"], { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.3, stagger: 0.04 }, 1.5);
tl.fromTo("#s08-name", { x: -700, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: "back.out(1.4)" }, 1.4);
// learning: marks get written in, one by one
["#s08-m1", "#s08-m2", "#s08-m3", "#s08-m4", "#s08-m5", "#s08-m6", "#s08-m7", "#s08-m8"].forEach((m, i) => {
  tl.fromTo(m, { scale: 0, opacity: 0, rotation: -25 }, { scale: 1, opacity: 1, rotation: 0, duration: 0.3, ease: "back.out(2.6)" }, 1.8 + i * 0.36);
});
// "even moves that only pay off later": the crossed-out quiet move turns into a star
const tLater = t2 + 0.5 * d2;
tl.fromTo("#s08-m8", { scale: 1 }, { scale: 1.35, duration: 0.18, yoyo: true, repeat: 3, ease: "sine.inOut", immediateRender: false }, tLater - 0.4);
tl.fromTo("#s08-arrow", { attr: { "stroke-dasharray": "0 700" } }, { attr: { "stroke-dasharray": "700 0" }, duration: 0.5, ease: "power1.inOut" }, tLater);
K.pop(tl, "#s08-ahead", tLater + 0.45, { duration: 0.25 });
K.pop(tl, "#s08-coin", tLater + 0.55);
tl.fromTo("#s08-coin", { rotation: 0 }, { rotation: 360, duration: 0.8, ease: "power2.out", immediateRender: false }, tLater + 0.55);
K.pop(tl, "#s08-bub", tLater + 0.8, { transformOrigin: "20% 110%" });
tl.to("#s08-m8", { scale: 0, opacity: 0, duration: 0.2, ease: "back.in(2)" }, tLater + 0.9);
tl.fromTo("#s08-star", { scale: 0, opacity: 0, rotation: -90 }, { scale: 1, opacity: 1, rotation: 0, duration: 0.45, ease: "back.out(2.5)" }, tLater + 1.05);
K.pulse(tl, "#s08-star", tLater + 1.5, K.D, 0.08, 0.7);
