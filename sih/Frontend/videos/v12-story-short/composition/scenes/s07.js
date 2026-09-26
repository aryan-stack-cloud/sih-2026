// s07 - #3 Bandit: every band is a slot machine. A catch is a win; it keeps score on every machine and keeps
// playing the one that wins most; now and then it tries another (explore), then goes back to the winner.
const G = "s07-g";
const t2 = K.cue("s07_2"), t3 = K.cue("s07_3");
const WX = { m1: -768, m2: -384, m3: 0, m4: 384 };   // window x offset for each machine's band pair
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
tl.set(["#s07-t1", "#s07-t2", "#s07-t3", "#s07-t4"], { opacity: 0 }, 0);
["#s07-c1", "#s07-c2", "#s07-c3"].forEach((c) => tl.set(c, { opacity: 0 }, 0));

// "every band is a slot machine": the window visits each machine's band pair, the machine hops
[["m1", 1.55], ["m2", 1.95], ["m3", 2.35], ["m4", 2.75]].forEach(([m, t]) => {
  tl.to("#s07-win", { x: WX[m], duration: 0.25, ease: "back.out(1.5)" }, t - 0.12);
  tl.fromTo("#s07-" + m, { y: 0 }, { y: -18, duration: 0.14, yoyo: true, repeat: 1, ease: "sine.out", immediateRender: false }, t);
});
tl.to("#s07-win", { x: WX.m3, duration: 0.3, ease: "back.out(1.5)" }, 3.0);

function pull(m, t) {
  tl.to("#s07-" + m + "-lever", { rotation: 58, svgOrigin: "300 300", duration: 0.18, ease: "power2.in" }, t);
  tl.to("#s07-" + m + "-lever", { rotation: 0, svgOrigin: "300 300", duration: 0.35, ease: "back.out(2)" }, t + 0.2);
  tl.fromTo("#s07-" + m + "-strip", { y: 0 }, { y: -660, duration: 1.0, ease: "power2.out", immediateRender: false }, t + 0.05);
  tl.fromTo("#s07-" + m + "-light", { opacity: 1 }, { opacity: 0.3, duration: 0.08, yoyo: true, repeat: 9, ease: "none", immediateRender: false }, t + 0.05);
}
function payout(t, first) {
  document.querySelectorAll("#s07-coins .coin").forEach((c, i) => {
    const dx = [-60, -20, 30, 70, 5][i], up = [220, 280, 250, 300, 340][i];
    tl.fromTo(c, { x: 0, y: 0, opacity: 0, rotation: 0 }, { x: dx * 0.6, y: -up, opacity: 1, rotation: 180, duration: 0.35, ease: "power2.out", immediateRender: first }, t + i * 0.05);
    tl.to(c, { x: dx, y: 45, rotation: 360, duration: 0.45, ease: "bounce.out" }, t + i * 0.05 + 0.35);
    tl.to(c, { opacity: 0, duration: 0.3 }, t + i * 0.05 + 1.2);
  });
  tl.fromTo(["#s07-h9", "#s07-h10"], { opacity: 0 }, { opacity: 0.9, duration: 0.15, yoyo: true, repeat: 1, immediateRender: first }, t - 0.05);
}
function flashTray(n, color, t) {
  tl.fromTo("#s07-t" + n, { backgroundColor: "#1F2340" }, { backgroundColor: color, duration: 0.14, yoyo: true, repeat: 3, ease: "none", immediateRender: false }, t);
  tl.fromTo("#s07-n" + n, { scale: 1 }, { scale: 1.35, duration: 0.14, yoyo: true, repeat: 1, ease: "sine.out", immediateRender: false }, t);
}

// "A catch is a win."
pull("m3", t2 - 0.35);
payout(t2 + 0.65, true);
K.pop(tl, "#s07-c1", t2 + 0.45, { transformOrigin: "50% 120%" });
K.rot(tl, G, "arm-f", -150, t2 + 0.7, 0.3, "back.out(2)");
K.rot(tl, G, "arm-f", 0, t2 + 1.4, 0.35);
K.mouth(tl, G, "open", t2 + 0.7); K.mouth(tl, G, "closed", t2 + 1.4);

// "It keeps score," -> every machine's win counter lights up; the one it just won on already reads 6
K.popOut(tl, "#s07-c1", t2 + 1.3);
tl.fromTo(["#s07-t1", "#s07-t2", "#s07-t3", "#s07-t4"], { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.4)", stagger: 0.07, immediateRender: false }, t2 + 1.35);
flashTray(3, "#1E8A4F", t2 + 1.75);

// "...and keeps playing the bands that win the most."
pull("m3", t2 + 2.2);
K.pop(tl, "#s07-c2", t2 + 2.4, { transformOrigin: "50% 120%" });
payout(t2 + 3.2, false);
tl.set("#s07-n3", { textContent: "7" }, t2 + 3.3);
flashTray(3, "#1E8A4F", t2 + 3.3);
K.pop(tl, "#s07-bub", t2 + 3.3, { transformOrigin: "88% 115%" });
K.talk(tl, G, t2 + 3.35, t2 + 4.0);

// "But now and then, it tries a new one, just in case it pays better."
K.popOut(tl, "#s07-bub", t3 - 0.05);
K.popOut(tl, "#s07-c2", t3 + 0.2);
K.pop(tl, "#s07-bub2", t3 + 0.2, { transformOrigin: "88% 115%" });
K.talk(tl, G, t3 + 0.25, t3 + 0.95);
tl.to("#s07-win", { x: WX.m1, duration: 0.3, ease: "back.out(1.5)" }, t3 + 0.35);
pull("m1", t3 + 0.45);
K.pop(tl, "#s07-c3", t3 + 0.6, { transformOrigin: "42% 120%" });
flashTray(1, "#E63946", t3 + 1.5);       // no win this time: the counter stays at 1
K.brows(tl, G, 6, t3 + 1.5);
K.popOut(tl, "#s07-bub2", t3 + 1.9);
tl.to("#s07-win", { x: WX.m3, duration: 0.35, ease: "back.out(1.5)" }, t3 + 2.3);   // ...and back to the winner
tl.fromTo("#s07-m3", { y: 0 }, { y: -18, duration: 0.14, yoyo: true, repeat: 1, ease: "sine.out", immediateRender: false }, t3 + 2.45);
K.brows(tl, G, 0, t3 + 2.4);
