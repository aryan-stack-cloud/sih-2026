// s12 - results. Busy night (Scenario B): Index 11 -> 13 of 100, +22%, same 97% reach. Turing data (same 50
// unseen recordings): all four learners more than double the old sweep (+120% to +172%), but reach fewer emitters.
const tC = K.cue("s12_2"), tT = K.cue("s12_3"), tR = K.cue("s12_4");
K.cam(tl, "#s12-cam", 0, K.D, { s: 1.0 }, { s: 1.03, y: -4 });

// A: "So, did it work?"
K.statement(tl, "#s12-st", 0.05, 0.9);
tl.to("#s12-st", { opacity: 0, duration: 0.18 }, tC - 0.15);

// C: busy night, 100-square grids
K.cut(tl, "#s12-C", null, tC - 0.12);
K.tagIn(tl, "#s12-tag2", tC);
tl.fromTo("#s12-src2", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.3 }, tC + 0.2);
tl.fromTo(["#s12-w1", "#s12-w2"], { scale: 0.6, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.4, ease: "back.out(1.6)", stagger: 0.1 }, tC - 0.1);
tl.fromTo("#s12-sig", { opacity: 0, y: -16 }, { opacity: 1, y: 0, duration: 0.3 }, tC + 0.3);
const lit1 = [7, 14, 22, 29, 36, 48, 53, 61, 77, 84, 95];
const lit2 = [4, 11, 19, 27, 33, 42, 50, 58, 66, 71, 79, 88, 97];
lit1.forEach((c, i) => tl.to("#s12-w1-c" + c, { fill: "#FFD166", duration: 0.1 }, tC + 0.45 + i * 0.05));
K.count(tl, "#s12-n1", tC + 0.45, 0, 11, 0.6);
lit2.forEach((c, i) => tl.to("#s12-w2-c" + c, { fill: "#2DB86B", duration: 0.1 }, tC + 1.05 + i * 0.045));
K.count(tl, "#s12-n2", tC + 1.05, 0, 13, 0.6);
tl.set("#s12-reach", { opacity: 0 }, 0);
K.pop(tl, "#s12-plus", tC + 1.95, { duration: 0.45 });
K.pulse(tl, "#s12-plus b", tC + 2.45, tT - 0.2, 0.05, 0.8);
tl.fromTo("#s12-reach", { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.3, ease: "back.out(2)", immediateRender: false }, tC + 2.95);

// T: the Turing scoreboard
K.cut(tl, "#s12-T", "#s12-C", tT - 0.1);
K.tagOut(tl, "#s12-tag2", tT - 0.15); tl.to("#s12-src2", { opacity: 0, duration: 0.2 }, tT - 0.15);
K.tagIn(tl, "#s12-tag5", tT);
tl.fromTo("#s12-src5", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.3 }, tT + 0.2);
K.pop(tl, "#s12-board", tT - 0.08, { duration: 0.45 });
tl.fromTo(["#s12-r1", "#s12-r2", "#s12-r3", "#s12-r4", "#s12-r5"], { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.25, stagger: 0.06 }, tT + 0.1);
// per 100 signal moments: 10.8, 26.7, 23.8, 26.7, 29.5 (track = 32)
const bars = [["1", 10.83, tT + 0.35], ["2", 26.75, tT + 1.3], ["3", 23.83, tT + 1.52], ["4", 26.66, tT + 1.74], ["5", 29.49, tT + 1.96]];
bars.forEach(([i, v, t]) => {
  tl.set("#s12-bar" + i, { scaleX: 0, transformOrigin: "0% 50%" }, 0);
  tl.to("#s12-bar" + i, { scaleX: v / 32, duration: 0.6, ease: "power2.out" }, t);
  K.count(tl, "#s12-val" + i, t, 0, v, 0.6);
});
tl.fromTo("#s12-2x", { opacity: 0, scaleY: 0, transformOrigin: "50% 0%" }, { opacity: 1, scaleY: 1, duration: 0.4, ease: "power2.out" }, tT + 1.0);
["#s12-gain2", "#s12-gain3", "#s12-gain4", "#s12-gain5"].forEach((g, i) => K.pop(tl, g, tT + 2.1 + i * 0.2, { duration: 0.35 }));

// R: "The price: they camp on busy bands, and reach fewer emitters."
tl.set(["#s12-rh", "#s12-rch1", "#s12-rch2", "#s12-rch3", "#s12-rch4", "#s12-rch5"], { opacity: 0 }, 0);
tl.fromTo("#s12-rh", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.3, immediateRender: false }, tR + 0.05);
["#s12-rch1", "#s12-rch2", "#s12-rch3", "#s12-rch4", "#s12-rch5"].forEach((r, i) => tl.fromTo(r, { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.2)", immediateRender: false }, tR + 0.3 + i * 0.15));
tl.fromTo(["#s12-rch2", "#s12-rch3", "#s12-rch4", "#s12-rch5"], { scale: 1 }, { scale: 1.15, duration: 0.14, yoyo: true, repeat: 1, ease: "sine.inOut", immediateRender: false }, tR + 1.3);
