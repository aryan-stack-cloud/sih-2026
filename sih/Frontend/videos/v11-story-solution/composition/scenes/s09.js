// s09 - #5 DQN: the cheat sheet is swapped for a neural network that scores all 16 bands at once.
const N = "s09-net", R = "s09-rb";
const t2 = K.cue("s09_2");
K.cam(tl, "#s09-cam", 0, K.D, { s: 1.0 }, { s: 1.04, x: 6, y: 6 });
K.numcard(tl, "#s09-num", "#s09-cam", 0.05, 0.8);
tl.fromTo("#s09-name", { x: -700, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: "back.out(1.4)" }, 1.4);
// the old cheat sheet arrives... and gets tossed
tl.fromTo("#s09-nb", { y: 600, rotation: 10 }, { y: 0, rotation: -3, duration: 0.5, ease: "back.out(1.4)" }, 1.1);
tl.to("#s09-nb", { x: -1300, y: -120, rotation: -70, duration: 0.55, ease: "power2.in" }, 2.3);
// the robot brain arrives, the network lights up on the wall screen
K.pop(tl, "#" + R, 2.5, { duration: 0.5 });
tl.fromTo("#" + N, { opacity: 0 }, { opacity: 1, duration: 0.3 }, 2.55);
tl.fromTo(["#" + N + "-ins rect", "#" + N + "-n1 circle", "#" + N + "-n2 circle"], { scale: 0, transformOrigin: "50% 50%" }, { scale: 1, duration: 0.25, ease: "back.out(2)", stagger: 0.012 }, 2.6);
tl.fromTo(["#" + N + "-links1", "#" + N + "-links2", "#" + N + "-links3"], { opacity: 0 }, { opacity: 1, duration: 0.4, stagger: 0.15 }, 2.9);
tl.fromTo(["#s09-lbl-in", "#s09-lbl-out"], { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.3, stagger: 0.2 }, 3.1);
for (let i = 1; i <= 16; i++) tl.set("#" + N + "-out-" + i, { scaleX: 0, transformOrigin: "0% 50%" }, 0);
// signal pulses flowing through the layers
for (let w = 0; w < 4; w++) {
  const tw = 3.0 + w * 0.9;
  tl.fromTo("#" + N + "-n1 circle", { fill: "#3DDCFF" }, { fill: "#FFC43D", duration: 0.12, yoyo: true, repeat: 1, stagger: 0.02, immediateRender: false }, tw);
  tl.fromTo("#" + N + "-n2 circle", { fill: "#3DDCFF" }, { fill: "#FFC43D", duration: 0.12, yoyo: true, repeat: 1, stagger: 0.02, immediateRender: false }, tw + 0.25);
}
for (let i = 1; i <= 9; i++) tl.fromTo("#" + R + "-node-" + i, { opacity: 0.45 }, { opacity: 1, duration: 0.2, yoyo: true, repeat: 9, ease: "none" }, 2.9 + i * 0.05);
tl.fromTo("#" + R + "-antenna", { fill: "#FFC43D" }, { fill: "#3DDCFF", duration: 0.25, yoyo: true, repeat: 9, ease: "none" }, 2.9);
tl.to(["#" + R + "-eye-l", "#" + R + "-eye-r"], { scaleY: 0.1, transformOrigin: "50% 50%", duration: 0.06, yoyo: true, repeat: 1 }, 3.6);
tl.to(["#" + R + "-eye-l", "#" + R + "-eye-r"], { scaleY: 0.1, transformOrigin: "50% 50%", duration: 0.06, yoyo: true, repeat: 1 }, 5.7);
// "It scores all sixteen bands at once"
tl.to("#" + N + "-outs rect[id]", { scaleX: 1, duration: 0.55, ease: "back.out(1.3)" }, t2 + 0.05);
tl.to(["#" + N + "-out-11", "#" + N + "-out-12"], { fill: "#FFC43D", duration: 0.2 }, t2 + 0.8);
tl.fromTo("#s09-pick", { x: 60, opacity: 0 }, { x: 0, opacity: 1, duration: 0.35, ease: "back.out(2)" }, t2 + 0.85);
