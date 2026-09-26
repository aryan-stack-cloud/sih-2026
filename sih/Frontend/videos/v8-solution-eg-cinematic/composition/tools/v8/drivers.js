        const P_SKY = 0.12,
          P_FAR = 0.4,
          P_BLD = 1,
          P_NEAR = 1.45,
          P_FG = 2.3;
        const D2R = Math.PI / 180;
        function lt(p, cam) {
          const zl = 1 + (cam.z - 1) * p;
          return { zl, ox: 960 + (cam.cx - 960) * p, oy: 540 + (cam.cy - 540) * p };
        }
        // 2D camera (with dutch roll) applied to a parallax layer
        function toScreen(p, cam, x, y) {
          const L = lt(p, cam);
          const dx = (x - L.ox) * L.zl,
            dy = (y - L.oy) * L.zl;
          const r = (cam.rot || 0) * D2R,
            c = Math.cos(r),
            s = Math.sin(r);
          return [960 + dx * c - dy * s, 540 + dx * s + dy * c];
        }
        function layerCSS(p, cam) {
          const L = lt(p, cam);
          return `translate(960px,540px) rotate(${(cam.rot || 0).toFixed(3)}deg) scale(${L.zl.toFixed(4)}) translate(${(-L.ox).toFixed(2)}px,${(-L.oy).toFixed(2)}px)`;
        }
        // the facade plane in real perspective — the exact math of #facade3d's
        // `perspective(P) rotateY(a)` about transform-origin (ox, oy); z points at the viewer
        const FAC = { ox: 1300, oy: 520, P: 2200 };
        function proj3(x, y, z, a) {
          const X = x - FAC.ox,
            Y = y - FAC.oy;
          const s = Math.sin(a * D2R),
            c = Math.cos(a * D2R);
          const x1 = X * c + z * s,
            z1 = -X * s + z * c;
          const w = 1 - z1 / FAC.P;
          return [FAC.ox + x1 / w, FAC.oy + Y / w, w];
        }
        const bldScreen = (cam, x, y, z) => {
          const q = proj3(x, y, z || 0, cam.a || 0);
          return toScreen(P_BLD, cam, q[0], q[1]);
        };
        const SPL = proj3(1532, 301, 0, 3); // rooms 03–04 centred in the left half of the split
        const extCam = new Track([
          [0, { cx: 900, cy: -130, z: 1.22, rot: -1.4, a: 26 }],
          [3.4, { cx: 990, cy: 548, z: 1.0, rot: 0, a: 17 }, "power2.inOut"],
          [7.0, { cx: 905, cy: 586, z: 1.12, rot: 0.35, a: 12 }, "power1.inOut"],
          [15.0, { cx: 1190, cy: 470, z: 1.4, rot: -0.5, a: 9 }],
          [18.2, { cx: 1212, cy: 460, z: 1.47, rot: 0, a: 7 }, "power1.inOut"],
          [18.2, { cx: SPL[0] + 480 / 1.9, cy: SPL[1], z: 1.9, rot: 0, a: 3 }],
          [22.4, { cx: SPL[0] + 480 / 1.9 + 12, cy: SPL[1] + 5, z: 1.95, rot: 0, a: 3 }, "none"],
          [22.4, { cx: 1330, cy: 520, z: 1.3, rot: 0.7, a: 10 }],
          [24.8, { cx: 1300, cy: 524, z: 1.26, rot: 0.3, a: 12 }, "power1.inOut"],
          [26.4, { cx: 1000, cy: 560, z: 0.985, rot: -1.7, a: 16 }, "power2.inOut"],
          [30.15, { cx: 1008, cy: 556, z: 1.0, rot: -0.9, a: 14 }, "power1.inOut"],
          [31.0, { cx: 1022, cy: 552, z: 1.02, rot: 0, a: 0 }, "power2.inOut"],
          [32.4, { cx: 1022, cy: 552, z: 1.02, rot: 0, a: 0 }],
        ]);
        function handheld(t, amp) {
          return [amp * (Math.sin(t * 0.83) + 0.45 * Math.sin(t * 2.17 + 1.3)), amp * (0.8 * Math.sin(t * 1.07 + 2.1) + 0.35 * Math.sin(t * 2.71))];
        }
        function camAt(t) {
          const c = Object.assign({}, extCam.at(t));
          // motivated pans: the camera leans toward the guard's light
          let k = 0;
          if (t >= 15 && t < 18.2) k = 0.14;
          else if (t >= 22.4 && t < 30.4) k = lerp(0.2, 0.06, sstep(24.8, 25.8, t)) * (1 - sstep(29.4, 30.3, t));
          if (k > 0) {
            const B = beamAt(t - 0.3);
            if (B) {
              const q = proj3(B.x + B.w / 2, B.y + B.h / 2, 0, c.a);
              c.cx += (q[0] - c.cx) * k;
              c.cy += (q[1] - c.cy) * k * 0.5;
            }
          }
          const amp = (1 - sstep(30.3, 30.9, t)) * (t >= 18.2 && t < 22.4 ? 0.45 : 1);
          const h = handheld(t, 2.6 * amp);
          c.cx += h[0] / c.z;
          c.cy += h[1] / c.z;
          return c;
        }
        const EL = {
          sky: $("#Lsky"),
          far: $("#Lfar"),
          bld: $("#Lbld"),
          near: $("#Lnear"),
          fg: $("#Lfg"),
          fac3d: $("#facade3d"),
          stars: Array.from(document.querySelectorAll("#sky-stars .star")),
          clouds: $("#sky-clouds"),
          rays: $("#sky-rays"),
          spotRect: $("#b-spotrect"),
          spotGlow: $("#b-spotglow"),
          lit: $("#b-lit"),
          cone: $("#eb-cone"),
          coneG: $("#eb-g"),
          clipPoly: $("#eb-clipPoly"),
          haze: $("#eb-hazeRect"),
          hazePat: $("#eb-haze"),
          ngSpot: $("#ng-spot"),
          ngLens: $("#ng-lens"),
          ngLensGlow: $("#ng-lensglow"),
          ngStreak: $("#ng-streak"),
          ngHead: $("#ng-head"),
          ngTorso: $("#ng-torso"),
          ngFore: $("#ng-fore"),
          ngLid: $("#ng-lid"),
          otLamp: $("#ot-lamp"),
          otLens: $("#ot-lens"),
          otGlow: $("#ot-lensglow"),
          otStreak: $("#ot-streak"),
          otGhosts: $("#ot-ghosts"),
          ghosts: Array.from(document.querySelectorAll("#ot-ghosts .ghost")),
          obRim: $("#ob-rim"),
          seenG: $("#eb-seen"),
          seenPath: $("#eb-seenPath"),
          seenTxt: $("#eb-seenTxt"),
          spotTag: $("#spotTag"),
          spotTagRooms: $("#spotTagRooms"),
          emptyTag: $("#emptyTag"),
          routeItems: Array.from(document.querySelectorAll("#route .rt-item")),
          // projected ground, side wall, lamp post
          ground: $("#bb-ground"),
          lines: Array.from(document.querySelectorAll("#bb-lines .bb-line")),
          pool1: $("#bb-pool1"),
          pool2: $("#bb-pool2"),
          poolG: $("#bb-pool"),
          doorPoolG: $("#bb-doorpool"),
          shadow: $("#bb-shadow"),
          side: $("#bb-side"),
          sideG: $("#bb-sidefade"),
          swins: Array.from(document.querySelectorAll("#bb-swins .bb-swin")),
          pipe: $("#bb-pipe"),
          door: $("#bb-door"),
          curb: $("#bb-curb"),
          dlamp: $("#bb-dlamp"),
          dhalo: $("#bb-dhalo"),
          lampCone: $("#bf-lampcone"),
          pole: $("#bf-pole"),
          arm: $("#bf-arm"),
          lhalo: $("#bf-lhalo"),
          lstreak: $("#bf-lstreak"),
          sneak: $("#b-sneak"),
        };
        EL.torch = [];
        EL.tspot = [];
        for (let n = 1; n <= 16; n++) {
          EL.torch[n] = document.getElementById("b-torch-" + n);
          EL.tspot[n] = document.getElementById("b-tspot-" + n);
        }
        const POST = { tx: 126, ty: 642, s: 0.62 }; // guard post placement in the near layer (matches #ng-post)
        const postPt = (x, y) => [POST.tx + x * POST.s, POST.ty + y * POST.s];
        const SPOT_PIVOT = [556, 214]; // spotlight yoke in guard-local space
        const OT_LAMP = [900, 858]; // over-the-shoulder lamp pivot (screen)
        // eyelid: k 0 = open, 1 = closed
        function lidPath(k) {
          return `M162 118 Q172 110.5 183 116.5 L183 116.5 Q172 ${f2(110.5 + k * 13)} 162 118 Z`;
        }
        function blinkAt(t, times) {
          let k = 0;
          for (const b of times) {
            const d = t - b;
            if (d >= 0 && d < 0.16) k = Math.max(k, Math.sin((d / 0.16) * Math.PI));
          }
          return k;
        }
        const quad = (a, b, c, d) => pts([a, b, c, d]);
        const pq = (x, y, z, a) => {
          const q = proj3(x, y, z, a);
          return [q[0], q[1]];
        };

        function drawBldOverlays(cam, t) {
          const a = cam.a || 0;
          // ground plane + parking lines + curb
          setA(EL.ground, "points", quad(pq(-500, 860, -700, a), pq(2700, 860, -700, a), pq(2700, 860, 900, a), pq(-500, 860, 900, a)));
          EL.lines.forEach((ln, i) => {
            const x = 860 + i * 90;
            setA(ln, "points", quad(pq(x - 2.5, 860, 30, a), pq(x + 2.5, 860, 30, a), pq(x + 2.5, 860, 360, a), pq(x - 2.5, 860, 360, a)));
          });
          setA(EL.curb, "points", quad(pq(800, 860, 0, a), pq(1800, 860, 0, a), pq(1800, 860, 16, a), pq(800, 860, 16, a)));
          // light pools on the ground (projected circles) — the lamp post and the fire door
          const pool = (el, grad, cx, cz, R) => {
            const ring = [];
            for (let i = 0; i < 20; i++) {
              const u = (i / 20) * Math.PI * 2;
              ring.push(pq(cx + Math.cos(u) * R, 860, cz + Math.sin(u) * R, a));
            }
            setA(el, "points", pts(ring));
            const xs = ring.map((p) => p[0]),
              ys = ring.map((p) => p[1]);
            const mx = (Math.min(...xs) + Math.max(...xs)) / 2,
              my = (Math.min(...ys) + Math.max(...ys)) / 2;
            const rx = (Math.max(...xs) - Math.min(...xs)) / 2,
              ry = Math.max(4, (Math.max(...ys) - Math.min(...ys)) / 2);
            setA(grad, "gradientTransform", `translate(${f1(mx)} ${f1(my)}) scale(${f2(rx / 10)} ${f2(ry / 10)})`);
          };
          pool(EL.pool1, EL.poolG, 700, 250, 200);
          pool(EL.pool2, EL.doorPoolG, 770, -96, 120);
          // the building's own shadow falls right and forward, away from the moon
          setA(EL.shadow, "points", quad(pq(1780, 860, 0, a), pq(1780, 860, -520, a), pq(2160, 860, -380, a), pq(2160, 860, 140, a)));
          // side wall (visible when the camera orbits left of the facade)
          const sw = [pq(820, 172, 0, a), pq(820, 860, 0, a), pq(820, 860, -520, a), pq(820, 172, -520, a)];
          setA(EL.side, "points", pts(sw));
          setA(EL.sideG, "x1", f1(sw[3][0]));
          setA(EL.sideG, "y1", f1(sw[3][1]));
          setA(EL.sideG, "x2", f1(sw[0][0]));
          setA(EL.sideG, "y2", f1(sw[0][1]));
          const wz = [
            [-430, -370, 300, 360],
            [-300, -240, 300, 360],
            [-430, -370, 450, 510],
            [-300, -240, 450, 510],
          ];
          EL.swins.forEach((el, i) => {
            const w = wz[i];
            setA(el, "points", quad(pq(820, w[2], w[0], a), pq(820, w[2], w[1], a), pq(820, w[3], w[1], a), pq(820, w[3], w[0], a)));
          });
          setA(EL.pipe, "points", quad(pq(820, 236, -16, a), pq(820, 236, -24, a), pq(820, 860, -24, a), pq(820, 860, -16, a)));
          setA(EL.door, "points", quad(pq(820, 768, -70, a), pq(820, 768, -124, a), pq(820, 860, -124, a), pq(820, 860, -70, a)));
          const dl = proj3(820, 752, -97, a);
          setA(EL.dlamp, "cx", f1(dl[0]));
          setA(EL.dlamp, "cy", f1(dl[1]));
          setA(EL.dhalo, "cx", f1(dl[0]));
          setA(EL.dhalo, "cy", f1(dl[1]));
          setA(EL.dhalo, "r", f1(46 / dl[2]));
          // lamp post in the courtyard (a billboard standing at z = 240)
          const base = proj3(700, 860, 240, a),
            top = proj3(700, 556, 240, a),
            head = proj3(752, 562, 240, a);
          const pw = 4.5 / base[2];
          setA(EL.pole, "points", quad([base[0] - pw, base[1]], [base[0] + pw, base[1]], [top[0] + pw, top[1]], [top[0] - pw, top[1]]));
          setA(EL.arm, "d", `M${f1(top[0])} ${f1(top[1] + 6)} Q${f1((top[0] + head[0]) / 2)} ${f1(top[1] - 14)} ${f1(head[0])} ${f1(head[1])}`);
          setA(EL.lhalo, "cx", f1(head[0]));
          setA(EL.lhalo, "cy", f1(head[1]));
          setA(EL.lhalo, "r", f1(120 / head[2]));
          setA(EL.lstreak, "cx", f1(head[0]));
          setA(EL.lstreak, "cy", f1(head[1]));
          const pl = proj3(620, 860, 250, a),
            pr = proj3(880, 860, 250, a);
          setA(EL.lampCone, "points", pts([[head[0] - 10, head[1]], [head[0] + 10, head[1]], [pr[0], pr[1]], [pl[0], pl[1]]]));
          // foreshadow: a small figure slips across the courtyard to the fire door
          if (t > 5.2 && t < 7.0) {
            const u = clamp((t - 5.3) / 1.55, 0, 1);
            const wx = lerp(560, 796, u),
              wz = lerp(300, -82, u);
            const q = proj3(wx, 860, wz, a);
            const P = baseThief();
            P.s = 0.125 / q[2];
            P.x = q[0];
            P.y = q[1];
            walkPose(P, u * Math.PI * 5.5, 24, 1);
            P.lean = 16;
            thiefApply("bt", P);
            EL.sneak.setAttribute("opacity", f2(sstep(5.3, 5.6, t) * (1 - sstep(6.7, 6.95, t))));
          } else EL.sneak.setAttribute("opacity", 0);
        }

        let lastTag = "",
          lastRoute = -1;
        function renderExt(t) {
          const cam = camAt(t);
          EL.sky.style.transform = layerCSS(P_SKY, cam);
          EL.far.style.transform = layerCSS(P_FAR, cam);
          EL.bld.style.transform = layerCSS(P_BLD, cam);
          EL.near.style.transform = layerCSS(P_NEAR, cam);
          EL.fg.style.transform = layerCSS(P_FG, cam);
          EL.fac3d.style.transform = `perspective(${FAC.P}px) rotateY(${(cam.a || 0).toFixed(3)}deg)`;
          // ambient: stars twinkle, clouds drift, the moon's rays breathe
          for (let i = 0; i < EL.stars.length; i += 7) EL.stars[i].setAttribute("opacity", f2(0.35 + 0.35 * Math.sin(t * 1.7 + i)));
          EL.clouds.setAttribute("transform", `translate(${f1(t * 7)} 0)`);
          EL.rays.setAttribute("transform", `rotate(${f2(Math.sin(t * 0.35) * 1.4)} 700 150)`);
          EL.rays.setAttribute("opacity", f2(0.75 + 0.25 * Math.sin(t * 0.9)));
          drawBldOverlays(cam, t);

          // the guard's light
          const B = beamAt(t);
          const inOTS = t >= 15.0 && t < 18.2;
          const inSplit = t >= 18.2 && t < 22.4;
          if (B) {
            setA(EL.spotRect, "x", f1(B.x));
            setA(EL.spotRect, "y", f1(B.y));
            setA(EL.spotRect, "width", f1(B.w));
            setA(EL.spotRect, "height", f1(B.h));
            setA(EL.spotGlow, "x", f1(B.x - 60));
            setA(EL.spotGlow, "y", f1(B.y - 50));
            setA(EL.spotGlow, "width", f1(B.w + 120));
            setA(EL.spotGlow, "height", f1(B.h + 100));
            setA(EL.lit, "opacity", f2(B.level));
            setA(EL.spotGlow, "opacity", f2(B.level));
          } else {
            setA(EL.lit, "opacity", 0);
            setA(EL.spotGlow, "opacity", 0);
          }
          const cx = B ? B.x + B.w / 2 : 1300,
            cy = B ? B.y + B.h / 2 : 400;
          const pivotW = postPt(SPOT_PIVOT[0], SPOT_PIVOT[1]);
          const pivotS = toScreen(P_NEAR, cam, pivotW[0], pivotW[1]);
          const tgtS = bldScreen(cam, cx, cy, 0);
          // the lamp lives in the (rotated) near layer: aim in layer space
          const aimScreen = (Math.atan2(tgtS[1] - pivotS[1], tgtS[0] - pivotS[0]) * 180) / Math.PI;
          const aimDeg = aimScreen - (cam.rot || 0);
          setA(EL.ngSpot, "transform", `translate(${SPOT_PIVOT[0]} ${SPOT_PIVOT[1] - 18}) rotate(${f1(aimDeg)})`);
          const lensL = M.ap(M.chain(M.t(SPOT_PIVOT[0], SPOT_PIVOT[1] - 18), M.r(aimDeg)), 56, 0);
          const lensW = postPt(lensL[0], lensL[1]);
          let lens = toScreen(P_NEAR, cam, lensW[0], lensW[1]);
          const lvl = B ? B.level : 0;
          if (inOTS) {
            const a2 = (Math.atan2(tgtS[1] - OT_LAMP[1], tgtS[0] - OT_LAMP[0]) * 180) / Math.PI;
            setA(EL.otLamp, "transform", `translate(${OT_LAMP[0]} ${OT_LAMP[1]}) rotate(${f1(a2)})`);
            const l2 = M.ap(M.chain(M.t(OT_LAMP[0], OT_LAMP[1]), M.r(a2)), 108, 0);
            lens = l2;
            setA(EL.otGlow, "cx", f1(l2[0]));
            setA(EL.otGlow, "cy", f1(l2[1]));
            setA(EL.otGlow, "opacity", f2(lvl));
            setA(EL.otStreak, "cx", f1(l2[0]));
            setA(EL.otStreak, "cy", f1(l2[1]));
            setA(EL.otStreak, "opacity", f2(lvl * 0.85));
            setA(EL.otLens, "fill", lvl > 0.3 ? "#f4f8ff" : "#121a2a");
            setA(EL.obRim, "opacity", f2(0.25 + 0.65 * lvl));
            // lens ghosts sit on the line from the light through the frame centre
            EL.ghosts.forEach((g, i) => {
              const k = [0.55, 1.25, 1.7][i];
              setA(g, "cx", f1(l2[0] + (960 - l2[0]) * k));
              setA(g, "cy", f1(l2[1] + (540 - l2[1]) * k));
            });
            setA(EL.otGhosts, "opacity", f2(lvl * 0.9));
          }
          setA(EL.ngLens, "fill", lvl > 0.3 ? "#f4f8ff" : "#121a2a");
          setA(EL.ngLensGlow, "cx", f1(lensW[0]));
          setA(EL.ngLensGlow, "cy", f1(lensW[1]));
          setA(EL.ngLensGlow, "opacity", f2(lvl * 0.9));
          setA(EL.ngStreak, "cx", f1(lensW[0]));
          setA(EL.ngStreak, "cy", f1(lensW[1]));
          setA(EL.ngStreak, "opacity", f2(lvl * 0.7));
          // volumetric cone in screen space, from the lens to the lit patch, with drifting haze
          if (B && lvl > 0.01 && !inSplit) {
            const c = [bldScreen(cam, B.x + 18, B.y + 16, 0), bldScreen(cam, B.x + B.w - 18, B.y + 16, 0), bldScreen(cam, B.x + B.w - 18, B.y + B.h - 16, 0), bldScreen(cam, B.x + 18, B.y + B.h - 16, 0)];
            const ang = c.map((q) => Math.atan2(q[1] - lens[1], q[0] - lens[0]));
            let iMin = 0,
              iMax = 0;
            for (let i = 1; i < 4; i++) {
              if (ang[i] < ang[iMin]) iMin = i;
              if (ang[i] > ang[iMax]) iMax = i;
            }
            const mid = [(c[0][0] + c[2][0]) / 2, (c[0][1] + c[2][1]) / 2];
            const dx = mid[0] - lens[0],
              dy = mid[1] - lens[1],
              dl = Math.hypot(dx, dy) || 1;
            const nx = -dy / dl,
              ny = dx / dl,
              wS = 10 * lt(P_NEAR, cam).zl * (inOTS ? 2.2 : 1);
            const poly = pts([[lens[0] + nx * wS, lens[1] + ny * wS], c[iMax], mid, c[iMin], [lens[0] - nx * wS, lens[1] - ny * wS]]);
            setA(EL.cone, "points", poly);
            setA(EL.clipPoly, "points", poly);
            setA(EL.coneG, "x1", f1(lens[0]));
            setA(EL.coneG, "y1", f1(lens[1]));
            setA(EL.coneG, "x2", f1(mid[0]));
            setA(EL.coneG, "y2", f1(mid[1]));
            setA(EL.cone, "opacity", f2(0.88 * lvl));
            setA(EL.haze, "opacity", f2(0.32 * lvl));
            setA(EL.hazePat, "patternTransform", `translate(${f1(t * 22)} ${f1(-t * 9)})`);
          } else {
            setA(EL.cone, "opacity", 0);
            setA(EL.haze, "opacity", 0);
          }

          // torches seen from outside (warm windows)
          for (let n = 1; n <= 16; n++) {
            const aL = activeLevel(n, t);
            const R = roomRect(n);
            setA(EL.torch[n], "opacity", f2(aL));
            if (aL > 0) {
              const sw = Math.sin(t * 5.3 + n * 1.7) * 0.32 + Math.sin(t * 2.1 + n) * 0.12;
              setA(EL.tspot[n], "cx", f1(R.x + R.w * (0.5 + sw)));
              setA(EL.tspot[n], "cy", f1(R.y + R.h * (0.56 + 0.1 * Math.sin(t * 3.7 + n))));
            }
          }
          // SEEN — a torch inside the light (the two honest hits in the room log)
          let seenRoom = 0;
          if (B && !B.moving) for (const r of pairRooms(B.pair)) if (activeLevel(r, t) > 0.5 && t > S4_T0) seenRoom = r;
          if (seenRoom) {
            const R = roomRect(seenRoom);
            const a0 = bldScreen(cam, R.x - 14, R.y - 14, 0),
              b0 = bldScreen(cam, R.x + R.w + 14, R.y + R.h + 14, 0);
            const L = 22;
            setA(EL.seenPath, "d", `M${f1(a0[0])} ${f1(a0[1] + L)} V${f1(a0[1])} H${f1(a0[0] + L)} M${f1(b0[0] - L)} ${f1(a0[1])} H${f1(b0[0])} V${f1(a0[1] + L)} M${f1(b0[0])} ${f1(b0[1] - L)} V${f1(b0[1])} H${f1(b0[0] - L)} M${f1(a0[0] + L)} ${f1(b0[1])} H${f1(a0[0])} V${f1(b0[1] - L)}`);
            setA(EL.seenTxt, "x", f1(a0[0]));
            setA(EL.seenTxt, "y", f1(a0[1] - 12));
            setA(EL.seenG, "opacity", 1);
            setA(EL.seenTxt, "opacity", 1);
          } else {
            setA(EL.seenG, "opacity", 0);
            setA(EL.seenTxt, "opacity", 0);
          }

          // the wide-shot guard: breathing, blinking, head follows his light
          const br = Math.sin(t * 1.6) * 0.012;
          setA(EL.ngTorso, "transform", `translate(0 ${f2(-br * 300)})`);
          let head = -6 + Math.sin(t * 0.55) * 5;
          if (B) head = clamp(aimDeg * 0.35 + 6, -16, 8);
          setA(EL.ngHead, "transform", `rotate(${f1(head)} 142 176)`);
          const write = t < 15 ? Math.sin(t * 7.3) * 2.2 : 0;
          setA(EL.ngFore, "transform", `rotate(${f1(write)} 178 300)`);
          setA(EL.ngLid, "d", lidPath(blinkAt(t, [1.7, 4.4, 6.2, 24.1, 27.3, 29.6])));

          // story tags (screen space)
          const showTag = B && ((t >= 15.7 && t < 18.2) || (t >= 22.4 && t < 24.8));
          if (showTag) {
            const q = bldScreen(cam, B.x + 16, B.y - 6, 0);
            EL.spotTag.style.transform = `translate(${f1(q[0])}px, ${f1(q[1] - 40)}px)`;
            const lbl = pairLabel(B.pair);
            if (lbl !== lastTag) {
              EL.spotTagRooms.textContent = lbl;
              lastTag = lbl;
            }
            EL.spotTag.style.opacity = f2(B.moving ? 0 : 1);
          } else EL.spotTag.style.opacity = 0;
          const R10 = roomRect(10);
          const q10 = bldScreen(cam, R10.x + 44, R10.y + R10.h + 16, 0);
          EL.emptyTag.style.transform = `translate(${f1(q10[0])}px, ${f1(q10[1])}px)`;
          EL.emptyTag.style.opacity = f2(sstep(23.72, 23.9, t) * (1 - sstep(24.55, 24.75, t)));
          const rk = B ? B.pair : -1;
          if (rk !== lastRoute) {
            EL.routeItems.forEach((el, k) => el.classList.toggle("rt-on", k === rk));
            lastRoute = rk;
          }
        }

        // ---------- 2a · side door: tracking shot ----------
        const DT = { stage: $("#doorStage"), world: $("#dr-world"), fg: $("#dr-fg"), leaf: $("#dr-leaf"), shadow: $("#dr-shadow"), refl: $("#dr-refl"), wrap: $("#dr-thiefWrap") };
        function renderDoor(t) {
          const lt0 = t - 7.0; // 0..2.8
          const P = baseThief();
          P.s = 0.86;
          P.dir = 1;
          P.y = 868;
          const walkEnd = 1.55;
          const xs = -160,
            xe = 1068;
          if (lt0 < walkEnd) {
            const u = E.o2(lt0 / walkEnd);
            P.x = lerp(xs, xe, u);
            walkPose(P, ((P.x - xs) / 150) * Math.PI, 26 * (1 - sstep(0.8, 1, lt0 / walkEnd) * 0.7), 1);
            P.lean = 16;
          } else {
            P.x = xe;
            walkPose(P, 0, 0, 1);
            P.lean = 14;
          }
          P.head = -8 - 34 * sstep(1.55, 1.8, lt0) * (1 - sstep(2.05, 2.25, lt0));
          if (lt0 > 2.15) {
            const u = E.io2(clamp((lt0 - 2.15) / 0.6, 0, 1));
            P.x = lerp(xe, 1300, u);
            walkPose(P, u * Math.PI * 2, 18, 1);
          }
          thiefApply("dt", P);
          DT.wrap.setAttribute("opacity", f2(1 - sstep(2.42, 2.72, lt0)));
          // the camera tracks him (he holds ~40% of frame), a foreground pipe sweeps past
          const camX = clamp(P.x - 700, -200, 470) + Math.sin(t * 1.3) * 3;
          DT.world.setAttribute("transform", `translate(${f1(-camX)} ${f1(Math.sin(t * 1.9) * 2)})`);
          DT.fg.setAttribute("transform", `translate(${f1(-camX * 1.6 - 420)} 0)`);
          DT.stage.style.transform = `scale(${f2(1.03 + lt0 * 0.018)})`;
          // his shadow on the wall grows as he walks into the lamp's light
          const nearLamp = Math.exp(-Math.pow((P.x - 1296) / 560, 2));
          DT.shadow.setAttribute("transform", "translate(1296 450) scale(1.32) translate(-1296 -450)");
          DT.shadow.setAttribute("opacity", f2(0.55 * nearLamp * (1 - sstep(2.42, 2.72, lt0))));
          DT.refl.setAttribute("transform", "translate(0 1736) scale(1 -1)");
          DT.refl.setAttribute("opacity", f2(0.22 * (1 - sstep(2.42, 2.72, lt0))));
          const open = sstep(1.95, 2.3, lt0);
          DT.leaf.setAttribute("transform", `translate(1416 0) scale(${f2(1 - 0.82 * open)} 1) translate(-1416 0)`);
        }

        // ---------- 2b + 3b · room 10 ----------
        const RM = {
          stage: $("#roomStage"),
          inner: $("#roomInner"),
          lit: $("#rm-lit"),
          mspot: $("#rm-mspot"),
          mcone: $("#rm-mcone"),
          cone: $("#rm-cone"),
          coneG: $("#rm-coneg"),
          mcg: $("#rm-mcg"),
          hot: $("#rm-hot"),
          amb: $("#rm-amb"),
          lensGlow: $("#rm-lensglow"),
          flare: $("#rm-flareline"),
          spill: $("#rm-spill"),
          spillSpot: $("#rm-spillSpot"),
          motes: Array.from(document.querySelectorAll("#rm-motes .mote")),
          cmotes: Array.from(document.querySelectorAll("#rm-cmotes .cmote")),
          glints: Array.from(document.querySelectorAll("#rm-glints .glint")),
          outbeam: $("#rm-outbeam"),
          shadows: [
            [$("#rm-sh-mon"), 548, 526],
            [$("#rm-sh-chair"), 648, 614],
            [$("#rm-sh-frame"), 1427, 602],
          ],
        };
        const roomTarget = new Track([
          [9.8, { x: 240, y: 470 }],
          [11.3, { x: 250, y: 470 }],
          [12.05, { x: 560, y: 540 }, "power2.inOut"],
          [12.8, { x: 880, y: 300 }, "power2.inOut"],
          [18.2, { x: 1330, y: 646 }],
          [19.3, { x: 1432, y: 604 }, "sine.inOut"],
          [20.4, { x: 1300, y: 668 }, "sine.inOut"],
          [21.4, { x: 1470, y: 640 }, "sine.inOut"],
          [22.4, { x: 1380, y: 656 }, "sine.inOut"],
        ]);
        function renderRoom(t) {
          const split = t >= 18.2;
          const P = baseThief();
          P.s = 1.02;
          P.y = 1020;
          P.dir = -1;
          let torchOn = 0;
          if (!split) {
            const lt0 = t - 9.8;
            const walkEnd = 1.0;
            if (lt0 < walkEnd) {
              P.x = lerp(1640, 1180, E.o2(lt0 / walkEnd));
              walkPose(P, ((1640 - P.x) / 150) * Math.PI, 22 * (1 - sstep(0.7, 1, lt0 / walkEnd)), 0.6);
              P.lean = 10;
            } else {
              P.x = 1180;
              walkPose(P, 0, 0, 0.5);
              P.lean = 8;
            }
            torchOn = t >= 11.08 ? 1 : 0;
            if (t >= 11.08 && t < 11.3) torchOn = [0.4, 1, 0.6, 1][Math.floor((t - 11.08) / 0.055)] || 1;
          } else {
            P.x = 1120;
            P.y = 1030;
            P.dir = 1;
            walkPose(P, 0, 0, 1.25);
            P.lean = 22;
            torchOn = t < 22.25 ? 1 : 0;
          }
          // camera: pans with him as he enters, then a slow push toward what the light finds
          const hh = handheld(t, 2.2);
          let push, shiftX, shiftY;
          if (split) {
            push = 1.12 + (t - 18.2) * 0.012;
            shiftX = 170 + hh[0];
            shiftY = hh[1];
          } else {
            const follow = -(P.x - 1180) * 0.35;
            push = 1.0 + (t - 9.8) * 0.02 + 0.05 * sstep(11.2, 12.8, t);
            shiftX = follow + 60 * sstep(11.2, 12.8, t) + hh[0];
            shiftY = -20 * sstep(11.2, 12.8, t) + hh[1];
          }
          RM.stage.style.transform = `translate(${f1(shiftX)}px, ${f1(shiftY)}px) scale(${f2(push)})`;
          const tg = roomTarget.at(t);
          P.head = split ? 18 : -6 + 10 * sstep(10.9, 11.2, t);
          if (t >= 10.85 || split) aimArm(P, tg.x, tg.y, -6);
          P.faceLit = torchOn * 0.6;
          thiefApply("rt", P);
          const Mf = thiefArmMatrix(P, true);
          const lens = M.ap(Mf, 0, 156);
          const tip = M.ap(Mf, 0, 400);
          const dir = [tip[0] - lens[0], tip[1] - lens[1]];
          const dl = Math.hypot(dir[0], dir[1]) || 1;
          const ux = dir[0] / dl,
            uy = dir[1] / dl;
          const dist = Math.hypot(tg.x - lens[0], tg.y - lens[1]);
          const land = [lens[0] + ux * dist, lens[1] + uy * dist];
          const spread = 0.24 * dist + 40;
          const nx = -uy,
            ny = ux;
          const p1 = [land[0] + nx * spread, land[1] + ny * spread],
            p2 = [land[0] - nx * spread, land[1] - ny * spread];
          const lensW = 9;
          const cone = [[lens[0] + nx * lensW, lens[1] + ny * lensW], p1, p2, [lens[0] - nx * lensW, lens[1] - ny * lensW]];
          setA(RM.cone, "points", pts(cone));
          setA(RM.mcone, "points", pts(cone));
          for (const g of [RM.coneG, RM.mcg]) {
            setA(g, "x1", f1(lens[0]));
            setA(g, "y1", f1(lens[1]));
            setA(g, "x2", f1(land[0]));
            setA(g, "y2", f1(land[1]));
          }
          const flick = 0.94 + 0.06 * Math.sin(t * 23) * Math.sin(t * 7.7);
          setA(RM.cone, "opacity", f2(torchOn * 0.95 * flick));
          setA(RM.mspot, "cx", f1(land[0]));
          setA(RM.mspot, "cy", f1(land[1]));
          setA(RM.mspot, "rx", f1(spread * 1.35));
          setA(RM.mspot, "ry", f1(spread * 1.1));
          setA(RM.lit, "opacity", f2(torchOn));
          setA(RM.hot, "cx", f1(land[0]));
          setA(RM.hot, "cy", f1(land[1]));
          setA(RM.hot, "rx", f1(spread * 0.9));
          setA(RM.hot, "ry", f1(spread * 0.75));
          setA(RM.hot, "opacity", f2(torchOn * 0.8 * flick));
          setA(RM.amb, "opacity", f2(torchOn * flick));
          setA(RM.lensGlow, "cx", f1(lens[0]));
          setA(RM.lensGlow, "cy", f1(lens[1]));
          setA(RM.lensGlow, "opacity", f2(torchOn));
          setA(RM.flare, "cx", f1(lens[0]));
          setA(RM.flare, "cy", f1(lens[1]));
          setA(RM.flare, "opacity", f2(torchOn * 0.75));
          // the torch lights the intruder himself (warm, strongest near his hands and face)
          setA(RM.spillSpot, "cx", f1(lens[0]));
          setA(RM.spillSpot, "cy", f1(lens[1]));
          setA(RM.spill, "opacity", f2(torchOn * 0.55));
          // objects in the beam throw shadows that swing opposite the light
          RM.shadows.forEach(([el, ox, oy]) => {
            const dx = (ox - lens[0]) * 0.2,
              dy = (oy - lens[1]) * 0.2;
            el.setAttribute("transform", `translate(${f1(dx)} ${f1(dy)})`);
          });
          // dust in the beam
          RM.motes.forEach((m, i) => {
            const u = 0.12 + ((hash(i * 3 + 1) + t * 0.035 * (0.5 + hash(i))) % 0.88);
            const v = (hash(i * 7 + 2) * 2 - 1) * 0.85 + Math.sin(t * 0.8 + i) * 0.08;
            const px = lens[0] + (land[0] - lens[0]) * u + nx * v * spread * u;
            const py = lens[1] + (land[1] - lens[1]) * u + ny * v * spread * u + Math.sin(t * 0.6 + i * 2) * 4;
            m.setAttribute("cx", f1(px));
            m.setAttribute("cy", f1(py));
            m.setAttribute("opacity", f2(torchOn * (0.25 + 0.55 * hash(i * 11)) * (1 - u * 0.5)));
          });
          // cool dust hanging in the moonlight shafts
          RM.cmotes.forEach((m, i) => {
            const u = (hash(i * 5 + 3) + t * 0.02) % 1;
            const px = 620 + hash(i * 13) * 600 - u * 160 + Math.sin(t * 0.5 + i) * 6;
            const py = 400 + u * 480;
            m.setAttribute("cx", f1(px));
            m.setAttribute("cy", f1(py));
            m.setAttribute("opacity", f2((0.2 + 0.35 * hash(i * 17)) * Math.sin(u * Math.PI)));
          });
          RM.glints.forEach((g) => {
            const gx = +g.dataset.x,
              gy = +g.dataset.y;
            const d = Math.hypot(gx - land[0], gy - land[1]);
            const k = torchOn * Math.pow(clamp(1 - d / (spread * 1.4), 0, 1), 1.5);
            g.setAttribute("opacity", f2(k));
            g.setAttribute("transform", `translate(${gx} ${gy}) scale(${f2(0.4 + k * 0.5)}) rotate(${f1(t * 40)})`);
          });
          setA(RM.outbeam, "opacity", f2(split ? 0.18 : 0));
        }

        // ---------- 2b insert · the switch ----------
        const IN = { stage: $("#insertStage"), thumb: $("#in-thumb"), light: $("#in-light"), lens: $("#in-lens") };
        function renderInsert(t) {
          const lt0 = t - 10.84;
          IN.stage.style.transform = `translate(${f1(-lt0 * 60)}px, 0px) scale(${f2(1.02 + lt0 * 0.16)})`;
          const press = sstep(10.96, 11.03, t) * (1 - sstep(11.1, 11.16, t));
          setA(IN.thumb, "transform", `translate(0 ${f1(press * 12)})`);
          const on = t >= 11.06 ? [0.45, 1, 0.7, 1][Math.min(3, Math.floor((t - 11.06) / 0.03))] : 0;
          setA(IN.light, "opacity", f2(on));
          setA(IN.lens, "fill", on > 0.3 ? "#fff3d6" : "#262b35");
        }

        // ---------- 2c · guard reaction: slow arc, rack focus, a blink ----------
        const RC = { stage: $("#reactStage"), bg: $("#rc-bg"), fg: $("#rc-fg"), near: $("#rc-near"), glow: $("#rc-glow"), head: $("#rg-head"), fore: $("#rg-fore"), torso: $("#rg-torso"), lid: $("#rg-lid") };
        function renderReact(t) {
          const lt0 = t - 12.8;
          RC.stage.style.transform = `scale(${f2(1.0 + lt0 * 0.022)})`;
          RC.bg.setAttribute("transform", `translate(${f1(-lt0 * 12)} 0)`);
          RC.fg.setAttribute("transform", `translate(${f1(-lt0 * 26)} 0)`);
          RC.near.setAttribute("transform", `translate(${f1(-lt0 * 70)} 0)`);
          const rack = sstep(13.35, 13.85, t) * (1 - sstep(14.35, 14.8, t));
          RC.bg.style.filter = `blur(${f1(9 - rack * 6.5)}px)`;
          RC.fg.style.filter = `blur(${f1(rack * 2.6)}px)`;
          RC.near.style.filter = `blur(${f1(10 - rack * 2)}px)`;
          RC.glow.setAttribute("opacity", f2(activeRoom10(t)));
          setA(RC.head, "transform", `rotate(${f1(13 + Math.sin(t * 1.3) * 1.2)} 142 176)`);
          setA(RC.fore, "transform", `rotate(${f1(Math.sin(t * 8.1) * 2.6)} 178 300)`);
          setA(RC.torso, "transform", `translate(0 ${f2(Math.sin(t * 1.6) * -3)})`);
          setA(RC.lid, "d", lidPath(Math.max(0.35, blinkAt(t, [13.3, 14.62]))));
        }
        function activeRoom10(t) {
          const a = sstep(13.2, 13.28, t) * (1 - sstep(14.3, 14.45, t));
          return a * (0.78 + 0.22 * Math.sin(t * 17) * Math.sin(t * 7.3));
        }

