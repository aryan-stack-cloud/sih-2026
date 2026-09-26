// s07 - #3 Bandit: every band is a slot machine. Keep playing the winner, sometimes try a new one.
const G = "s07-g";
K.cam(tl, "#s07-cam", 0, K.D, { s: 1.0 }, { s: 1.04, x: -8, y: 6 });
K.numcard(tl, "#s07-num", "#s07-cam", 0.05, 0.8);
// casino lights chase
for (let i = 1; i <= 23; i++) {
  const reps = Math.max(0, Math.floor((K.D - 0.1) / 0.5) - 1);
  tl.fromTo("#s07-bg-casino-light-" + i, { opacity: 0.45 }, { opacity: 1, duration: 0.25, yoyo: true, repeat: reps, ease: "none" }, 0.05 + (i % 4) * 0.12);
}
tl.fromTo(["#s07-m1", "#s07-m2", "#s07-m3", "#s07-m4"], { y: 500, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, ease: "back.out(1.5)", stagger: 0.08 }, 1.0);
tl.fromTo("#s07-name", { x: -700, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: "back.out(1.4)" }, 1.4);
tl.fromTo("#s07-g-wrap", { x: 420 }, { x: 0, duration: 0.5, ease: "power3.out" }, 1.2);
K.idle(tl, G, 1.2, K.D);
K.blinks(tl, G, 1.2, K.D, 2.2);
tl.fromTo("#s07-win", { opacity: 0 }, { opacity: 1, duration: 0.25 }, 1.25);

function pull(m, t, win) {
  tl.to("#" + m + "-lever", { rotation: 58, svgOrigin: "300 300", duration: 0.18, ease: "power2.in" }, t);
  tl.to("#" + m + "-lever", { rotation: 0, svgOrigin: "300 300", duration: 0.35, ease: "back.out(2)" }, t + 0.2);
  tl.fromTo("#" + m + "-strip", { y: 0 }, { y: -660, duration: 1.0, ease: "power2.out", immediateRender: false }, t + 0.05);
  tl.fromTo("#" + m + "-light", { opacity: 1 }, { opacity: 0.3, duration: 0.08, yoyo: true, repeat: 9, ease: "none", immediateRender: false }, t + 0.05);
  if (win !== undefined) tl.to("#s07-win", { x: win, duration: 0.3, ease: "back.out(1.5)" }, t - 0.1);
}
function payout(t, n) {
  document.querySelectorAll("#s07-coins .coin").forEach((c, i) => {
    const dx = [-60, -20, 30, 70, 5][i], up = [220, 280, 250, 300, 340][i];
    tl.fromTo(c, { x: 0, y: 0, opacity: 0, rotation: 0 }, { x: dx * 0.6, y: -up, opacity: 1, rotation: 180, duration: 0.35, ease: "power2.out", immediateRender: n === 1 }, t + i * 0.05);
    tl.to(c, { x: dx, y: 10, rotation: 360, duration: 0.45, ease: "bounce.out" }, t + i * 0.05 + 0.35);
    tl.to(c, { opacity: 0, duration: 0.3 }, t + i * 0.05 + 1.3);
  });
  tl.fromTo(["#s07-h9", "#s07-h10"], { opacity: 0 }, { opacity: 0.9, duration: 0.15, yoyo: true, repeat: 1, immediateRender: n === 1 }, t);
  tl.fromTo("#s07-score3", { scale: 0.3, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.35, ease: "back.out(2.5)", immediateRender: n === 1 }, t + 0.1);
  tl.set("#s07-sv3", { textContent: "+" + n }, t + 0.1);
}
pull("s07-m3", 1.3);
payout(2.35, 1);
pull("s07-m3", 3.0);
payout(4.05, 2);
K.rot(tl, G, "arm-f", -150, 2.45, 0.3, "back.out(2)");
K.rot(tl, G, "arm-f", 0, 3.2, 0.35);
K.mouth(tl, G, "open", 2.45); K.mouth(tl, G, "closed", 3.2);
K.pop(tl, "#s07-bub", 4.15, { transformOrigin: "88% 115%" });
K.talk(tl, G, 4.2, 4.9);
K.popOut(tl, "#s07-bub", K.cue("s07_2") + 1.2);

// "now and then, try a new one"
K.pop(tl, "#s07-bub2", K.cue("s07_2") + 1.25, { transformOrigin: "88% 115%" });
K.talk(tl, G, K.cue("s07_2") + 1.3, K.cue("s07_2") + 2.0);
pull("s07-m1", K.cue("s07_2") + 1.45, -768);
K.pop(tl, "#s07-score1", K.cue("s07_2") + 2.5);
K.brows(tl, G, 6, K.cue("s07_2") + 2.5);
