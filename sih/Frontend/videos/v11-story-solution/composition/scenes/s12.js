// s12 - results: rhythm trap, busy night (11 -> 13 of 100, +22%), same reach (97%), greedy Bandit, speed.
const G = "s12-g";
const tB = K.cue("s12_2"), tC = K.cue("s12_3"), t4 = K.cue("s12_4"), tD = K.cue("s12_5"), tE = K.cue("s12_6"), tF = K.cue("s12_7");
K.cam(tl, "#s12-cam", 0, K.D, { s: 1.0 }, { s: 1.03, y: -4 });

// A: "So, did it work?"
K.statement(tl, "#s12-st", 0.05, 1.2);
tl.to("#s12-st", { opacity: 0, duration: 0.2 }, tB - 0.12);

// B: the rhythm trap scoreboard
K.cut(tl, "#s12-B", null, tB - 0.1);
K.tagIn(tl, "#s12-tag1", tB);
tl.fromTo("#s12-src1", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.3 }, tB + 0.2);
[["#s12-c1", 0.9], ["#s12-c2", 1.9], ["#s12-c3", 2.7]].forEach(([c, dt]) => tl.fromTo(c, { y: 300, opacity: 0, rotation: -4 }, { y: 0, opacity: 1, rotation: 0, duration: 0.45, ease: "back.out(1.6)" }, tB + dt));
tl.fromTo("#s12-c1 strong", { scale: 1 }, { scale: 1.15, duration: 0.12, yoyo: true, repeat: 1, immediateRender: false }, tB + 1.2);

// C: busy night, 100-square grids
K.cut(tl, "#s12-C", "#s12-B", tC - 0.1);
K.tagOut(tl, "#s12-tag1", tC - 0.15); tl.to("#s12-src1", { opacity: 0, duration: 0.2 }, tC - 0.15);
K.tagIn(tl, "#s12-tag2", tC);
tl.fromTo("#s12-src2", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.3 }, tC + 0.2);
tl.fromTo(["#s12-w1", "#s12-w2"], { scale: 0.6, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.45, ease: "back.out(1.6)", stagger: 0.12 }, tC);
tl.fromTo("#s12-sig", { opacity: 0, y: -16 }, { opacity: 1, y: 0, duration: 0.3 }, tC + 0.5);
const lit1 = [7, 14, 22, 29, 36, 48, 53, 61, 77, 84, 95];
const lit2 = [4, 11, 19, 27, 33, 42, 50, 58, 66, 71, 79, 88, 97];
lit1.forEach((c, i) => tl.to("#s12-w1-c" + c, { fill: "#FFD166", duration: 0.12 }, tC + 2.2 + i * 0.07));
K.count(tl, "#s12-n1", tC + 2.2, 0, 11, 0.8);
lit2.forEach((c, i) => tl.to("#s12-w2-c" + c, { fill: "#2DB86B", duration: 0.12 }, t4 + 0.3 + i * 0.06));
K.count(tl, "#s12-n2", t4 + 0.3, 0, 13, 0.8);
K.pop(tl, "#s12-plus", t4 + 2.0, { duration: 0.5 });
K.pulse(tl, "#s12-plus b", t4 + 2.6, tD, 0.05, 0.8);

// D: same reach
K.cut(tl, "#s12-D", "#s12-C", tD - 0.1);
tl.to(["#s12-g1", "#s12-g2"], { attr: { "stroke-dasharray": "972 1006" }, duration: 1.0, ease: "power2.out", stagger: 0.2 }, tD + 0.2);
tl.fromTo("#s12-D .gz", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.35, ease: "back.out(2)", stagger: 0.2 }, tD + 0.9);

// E: the greedy Bandit
K.cut(tl, "#s12-E", "#s12-D", tE - 0.1);
K.tagOut(tl, "#s12-tag2", tE - 0.15); tl.to("#s12-src2", { opacity: 0, duration: 0.2 }, tE - 0.15);
K.tagIn(tl, "#s12-tag3", tE);
tl.fromTo("#s12-src4", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.3 }, tE + 0.2);
K.idle(tl, G, tE, tF);
K.blinks(tl, G, tE, tF, 2.2);
tl.fromTo("#s12-e1", { x: 500, opacity: 0 }, { x: 0, opacity: 1, duration: 0.45, ease: "back.out(1.5)" }, tE + 0.8);
K.rot(tl, G, "arm-n", 60, tE + 2.0, 0.35, "back.out(2)");
K.rot(tl, G, "fore-n", 70, tE + 2.05, 0.35, "back.out(2)");
K.pop(tl, "#s12-bub", tE + 2.2, { transformOrigin: "85% 115%" });
K.talk(tl, G, tE + 2.25, tE + 3.4);
tl.fromTo("#s12-e2", { x: 500, opacity: 0 }, { x: 0, opacity: 1, duration: 0.45, ease: "back.out(1.5)" }, tE + 4.9);
K.popOut(tl, "#s12-bub", tE + 4.7);

// F: speed
K.cut(tl, "#s12-F", "#s12-E", tF - 0.1);
K.tagOut(tl, "#s12-tag3", tF - 0.15); tl.to("#s12-src4", { opacity: 0, duration: 0.2 }, tF - 0.15);
K.tagIn(tl, "#s12-tag4", tF);
tl.fromTo("#s12-src3", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.3 }, tF + 0.2);
K.pop(tl, "#s12-sw", tF);
tl.fromTo("#s12-sw-sw-hand", { rotation: 0, svgOrigin: "200 235" }, { rotation: 55, svgOrigin: "200 235", duration: 0.25, ease: "back.out(3)" }, tF + 0.3);
K.count(tl, "#s12-ms", tF + 0.3, 0, 6.6, 0.8, (v) => v.toFixed(1) + " ms");
