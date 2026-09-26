// s07 - #1 Bandit as fishing spots: every band is a spot; a caught signal is a fish; it keeps a tally
// for every spot, mostly fishes where it has caught the most, and now and then tries a new spot
// (the fish have moved to 13-14, and the exploring cast finds them).
const G = "s07-g";
const t1 = K.cue("s07_1"), t2 = K.cue("s07_2"), t3 = K.cue("s07_3"), t4 = K.cue("s07_4");
const X = (i) => 130 + 80 * (i - 1);          // spot centre x; waterline y = 640
const TIP = { "#s07-line1": [1150, 382], "#s07-line2": [1250, 352] };
const BUCKET = [1455, 905];

K.cam(tl, "#s07-cam", 0, K.D, { s: 1.0 }, { s: 1.045, x: 10, y: -6 });
K.numcard(tl, "#s07-num", "#s07-cam", 0.05, 0.8);

// ambient life: sky sparkles, fireflies, moon and lantern glow, drifting ripples
K.twinkle(tl, [1, 2, 3, 4, 5, 6, 7, 8].map((i) => "#s07-bg-lake-sparkle-" + i), 0, K.D);
K.twinkle(tl, [1, 2, 3, 4, 5, 6].map((i) => "#s07-bg-lake-firefly-" + i), 0.2, K.D);
tl.fromTo("#s07-bg-lake-moon-glow", { opacity: 0.75 }, { opacity: 1, duration: 1.4, yoyo: true, ease: "sine.inOut", repeat: Math.max(0, Math.floor(K.D / 1.4) - 1) }, 0);
tl.fromTo("#s07-bg-lake-lantern-glow", { opacity: 0.7 }, { opacity: 1, duration: 0.35, yoyo: true, ease: "sine.inOut", repeat: Math.max(0, Math.floor(K.D / 0.35) - 1) }, 0);
for (let i = 1; i <= 10; i++) {
  const d = 1.6 + (i % 4) * 0.3;
  tl.fromTo("#s07-bg-lake-ripple-" + i, { x: 0 }, { x: i % 2 ? 26 : -26, duration: d, yoyo: true, ease: "sine.inOut", repeat: Math.max(0, Math.floor(K.D / d) - 1) }, (i % 5) * 0.2);
}
tl.fromTo("#s07-bg-lake-reflection", { scaleX: 1, transformOrigin: "50% 50%" }, { scaleX: 1.08, duration: 1.1, yoyo: true, ease: "sine.inOut", repeat: Math.max(0, Math.floor(K.D / 1.1) - 1) }, 0);

// "Every band is a fishing spot": the 16 spots pop in along the band row and bob
for (let i = 1; i <= 16; i++) {
  const t = 1.0 + (i - 1) * 0.04;
  tl.fromTo("#s07-b" + i, { scale: 0, opacity: 0, transformOrigin: "50% 80%" }, { scale: 1, opacity: 1, duration: 0.35, ease: "back.out(2.4)" }, t);
  const d = 0.8 + (i % 3) * 0.17;
  tl.fromTo("#s07-b" + i, { y: 0 }, { y: -6, duration: d, yoyo: true, ease: "sine.inOut", repeat: Math.max(0, Math.floor((K.D - t - 0.4) / d) - 1), immediateRender: false }, t + 0.4);
}
tl.fromTo("#s07 .bn", { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.25, stagger: 0.03 }, 1.2);
tl.fromTo("#s07-name", { x: -700, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: "back.out(1.4)" }, 1.45);
tl.fromTo("#s07-g-wrap", { x: 420 }, { x: 0, duration: 0.55, ease: "power3.out" }, 1.2);
K.idle(tl, G, 1.2, K.D);
K.blinks(tl, G, 1.2, K.D, 2.3);
tl.fromTo(["#s07-rods", "#s07-bucket"], { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.4, ease: "back.out(1.6)" }, 1.3);
// the fish are hiding under spots 9-10 (shadows swim a little on the spot)
["#s07-sh1", "#s07-sh2", "#s07-sh3"].forEach((f, i) => {
  tl.fromTo(f, { opacity: 0 }, { opacity: 0.32, duration: 0.5 }, 1.6 + i * 0.1);
  tl.fromTo(f, { rotation: -4 }, { rotation: 4, duration: 0.45 + i * 0.1, yoyo: true, ease: "sine.inOut", repeat: Math.max(0, Math.floor((K.D - 1.6) / (0.45 + i * 0.1)) - 1) }, 1.6);
});
["#s07-c1", "#s07-c2", "#s07-c3", "#s07-c4", "#s07-c5"].forEach((c) => tl.set(c, { opacity: 0 }, 0));
tl.set(["#s07-t1", "#s07-t2", "#s07-t3", "#s07-t4", "#s07-t5", "#s07-t6", "#s07-t7", "#s07-t8", "#s07-t9", "#s07-t10", "#s07-t11", "#s07-t12", "#s07-t13", "#s07-t14", "#s07-t15", "#s07-t16",
  "#s07-g9", "#s07-g10", "#s07-plus", "#s07-sp", "#s07-fish", "#s07-dice", "#s07-bub"], { opacity: 0 }, 0);

function callIn(c, t) { tl.fromTo(c, { opacity: 0, y: -30, scale: 0.8 }, { opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "back.out(2)", immediateRender: false }, t); }
function callOut(c, t) { tl.to(c, { opacity: 0, y: -20, duration: 0.2, ease: "power2.in" }, t); }
function cast(line, i, t) {
  tl.to(line, { attr: { x2: X(i), y2: 590 }, duration: 0.45, ease: "power2.out" }, t);
}
function reel(line, t) {
  tl.to(line, { attr: { x2: TIP[line][0], y2: TIP[line][1] }, duration: 0.22, ease: "power2.in" }, t);
}
function plusOne(i, t, v) {
  tl.set("#s07-plus", { x: X(i) - X(9), y: 0 }, t);
  tl.fromTo("#s07-plus", { opacity: 1, y: 10, scale: 0.6 }, { opacity: 0, y: -50, scale: 1.2, duration: 0.8, ease: "power2.out", immediateRender: false }, t);
  tl.set("#s07-t" + i, { textContent: String(v) }, t + 0.05);
  tl.fromTo("#s07-t" + i, { scale: 1, backgroundColor: "#FDFCF8" }, { scale: 1.4, backgroundColor: "#2DB86B", duration: 0.15, yoyo: true, repeat: 1, ease: "sine.out", immediateRender: false }, t + 0.05);
}
function catchAt(i, t) {       // bite, splash, the fish leaps into the bucket (lands at t + 1.25)
  tl.fromTo("#s07-b" + i + "-buoy-body", { y: 0 }, { y: 10, duration: 0.1, yoyo: true, repeat: 3, ease: "sine.inOut", immediateRender: false }, t);
  tl.fromTo("#s07-b" + i + "-buoy-ring", { scale: 1, opacity: 1 }, { scale: 2.4, opacity: 0, duration: 0.6, ease: "power2.out", transformOrigin: "50% 50%", immediateRender: false }, t);
  tl.set("#s07-sp", { x: X(i) - 75, y: 541 }, t + 0.35);
  tl.fromTo("#s07-sp", { opacity: 1, scale: 0.3, transformOrigin: "50% 100%" }, { opacity: 0, scale: 1.1, duration: 0.65, ease: "power2.out", immediateRender: false }, t + 0.35);
  tl.set("#s07-fish", { x: X(i) - 78, y: 600, rotation: -35, scale: 1, opacity: 1 }, t + 0.35);
  tl.to("#s07-fish", { y: 380, duration: 0.38, ease: "power2.out" }, t + 0.35);
  tl.to("#s07-fish", { x: BUCKET[0] - 78, duration: 0.85, ease: "power1.inOut" }, t + 0.42);
  tl.to("#s07-fish", { y: BUCKET[1] - 60, duration: 0.5, ease: "power2.in" }, t + 0.75);
  tl.to("#s07-fish", { rotation: 160, duration: 0.85, ease: "none" }, t + 0.42);
  tl.fromTo("#s07-fish-fish-tail", { rotation: -18, svgOrigin: "70 70" }, { rotation: 18, svgOrigin: "70 70", duration: 0.08, yoyo: true, repeat: 9, ease: "none", immediateRender: false }, t + 0.35);
  tl.to("#s07-fish", { opacity: 0, scale: 0.4, duration: 0.1 }, t + 1.25);
  tl.fromTo("#s07-bucket", { scale: 1, transformOrigin: "50% 100%" }, { scale: 1.08, duration: 0.1, yoyo: true, repeat: 1, ease: "sine.out", immediateRender: false }, t + 1.25);
}
function cheer(t) {
  K.rot(tl, G, "arm-f", -150, t, 0.3, "back.out(2)");
  K.rot(tl, G, "arm-f", 0, t + 0.75, 0.35);
  K.mouth(tl, G, "open", t); K.mouth(tl, G, "closed", t + 0.75);
}

// "Number one: the Bandit. Every band is a fishing spot."
callIn("#s07-c1", t1 + 1.8);
tl.fromTo("#s07 .bn", { scale: 1 }, { scale: 1.3, duration: 0.14, yoyo: true, repeat: 1, stagger: 0.035, ease: "sine.inOut", immediateRender: false }, t1 + 1.9);

// "Each signal it catches is a fish, ..."
callOut("#s07-c1", t2 + 0.2);
cast("#s07-line1", 9, t2 - 0.35);
cast("#s07-line2", 10, t2 - 0.25);
catchAt(9, t2 + 0.35);
callIn("#s07-c2", t2 + 0.55);
cheer(t2 + 1.6);
// "...and it keeps a tally for every spot."
callOut("#s07-c2", t2 + 1.85);
callIn("#s07-c3", t2 + 2.0);
for (let i = 1; i <= 16; i++) tl.fromTo("#s07-t" + i, { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.4)", immediateRender: false }, t2 + 1.95 + (i - 1) * 0.03);
plusOne(9, t2 + 2.4, 6);

// "Mostly, it fishes where it has caught the most."
callOut("#s07-c3", t3 - 0.1);
callIn("#s07-c4", t3 + 0.05);
["#s07-g9", "#s07-g10"].forEach((g) => tl.fromTo(g, { opacity: 0, scale: 1.4 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)", immediateRender: false }, t3 + 0.1));
reel("#s07-line1", t3 + 0.35); reel("#s07-line2", t3 + 0.4);
cast("#s07-line1", 9, t3 + 0.6); cast("#s07-line2", 10, t3 + 0.65);
catchAt(10, t3 + 0.9);
plusOne(10, t3 + 2.2, 6);
cheer(t3 + 2.15);

// "But now and then, it tries a new spot, in case the fish have moved."
callOut("#s07-c4", t4 - 0.1);
tl.to(["#s07-g9", "#s07-g10"], { opacity: 0, duration: 0.25 }, t4 + 0.2);
callIn("#s07-c5", t4 + 0.1);
tl.fromTo("#s07-dice", { opacity: 1, x: 260, y: -220, rotation: 0 }, { opacity: 1, x: 0, y: 0, rotation: 540, duration: 0.7, ease: "power2.out", immediateRender: false }, t4 + 0.05);
tl.fromTo("#s07-dice", { scale: 1 }, { scale: 1.12, duration: 0.1, yoyo: true, repeat: 1, ease: "sine.out", immediateRender: false }, t4 + 0.75);
tl.to("#s07-dice", { opacity: 0, scale: 0.6, duration: 0.25 }, t4 + 2.15);
// the fish swim from spots 9-10 over to 13-14
["#s07-sh1", "#s07-sh2", "#s07-sh3"].forEach((f, i) => tl.to(f, { x: 320, duration: 1.8, ease: "power1.inOut" }, t4 - 0.2 + i * 0.12));
reel("#s07-line2", t4 + 0.85);
cast("#s07-line2", 13, t4 + 1.1);
K.brows(tl, G, -6, t4 + 1.0);
K.rot(tl, G, "head", -8, t4 + 1.0, 0.4, "sine.inOut");
catchAt(13, t4 + 1.7);
K.mouth(tl, G, "o", t4 + 2.05);
plusOne(13, t4 + 3.0, 1);
tl.to("#s07-t13", { backgroundColor: "#FFC43D", duration: 0.2 }, t4 + 3.4);   // the newly found spot turns gold
K.pop(tl, "#s07-bub", t4 + 2.4, { transformOrigin: "18% 115%" });
K.talk(tl, G, t4 + 2.45, t4 + 3.2);
K.rot(tl, G, "head", 0, t4 + 2.4, 0.35);
cheer(t4 + 2.95);
