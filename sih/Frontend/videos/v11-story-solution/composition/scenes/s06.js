// s06 - #2 Index: a to-do list. Busy bands and overdue bands jump to the top; the window follows.
const ROW = (r) => "#s06-r" + r;
const tBusy = K.cue("s06_2") + 0.15, tWait = K.cue("s06_2") + 1.45;
const hi = (sel, t) => tl.to(sel, { backgroundColor: "#E4F6EC", borderColor: "#2DB86B", duration: 0.2 }, t);
const lo = (sel, t) => tl.to(sel, { backgroundColor: "#F4F6FA", borderColor: "#D8DEEA", duration: 0.2 }, t);

K.cam(tl, "#s06-cam", 0, K.D, { s: 1.0 }, { s: 1.045, x: 10, y: 4 });
K.numcard(tl, "#s06-num", "#s06-cam", 0.05, 0.8);
tl.fromTo("#s06-board", { y: 700, rotation: -6 }, { y: 0, rotation: 0, duration: 0.6, ease: "back.out(1.3)" }, 1.1);
tl.fromTo("#s06-name", { x: -700, opacity: 0 }, { x: 0, opacity: 1, duration: 0.5, ease: "back.out(1.4)" }, 1.4);
K.pop(tl, "#s06-clock", 1.5);
tl.fromTo("#s06-clock-clock-hand-min", { rotation: 0, svgOrigin: "200 222" }, { rotation: 720, svgOrigin: "200 222", duration: K.D - 1.5, ease: "none" }, 1.5);
hi(ROW(1), 1.7);
tl.fromTo("#s06-win", { opacity: 0, scale: 1.3 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)" }, 1.7);

// "Bands that look busy": 11-12 shows activity, its busy meter jumps, it climbs to the top
tl.fromTo(["#s06-h11", "#s06-h12"], { opacity: 0 }, { opacity: 0.8, duration: 0.12, yoyo: true, repeat: 3 }, tBusy);
tl.set(["#s06-busy2", "#s06-wait4"], { transformOrigin: "0% 50%" }, 0);
tl.set("#s06-busy2", { scaleX: 0.25 }, 0);
tl.set("#s06-wait4", { scaleX: 0.45 }, 0);
tl.to("#s06-busy2", { scaleX: 0.92, duration: 0.45, ease: "power2.out" }, tBusy + 0.2);
tl.to(ROW(2), { y: -108, duration: 0.45, ease: "back.out(1.5)" }, tBusy + 0.65);
tl.to(ROW(1), { y: 108, duration: 0.45, ease: "back.out(1.5)" }, tBusy + 0.65);
lo(ROW(1), tBusy + 0.65); hi(ROW(2), tBusy + 0.7);
tl.to("#s06-win", { x: 576, duration: 0.4, ease: "back.out(1.4)" }, tBusy + 0.8);

// "or have waited too long": the overdue alarm rings and 1-2 jumps to the top
tl.to("#s06-wait4", { scaleX: 1, duration: 0.5, ease: "power1.in" }, tWait);
tl.fromTo("#s06-clock-clock-bells", { rotation: -9, svgOrigin: "200 112" }, { rotation: 9, svgOrigin: "200 112", duration: 0.06, yoyo: true, repeat: 11, ease: "none" }, tWait + 0.35);
tl.fromTo("#s06-clock", { x: 0 }, { x: 5, duration: 0.05, yoyo: true, repeat: 13, ease: "none", immediateRender: false }, tWait + 0.35);
K.pop(tl, "#s06-bub", tWait + 0.35, { transformOrigin: "20% 115%" });
tl.to(ROW(4), { y: -324, duration: 0.5, ease: "back.out(1.3)" }, tWait + 0.85);
tl.to(ROW(2), { y: 0, duration: 0.45, ease: "back.out(1.5)" }, tWait + 0.85);
tl.to(ROW(1), { y: 216, duration: 0.45, ease: "back.out(1.5)" }, tWait + 0.85);
tl.to(ROW(3), { y: 108, duration: 0.45, ease: "back.out(1.5)" }, tWait + 0.85);
lo(ROW(2), tWait + 0.85); hi(ROW(4), tWait + 0.9);
tl.to("#s06-win", { x: -384, duration: 0.45, ease: "back.out(1.4)" }, tWait + 1.0);
