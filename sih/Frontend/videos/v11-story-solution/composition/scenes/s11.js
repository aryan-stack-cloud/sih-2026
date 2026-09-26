// s11 - training data (simulator + Alan Turing Institute), unseen-run exam, measured training times.
const G = "s11-g";
const t1 = K.cue("s11_1"), tB = K.cue("s11_2"), tC = K.cue("s11_3"), t4 = K.cue("s11_4");

// Shot A: the case file
K.cam(tl, "#s11-A", 0, tB, { s: 1.0 }, { s: 1.04, y: 6 });
K.tagIn(tl, "#s11-tag1", 0.2);
tl.fromTo("#s11-file", { y: 420, rotation: 5 }, { y: 0, rotation: 0, duration: 0.55, ease: "back.out(1.4)" }, 0.3);
tl.to("#s11-file-folder-flap", { scaleY: 0.2, svgOrigin: "500 200", duration: 0.4, ease: "power2.in" }, 1.2);
tl.fromTo("#s11-p1", { x: 380, y: 60, rotation: 8, opacity: 0 }, { x: 0, y: 0, rotation: -5, opacity: 1, duration: 0.6, ease: "back.out(1.3)" }, t1 + 2.2);
tl.fromTo("#s11-p1 .blip", { opacity: 0.25 }, { opacity: 1, duration: 0.2, stagger: 0.12, yoyo: true, repeat: 7, ease: "none" }, t1 + 2.9);
[300, 120, 380, 60, 240].forEach((x, i) => tl.to("#s11-hop", { x, duration: 0.5, ease: "power2.inOut" }, t1 + 2.9 + i * 0.6));
tl.fromTo("#s11-p2", { x: -380, y: 60, rotation: -8, opacity: 0 }, { x: 0, y: 0, rotation: 5, opacity: 1, duration: 0.6, ease: "back.out(1.3)" }, t1 + 4.3);
tl.fromTo("#s11-dots .pdot", { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.2, stagger: 0.025, ease: "back.out(2)" }, t1 + 4.8);
// pulses get binned into 16 frequency columns = the same 16 bands our receiver scans
document.querySelectorAll("#s11-dots .pdot").forEach((d) => {
  const x = parseFloat(d.style.left);
  const col = Math.min(15, Math.floor(x / (516 / 16)));
  const cx = col * (516 / 16) + (516 / 16 - 16) / 2;
  tl.to(d, { x: cx - x, duration: 0.5, ease: "power2.inOut" }, t1 + 6.1);
});
tl.fromTo("#s11-src1", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35 }, t1 + 4.6);

// Shot B: the exam on runs it has never seen
K.cut(tl, "#s11-B", "#s11-A", tB);
K.tagOut(tl, "#s11-tag1", tB - 0.1);
tl.to("#s11-src1", { opacity: 0, duration: 0.2 }, tB - 0.1);
K.tagIn(tl, "#s11-tag2", tB + 0.1);
K.cam(tl, "#s11-B", tB, tC, { s: 1.0 }, { s: 1.05, y: 10 });
tl.fromTo("#s11-B .chalk", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.35, stagger: 0.35 }, tB + 0.1);
K.idle(tl, G, tB, tC);
K.mouth(tl, G, "o", tB + 0.6);
K.brows(tl, G, -8, tB + 0.6);
K.rot(tl, G, "head", 6, tB + 0.9, 0.3);
K.rot(tl, G, "head", -6, tB + 1.3, 0.3);

// Shot C: the training-time race
K.cut(tl, "#s11-C", "#s11-B", tC);
K.tagOut(tl, "#s11-tag2", tC - 0.1);
K.tagIn(tl, "#s11-tag3", tC + 0.1);
tl.fromTo("#s11-src2", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35 }, tC + 0.3);
K.cam(tl, "#s11-C", tC, K.D, { s: 1.0 }, { s: 1.03, x: -8 });
K.pop(tl, "#s11-board", tC + 0.15, { duration: 0.5 });
K.pop(tl, "#s11-lap", tC + 1.1);
K.pop(tl, "#s11-sw", tC + 1.4);
tl.fromTo("#s11-sw-sw-hand", { rotation: 0, svgOrigin: "200 235" }, { rotation: 1440, svgOrigin: "200 235", duration: K.D - tC - 1.5, ease: "none" }, tC + 1.5);
const fmt = (v) => { let m = Math.floor(v / 60), s = Math.round(v - m * 60); if (s === 60) { m += 1; s = 0; } return m + " min " + String(s).padStart(2, "0") + " s"; };
const race = [["1", 80.6, tC + 3.1, 0.9], ["2", 213.1, t4 + 0.2, 0.9], ["3", 326.8, t4 + 0.6, 1.0], ["4", 446.9, t4 + 1.0, 1.2]];
race.forEach(([i, sec, t, d]) => {
  tl.set("#s11-b" + i, { scaleX: 0, transformOrigin: "0% 50%" }, 0);
  tl.to("#s11-b" + i, { scaleX: sec / 446.9, duration: d, ease: "power1.inOut" }, t);
  K.count(tl, "#s11-v" + i, t, 0, sec, d, fmt);
});
tl.fromTo(["#s11-z1", "#s11-z2"], { opacity: 0, x: -40 }, { opacity: 1, x: 0, duration: 0.35, stagger: 0.25, ease: "back.out(1.8)" }, t4 + 3.2);
