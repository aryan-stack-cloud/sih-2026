// s01 - cold open: the guard, 16 rooms, a torch flash in room 11, the beam arrives too late.
const G = "s01-g";
// searchlight geometry on screen (searchlight.svg placed at left 470, top 700, width 220)
const SL = { px: 555.5, py: 808.3, r: 81.2, half: 28.8 };
const WIN = (n) => { const r = Math.floor((n - 1) / 4), c = (n - 1) % 4; return { x: 760 + c * 200, y: 220 + r * 170, w: 150, h: 120 }; };
function aim(a, b) { // beam hull from the lens to windows a..b (same row), and the head angle
  const A = WIN(a), B = WIN(b);
  const x0 = A.x, x1 = B.x + B.w, y0 = A.y, y1 = A.y + A.h;
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const th = Math.atan2(cy - SL.py, cx - SL.px);
  const lx = SL.px + SL.r * Math.cos(th), ly = SL.py + SL.r * Math.sin(th);
  const ux = -Math.sin(th) * SL.half, uy = Math.cos(th) * SL.half;
  const p1 = [lx - ux, ly - uy], p2 = [lx + ux, ly + uy];
  const pts = [p1, [x0, y0], [x1, y0], [x1, y1], p2].map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
  return { pts, deg: (th * 180) / Math.PI };
}
const A12 = aim(1, 2), A1112 = aim(11, 12);

const d2 = K.dur("s01_2");
const tFlash = K.end("s01_2") - 1.25;      // "...flash a torch for a split second"
const tSwing = tFlash + 0.5;               // guard reacts late
const tArrive = tSwing + 0.72;
const tClose = K.cue("s01_3");             // cut to close-up

// camera: slow push on the wide, then a hard cut to the guard close-up
K.cam(tl, "#s01-cam", 0, tClose, { s: 1 }, { s: 1.06, x: -30, y: 10 });
tl.set("#s01-cam", { scale: 3.0, x: 1400, y: -422 }, tClose);
K.cam(tl, "#s01-cam", tClose, K.D, { s: 3.0, x: 1400, y: -422 }, { s: 3.12, x: 1452, y: -448 });

// ambience
K.twinkle(tl, ["#s01-sky-sparkle-1", "#s01-sky-sparkle-2", "#s01-sky-sparkle-3", "#s01-sky-sparkle-4", "#s01-sky-sparkle-5", "#s01-sky-sparkle-6", "#s01-sky-sparkle-7", "#s01-sky-sparkle-8"], 0, K.D);
K.pulse(tl, "#s01-bld-lamp-glow-1", 0, K.D, 0.08, 2.2);
K.pulse(tl, "#s01-bld-lamp-glow-2", 0, K.D, 0.08, 2.6);
K.idle(tl, G, 0, K.D);
K.blinks(tl, G, 0, tClose, 2.4);

// searchlight starts on rooms 1-2
tl.set("#s01-sl-sl-head", { rotation: A12.deg, svgOrigin: "202 256" }, 0);
tl.set("#s01-beam", { attr: { points: A12.pts } }, 0);
tl.set(["#s01-bld-win-1-lit", "#s01-bld-win-2-lit"], { opacity: 0.85 }, 0);
K.pulse(tl, "#s01-beam-svg", 0, tSwing, 0.012, 1.6);

// "Remember our night guard?"
K.tagIn(tl, "#s01-tag", K.cue("s01_1") + 0.2);
K.rot(tl, G, "head", -6, K.cue("s01_1") + 0.2, 0.4);
K.rot(tl, G, "head", 0, K.cue("s01_1") + 1.0, 0.4);

// "One searchlight, sixteen rooms, ..."
K.pop(tl, "#s01-lbl-sl", K.cue("s01_2"));
tl.fromTo("#s01-beam", { attr: { "fill-opacity": 0.34 } }, { attr: { "fill-opacity": 0.55 }, duration: 0.25, yoyo: true, repeat: 1, ease: "sine.inOut" }, K.cue("s01_2") + 0.1);
K.popOut(tl, "#s01-lbl-sl", K.cue("s01_2") + 0.3 * d2 + 0.6);
const tRooms = K.cue("s01_2") + 0.24 * d2;
tl.fromTo("#s01-nums .roomnum", { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2.5)", stagger: 0.035 }, tRooms);
K.pop(tl, "#s01-lbl-rooms", tRooms + 0.2);
K.popOut(tl, "#s01-lbl-rooms", tFlash - 0.6);

// the flash in room 11: visible for a split second, then gone
tl.set("#s01-intr-wrap", { opacity: 1 }, tFlash - 0.05);
tl.fromTo("#s01-torchglow", { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, duration: 0.08, ease: "power2.out" }, tFlash);
tl.set("#s01-bld-win-11-lit", { opacity: 0.9 }, tFlash);
tl.set("#s01-i-beam", { opacity: 1 }, tFlash);
tl.to("#s01-torchglow", { opacity: 0, duration: 0.18, ease: "power2.in" }, tFlash + 0.34);
tl.set(["#s01-bld-win-11-lit", "#s01-i-beam"], { opacity: 0 }, tFlash + 0.42);
tl.set("#s01-intr-wrap", { opacity: 0 }, tFlash + 0.48);
tl.to("#s01-nums .roomnum", { opacity: 0, duration: 0.25, ease: "none" }, tFlash + 0.6);

// the guard reacts late and swings the light
K.mouth(tl, G, "o", tFlash + 0.25);
K.brows(tl, G, -8, tFlash + 0.25);
K.rot(tl, G, "arm-f", -38, tSwing - 0.1, 0.35, "back.out(2)");
tl.to("#s01-sl-sl-head", { rotation: A1112.deg, svgOrigin: "202 256", duration: 0.72, ease: "power2.inOut" }, tSwing);
tl.to("#s01-beam", { attr: { points: A1112.pts }, duration: 0.72, ease: "power2.inOut" }, tSwing);
tl.set(["#s01-bld-win-1-lit", "#s01-bld-win-2-lit"], { opacity: 0 }, tSwing + 0.12);
tl.set(["#s01-bld-win-11-lit", "#s01-bld-win-12-lit"], { opacity: 0.85 }, tArrive - 0.05);
K.stamp(tl, "#s01-stamp", tArrive + 0.12, -8);
K.mouth(tl, G, "closed", tArrive + 0.9);
K.rot(tl, G, "arm-f", 0, tArrive + 0.8, 0.4);

// close-up: "By the time his light gets there, they're gone."
tl.set("#s01-stamp", { opacity: 0 }, tClose);
K.brows(tl, G, 0, tClose);
K.blink(tl, G, tClose + 0.5);
K.mouth(tl, G, "o", K.end("s01_3") - 0.4);
K.brows(tl, G, -10, K.end("s01_3") - 0.4);
K.pop(tl, "#s01-bubble", K.end("s01_3") + 0.12, { transformOrigin: "20% 110%" });
K.talk(tl, G, K.end("s01_3") + 0.15, K.end("s01_3") + 1.0);
// both arms up in frustration
K.rot(tl, G, "arm-n", 150, K.end("s01_3") + 0.05, 0.32, "back.out(2)");
K.rot(tl, G, "fore-n", -35, K.end("s01_3") + 0.1, 0.3, "back.out(2)");
K.rot(tl, G, "arm-f", -150, K.end("s01_3") + 0.05, 0.32, "back.out(2)");
K.rot(tl, G, "fore-f", 35, K.end("s01_3") + 0.1, 0.3, "back.out(2)");
tl.fromTo("#" + G + "-body", { rotation: 0 }, { rotation: 2.5, svgOrigin: "204 780", duration: 0.14, yoyo: true, repeat: 3, ease: "sine.inOut" }, K.end("s01_3") + 0.4);
