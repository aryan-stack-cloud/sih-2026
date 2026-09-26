// s08 - #2 Q-learning as a maze: every move has a score; the first run credits only the last move,
// the next run credits the move before it, and run after run the credit flows back until the path lights up.
const E = "s08-e", M = "s08-maze";
const t1 = K.cue("s08_1"), t2 = K.cue("s08_2"), t3 = K.cue("s08_3"), t4 = K.cue("s08_4");
// path cell centres (screen) from START to the signal, badge centres of the 8 path moves, and the tile each move leaves
const P = [[605, 691], [747, 691], [747, 549], [889, 549], [1031, 549], [1031, 407], [1173, 407], [1315, 407], [1315, 265]];
const B = [[676, 649], [795, 620], [818, 507], [960, 507], [1079, 478], [1102, 365], [1244, 365], [1363, 336]];
const TILE = ["c0r3", "c1r3", "c1r2", "c2r2", "c3r2", "c3r1", "c4r1", "c5r1"];
const CREDIT = [3, 4, 5, 6, 7, 8, 9, 10];

K.cam(tl, "#s08-cam", 0, t4, { s: 1.0 }, { s: 1.035, x: -6, y: 4 });
K.cam(tl, "#s08-cam", t4, K.D, { s: 1.035, x: -6, y: 4 }, { s: 1.07, x: -30, y: 10 });
K.numcard(tl, "#s08-num", "#s08-cam", 0.05, 0.8);

// the maze builds itself
tl.fromTo("#s08-board-wrap", { y: 80, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, ease: "back.out(1.3)" }, 1.0);
const tiles = [];
for (let r = 0; r < 4; r++) for (let c = 0; c < 6; c++) tiles.push("#" + M + "-tile-c" + c + "r" + r);
tl.fromTo(tiles, { scale: 0.4, opacity: 0, transformOrigin: "50% 50%" }, { scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2)", stagger: 0.015 }, 1.15);
tl.fromTo("#" + M + "-walls", { opacity: 0 }, { opacity: 1, duration: 0.3 }, 1.5);
K.pop(tl, "#" + M + "-start", 1.6, { transformOrigin: "50% 50%" });
K.pop(tl, "#s08-token", 1.65);
tl.fromTo("#s08-start", { opacity: 0 }, { opacity: 1, duration: 0.3 }, 1.7);
K.pop(tl, "#" + M + "-goal", 1.7, { transformOrigin: "50% 50%" });
tl.fromTo("#" + M + "-goal-glow", { opacity: 0.55 }, { opacity: 1, duration: 0.5, yoyo: true, ease: "sine.inOut", repeat: Math.max(0, Math.floor((K.D - 1.9) / 0.5) - 1) }, 1.9);
tl.fromTo("#s08-name", { x: -700, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: "back.out(1.4)" }, 1.4);
["#s08-lg1", "#s08-lg2", "#s08-lg3"].forEach((l, i) => K.slideIn(tl, l, 1.95 + i * 0.25, -80, 0));
tl.fromTo("#s08-e-wrap", { x: 420 }, { x: 0, duration: 0.55, ease: "power3.out" }, 1.3);
K.idle(tl, E, 1.3, K.D);
K.blinks(tl, E, 1.3, K.D, 2.4);

// "...where every move gets a score": all the moves appear with a score of 0
const arrows = [];
for (let k = 1; k <= 8; k++) arrows.push("#" + M + "-arrow-" + k);
for (let j = 1; j <= 4; j++) arrows.push("#" + M + "-alt-" + j);
tl.fromTo(arrows, { scale: 0, opacity: 0, transformOrigin: "50% 50%" }, { scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2.4)", stagger: 0.05 }, t1 + 2.45);
const badges = [];
for (let k = 1; k <= 8; k++) badges.push("#s08-a" + k);
for (let j = 1; j <= 4; j++) badges.push("#s08-l" + j);
tl.fromTo(badges, { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.28, ease: "back.out(2.4)", stagger: 0.05 }, t1 + 2.7);
tl.set(["#s08-run", "#s08-p", "#s08-burst", "#s08-bub"], { opacity: 0 }, 0);

// helpers: walk the token along the path, flash the signal, credit one move, fly a credit spark back
function walk(t, step) {
  for (let k = 1; k < P.length; k++) {
    tl.to("#s08-token", { x: P[k][0] - P[0][0], y: P[k][1] - P[0][1], duration: step * 0.85, ease: "power1.inOut" }, t + (k - 1) * step);
  }
  return t + (P.length - 1) * step;
}
function reset(t) {
  tl.to("#s08-token", { opacity: 0, scale: 0.5, duration: 0.12 }, t);
  tl.set("#s08-token", { x: 0, y: 0 }, t + 0.13);
  tl.to("#s08-token", { opacity: 1, scale: 1, duration: 0.18, ease: "back.out(2)" }, t + 0.14);
}
function reach(t) {
  tl.fromTo("#s08-burst", { opacity: 1, scale: 0.4, rotation: 0 }, { opacity: 0, scale: 1.5, rotation: 30, duration: 0.55, ease: "power2.out", immediateRender: false }, t);
  tl.fromTo("#" + M + "-goal", { scale: 1 }, { scale: 1.35, duration: 0.14, yoyo: true, repeat: 1, ease: "sine.out", transformOrigin: "50% 50%", immediateRender: false }, t);
}
function credit(k, t) {   // k = 1..8
  const id = "#s08-a" + k;
  tl.set(id, { textContent: "+" + CREDIT[k - 1] }, t);
  tl.to(id, { backgroundColor: "#1E8A4F", color: "#FDFCF8", duration: 0.15 }, t);
  tl.fromTo(id, { scale: 1 }, { scale: 1.35, duration: 0.14, yoyo: true, repeat: 1, ease: "sine.out", immediateRender: false }, t);
  tl.to("#" + M + "-arrow-" + k, { attr: { fill: "#2DB86B" }, duration: 0.2 }, t);
  tl.to("#" + M + "-glow-" + TILE[k - 1], { opacity: 0.32, duration: 0.3 }, t);
}
function spark(from, to, t, d) {  // badge index 1..8
  const a = B[from - 1], b = B[to - 1];
  tl.fromTo("#s08-p", { x: a[0] - 13, y: a[1] - 13, opacity: 1, scale: 1 }, { x: b[0] - 13, y: b[1] - 13, opacity: 1, scale: 1, duration: d, ease: "power1.inOut", immediateRender: false }, t);
  tl.to("#s08-p", { opacity: 0, scale: 0.4, duration: 0.1 }, t + d);
}

// RUN 1 - "The first time it reaches a signal, only the last move gets credit."
K.pop(tl, "#s08-run", t2 - 0.25);
const r1 = walk(t2 + 0.1, 0.2);
reach(r1 + 0.02);
credit(8, t2 + 2.1);
// the engineer points at the credited move (arm-n swings left toward the board)
K.rot(tl, E, "arm-n", 78, t2 + 2.0, 0.35, "back.out(2)");
K.rot(tl, E, "fore-n", 25, t2 + 2.05, 0.35, "back.out(2)");
K.rot(tl, E, "arm-n", 0, t2 + 3.1, 0.4);
K.rot(tl, E, "fore-n", 0, t2 + 3.1, 0.4);

// RUN 2 - "Next time, the move before that gets credit too, because it led there."
tl.set("#s08-runv", { textContent: "2" }, t3 - 0.15);
tl.fromTo("#s08-run b", { scale: 1.3 }, { scale: 1, duration: 0.3, ease: "back.out(2)", immediateRender: false }, t3 - 0.15);
reset(t3 - 0.1);
const r2 = walk(t3 + 0.1, 0.14);
reach(r2 + 0.02);
spark(8, 7, t3 + 1.5, 0.42);
credit(7, t3 + 1.95);
K.pop(tl, "#s08-bub", t3 + 2.3, { transformOrigin: "18% 115%" });
K.talk(tl, E, t3 + 2.35, t3 + 3.05);
K.popOut(tl, "#s08-bub", t4 - 0.1);

// RUN 3 -> 20 - "Run after run, the credit flows back, until the whole path lights up."
for (let n = 3; n <= 20; n++) tl.set("#s08-runv", { textContent: String(n) }, t4 + 0.1 + (n - 3) * 0.14);
[6, 5, 4, 3, 2, 1].forEach((k, i) => {
  const t = t4 + 0.35 + i * 0.35;
  spark(k + 1, k, t - 0.3, 0.28);
  credit(k, t);
});
tl.to(TILE.map((c) => "#" + M + "-glow-" + c), { opacity: 0.55, duration: 0.25, yoyo: true, repeat: 3, ease: "sine.inOut" }, t4 + 2.55);
reset(t4 + 2.5);
const r3 = walk(t4 + 2.7, 0.11);
reach(r3 + 0.02);
K.rot(tl, E, "arm-n", -150, t4 + 2.7, 0.3, "back.out(2)");
K.rot(tl, E, "arm-f", 150, t4 + 2.7, 0.3, "back.out(2)");
K.mouth(tl, E, "open", t4 + 2.7);
