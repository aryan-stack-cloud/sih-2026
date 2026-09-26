// s05 - #1 CTMC: roll the dice -> random hops at random times -> the rhythm can't time it.
const I = "s05-i";
const WINX = (p) => -11 + p * 192;           // window x for band pair p (0..7)
K.cam(tl, "#s05-cam", 0, K.D, { s: 1.0 }, { s: 1.045, x: -12, y: 6 });
K.numcard(tl, "#s05-num", "#s05-cam", 0.05, 0.8);
tl.fromTo("#s05-name", { x: -700, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: "back.out(1.4)" }, K.cue("s05_1") + 1.05);

// the intruder and its metronome are back from the rhythm trap
tl.fromTo("#s05-met-metro-arm", { rotation: -24, svgOrigin: "200 446" }, { rotation: 24, svgOrigin: "200 446", duration: 0.3, ease: "sine.inOut", yoyo: true, repeat: Math.max(0, Math.floor(K.D / 0.3) - 1) }, 0);
K.pulse(tl, "#s05-i-wrap", 0, K.D, 0.02, 0.6);

// the dice: a 3/4 resting pose, then four rolls with different waits
tl.set("#s05-cube", { rotationX: -24, rotationY: 36 }, 0);
const rolls = [[1.2, 425, 575, 5], [2.3, 695, 1025, 1], [3.55, 1055, 1295, 6], [5.0, 1505, 1655, 3]];
rolls.forEach(([t, rx, ry, p]) => {
  tl.to("#s05-cube", { rotationX: rx, rotationY: ry, duration: 0.55, ease: "power3.out" }, t);
  tl.fromTo("#s05-dice", { y: 0 }, { y: -150, duration: 0.24, ease: "power2.out", yoyo: true, repeat: 1, immediateRender: false }, t);
  tl.fromTo("#s05-dshadow", { scale: 1, opacity: 1 }, { scale: 0.6, opacity: 0.5, duration: 0.24, ease: "power2.out", yoyo: true, repeat: 1, immediateRender: false }, t);
  tl.to("#s05-win", { x: WINX(p) + 11, duration: 0.28, ease: "back.out(1.6)" }, t + 0.5);
});
// the signal flashes on its old rhythm - but this time the window lands on it
const tHit = 3.55 + 0.5;
tl.set(["#s05-f13", "#s05-f14"], { opacity: 1 }, tHit - 0.08);
tl.set("#" + I + "-beam", { opacity: 1 }, tHit - 0.08);
tl.set(["#s05-f13", "#s05-f14"], { opacity: 0 }, tHit + 0.2);
tl.fromTo(["#s05-h13", "#s05-h14"], { opacity: 0 }, { opacity: 1, duration: 0.12 }, tHit + 0.2);
tl.to(["#s05-h13", "#s05-h14"], { opacity: 0, duration: 0.4 }, tHit + 1.2);
tl.set("#" + I + "-beam", { opacity: 0 }, tHit + 0.35);
K.stamp(tl, "#s05-stamp", tHit + 0.15, 6);
tl.to("#s05-stamp", { opacity: 0, duration: 0.3 }, tHit + 1.5);
tl.fromTo("#s05-i-wrap", { rotation: 0 }, { rotation: -6, duration: 0.1, yoyo: true, repeat: 5, immediateRender: false, transformOrigin: "50% 100%" }, tHit + 0.2);
K.pop(tl, "#s05-bub", 2.75, { transformOrigin: "88% 115%" });
K.popOut(tl, "#s05-bub", tHit - 0.1);
tl.fromTo("#s05-src", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.3 }, tHit + 0.3);
