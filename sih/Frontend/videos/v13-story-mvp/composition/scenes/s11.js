// s11 - training data (simulator + recordings from the 70 GB Alan Turing Institute dataset), an exam on
// 50 unseen recordings, and the training effort from the model registry: 2 days, 34 runs, 1.9 M practice steps.
const G = "s11-g";
const t1 = K.cue("s11_1"), tB = t1 + 6.35, tC = K.cue("s11_2") - 0.05;

// Shot A: the case file
K.cam(tl, "#s11-A", 0, tB, { s: 1.0 }, { s: 1.04, y: 6 });
K.tagIn(tl, "#s11-tag1", 0.2);
tl.fromTo("#s11-file", { y: 420, rotation: 5 }, { y: 0, rotation: 0, duration: 0.55, ease: "back.out(1.4)" }, 0.3);
tl.to("#s11-file-folder-flap", { scaleY: 0.2, svgOrigin: "500 200", duration: 0.4, ease: "power2.in" }, 0.9);
// "our simulator"
tl.fromTo("#s11-p1", { x: 380, y: 60, rotation: 8, opacity: 0 }, { x: 0, y: 0, rotation: -5, opacity: 1, duration: 0.6, ease: "back.out(1.3)" }, t1 + 0.45);
tl.fromTo("#s11-p1 .blip", { opacity: 0.25 }, { opacity: 1, duration: 0.2, stagger: 0.12, yoyo: true, repeat: 7, ease: "none" }, t1 + 1.1);
[300, 120, 380, 60, 240].forEach((x, i) => tl.to("#s11-hop", { x, duration: 0.5, ease: "power2.inOut" }, t1 + 1.1 + i * 0.6));
// "...recordings from the Alan Turing Institute's..."
tl.fromTo("#s11-p2", { x: -380, y: 60, rotation: -8, opacity: 0 }, { x: 0, y: 0, rotation: 5, opacity: 1, duration: 0.6, ease: "back.out(1.3)" }, t1 + 2.1);
tl.fromTo("#s11-dots .pdot", { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.2, stagger: 0.02, ease: "back.out(2)" }, t1 + 2.6);
// pulses get binned into 16 frequency columns = the same 16 bands our receiver scans
document.querySelectorAll("#s11-dots .pdot").forEach((d) => {
  const x = parseFloat(d.style.left);
  const col = Math.min(15, Math.floor(x / (516 / 16)));
  const cx = col * (516 / 16) + (516 / 16 - 16) / 2;
  tl.to(d, { x: cx - x, duration: 0.5, ease: "power2.inOut" }, t1 + 3.7);
});
// "...seventy-gigabyte radar dataset"
tl.fromTo("#s11-gb", { scale: 2.2, opacity: 0, rotation: -6 }, { scale: 1, opacity: 1, rotation: 6, duration: 0.3, ease: "power4.in" }, t1 + 4.45);
K.count(tl, "#s11-gbv", t1 + 4.5, 0, 70, 0.7, (v) => Math.round(v) + " GB");
tl.fromTo("#s11-src1", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35 }, t1 + 4.8);

// Shot B: "...then faced ones they'd never seen" - the exam
K.cut(tl, "#s11-B", "#s11-A", tB);
K.tagOut(tl, "#s11-tag1", tB - 0.1);
tl.to("#s11-src1", { opacity: 0, duration: 0.2 }, tB - 0.1);
K.tagIn(tl, "#s11-tag2", tB + 0.1);
K.cam(tl, "#s11-B", tB, tC, { s: 1.0 }, { s: 1.05, y: 10 });
tl.fromTo("#s11-B .chalk", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.3, stagger: 0.3 }, tB + 0.05);
K.idle(tl, G, tB, tC);
K.mouth(tl, G, "o", tB + 0.5);
K.brows(tl, G, -8, tB + 0.5);
K.rot(tl, G, "head", 6, tB + 0.8, 0.3);
K.rot(tl, G, "head", -6, tB + 1.2, 0.3);

// Shot C: "Two days of training runs in all, yet each final model trains in under an hour."
K.cut(tl, "#s11-C", "#s11-B", tC);
K.tagOut(tl, "#s11-tag2", tC - 0.1);
K.tagIn(tl, "#s11-tag3", tC + 0.1);
tl.fromTo("#s11-src2", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.35 }, tC + 0.3);
K.cam(tl, "#s11-C", tC, K.D, { s: 1.0 }, { s: 1.03, x: -8 });
tl.fromTo("#s11-days", { scale: 0.3, opacity: 0, rotation: -10 }, { scale: 1, opacity: 1, rotation: 0, duration: 0.5, ease: "back.out(2.2)" }, tC + 0.2);
K.pulse(tl, "#s11-days b", tC + 0.75, tC + 2.0, 0.035, 0.6);
K.pop(tl, "#s11-board", tC + 0.1, { duration: 0.5 });
K.pop(tl, "#s11-lap", tC + 0.5);
K.pop(tl, "#s11-sw", tC + 0.7);
tl.fromTo("#s11-sw-sw-hand", { rotation: 0, svgOrigin: "200 235" }, { rotation: 1080, svgOrigin: "200 235", duration: K.D - tC - 0.8, ease: "none" }, tC + 0.8);
// "...thirty-four training runs, and nearly two million practice steps for the neural networks."
tl.set(["#s11-st1", "#s11-st2", "#s11-st3"], { opacity: 0, x: -40 }, 0);
tl.fromTo("#s11-st1", { opacity: 0, x: -40 }, { opacity: 1, x: 0, duration: 0.35, ease: "back.out(1.6)", immediateRender: false }, tC + 1.55);
K.count(tl, "#s11-n1", tC + 1.6, 0, 34, 0.9);
["#s11-c1", "#s11-c2", "#s11-c3", "#s11-c4"].forEach((c, i) => K.pop(tl, c, tC + 2.2 + i * 0.12, { duration: 0.3 }));
tl.fromTo("#s11-st2", { opacity: 0, x: -40 }, { opacity: 1, x: 0, duration: 0.35, ease: "back.out(1.6)", immediateRender: false }, tC + 3.15);
K.count(tl, "#s11-n2", tC + 3.2, 0, 1.9, 1.0, (v) => v.toFixed(1) + " M");
tl.fromTo("#s11-st3", { opacity: 0, x: -40 }, { opacity: 1, x: 0, duration: 0.35, ease: "back.out(1.6)", immediateRender: false }, tC + 4.7);
