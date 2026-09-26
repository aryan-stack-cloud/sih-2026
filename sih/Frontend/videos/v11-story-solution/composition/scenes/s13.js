// s13 - close: sunrise, the guard with his chai, three lines and the PUSHPAK lockup.
const G = "s13-g";
const t = K.cue("s13_1"), d = K.dur("s13_1");
K.cam(tl, "#s13-cam", 0, K.D, { s: 1.06, y: 10 }, { s: 1.0, y: 0 });
tl.fromTo("#s13-sky-sunrise-sun", { y: 120 }, { y: 0, duration: K.D, ease: "sine.out" }, 0);
["#s13-sky-cloud-1", "#s13-sky-cloud-2", "#s13-sky-cloud-3", "#s13-sky-cloud-4"].forEach((c, i) => tl.fromTo(c, { x: 0 }, { x: (i % 2 ? -1 : 1) * 60, duration: K.D, ease: "none" }, 0));
K.idle(tl, G, 0, K.D);
K.blinks(tl, G, 0, K.D, 2.0);
K.rot(tl, G, "arm-f", -40, 0.2, 0.5, "sine.inOut");
K.rot(tl, G, "fore-f", -95, 0.25, 0.5, "sine.inOut");
tl.fromTo("#s13-tea", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.5 }, 0.3);
tl.fromTo("#s13-tea", { y: 0 }, { y: -30, duration: 0.6, yoyo: true, repeat: 1, ease: "sine.inOut", immediateRender: false }, t + d * 0.3);
K.rot(tl, G, "head", -5, t, 0.5, "sine.inOut");
[["#s13-l1", 0.0], ["#s13-l2", 0.3], ["#s13-l3", 0.64]].forEach(([l, f]) => tl.fromTo(l, { x: 120, opacity: 0, scale: 0.8 }, { x: 0, opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2)" }, t + f * d));
K.pulse(tl, "#s13-l3", t + 0.64 * d + 0.5, K.D, 0.04, 0.9);
tl.fromTo("#s13-logo", { y: 80, opacity: 0 }, { y: 0, opacity: 1, duration: 0.55, ease: "back.out(1.6)" }, t + d + 0.3);
