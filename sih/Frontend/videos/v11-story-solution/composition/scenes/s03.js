// s03 - the old way: a fixed clock-hand sweep; a signal on the same rhythm is never caught.
const D = "s03-dial", I = "s03-i";
const STEP = 0.3, T0 = 0.5;
const tIntro = K.cue("s03_2"), tTest = K.cue("s03_3");

K.cam(tl, "#s03-cam", 0, K.D, { s: 1.0 }, { s: 1.05, x: 20, y: -8 });
K.tagIn(tl, "#s03-tag1", 0.3);
K.pop(tl, "#" + D, 0.05, { duration: 0.5 });

// clock-hand sweep: 8 positions (2 bands each), stepping in a fixed order forever
let prev = null;
for (let k = 0, t = T0; t < K.D - 0.05; k++, t = T0 + k * STEP) {
  const p = k % 8;
  tl.set("#" + D + "-hand", { rotation: p * 45, svgOrigin: "400 400" }, t);
  if (prev !== null) tl.set(["#" + D + "-slot-" + (2 * prev + 1) + "-lit", "#" + D + "-slot-" + (2 * prev + 2) + "-lit"], { opacity: 0 }, t);
  tl.set(["#" + D + "-slot-" + (2 * p + 1) + "-lit", "#" + D + "-slot-" + (2 * p + 2) + "-lit"], { opacity: 0.9 }, t);
  prev = p;
  // the signal in bands 13-14 lives on the same rhythm: it flashes while the hand is at 5-6
  if (p === 2 && t > tIntro + 0.6) {
    tl.set(["#" + D + "-slot-13-red", "#" + D + "-slot-14-red"], { opacity: 1 }, t + 0.04);
    tl.set(["#" + D + "-slot-13-red", "#" + D + "-slot-14-red"], { opacity: 0 }, t + 0.26);
    tl.set("#" + I + "-beam", { opacity: 1 }, t + 0.04);
    tl.set("#" + I + "-beam", { opacity: 0 }, t + 0.26);
  }
}

// the sneaky signal with its metronome
tl.fromTo("#s03-i-wrap", { x: 420, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: "back.out(1.5)" }, tIntro);
K.pop(tl, "#s03-met", tIntro + 0.15);
tl.fromTo("#s03-met-metro-arm", { rotation: -24, svgOrigin: "200 446" }, { rotation: 24, svgOrigin: "200 446", duration: STEP, ease: "sine.inOut", yoyo: true, repeat: Math.max(0, Math.floor((K.D - tIntro) / STEP) - 2) }, tIntro + 0.2);
K.pulse(tl, "#s03-i-wrap", tIntro + 0.6, K.D, 0.025, STEP * 2);
K.pop(tl, "#s03-bub", tIntro + 0.6 * K.dur("s03_2"), { transformOrigin: "30% 110%" });
K.popOut(tl, "#s03-bub", tTest + 0.6);
K.pop(tl, "#s03-count", tIntro + 1.4);
tl.fromTo("#s03-count b", { scale: 1 }, { scale: 1.12, duration: 0.12, yoyo: true, repeat: 1, immediateRender: false }, tIntro + 3.7);

// the test result
K.tagOut(tl, "#s03-tag1", tTest - 0.1);
K.tagIn(tl, "#s03-tag2", tTest + 0.1);
tl.fromTo("#s03-src", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35 }, tTest + 0.4);
K.stamp(tl, "#s03-stamp", K.end("s03_3") - 1.0, -7);
