// s08 - #4 Q-learning: a cheat sheet with a score for every move in every situation; a move that only
// sets up a catch a few steps later gets credit flowing back to it (1 -> 6).
const t2 = K.cue("s08_2"), t3 = K.cue("s08_3");
K.cam(tl, "#s08-cam", 0, K.D, { s: 1.0 }, { s: 1.045, x: -10, y: 8 });
K.numcard(tl, "#s08-num", "#s08-cam", 0.05, 0.8);
tl.fromTo("#s08-nb", { y: 760, rotation: 8 }, { y: 0, rotation: -1.5, duration: 0.6, ease: "back.out(1.3)" }, 1.05);
tl.fromTo(["#s08 .chip-col", "#s08 .chip-row", "#s08 .cap"], { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.3, stagger: 0.04 }, 1.5);
tl.fromTo("#s08-name", { x: -700, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: "back.out(1.4)" }, 1.4);
tl.set(["#s08-rowhi", "#s08-best", "#s08-ring", "#s08-steps", "#s08-credit"], { opacity: 0 }, 0);

// "For each situation, ..." -> the situations light up in turn
["#s08-r1", "#s08-r2", "#s08-r3", "#s08-r4"].forEach((r, i) => tl.fromTo(r, { scale: 1 }, { scale: 1.12, duration: 0.14, yoyo: true, repeat: 1, ease: "sine.inOut", immediateRender: false }, t2 + i * 0.15));
// "...it scores every move." -> a score is written into every cell, row by row
const cells = [];
for (let r = 1; r <= 4; r++) for (let c = 1; c <= 4; c++) cells.push("#s08-v" + r + c);
cells.forEach((v, i) => tl.fromTo(v, { scale: 0, opacity: 0, rotation: -20 }, { scale: 1, opacity: 1, rotation: 0, duration: 0.28, ease: "back.out(2.6)" }, t2 + 0.55 + i * 0.07));
// in a busy moment, the best-scoring move is the one it picks
tl.to("#s08-rowhi", { opacity: 0.45, duration: 0.2 }, t2 + 1.85);
K.pop(tl, "#s08-best", t2 + 1.95, { duration: 0.35 });
tl.to(["#s08-rowhi", "#s08-best"], { opacity: 0, duration: 0.25 }, t3 - 0.1);

// "Even a move that sets up a catch a few steps later gets credit."
K.pop(tl, "#s08-ring", t3 + 0.05, { duration: 0.35 });
tl.fromTo("#s08-v13", { scale: 1 }, { scale: 1.3, duration: 0.15, yoyo: true, repeat: 1, ease: "sine.inOut", immediateRender: false }, t3 + 0.15);
tl.fromTo("#s08-arrow", { attr: { "stroke-dasharray": "0 700" } }, { attr: { "stroke-dasharray": "700 0" }, duration: 0.5, ease: "power1.inOut" }, t3 + 0.35);
["#s08-d1", "#s08-d2", "#s08-d3"].forEach((d, i) => {
  K.pop(tl, d, t3 + 0.45 + i * 0.15, { duration: 0.25, transformOrigin: "50% 50%" });
  tl.to(d, { attr: { fill: "#FFC43D" }, duration: 0.1 }, t3 + 0.55 + i * 0.15);
});
tl.fromTo("#s08-steps", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.3 }, t3 + 0.55);
K.pop(tl, "#s08-ahead", t3 + 0.8, { duration: 0.25 });
K.pop(tl, "#s08-coin", t3 + 1.0);
tl.fromTo("#s08-coin", { rotation: 0 }, { rotation: 360, duration: 0.8, ease: "power2.out", immediateRender: false }, t3 + 1.0);
// the credit flows back to the move that set it up
K.pop(tl, "#s08-credit", t3 + 1.8, { duration: 0.3 });
tl.to("#s08-credit", { x: -505, duration: 0.5, ease: "power1.inOut" }, t3 + 2.0);
tl.to("#s08-credit", { y: -110, duration: 0.25, ease: "power1.out" }, t3 + 2.0);
tl.to("#s08-credit", { y: -68, duration: 0.25, ease: "power1.in" }, t3 + 2.25);
tl.to("#s08-credit", { opacity: 0, scale: 0.6, duration: 0.15 }, t3 + 2.45);
K.count(tl, "#s08-v13", t3 + 2.45, 1, 6, 0.35);
tl.to("#s08-v13", { color: "#1E8A4F", duration: 0.2 }, t3 + 2.45);
tl.fromTo("#s08-v13", { scale: 1 }, { scale: 1.4, duration: 0.18, yoyo: true, repeat: 1, ease: "sine.out", immediateRender: false }, t3 + 2.45);
tl.to("#s08-ring", { borderColor: "#2DB86B", duration: 0.2 }, t3 + 2.45);
K.pop(tl, "#s08-bub", t3 + 2.55, { transformOrigin: "20% 110%" });
K.pulse(tl, "#s08-ring", t3 + 2.8, K.D, 0.06, 0.7);
