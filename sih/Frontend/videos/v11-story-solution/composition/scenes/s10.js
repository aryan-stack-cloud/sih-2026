// s10 - #6 PPO: a prize wheel of band pairs; slices that catch signals grow, so good picks come up more.
const R = "s10-rb";
const t2 = K.cue("s10_2");
K.cam(tl, "#s10-cam", 0, K.D, { s: 1.0 }, { s: 1.045, x: 8, y: 4 });
K.numcard(tl, "#s10-num", "#s10-cam", 0.05, 0.8);
tl.fromTo("#s10-name", { x: -700, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: "back.out(1.4)" }, 1.35);
K.pop(tl, "#" + R, 1.0, { duration: 0.45 });
tl.fromTo("#s10-win", { opacity: 0 }, { opacity: 1, duration: 0.25 }, 1.0);
for (let i = 1; i <= 9; i++) tl.fromTo("#" + R + "-node-" + i, { opacity: 0.5 }, { opacity: 1, duration: 0.18, yoyo: true, repeat: Math.max(0, Math.floor((K.D - 1.2) / 0.36) - 1), ease: "none" }, 1.2 + i * 0.04);

// spin 1: equal slices, lands on 11-12 (slice 6): 2 turns + 112.5 degrees
tl.fromTo("#s10-w1", { rotation: 0 }, { rotation: 832.5, duration: 2.2, ease: "power3.out", transformOrigin: "50% 50%" }, 1.2);
tl.fromTo("#s10-top-pointer", { rotation: -14, svgOrigin: "350 16" }, { rotation: 14, svgOrigin: "350 16", duration: 0.07, yoyo: true, repeat: 15, ease: "none" }, 1.25);
tl.to("#s10-top-pointer", { rotation: 0, svgOrigin: "350 16", duration: 0.3, ease: "back.out(3)" }, 2.4);
tl.to("#s10-win", { x: 768, duration: 0.35, ease: "back.out(1.5)" }, 3.35);
tl.fromTo(["#s10-h11", "#s10-h12"], { opacity: 0 }, { opacity: 0.9, duration: 0.15, yoyo: true, repeat: 3 }, 3.5);
tl.fromTo("#s10-w1-slice-6", { opacity: 1 }, { opacity: 0.6, duration: 0.12, yoyo: true, repeat: 3, immediateRender: false }, 3.45);

// "The slices that catch signals keep getting bigger": morph to the weighted wheel
const tGrow = t2 + 0.7;
tl.set("#s10-w2", { rotation: 841.5, transformOrigin: "50% 50%" }, 0);
tl.to("#s10-w2", { opacity: 1, duration: 0.45, ease: "none" }, tGrow);
tl.to("#s10-w1", { opacity: 0, duration: 0.45, ease: "none" }, tGrow);
tl.fromTo("#s10-wheels", { scale: 1 }, { scale: 1.06, duration: 0.25, yoyo: true, repeat: 1, ease: "sine.inOut", immediateRender: false }, tGrow);
tl.fromTo("#s10-grow", { opacity: 0, x: -30 }, { opacity: 1, x: 0, duration: 0.35, ease: "back.out(2)" }, tGrow + 0.2);
tl.to("#s10-grow", { opacity: 0, duration: 0.25 }, tGrow + 1.4);
// spin 2: the big 11-12 slice comes up again
tl.to("#s10-w2", { rotation: 1561.5, duration: 1.5, ease: "power3.out" }, t2 + 1.5);
tl.fromTo("#s10-top-pointer", { rotation: -14, svgOrigin: "350 16" }, { rotation: 14, svgOrigin: "350 16", duration: 0.07, yoyo: true, repeat: 9, ease: "none", immediateRender: false }, t2 + 1.55);
tl.to("#s10-top-pointer", { rotation: 0, svgOrigin: "350 16", duration: 0.3, ease: "back.out(3)" }, t2 + 2.3);
tl.fromTo(["#s10-h11", "#s10-h12"], { opacity: 0 }, { opacity: 0.9, duration: 0.15, yoyo: true, repeat: 3, immediateRender: false }, t2 + 3.0);
