// s04 - the plan: look -> learn -> pick every 10 ms; six ways to pick, sorted into three families (shown).
const E = "s04-e";
const d1 = K.dur("s04_1"), t1 = K.cue("s04_1");
const tSix = K.cue("s04_2"), tFam = K.end("s04_2") - 0.45;

// Shot A: whiteboard loop
K.cam(tl, "#s04-A", 0, tSix, { s: 1.0 }, { s: 1.04, x: 14 });
K.tagIn(tl, "#s04-tag", 0.2);
K.idle(tl, E, 0, tSix);
K.blinks(tl, E, 0, tSix, 2.3);
K.rot(tl, E, "arm-n", 62, 0.25, 0.4, "back.out(1.6)");
K.rot(tl, E, "fore-n", 55, 0.3, 0.4, "back.out(1.6)");
tl.fromTo("#" + E + "-fore-n", { rotation: 55 }, { rotation: 66, svgOrigin: K.piv(E, "fore-n"), duration: 0.16, yoyo: true, repeat: 17, ease: "sine.inOut", immediateRender: false }, 0.8);
K.pop(tl, "#s04-ms", t1 + 0.1 * d1);
const nodes = ["#s04-n1", "#s04-n2", "#s04-n3"], at = [0.3, 0.48, 0.64];
nodes.forEach((n, i) => K.pop(tl, n, t1 + at[i] * d1));
const arcs = ["#s04-arc1", "#s04-arc2", "#s04-arc3"], heads = ["#s04-h1", "#s04-h2", "#s04-h3"];
arcs.forEach((a, i) => {
  const ta = t1 + at[i] * d1 + 0.3;
  tl.fromTo(a, { attr: { "stroke-dasharray": "0 900" } }, { attr: { "stroke-dasharray": "900 0" }, duration: 0.5, ease: "power1.inOut" }, ta);
  K.pop(tl, heads[i], ta + 0.45, { duration: 0.25 });
});
// the loop keeps running: nodes light up in turn
for (let r = 0; r < 3; r++) nodes.forEach((n, i) => {
  const tp = t1 + 0.72 * d1 + (r * 3 + i) * 0.33;
  if (tp < tSix - 0.3) tl.fromTo(n, { scale: 1 }, { scale: 1.12, duration: 0.15, yoyo: true, repeat: 1, ease: "sine.inOut", immediateRender: false }, tp);
});
K.pulse(tl, "#s04-ms", t1 + 0.1 * d1 + 0.45, tSix, 0.05, 0.66);

// Shot B: six ways, sorted into three families
K.cut(tl, "#s04-B", "#s04-A", tSix - 0.05);
K.tagOut(tl, "#s04-tag", tSix - 0.1);
K.cam(tl, "#s04-B", tSix - 0.05, K.D, { s: 1.0 }, { s: 1.03, y: -6 });
const tiles = ["#s04-t6", "#s04-t1", "#s04-t4", "#s04-t5", "#s04-t2", "#s04-t3"];      // jumbled row
const finalX = { "#s04-t1": 195, "#s04-t2": 445, "#s04-t3": 735, "#s04-t4": 985, "#s04-t5": 1275, "#s04-t6": 1525 };
tiles.forEach((t, i) => {
  const rowX = 160 + i * 280;
  tl.fromTo(t, { x: rowX - finalX[t], y: 60, scale: 0, opacity: 0, rotation: (i % 2 ? 8 : -8) }, { scale: 1, opacity: 1, rotation: (i % 2 ? 4 : -4), duration: 0.4, ease: "back.out(2.2)" }, tSix + 0.12 + i * 0.08);
});
K.pop(tl, "#s04-six", tSix + 0.3);
tl.to("#s04-six", { opacity: 0, y: 30, duration: 0.25 }, tFam - 0.05);
const fam = [["#s04-f1", ["#s04-t1", "#s04-t2"], 0.0], ["#s04-f2", ["#s04-t3", "#s04-t4"], 0.25], ["#s04-f3", ["#s04-t5", "#s04-t6"], 0.5]];
fam.forEach(([f, ts, frac]) => {
  const tf = tFam + frac;
  tl.fromTo(f, { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.35, ease: "power3.out" }, tf);
  ts.forEach((t, j) => tl.to(t, { x: 0, y: 0, rotation: 0, duration: 0.5, ease: "back.out(1.4)" }, tf + 0.1 + j * 0.08));
});
