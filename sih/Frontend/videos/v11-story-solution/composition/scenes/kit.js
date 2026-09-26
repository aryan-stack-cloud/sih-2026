/* Runtime helpers shared by every scene builder. All helpers only ADD tweens to the timeline they
   are given, at explicit positions, so every frame is a pure function of timeline time. */
window.KIT = (function () {
  const PIV = window.CAST_PIVOTS || {};
  const kinds = ["guard", "engineer", "intruder"];

  function kindOf(id) {
    const el = document.getElementById(id);
    if (!el) return "guard";
    for (const k of kinds) if (el.classList.contains("char-" + k)) return k;
    return "guard";
  }
  function piv(id, part) {
    const p = (PIV[kindOf(id)] || {})[part] || [0, 0];
    return p[0] + " " + p[1];
  }

  /* mouth flaps between t0 and t1 (deterministic rhythm) */
  const FLAP = [0.12, 0.09, 0.14, 0.08, 0.11, 0.1, 0.15, 0.09, 0.12, 0.07];
  function talk(tl, id, t0, t1) {
    const open = "#" + id + "-mouth-open", closed = "#" + id + "-mouth-closed";
    let t = t0, i = 0, isOpen = false;
    while (t < t1 - 0.05) {
      isOpen = !isOpen;
      tl.set(open, { opacity: isOpen ? 1 : 0 }, t);
      tl.set(closed, { opacity: isOpen ? 0 : 1 }, t);
      t += FLAP[i++ % FLAP.length] * (isOpen ? 1.15 : 0.9);
    }
    tl.set(open, { opacity: 0 }, t1);
    tl.set(closed, { opacity: 1 }, t1);
  }
  /* switch to a held expression mouth: "o" (surprised) or "open" */
  function mouth(tl, id, state, t) {
    for (const s of ["closed", "open", "o"]) tl.set("#" + id + "-mouth-" + s, { opacity: s === state ? 1 : 0 }, t);
  }
  function blink(tl, id, t) {
    const o = piv(id, "eyes");
    tl.to("#" + id + "-eyes", { scaleY: 0.08, svgOrigin: o, duration: 0.06, ease: "power1.in" }, t);
    tl.to("#" + id + "-eyes", { scaleY: 1, svgOrigin: o, duration: 0.09, ease: "power1.out" }, t + 0.08);
  }
  function blinks(tl, id, t0, t1, every) {
    const step = every || 2.7;
    for (let t = t0 + 0.6; t < t1 - 0.2; t += step) blink(tl, id, t);
  }
  /* rotate a limb/head around its rig pivot */
  function rot(tl, id, part, angle, t, dur, ease) {
    tl.to("#" + id + "-" + part, { rotation: angle, svgOrigin: piv(id, part), duration: dur === undefined ? 0.4 : dur, ease: ease || "power2.out" }, t);
  }
  /* gentle breathing bob for a character between t0 and t1 */
  function idle(tl, id, t0, t1) {
    const cycles = Math.max(1, Math.floor((t1 - t0) / 1.8));
    tl.fromTo("#" + id + "-body", { y: 0 }, { y: -5, duration: 0.9, ease: "sine.inOut", yoyo: true, repeat: cycles * 2 - 1 }, t0);
  }
  /* brow raise (surprise) or frown */
  function brows(tl, id, dy, t, dur) {
    tl.to("#" + id + "-brows", { y: dy, duration: dur || 0.2, ease: "power2.out" }, t);
  }

  /* entrances / exits */
  function pop(tl, sel, t, extra) {
    tl.fromTo(sel, { scale: 0.2, opacity: 0 }, Object.assign({ scale: 1, opacity: 1, duration: 0.42, ease: "back.out(2.2)" }, extra || {}), t);
  }
  function popOut(tl, sel, t) {
    tl.to(sel, { scale: 0.6, opacity: 0, duration: 0.22, ease: "back.in(2)" }, t);
  }
  function slideIn(tl, sel, t, fromX, fromY) {
    tl.fromTo(sel, { x: fromX || 0, y: fromY || 0, opacity: 0 }, { x: 0, y: 0, opacity: 1, duration: 0.55, ease: "power3.out" }, t);
  }
  function tagIn(tl, sel, t) {
    tl.fromTo(sel, { x: -560, opacity: 0 }, { x: 0, opacity: 1, duration: 0.55, ease: "back.out(1.4)" }, t);
  }
  function tagOut(tl, sel, t) {
    tl.to(sel, { x: -560, opacity: 0, duration: 0.35, ease: "power2.in" }, t);
  }
  function fadeIn(tl, sel, t, d) { tl.fromTo(sel, { opacity: 0 }, { opacity: 1, duration: d || 0.3, ease: "none" }, t); }
  function fadeOut(tl, sel, t, d) { tl.to(sel, { opacity: 0, duration: d || 0.3, ease: "none" }, t); }
  /* hard cut between shots inside one scene */
  function cut(tl, show, hide, t) {
    tl.set(show, { opacity: 1 }, t);
    if (hide) tl.set(hide, { opacity: 0 }, t);
  }
  /* stamp slam (MISSED!, 0 CAUGHT...) */
  function stamp(tl, sel, t, rot0) {
    const r = rot0 === undefined ? -8 : rot0;
    tl.fromTo(sel, { scale: 2.4, opacity: 0, rotation: r - 10 }, { scale: 1, opacity: 1, rotation: r, duration: 0.28, ease: "power4.in" }, t);
    tl.fromTo(sel, { x: 0 }, { x: 6, duration: 0.05, yoyo: true, repeat: 3, ease: "none" }, t + 0.28);
  }
  /* big "#N" card over a blurred scene camera */
  function numcard(tl, cardSel, camSel, t, hold) {
    const h = hold || 1.1;
    tl.fromTo(camSel, { filter: "blur(0px)" }, { filter: "blur(10px)", duration: 0.25, ease: "power1.out" }, t);
    tl.fromTo(cardSel, { opacity: 0 }, { opacity: 1, duration: 0.2, ease: "none" }, t);
    tl.fromTo(cardSel + " b", { scale: 0.3, rotation: -12 }, { scale: 1, rotation: 0, duration: 0.5, ease: "back.out(2.4)" }, t);
    tl.to(cardSel + " b", { scale: 1.06, duration: h, ease: "none" }, t + 0.5);
    tl.to(cardSel, { opacity: 0, duration: 0.22, ease: "none" }, t + 0.5 + h);
    tl.to(camSel, { filter: "blur(0px)", duration: 0.3, ease: "power1.out" }, t + 0.5 + h);
  }
  /* full-frame statement card */
  function statement(tl, sel, t, hold) {
    tl.fromTo(sel, { opacity: 0 }, { opacity: 1, duration: 0.18, ease: "none" }, t);
    tl.fromTo(sel + " p", { scale: 0.7, y: 40 }, { scale: 1, y: 0, duration: 0.5, ease: "back.out(1.8)" }, t);
    tl.to(sel + " p", { scale: 1.04, duration: hold || 1.5, ease: "none" }, t + 0.5);
  }
  /* slow camera move on a wrapper */
  function cam(tl, sel, t0, t1, from, to, ease) {
    tl.fromTo(sel, { scale: from.s || 1, x: from.x || 0, y: from.y || 0 },
      { scale: to.s || 1, x: to.x || 0, y: to.y || 0, duration: Math.max(0.1, t1 - t0), ease: ease || "sine.inOut" }, t0);
  }
  /* twinkle a list of selectors (finite repeats) */
  function twinkle(tl, sels, t0, t1) {
    sels.forEach(function (s, i) {
      const period = 0.9 + (i % 4) * 0.23;
      const reps = Math.max(0, Math.floor((t1 - t0) / period) - 1);
      tl.fromTo(s, { opacity: 0.35, scale: 0.8 }, { opacity: 1, scale: 1.15, duration: period / 2, ease: "sine.inOut", yoyo: true, repeat: reps, transformOrigin: "50% 50%" }, t0 + (i % 5) * 0.17);
    });
  }
  /* pulse (breathing scale) */
  function pulse(tl, sel, t0, t1, amt, period) {
    const p = period || 1.2;
    const reps = Math.max(0, Math.floor((t1 - t0) / (p / 2)) - 1);
    tl.fromTo(sel, { scale: 1 }, { scale: 1 + (amt || 0.05), duration: p / 2, ease: "sine.inOut", yoyo: true, repeat: reps }, t0);
  }
  /* number count-up into an element's textContent */
  function count(tl, sel, t, from, to, dur, fmt) {
    const o = { v: from };
    const f = fmt || function (v) { return String(Math.round(v)); };
    tl.fromTo(o, { v: from }, {
      v: to, duration: dur || 1, ease: "power2.out",
      onUpdate: function () { const el = document.querySelector(sel); if (el) el.textContent = f(o.v); }
    }, t);
  }
  return { talk, mouth, blink, blinks, rot, idle, brows, pop, popOut, slideIn, tagIn, tagOut, fadeIn, fadeOut, cut, stamp, numcard, statement, cam, twinkle, pulse, count, piv };
})();
