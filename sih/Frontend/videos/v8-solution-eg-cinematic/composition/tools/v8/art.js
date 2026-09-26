        function artSky() {
          const r = mulberry32(11);
          let stars = "";
          for (let i = 0; i < 190; i++) {
            const x = -700 + r() * 3300,
              y = -900 + r() * 1480,
              rad = 0.55 + r() * 1.35,
              o = 0.25 + r() * 0.6;
            stars += `<circle class="star" cx="${f1(x)}" cy="${f1(y)}" r="${f2(rad)}" fill="#e3eaf8" opacity="${f2(o)}"/>`;
          }
          const rr = mulberry32(19);
          let rays = "";
          for (let i = 0; i < 8; i++) {
            const ang = ((14 + i * 9 + rr() * 5) * Math.PI) / 180,
              len = 1500 + rr() * 500,
              w = 36 + rr() * 90;
            const ex = 700 + Math.cos(ang) * len,
              ey = 150 + Math.sin(ang) * len;
            const nx = -Math.sin(ang) * w,
              ny = Math.cos(ang) * w;
            rays += `<polygon points="700,150 ${f1(ex + nx)},${f1(ey + ny)} ${f1(ex - nx)},${f1(ey - ny)}" fill="url(#sky-ray)" opacity="${f2(0.4 + rr() * 0.5)}"/>`;
          }
          const cloud = (cx, cy, rx, ry, o) =>
            `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="#1a2644" opacity="${o}"/><ellipse cx="${cx - rx * 0.08}" cy="${cy - ry * 0.35}" rx="${rx * 0.86}" ry="${ry * 0.5}" fill="#3b5080" opacity="${f2(o * 0.55)}"/>`;
          return `<svg width="1920" height="1080" viewBox="0 0 1920 1080">
            <defs>
              <radialGradient id="sky-g" gradientUnits="userSpaceOnUse" cx="700" cy="150" r="2200">
                <stop offset="0" stop-color="#253866"/><stop offset=".18" stop-color="#182647"/><stop offset=".5" stop-color="#0e172e"/><stop offset="1" stop-color="#050912"/></radialGradient>
              <radialGradient id="sky-halo" gradientUnits="userSpaceOnUse" cx="700" cy="150" r="360">
                <stop offset="0" stop-color="#dfe8fa" stop-opacity=".5"/><stop offset=".2" stop-color="#a7bbe3" stop-opacity=".18"/><stop offset="1" stop-color="#a7bbe3" stop-opacity="0"/></radialGradient>
              <radialGradient id="sky-ray" gradientUnits="userSpaceOnUse" cx="700" cy="150" r="1800">
                <stop offset="0" stop-color="#c3d3f3" stop-opacity=".2"/><stop offset=".45" stop-color="#8fa6d6" stop-opacity=".06"/><stop offset="1" stop-color="#8fa6d6" stop-opacity="0"/></radialGradient>
              <linearGradient id="sky-streak" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#cfe0ff" stop-opacity="0"/><stop offset=".5" stop-color="#f1f6ff" stop-opacity=".75"/><stop offset="1" stop-color="#cfe0ff" stop-opacity="0"/></linearGradient>
              <filter id="sky-soft" x="-60%" y="-200%" width="220%" height="500%"><feGaussianBlur stdDeviation="16"/></filter>
              <filter id="sky-rayblur" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="10"/></filter>
            </defs>
            <rect x="-1000" y="-1400" width="4000" height="3400" fill="url(#sky-g)"/>
            <g id="sky-stars">${stars}</g>
            <g id="sky-rays" filter="url(#sky-rayblur)" style="mix-blend-mode:screen">${rays}</g>
            <circle cx="700" cy="150" r="360" fill="url(#sky-halo)"/>
            <g>
              <circle cx="700" cy="150" r="40" fill="#eef2fb"/>
              <circle cx="688" cy="140" r="9" fill="#d3dbea" opacity=".75"/>
              <circle cx="714" cy="163" r="6" fill="#d6dcea" opacity=".65"/>
              <circle cx="707" cy="131" r="4" fill="#d3dbea" opacity=".6"/>
              <circle cx="682" cy="165" r="3.2" fill="#d3dbea" opacity=".55"/>
              <path d="M708 111 A40 40 0 0 1 708 189 A31 40 0 0 0 708 111Z" fill="#b9c4da" opacity=".38"/>
            </g>
            <ellipse cx="700" cy="150" rx="560" ry="2.4" fill="url(#sky-streak)" opacity=".55"/>
            <g id="sky-clouds" filter="url(#sky-soft)">
              ${cloud(540, 214, 250, 26, 0.7)}${cloud(930, 112, 200, 18, 0.55)}${cloud(1560, 86, 340, 30, 0.7)}
              ${cloud(150, 340, 300, 24, 0.6)}${cloud(2220, 190, 300, 26, 0.6)}${cloud(1200, -180, 380, 34, 0.6)}
              ${cloud(420, -420, 420, 40, 0.55)}${cloud(1500, -560, 360, 32, 0.5)}
            </g>
          </svg>`;
        }

        function artFar() {
          const r = mulberry32(23);
          let d = "M-900 1000 L-900 790 ";
          let x = -900;
          while (x < 2900) {
            const w = 16 + r() * 42,
              h = 20 + r() * 52;
            d += `Q${f1(x + w / 2)} ${f1(792 - h)} ${f1(x + w)} ${f1(796 - r() * 12)} `;
            x += w;
          }
          d += "L2900 1000 Z";
          const bl = [
            [-520, 640, 280, 200],
            [-210, 692, 190, 150],
            [30, 664, 160, 180],
            [1830, 628, 240, 210],
            [2090, 684, 280, 160],
            [2400, 650, 220, 190],
          ];
          let blocks = "";
          for (const b of bl) {
            blocks += `<rect x="${b[0]}" y="${b[1]}" width="${b[2]}" height="${b[3]}" fill="#0e1629"/><rect x="${b[0]}" y="${b[1]}" width="${b[2]}" height="3" fill="#1a2440"/>`;
            for (let k = 0; k < 7; k++) if (r() > 0.55) blocks += `<rect x="${f1(b[0] + 14 + r() * (b[2] - 28))}" y="${f1(b[1] + 18 + r() * (b[3] * 0.5))}" width="3" height="4" fill="#9fb3dc" opacity="${f2(0.25 + r() * 0.35)}"/>`;
          }
          return `<svg width="1920" height="1080" viewBox="0 0 1920 1080">
            <defs><linearGradient id="far-fog" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#22325a" stop-opacity="0"/><stop offset=".55" stop-color="#22325a" stop-opacity=".55"/><stop offset="1" stop-color="#22325a" stop-opacity="0"/></linearGradient></defs>
            ${blocks}<path d="${d}" fill="#0a1020"/>
            <rect x="-900" y="700" width="3800" height="190" fill="url(#far-fog)"/>
          </svg>`;
        }

        // small furniture silhouettes seen through a window (tone: cool|warm)
        const TONES = {
          cool: { wall: "#35456a", wall2: "#2a3858", floor: "#1f2a45", furn: "#141d34", edge: "#8ea3d1" },
          warm: { wall: "#5a3a18", wall2: "#40280f", floor: "#2c1b0a", furn: "#170f07", edge: "#f0b25a" },
        };
        function interior(n, tone) {
          const R = roomRect(n),
            T = TONES[tone],
            r = mulberry32(100 + n);
          const fy = R.y + R.h * 0.8;
          let s = `<rect x="${R.x}" y="${R.y}" width="${R.w}" height="${R.h}" fill="${T.wall}"/>`;
          s += `<rect x="${R.x}" y="${R.y}" width="${R.w}" height="${R.h * 0.35}" fill="${T.wall2}" opacity=".6"/>`;
          s += `<rect x="${R.x}" y="${f1(fy)}" width="${R.w}" height="${f1(R.y + R.h - fy)}" fill="${T.floor}"/>`;
          const cx = R.x + 8 + r() * 40;
          s += `<rect x="${f1(cx)}" y="${f1(R.y + 22)}" width="30" height="${f1(fy - R.y - 22)}" fill="${T.furn}"/><rect x="${f1(cx)}" y="${f1(R.y + 22)}" width="30" height="2" fill="${T.edge}" opacity=".7"/>`;
          s += `<rect x="${f1(cx + 4)}" y="${f1(R.y + 36)}" width="22" height="2" fill="${T.edge}" opacity=".35"/><rect x="${f1(cx + 4)}" y="${f1(R.y + 50)}" width="22" height="2" fill="${T.edge}" opacity=".35"/>`;
          const dx = R.x + 70 + r() * 40;
          s += `<rect x="${f1(dx)}" y="${f1(fy - 26)}" width="78" height="6" fill="${T.furn}"/><rect x="${f1(dx)}" y="${f1(fy - 26)}" width="78" height="1.6" fill="${T.edge}" opacity=".8"/>`;
          s += `<rect x="${f1(dx + 6)}" y="${f1(fy - 20)}" width="5" height="20" fill="${T.furn}"/><rect x="${f1(dx + 67)}" y="${f1(fy - 20)}" width="5" height="20" fill="${T.furn}"/>`;
          s += `<rect x="${f1(dx + 24)}" y="${f1(fy - 50)}" width="30" height="21" fill="${T.furn}"/><rect x="${f1(dx + 24)}" y="${f1(fy - 50)}" width="30" height="1.5" fill="${T.edge}" opacity=".6"/>`;
          const chx = dx + 50 + r() * 14;
          s += `<rect x="${f1(chx)}" y="${f1(fy - 36)}" width="6" height="26" fill="${T.furn}"/><rect x="${f1(chx - 16)}" y="${f1(fy - 14)}" width="22" height="5" fill="${T.furn}"/>`;
          return s;
        }

        /* the facade is one flat plane; #facade3d gives it real perspective (see proj3) */
        function artBuilding() {
          let defs = `
            <radialGradient id="b-moonwash" gradientUnits="userSpaceOnUse" cx="760" cy="120" r="1100">
              <stop offset="0" stop-color="#a9bde6" stop-opacity=".2"/><stop offset=".6" stop-color="#9fb4dd" stop-opacity=".05"/><stop offset="1" stop-color="#9fb4dd" stop-opacity="0"/></radialGradient>
            <linearGradient id="b-base" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#03060d" stop-opacity=".6"/></linearGradient>
            <linearGradient id="b-stain" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#070b16" stop-opacity=".45"/><stop offset="1" stop-color="#070b16" stop-opacity="0"/></linearGradient>
            <radialGradient id="b-torchg"><stop offset="0" stop-color="#fff3cf"/><stop offset=".25" stop-color="#ffd68a" stop-opacity=".95"/><stop offset=".6" stop-color="#e89a36" stop-opacity=".45"/><stop offset="1" stop-color="#b8661a" stop-opacity="0"/></radialGradient>
            <radialGradient id="b-bloomg"><stop offset="0" stop-color="#ffb24e" stop-opacity=".5"/><stop offset=".5" stop-color="#d9832a" stop-opacity=".16"/><stop offset="1" stop-color="#d9832a" stop-opacity="0"/></radialGradient>
            <radialGradient id="b-spillg"><stop offset="0" stop-color="#e8964a" stop-opacity=".32"/><stop offset="1" stop-color="#e8964a" stop-opacity="0"/></radialGradient>
            <radialGradient id="b-spotglowg"><stop offset="0" stop-color="#eaf1ff" stop-opacity=".34"/><stop offset=".55" stop-color="#c9d8f5" stop-opacity=".12"/><stop offset="1" stop-color="#c9d8f5" stop-opacity="0"/></radialGradient>
            <filter id="b-mblur" x="-40%" y="-60%" width="180%" height="220%"><feGaussianBlur stdDeviation="16"/></filter>
            <filter id="b-glowblur" x="-60%" y="-80%" width="220%" height="260%"><feGaussianBlur stdDeviation="24"/></filter>
            <mask id="b-spotmask" maskUnits="userSpaceOnUse" x="-400" y="-400" width="3000" height="2200">
              <rect id="b-spotrect" x="0" y="0" width="10" height="10" rx="46" fill="#fff" filter="url(#b-mblur)"/>
            </mask>`;
          for (let n = 1; n <= 16; n++) {
            const R = roomRect(n);
            defs += `<clipPath id="b-wclip-${n}"><rect x="${R.x}" y="${R.y}" width="${R.w}" height="${R.h}"/></clipPath>`;
          }
          const AC = [3, 8, 10, 13, 15];
          const CURTAIN = [5, 12, 14];
          const facade = (lit) => {
            const P = lit
              ? { base: "#44547a", slab: "#51628c", slabHi: "#7488b5", pil: "#4a5b84", pilHi: "#8295c2", par: "#4e5f88", frame: "#7384ae", recess: "#2a3656", sill: "#62739d", sillHi: "#a9b9de", ac: "#5d6d96", acHi: "#9aabd2" }
              : { base: "#1a2236", slab: "#212b43", slabHi: "#2e3a59", pil: "#1d2640", pilHi: "#29355a", par: "#232e48", frame: "#2b3553", recess: "#10172a", sill: "#27314c", sillHi: "#3b4768", glass: "#0a0f1d", ac: "#20293f", acHi: "#34405f" };
            let s = `<rect x="820" y="180" width="960" height="680" fill="${P.base}"/>`;
            // concrete panel joints
            for (let i = 1; i < 12; i++) s += `<rect x="${820 + i * 80}" y="180" width="1" height="680" fill="${lit ? "#56668f" : "#1d2539"}" opacity=".5"/>`;
            s += `<rect x="812" y="174" width="976" height="40" fill="${P.par}"/><rect x="808" y="170" width="984" height="8" fill="${lit ? "#8ea0c8" : "#34405f"}"/>`;
            for (const y of [214, 372, 524, 676]) s += `<rect x="820" y="${y}" width="960" height="18" fill="${P.slab}"/><rect x="820" y="${y}" width="960" height="2" fill="${P.slabHi}"/>`;
            s += `<rect x="820" y="826" width="960" height="34" fill="${P.slab}"/><rect x="820" y="826" width="960" height="2" fill="${P.slabHi}"/>`;
            for (const x of [820, 1044, 1276, 1508, 1740]) {
              const w = x === 820 ? 40 : x === 1740 ? 40 : 48;
              s += `<rect x="${x}" y="232" width="${w}" height="594" fill="${P.pil}"/><rect x="${x}" y="232" width="2" height="594" fill="${P.pilHi}"/>`;
            }
            // a sagging service cable along the second floor
            s += `<path d="M822 396 Q1060 412 1300 398 Q1540 386 1778 400" stroke="${lit ? "#26314e" : "#0c1120"}" stroke-width="2" fill="none"/>`;
            for (let n = 1; n <= 16; n++) {
              const R = roomRect(n);
              s += `<rect x="${R.x - 7}" y="${R.y - 7}" width="${R.w + 14}" height="${R.h + 14}" fill="${P.recess}"/>`;
              s += `<rect x="${R.x - 4}" y="${R.y - 4}" width="${R.w + 8}" height="${R.h + 8}" fill="${P.frame}"/>`;
              if (lit) {
                s += interior(n, "cool");
                s += `<polygon points="${pts([[R.x + R.w * 0.58, R.y], [R.x + R.w * 0.8, R.y], [R.x + R.w * 0.42, R.y + R.h], [R.x + R.w * 0.2, R.y + R.h]])}" fill="#dfe9ff" opacity=".12"/>`;
              } else {
                s += `<rect x="${R.x}" y="${R.y}" width="${R.w}" height="${R.h}" fill="${P.glass}"/>`;
                if ([2, 7, 11, 16].indexOf(n) >= 0) {
                  const bh = [0.55, 0.35, 0.7, 0.45][[2, 7, 11, 16].indexOf(n)] * R.h;
                  s += `<rect x="${R.x}" y="${R.y}" width="${R.w}" height="${f1(bh)}" fill="#141c30"/>`;
                  for (let yy = R.y + 5; yy < R.y + bh - 2; yy += 8) s += `<rect x="${R.x}" y="${f1(yy)}" width="${R.w}" height="2" fill="#1e2842"/>`;
                }
                if (CURTAIN.indexOf(n) >= 0) {
                  for (let k = 0; k < 4; k++) s += `<rect x="${R.x + 4 + k * 9}" y="${R.y}" width="6" height="${R.h}" fill="#111827" opacity=".9"/><rect x="${R.x + R.w - 12 - k * 9}" y="${R.y}" width="6" height="${R.h}" fill="#111827" opacity=".9"/>`;
                }
                s += `<polygon points="${pts([[R.x + R.w * 0.58, R.y], [R.x + R.w * 0.8, R.y], [R.x + R.w * 0.42, R.y + R.h], [R.x + R.w * 0.2, R.y + R.h]])}" fill="#26355a" opacity=".42"/>`;
              }
              s += `<rect x="${R.x}" y="${R.y + 30}" width="${R.w}" height="4" fill="${P.frame}"/>`;
              s += `<rect x="${R.x - 11}" y="${R.y + R.h + 4}" width="${R.w + 22}" height="8" fill="${P.sill}"/><rect x="${R.x - 11}" y="${R.y + R.h + 4}" width="${R.w + 22}" height="1.6" fill="${P.sillHi}"/>`;
              if (!lit) s += `<rect x="${R.x + 24}" y="${R.y + R.h + 12}" width="${R.w * 0.55}" height="46" fill="url(#b-stain)"/>`;
              if (AC.indexOf(n) >= 0) {
                const ax = R.x + R.w - 58,
                  ay = R.y + R.h + 16;
                s += `<rect x="${ax}" y="${ay}" width="48" height="26" rx="2" fill="${P.ac}"/><rect x="${ax}" y="${ay}" width="48" height="2" fill="${P.acHi}"/>`;
                for (let g = 0; g < 5; g++) s += `<rect x="${ax + 5 + g * 8}" y="${ay + 6}" width="4" height="16" fill="${lit ? "#3f4d72" : "#161d30"}"/>`;
              }
            }
            return s;
          };
          let torches = "";
          for (let n = 1; n <= 16; n++) {
            const R = roomRect(n);
            torches += `<g id="b-torch-${n}" opacity="0">
              <ellipse cx="${R.x + R.w / 2}" cy="${R.y + R.h / 2}" rx="200" ry="126" fill="url(#b-bloomg)" style="mix-blend-mode:screen"/>
              <ellipse cx="${R.x + R.w / 2}" cy="${R.y + R.h + 40}" rx="${R.w * 0.62}" ry="40" fill="url(#b-spillg)" style="mix-blend-mode:screen"/>
              <g clip-path="url(#b-wclip-${n})">${interior(n, "warm")}
                <circle id="b-tspot-${n}" cx="${R.x + R.w / 2}" cy="${R.y + R.h / 2}" r="58" fill="url(#b-torchg)" style="mix-blend-mode:screen"/>
              </g></g>`;
          }
          let plates = "";
          for (let n = 1; n <= 16; n++) {
            const R = roomRect(n);
            plates += `<text class="plate" x="${R.x - 11}" y="${R.y + 26}" text-anchor="end" font-family="JetBrains Mono, monospace" font-size="19" font-weight="700" fill="#d3daea" stroke="#0b1020" stroke-width="3.5" paint-order="stroke" opacity="0">${pad2(n)}</text>`;
          }
          const roof = `<rect x="900" y="146" width="96" height="30" fill="#161e31"/><rect x="900" y="146" width="96" height="2" fill="#2f3b5c"/><rect x="1014" y="156" width="52" height="20" fill="#161e31"/>
            <rect x="1560" y="124" width="70" height="52" fill="#141c2f"/><ellipse cx="1595" cy="124" rx="35" ry="7" fill="#1e2842"/><rect x="1690" y="84" width="4" height="92" fill="#1a2238"/>
            <path d="M1692 90 L1676 176 M1692 90 L1708 176" stroke="#1a2238" stroke-width="2"/>`;
          return `<svg width="1920" height="1080" viewBox="0 0 1920 1080"><defs>${defs}</defs>
            ${roof}
            <g id="b-dark">${facade(false)}</g>
            <rect x="820" y="180" width="960" height="680" fill="url(#b-moonwash)"/>
            <rect x="820" y="180" width="3" height="680" fill="#5a6c96" opacity=".8"/>
            <rect x="820" y="770" width="960" height="90" fill="url(#b-base)"/>
            <g id="b-lit" mask="url(#b-spotmask)" opacity="0">${facade(true)}</g>
            <g id="b-torches">${torches}</g>
            <rect id="b-spotglow" x="0" y="0" width="10" height="10" rx="40" fill="url(#b-spotglowg)" filter="url(#b-glowblur)" opacity="0" style="mix-blend-mode:screen"/>
            <g id="b-plates">${plates}</g>
          </svg>`;
        }

        /* ground, side wall, lamp post, fog and the foreshadow figure are drawn per frame through proj3 */
        function artBldBack() {
          let lines = "";
          for (let i = 0; i < 11; i++) lines += `<polygon class="bb-line" points="0,0 0,0 0,0 0,0" fill="#1b2542"/>`;
          let sidewin = "";
          for (let i = 0; i < 4; i++) sidewin += `<polygon class="bb-swin" points="0,0 0,0 0,0 0,0" fill="#0a0f1c"/>`;
          return `<svg width="1920" height="1080" viewBox="0 0 1920 1080">
            <defs>
              <radialGradient id="bb-pool" gradientUnits="userSpaceOnUse" cx="0" cy="0" r="10"><stop offset="0" stop-color="#cfdcf5" stop-opacity=".2"/><stop offset=".55" stop-color="#9fb4dd" stop-opacity=".06"/><stop offset="1" stop-color="#9fb4dd" stop-opacity="0"/></radialGradient>
              <radialGradient id="bb-doorpool" gradientUnits="userSpaceOnUse" cx="0" cy="0" r="10"><stop offset="0" stop-color="#cfdcf5" stop-opacity=".22"/><stop offset="1" stop-color="#9fb4dd" stop-opacity="0"/></radialGradient>
              <radialGradient id="bb-halo"><stop offset="0" stop-color="#e6eefc" stop-opacity=".8"/><stop offset=".25" stop-color="#c3d3f3" stop-opacity=".25"/><stop offset="1" stop-color="#c3d3f3" stop-opacity="0"/></radialGradient>
              <linearGradient id="bb-sidefade" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#070b16"/><stop offset="1" stop-color="#121a2e"/></linearGradient>
            </defs>
            <polygon id="bb-ground" points="0,0 0,0 0,0 0,0" fill="#0c1221"/>
            <g id="bb-lines">${lines}</g>
            <polygon id="bb-pool1" points="0,0 0,0 0,0" fill="url(#bb-pool)"/>
            <polygon id="bb-pool2" points="0,0 0,0 0,0" fill="url(#bb-doorpool)"/>
            <polygon id="bb-shadow" points="0,0 0,0 0,0 0,0" fill="#03050c" opacity=".35"/>
            <polygon id="bb-side" points="0,0 0,0 0,0 0,0" fill="url(#bb-sidefade)"/>
            <g id="bb-swins">${sidewin}</g>
            <polygon id="bb-pipe" points="0,0 0,0 0,0 0,0" fill="#0b1120"/>
            <polygon id="bb-door" points="0,0 0,0 0,0 0,0" fill="#1f2840"/>
            <polygon id="bb-curb" points="0,0 0,0 0,0 0,0" fill="#1c2640"/>
            <circle id="bb-dlamp" cx="0" cy="0" r="3" fill="#f0f5ff"/>
            <circle id="bb-dhalo" cx="0" cy="0" r="40" fill="url(#bb-halo)"/>
          </svg>`;
        }
        function artBldFront() {
          return `<svg width="1920" height="1080" viewBox="0 0 1920 1080">
            <defs>
              <radialGradient id="bf-halo"><stop offset="0" stop-color="#f0f5ff" stop-opacity=".95"/><stop offset=".18" stop-color="#cfdcf5" stop-opacity=".35"/><stop offset="1" stop-color="#cfdcf5" stop-opacity="0"/></radialGradient>
              <linearGradient id="bf-streak" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#dfe9ff" stop-opacity="0"/><stop offset=".5" stop-color="#f3f7ff" stop-opacity=".85"/><stop offset="1" stop-color="#dfe9ff" stop-opacity="0"/></linearGradient>
              <linearGradient id="bf-cone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#dfe8fa" stop-opacity=".14"/><stop offset="1" stop-color="#dfe8fa" stop-opacity="0"/></linearGradient>
              <filter id="bf-fog" x="-30%" y="-200%" width="160%" height="500%"><feGaussianBlur stdDeviation="26"/></filter>
            </defs>
            <g id="bf-fogband" filter="url(#bf-fog)">
              <ellipse id="bf-fog1" cx="1200" cy="870" rx="1300" ry="38" fill="#2a3a62" opacity=".42"/>
              <ellipse id="bf-fog2" cx="600" cy="905" rx="900" ry="30" fill="#24345a" opacity=".38"/>
            </g>
            <g id="bf-lamp">
              <polygon id="bf-lampcone" points="0,0 0,0 0,0" fill="url(#bf-cone)"/>
              <polygon id="bf-pole" points="0,0 0,0 0,0 0,0" fill="#141b2b"/>
              <path id="bf-arm" d="" stroke="#141b2b" stroke-width="7" fill="none"/>
              <circle id="bf-lhalo" cx="0" cy="0" r="90" fill="url(#bf-halo)" style="mix-blend-mode:screen"/>
              <ellipse id="bf-lstreak" cx="0" cy="0" rx="260" ry="2" fill="url(#bf-streak)" style="mix-blend-mode:screen"/>
            </g>
            <g id="b-sneak" opacity="0">${thiefSVG("bt")}</g>
          </svg>`;
        }

        /* ----- the guard, side view (faces right) ----- local box ~(-200..640, 0..540), floor y 540 */
        function guardSide(p, opts) {
          const o = opts || {};
          const uni = "#223261",
            uniLit = "#30447c",
            uniDk = "#162045",
            skin = "#a26c49",
            skinLit = "#c99470",
            skinDk = "#7a5036";
          return `
          <g id="${p}">
            ${
              o.booth
                ? `<g>
              <rect x="-196" y="40" width="306" height="500" fill="#121a2b"/><rect x="-196" y="40" width="306" height="500" fill="url(#${p}-boothwall)"/>
              <rect x="-212" y="24" width="338" height="24" fill="#18213a"/><rect x="-212" y="24" width="338" height="3" fill="#3a4a72"/>
              <rect x="-154" y="104" width="180" height="140" fill="#0b1120"/>
              <rect x="-150" y="108" width="172" height="132" fill="url(#${p}-boothglow)"/>
              <rect x="-154" y="104" width="180" height="4" fill="#2b3553"/><rect x="-66" y="104" width="4" height="140" fill="#1b2438"/>
              <rect x="-150" y="206" width="170" height="10" fill="#0e1422"/><rect x="-120" y="170" width="40" height="36" fill="#141c2f"/>
              <rect x="-154" y="64" width="124" height="26" rx="3" fill="#1c2640"/><text x="-92" y="83" font-family="Archivo, sans-serif" font-size="15" font-weight="800" letter-spacing="3" fill="#aab5d0" text-anchor="middle">SECURITY</text>
              <circle cx="96" cy="32" r="5" fill="#e8f0ff"/><circle cx="96" cy="32" r="30" fill="url(#${p}-bulb)" style="mix-blend-mode:screen"/>
            </g>`
                : ""
            }
            <!-- chair back + base -->
            <path d="M34 238 C30 226 42 220 54 224 L62 228 C70 232 68 246 67 252 L60 398 C60 408 52 412 44 410 L40 408 C33 406 31 398 31 390 Z" fill="#151d2f"/>
            <path d="M40 238 L44 396" stroke="#2a3552" stroke-width="2"/>
            <rect x="94" y="428" width="12" height="96" fill="#141b2b"/><rect x="94" y="428" width="3" height="96" fill="#26304a"/>
            <rect x="26" y="522" width="148" height="8" rx="4" fill="#0f1522"/>
            <circle cx="34" cy="533" r="8" fill="#0b1019"/><circle cx="100" cy="534" r="8" fill="#0b1019"/><circle cx="166" cy="533" r="8" fill="#0b1019"/>
            <!-- far leg -->
            <g fill="#131b30">
              <path d="M92 356 C150 350 220 350 250 354 C270 356 278 372 272 388 C268 400 256 406 240 404 C190 402 140 406 96 406 Z"/>
              <path d="M238 382 C250 378 272 378 276 388 L278 498 C278 506 272 510 264 510 L248 510 C242 510 238 504 238 496 Z"/>
              <path d="M236 500 C236 492 248 490 258 492 L286 500 C302 504 312 512 310 520 C309 526 302 530 294 530 L242 530 C234 530 232 522 234 514 Z" fill="#0a0e18"/>
            </g>
            <!-- seat -->
            <rect x="34" y="402" width="154" height="26" rx="11" fill="#19212f"/><rect x="40" y="402" width="140" height="3" rx="1.5" fill="#2e3956"/>
            <!-- torso + head + arms breathe together -->
            <g id="${p}-torso">
              <!-- far forearm on the logbook -->
              <path d="M176 300 C206 292 236 290 256 292 C264 293 266 304 258 308 C236 312 206 314 182 316 Z" fill="#18234a"/>
              <path d="M250 290 C258 285 272 286 280 292 C286 296 286 304 280 307 L256 310 C249 307 246 298 250 290 Z" fill="${skinDk}"/>
              <path d="M262 306 L284 306 M264 301 L286 301" stroke="#5c3a27" stroke-width="1.4"/>
              <!-- body -->
              <path d="M70 392 C64 330 70 262 86 216 C94 198 116 188 140 188 C164 188 186 198 194 216 C206 252 206 330 198 392 Z" fill="${uni}"/>
              <path d="M170 196 C190 206 198 230 202 262 C206 310 204 360 198 392 L182 392 C188 350 190 300 186 262 C182 232 176 212 160 198 Z" fill="${uniLit}"/>
              <path d="M74 390 C70 330 74 270 88 222 C92 210 100 202 110 198 C98 230 92 290 94 390 Z" fill="${uniDk}"/>
              <path d="M120 262 C130 300 128 340 124 380 M150 250 C160 290 160 330 156 372" stroke="#1b2754" stroke-width="2" fill="none" opacity=".8"/>
              <path d="M186 220 C194 260 196 320 192 388" stroke="#1a2650" stroke-width="2" fill="none"/>
              <circle cx="191" cy="250" r="2.6" fill="#8da0c8"/><circle cx="194" cy="290" r="2.6" fill="#8da0c8"/><circle cx="195" cy="330" r="2.6" fill="#8da0c8"/><circle cx="195" cy="366" r="2.6" fill="#8da0c8"/>
              <!-- pocket with flap + pen clip, name tag, badge -->
              <path d="M158 238 L188 236 L190 266 L160 268 Z" fill="#1d2a55"/><path d="M158 238 L188 236 L188 246 L158 248 Z" fill="#172247"/><circle cx="173" cy="243" r="1.8" fill="#8da0c8"/>
              <rect x="168" y="228" width="2.4" height="14" rx="1" fill="#c9d3e6"/>
              <rect x="160" y="276" width="28" height="8" rx="1.5" fill="#0d1428"/><rect x="163" y="279" width="18" height="2" fill="#aab5d0"/>
              <path d="M166 214 L178 213 L180 226 L172 232 L165 226 Z" fill="#c9d3e6"/><path d="M169 217 L176 216 L177 224 L172 228 L168 224 Z" fill="#223261"/><circle cx="172.5" cy="221" r="1.6" fill="#c9d3e6"/>
              <!-- radio mic on the chest, coiled cable to the belt -->
              <rect x="180" y="226" width="12" height="22" rx="4" fill="#0c111b"/><rect x="182" y="230" width="8" height="3" fill="#2a3348"/>
              <path d="M186 248 C194 254 180 260 188 266 C196 272 180 278 188 284 C196 290 182 296 188 304 C192 320 150 350 110 368" stroke="#0c111b" stroke-width="2" fill="none"/>
              <!-- epaulette -->
              <rect x="104" y="190" width="72" height="12" rx="4" fill="#18234a"/><circle cx="166" cy="196" r="3" fill="#aeb9d2"/>
              <!-- belt with buckle and a radio pouch -->
              <rect x="66" y="376" width="136" height="16" fill="#0f1526"/><rect x="66" y="376" width="136" height="2" fill="#26304c"/><rect x="190" y="377" width="12" height="14" rx="2" fill="#a9b4c9"/>
              <rect x="72" y="360" width="30" height="40" rx="4" fill="#0b1019"/><rect x="80" y="330" width="4" height="32" rx="2" fill="#0b1019"/><circle cx="82" cy="330" r="3" fill="#0b1019"/>
              <!-- collar + neck -->
              <path d="M126 192 L126 166 C126 158 150 158 152 166 L156 192 Z" fill="${skinDk}"/>
              <path d="M122 190 C132 180 148 178 160 184 L170 200 L150 196 L136 202 Z" fill="#2c3e74"/>
              <path d="M150 182 L172 202 L160 204 Z" fill="#243565"/>
              <!-- head -->
              <g id="${p}-head">
                <path d="M104 140 C100 112 112 84 140 78 C162 74 180 84 186 104 L188 116 C189 120 192 124 196 130 C199 134 197 137 192 138 L190 139 C191 143 190 146 188 147 C190 150 189 153 186 154 C185 160 182 165 176 168 C166 174 150 176 138 172 C124 168 110 160 104 140 Z" fill="${skin}"/>
                <path d="M178 96 C186 104 188 114 190 122 C194 128 197 132 194 136 L188 138 C190 146 186 156 182 160 C176 168 166 172 158 172 C170 160 176 140 176 120 Z" fill="${skinLit}" opacity=".85"/>
                <path d="M104 140 C100 112 112 88 132 80 C120 100 116 130 124 168 C112 160 106 150 104 140 Z" fill="${skinDk}" opacity=".7"/>
                <path d="M126 150 C132 164 146 172 164 172 C150 177 134 173 124 162 Z" fill="${skinDk}" opacity=".55"/>
                <path d="M106 134 C104 116 110 100 124 94 L150 96 C138 104 128 116 126 134 Z" fill="#17110d"/>
                <path d="M114 106 C120 102 128 102 134 104 M112 118 C118 114 124 114 130 116" stroke="#2c2119" stroke-width="1.6" fill="none"/>
                <path d="M146 110 L154 110 L156 136 L149 138 Z" fill="#17110d"/>
                <path d="M122 122 C130 118 139 124 139 134 C139 145 133 151 126 151 C121 146 119 135 122 122 Z" fill="#96613f"/>
                <path d="M126 128 C131 128 134 134 132 143" stroke="#6b4430" stroke-width="2" fill="none"/>
                <!-- eye (blinks) -->
                <g id="${p}-eye">
                  <path d="M163 118 Q172 111 182 116.5 Q173 122.5 163 118 Z" fill="#efe9e1"/>
                  <circle cx="175" cy="117.4" r="3.3" fill="#3b2415"/><circle cx="175.6" cy="117.4" r="1.6" fill="#0e0907"/><circle cx="176.6" cy="116.2" r="0.95" fill="#fff"/>
                  <path id="${p}-lid" d="M162 118 Q172 110.5 183 116.5 L183 116.5 Q172 110.5 162 118 Z" fill="${skin}"/>
                  <path d="M162.5 117.6 Q172 110.8 182.6 116.2" stroke="#24170f" stroke-width="2.2" fill="none" stroke-linecap="round"/>
                </g>
                <path d="M159 107 Q171 100.5 185 105 L184 108.5 Q171 105 160 110.5 Z" fill="#1d130d"/>
                <path d="M185 136 Q189 138.5 192 136" stroke="#6b4430" stroke-width="1.8" fill="none"/>
                <path d="M188 124 C190 128 192 132 192 136" stroke="#8a5a3c" stroke-width="1.4" fill="none" opacity=".7"/>
                <!-- moustache, lips -->
                <path d="M177 141.5 C183 138.5 192 139 195 143.5 C191 147.5 184 147.5 179 146 C176 145 175.5 143 177 141.5 Z" fill="#17100c"/>
                <path d="M180 142 C185 140.5 190 141 193 143" stroke="#3a2a20" stroke-width="1.1" fill="none"/>
                <path d="M183 151.5 Q187 152.5 190 150.5" stroke="#5a3526" stroke-width="2" fill="none"/>
                <path d="M182 154 Q186 157 189 154" stroke="#7a4a33" stroke-width="1.4" fill="none" opacity=".7"/>
                <path d="M160 98 L196 104 L194 116 L162 114 Z" fill="#000" opacity=".22"/>
                <!-- cap -->
                <path d="M98 108 C96 88 118 64 150 62 C176 60 194 72 196 92 L196 104 L99 111 Z" fill="#1c2850"/>
                <path d="M110 80 C126 66 150 62 170 64 C156 68 136 74 116 86 Z" fill="#2e4074"/>
                <path d="M150 63 L152 104" stroke="#162042" stroke-width="1.6"/>
                <path d="M98 102 L196 97 L197 110 L99 115 Z" fill="#0f172d"/>
                <path d="M120 104 L196 100" stroke="#aeb9d2" stroke-width="1.6"/>
                <path d="M176 104 C192 104 208 108 216 115 C208 120 190 118 178 114 Z" fill="#090d18"/>
                <path d="M182 107 Q196 109 210 114" stroke="#46557e" stroke-width="1.8" fill="none"/>
                <path d="M176 76 L186 79 L186 90 L181 94 L176 90 Z" fill="#c9d3e6"/><path d="M181 80 L182.5 84 L186 84.4 L183.3 86.6 L184.2 90 L181 88 L177.8 90 L178.7 86.6 L176 84.4 L179.5 84 Z" fill="#1c2850"/>
              </g>
              <!-- near arm -->
              <g id="${p}-arm">
                <path d="M126 214 C126 198 172 196 178 214 L198 292 C202 306 190 318 178 318 C166 318 158 310 156 300 Z" fill="${uni}"/>
                <path d="M160 206 C172 204 178 210 180 218 L198 290 C200 298 196 306 190 310 Z" fill="${uniLit}"/>
                <path d="M146 252 C156 262 170 266 184 262" stroke="#1b2754" stroke-width="1.8" fill="none"/>
                <path d="M148 226 L172 224 L174 250 L162 260 L150 250 Z" fill="#2f4478" stroke="#a9b8dc" stroke-width="1.6"/>
                <text x="161" y="241" text-anchor="middle" font-family="Archivo, sans-serif" font-weight="800" font-size="5.2" letter-spacing=".3" fill="#dfe6f5">SECURITY</text>
                <path d="M156 246 L166 246" stroke="#dfe6f5" stroke-width="1.2"/>
                <g id="${p}-fore">
                  <path d="M170 296 C200 288 238 284 262 286 C272 287 276 300 268 308 C250 312 212 316 182 318 C168 318 162 304 170 296 Z" fill="${uni}"/>
                  <path d="M176 292 C204 286 238 283 260 285 L262 292 C236 292 206 296 178 302 Z" fill="${uniLit}"/>
                  <path d="M214 290 C220 298 222 306 220 314" stroke="#1b2754" stroke-width="1.6" fill="none"/>
                  <rect x="250" y="284" width="12" height="26" rx="3" fill="#1a2649"/>
                  <rect x="246" y="286" width="7" height="22" rx="2" fill="#0d1220"/><rect x="247.5" y="292" width="4" height="9" rx="1" fill="#c9d3e6"/>
                  <!-- hand holding a pen: back of the hand, curled fingers, thumb -->
                  <path d="M260 285 C270 280 286 281 294 288 C299 293 299 301 294 306 L272 311 C262 309 256 297 260 285 Z" fill="${skin}"/>
                  <path d="M266 283 C276 280 288 282 293 288" stroke="${skinLit}" stroke-width="3" fill="none" stroke-linecap="round"/>
                  <path d="M272 309 C274 315 280 317 284 313 M280 307 C283 313 289 314 292 310 M287 304 C291 309 296 309 298 305" stroke="${skinDk}" stroke-width="6.5" fill="none" stroke-linecap="round"/>
                  <path d="M270 287 Q279 278 291 282" stroke="${skin}" stroke-width="8" fill="none" stroke-linecap="round"/>
                  ${o.pen ? `<g id="${p}-pen"><path d="M282 296 L316 316" stroke="#0e1320" stroke-width="3.6" stroke-linecap="round"/><path d="M284 297 L292 302" stroke="#c9d3e6" stroke-width="1.4"/></g>` : ""}
                </g>
              </g>
            </g>
            <!-- near leg -->
            <path d="M96 362 C150 356 220 356 262 360 C282 362 290 380 284 398 C280 412 266 418 250 416 C200 414 150 418 104 418 Z" fill="#1b2540"/>
            <path d="M104 362 C150 357 220 356 262 360 C272 361 280 366 283 372 C240 368 160 368 104 370 Z" fill="#2c3a5e"/>
            <path d="M130 378 C170 376 220 376 258 380" stroke="#131b30" stroke-width="1.8" fill="none"/>
            <path d="M250 392 C262 388 286 388 290 398 L292 506 C292 514 286 518 278 518 L262 518 C256 518 252 512 252 504 Z" fill="#1b2540"/>
            <path d="M284 396 C290 400 292 420 292 506 L286 510 C286 470 284 430 280 400 Z" fill="#2c3a5e"/>
            <path d="M270 400 L272 500" stroke="#131b30" stroke-width="1.6"/>
            <path d="M250 506 C250 498 262 496 272 498 L300 506 C318 510 328 518 326 528 C325 534 318 538 310 538 L256 538 C248 538 246 530 248 522 Z" fill="#0c111c"/>
            <path d="M248 532 L326 532" stroke="#232c42" stroke-width="3"/>
            <path d="M276 500 L302 508 C312 511 318 515 320 520" stroke="#2c3550" stroke-width="2" fill="none"/>
            <path d="M282 504 L288 499 M290 507 L296 502" stroke="#3a4462" stroke-width="1.4"/>
          </g>`;
        }

        /* ----- desk, lamp, spotlight (in front of the side-view guard) ----- */
        function guardDesk(p) {
          return `
          <g id="${p}-desk">
            <path d="M234 300 L558 294 L562 306 L232 312 Z" fill="#1d2539"/>
            <rect x="232" y="306" width="330" height="13" fill="#161d2e"/><rect x="232" y="306" width="330" height="2" fill="#3a4768"/>
            <rect x="244" y="319" width="306" height="42" fill="#121928"/>
            <rect x="250" y="319" width="12" height="221" fill="#0f1522"/><rect x="536" y="319" width="12" height="221" fill="#0f1522"/>
            <rect x="440" y="319" width="96" height="152" fill="#141b2b"/><rect x="440" y="394" width="96" height="2" fill="#222b42"/><rect x="478" y="354" width="22" height="4" rx="2" fill="#2e3955"/><rect x="478" y="428" width="22" height="4" rx="2" fill="#2e3955"/>
            <!-- logbook, open, lit by the desk lamp -->
            <path d="M292 297 L394 292 L398 301 L296 305 Z" fill="#e3e8f2"/><path d="M345 293.5 L347 303" stroke="#8e97ab" stroke-width="1.6"/>
            <path d="M302 298 L338 297 M302 301 L338 300 M353 296 L388 295 M353 299 L388 298" stroke="#7d879d" stroke-width=".9"/>
            <path d="M296 305 L398 301 L399 304 L297 308 Z" fill="#6b7590"/>
            <rect x="408" y="276" width="18" height="22" rx="2" fill="#27314d"/><path d="M426 281 C434 281 434 293 426 293" stroke="#27314d" stroke-width="3" fill="none"/>
            <path d="M412 272 C410 264 416 262 414 254 M420 272 C418 266 424 262 422 256" stroke="#9aa9c9" stroke-width="1.2" fill="none" opacity=".35"/>
            <rect x="436" y="266" width="16" height="31" rx="3" fill="#0e131f"/><rect x="440" y="244" width="3" height="24" fill="#0e131f"/><circle cx="447" cy="272" r="1.8" fill="#bcd0f5"/><rect x="439" y="280" width="10" height="10" rx="1" fill="#1b2336"/>
            <ellipse cx="500" cy="297" rx="20" ry="4" fill="#20283c"/>
            <path d="M500 296 L520 238 L480 214" stroke="#2a3350" stroke-width="6" fill="none" stroke-linejoin="round" stroke-linecap="round"/>
            <circle cx="520" cy="238" r="4" fill="#3a4666"/>
            <path d="M462 204 L494 202 L489 226 L458 231 Z" fill="#2f3a57"/><path d="M462 204 L494 202 L493 208 L462 210 Z" fill="#4a578a"/>
            <polygon points="460,230 489,226 560,302 372,307" fill="url(#${p}-lampcone)" style="mix-blend-mode:screen"/>
            <ellipse cx="350" cy="300" rx="92" ry="12" fill="url(#${p}-deskpool)" style="mix-blend-mode:screen"/>
            <ellipse cx="475" cy="229" rx="10" ry="4" fill="#f2f6ff"/>
            <circle cx="475" cy="229" r="26" fill="url(#${p}-bulb)" style="mix-blend-mode:screen"/>
            <rect x="552" y="206" width="9" height="92" fill="#1b2233"/><rect x="552" y="206" width="2" height="92" fill="#2e3a58"/>
            <path d="M540 218 L574 218 L570 206 L544 206 Z" fill="#1b2233"/>
            <g id="${p}-spot">
              <rect x="-40" y="-23" width="92" height="46" rx="9" fill="#27304a"/>
              <rect x="-40" y="-23" width="92" height="7" rx="3" fill="#46547c"/>
              <path d="M-30 -12 L40 -12 M-30 -4 L40 -4 M-30 4 L40 4" stroke="#1d2540" stroke-width="2"/>
              <rect x="-34" y="-35" width="26" height="14" rx="6" fill="none" stroke="#27304a" stroke-width="5"/>
              <ellipse cx="52" cy="0" rx="7" ry="23" fill="#3a4666"/>
              <ellipse id="${p}-lens" cx="54" cy="0" rx="4.5" ry="18" fill="#121a2a"/>
            </g>
          </g>`;
        }
        function guardDefs(p) {
          return `<linearGradient id="${p}-lampcone" gradientUnits="userSpaceOnUse" x1="475" y1="229" x2="470" y2="305">
            <stop offset="0" stop-color="#e6eefc" stop-opacity=".55"/><stop offset="1" stop-color="#e6eefc" stop-opacity=".04"/></linearGradient>
            <radialGradient id="${p}-deskpool"><stop offset="0" stop-color="#eef3ff" stop-opacity=".55"/><stop offset="1" stop-color="#eef3ff" stop-opacity="0"/></radialGradient>
            <radialGradient id="${p}-bulb"><stop offset="0" stop-color="#ffffff" stop-opacity=".9"/><stop offset=".3" stop-color="#dfe9ff" stop-opacity=".35"/><stop offset="1" stop-color="#dfe9ff" stop-opacity="0"/></radialGradient>
            <linearGradient id="${p}-boothwall" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0a0f1c" stop-opacity=".6"/><stop offset="1" stop-color="#2a3656" stop-opacity=".25"/></linearGradient>
            <radialGradient id="${p}-boothglow" cx=".5" cy=".3" r=".8"><stop offset="0" stop-color="#9fb3dc" stop-opacity=".55"/><stop offset="1" stop-color="#1a2440" stop-opacity=".1"/></radialGradient>`;
        }

        /* ----- the guard from behind (over-the-shoulder), drawn in screen space ----- */
        function guardBack(p) {
          let hair = "";
          const hr = mulberry32(77);
          for (let i = 0; i < 26; i++) {
            const x = 244 + hr() * 148,
              y = 646 + hr() * 86;
            hair += `<path d="M${f1(x)} ${f1(y)} q${f1(-3 + hr() * 6)} ${f1(6 + hr() * 6)} ${f1(-2 + hr() * 4)} ${f1(12 + hr() * 6)}" stroke="#2a1f18" stroke-width="1.6" fill="none"/>`;
          }
          return `<g id="${p}">
            <path d="M-60 1090 C-50 980 -10 900 70 866 C140 836 214 818 262 812 L372 812 C420 818 486 834 540 862 C612 900 650 980 660 1090 Z" fill="#111a34"/>
            <path d="M70 866 C140 836 214 818 262 812 L250 836 C190 846 130 866 92 892 Z" fill="#1a2750"/>
            <path d="M318 830 C320 900 318 980 316 1090" stroke="#0b1126" stroke-width="3" fill="none"/>
            <path d="M40 940 C90 900 150 878 200 870 M420 872 C480 884 540 910 580 950" stroke="#0b1126" stroke-width="3" fill="none"/>
            <rect x="96" y="850" width="120" height="22" rx="6" fill="#0c1328" transform="rotate(-12 156 861)"/>
            <rect x="420" y="848" width="122" height="22" rx="6" fill="#0c1328" transform="rotate(13 481 859)"/>
            <circle cx="206" cy="852" r="4" fill="#aab5d0" opacity=".85"/><circle cx="430" cy="852" r="4" fill="#aab5d0" opacity=".85"/>
            <!-- shoulder radio + antenna -->
            <rect x="150" y="824" width="30" height="44" rx="6" fill="#0a0f1c" transform="rotate(-18 165 846)"/>
            <path d="M160 826 L140 760" stroke="#0a0f1c" stroke-width="5" stroke-linecap="round"/><circle cx="140" cy="758" r="4" fill="#0a0f1c"/>
            <!-- collar + neck -->
            <path d="M232 822 C240 796 268 786 318 786 C366 786 392 796 402 822 C360 834 276 834 232 822 Z" fill="#0c1326"/>
            <path d="M246 818 L290 796 L318 806 L346 796 L390 818" stroke="#1a2750" stroke-width="3" fill="none"/>
            <path d="M262 800 C262 764 272 742 284 734 L350 734 C362 742 372 764 372 800 C340 808 294 808 262 800 Z" fill="#35251b"/>
            <path d="M350 738 C362 748 370 770 372 798 L360 800 C360 776 356 756 346 742 Z" fill="#4a3325" opacity=".8"/>
            <!-- head: short dark hair -->
            <path d="M234 668 C226 612 250 566 317 560 C384 566 408 612 400 668 C394 712 360 744 317 744 C274 744 240 712 234 668 Z" fill="#17110d"/>
            <g>${hair}</g>
            <path d="M360 580 C392 604 404 640 398 676 C394 700 382 716 368 728 C384 700 388 650 360 580 Z" fill="#2a1f18"/>
            <ellipse cx="232" cy="672" rx="13" ry="26" fill="#4d3325"/><ellipse cx="402" cy="672" rx="13" ry="26" fill="#5a3b2b"/>
            <path d="M400 660 C406 666 406 680 400 688" stroke="#3a2619" stroke-width="2" fill="none"/>
            <!-- peaked cap from behind -->
            <path d="M242 632 L220 578 C214 556 252 540 317 538 C382 540 420 556 414 578 L392 632 Z" fill="#1a2749"/>
            <path d="M222 568 C236 550 276 542 317 541 C358 542 398 550 412 568 C380 558 350 555 317 555 C284 555 254 558 222 568 Z" fill="#2e4076"/>
            <path d="M270 546 L280 630 M364 546 L354 630 M317 540 L317 630" stroke="#141f3e" stroke-width="1.6"/>
            <path d="M240 616 L394 616 L390 640 L244 640 Z" fill="#0d1428"/>
            <path d="M262 628 L372 628" stroke="#1b2645" stroke-width="3"/>
            <!-- right arm reaching to the spotlight handle -->
            <path d="M430 842 C500 846 572 866 630 896 C660 912 668 942 646 958 C622 972 590 962 560 946 C512 922 466 906 420 896 Z" fill="#141e3c"/>
            <path d="M470 870 C500 880 530 892 556 906" stroke="#0b1126" stroke-width="2.4" fill="none"/>
            <path d="M600 900 C650 880 712 858 760 842 C786 834 806 846 806 868 C806 888 788 896 766 902 C716 916 668 934 632 950 Z" fill="#17224a"/>
            <rect x="738" y="846" width="16" height="44" rx="4" fill="#0e1530" transform="rotate(-18 746 868)"/>
            <path d="M760 832 C778 820 806 822 816 840 C824 856 816 874 798 878 L774 882 C760 874 752 848 760 832 Z" fill="#4d3325"/>
            <path d="M784 826 C794 824 806 830 810 840" stroke="#6b4834" stroke-width="3" fill="none" stroke-linecap="round"/>
            <g id="${p}-rim" fill="none" stroke="#b3c5ea" stroke-linecap="round" opacity="0">
              <path d="M317 538 C382 540 420 556 414 578 L392 632" stroke-width="3.5"/>
              <path d="M400 668 C396 704 380 728 356 740" stroke-width="3"/>
              <path d="M372 812 C420 818 486 834 540 862" stroke-width="3.5"/>
              <path d="M760 842 C786 834 806 846 806 868" stroke-width="3"/>
              <path d="M140 758 L158 820" stroke-width="2"/>
            </g>
          </g>`;
        }

        /* ----- the thief (faces right in local space). feet centre (160,580) ----- */
        function thiefSVG(p) {
          const hood = "#1d2029",
            hoodLit = "#2d313d",
            pants = "#14161c",
            glove = "#0f1013";
          const leg = (id, c, cLit, near) => `
            <g id="${p}-${id}Thigh">
              <path d="M-20 -6 C-22 -16 20 -18 22 -6 L20 118 C18 128 -16 128 -18 118 Z" fill="${c}"/>
              <path d="M10 -10 C18 -8 22 -2 22 6 L19 116 C18 122 14 126 10 126 Z" fill="${cLit}" opacity=".5"/>
              ${near ? `<path d="M-2 40 L20 40 L20 76 L-2 78 Z" fill="#191c23"/><path d="M-3 40 L21 40 L21 48 L-3 49 Z" fill="#20242d"/><circle cx="9" cy="45" r="1.6" fill="#3a3f4c"/>` : ""}
              <path d="M-8 96 C0 100 8 100 14 96" stroke="#0b0c10" stroke-width="1.6" fill="none"/>
              <g id="${p}-${id}Shin" transform="translate(0 120)">
                <path d="M-17 -4 C-18 -12 17 -12 18 -4 L16 110 C15 118 -14 118 -15 110 Z" fill="${c}"/>
                <path d="M6 -8 C14 -6 18 0 18 6 L16 106 C15 112 11 114 8 114 Z" fill="${cLit}" opacity=".45"/>
                <path d="M-16 92 C-8 98 8 98 16 92 M-15 100 C-6 104 6 104 15 100" stroke="#0b0c10" stroke-width="1.6" fill="none"/>
                <path d="M-18 104 C-18 96 -4 94 8 96 L38 108 C52 113 56 122 52 130 C50 134 44 136 36 136 L-14 136 C-20 136 -22 128 -20 120 Z" fill="#0b0c10"/>
                <path d="M-20 129 L52 129" stroke="#454b5a" stroke-width="3.2"/>
                <path d="M6 104 L14 100 M14 107 L22 103 M22 110 L30 106" stroke="#2a2e38" stroke-width="1.6"/>
                <path d="M-16 106 L-16 118" stroke="#2a2e38" stroke-width="3"/>
              </g>
            </g>`;
          const arm = (id, c, cLit, torch) => `
            <g id="${p}-${id}Arm">
              <path d="M-17 -6 C-18 -18 18 -18 18 -6 L16 88 C15 98 -14 98 -15 88 Z" fill="${c}"/>
              <path d="M6 -14 C14 -10 18 -4 18 4 L16 86 C15 92 12 96 8 96 Z" fill="${cLit}" opacity=".55"/>
              <path d="M-12 44 C-4 48 4 48 12 44" stroke="#15171d" stroke-width="1.6" fill="none"/>
              <g id="${p}-${id}Fore" transform="translate(0 92)">
                <path d="M-15 -4 C-16 -12 15 -12 15 -4 L13 82 C12 90 -12 90 -13 82 Z" fill="${c}"/>
                <path d="M-13 70 L13 70 L13 80 L-13 80 Z" fill="#16181e"/>
                <path d="M-13 73 L13 73 M-13 76 L13 76" stroke="#0e1014" stroke-width="1"/>
                <path d="M-15 78 C-16 70 15 70 16 78 L15 104 C14 114 -13 114 -14 104 Z" fill="${glove}"/>
                <path d="M-12 100 C-8 108 -2 110 2 106 M-2 104 C2 112 8 112 10 106 M8 102 C12 108 16 106 16 100" stroke="#1d1f25" stroke-width="5" fill="none" stroke-linecap="round"/>
                <path d="M-10 84 L10 84" stroke="#23262e" stroke-width="1.4"/>
                ${
                  torch
                    ? `<g id="${p}-torch"><rect x="-7" y="84" width="14" height="56" rx="4" fill="#8d97aa"/><rect x="-7" y="84" width="4" height="56" rx="2" fill="#c3cbdb"/>
                  <path d="M-7 96 L7 96 M-7 100 L7 100 M-7 104 L7 104 M-7 108 L7 108" stroke="#6b7488" stroke-width="1"/>
                  <rect x="5" y="112" width="4" height="8" rx="1.5" fill="#23262e"/>
                  <path d="M-11 132 L11 132 L12 152 L-12 152 Z" fill="#a2acbf"/><path d="M-11 132 L-5 132 L-6 152 L-12 152 Z" fill="#c9d0de"/><rect x="-12" y="150" width="24" height="5" rx="2" fill="#5f687a"/>
                  <ellipse id="${p}-lens" cx="0" cy="155" rx="10" ry="3" fill="#39414f"/></g>`
                    : ""
                }
              </g>
            </g>`;
          return `<g id="${p}">
            <g id="${p}-farLegRoot" transform="translate(154 330)">${leg("far", "#0f1115", "#1d2027", false)}</g>
            <g id="${p}-torsoA">
              <g id="${p}-farArmRoot" transform="translate(158 190)">${arm("far", "#15171d", "#22252d", false)}</g>
              <!-- backpack: body, front pocket, zip pulls, strap buckle -->
              <path d="M84 176 C82 166 96 160 108 162 L134 166 C142 168 144 178 142 188 L136 296 C134 306 124 310 112 308 L94 304 C84 302 80 292 82 282 Z" fill="#20242c"/>
              <path d="M86 200 C84 180 92 172 104 172 L112 174 C104 190 100 230 100 300 L94 302 C86 298 84 280 86 200 Z" fill="#2a2f39" opacity=".7"/>
              <path d="M88 200 L138 204 M86 250 L136 254" stroke="#15181e" stroke-width="3"/>
              <rect x="94" y="214" width="32" height="30" rx="5" fill="#262a33"/><path d="M96 220 L124 220" stroke="#15181e" stroke-width="2"/>
              <rect x="102" y="216" width="3" height="10" rx="1.5" fill="#6d7688"/><rect x="112" y="216" width="3" height="10" rx="1.5" fill="#6d7688"/>
              <path d="M96 164 C98 150 118 148 124 160" stroke="#15181e" stroke-width="5" fill="none"/>
              <!-- hoodie -->
              <path d="M118 330 C110 280 112 222 124 190 C132 170 150 160 170 160 C190 162 204 176 206 200 C210 240 208 290 204 332 Z" fill="${hood}"/>
              <path d="M186 168 C200 178 206 196 208 220 C210 260 208 300 204 332 L194 332 C198 290 198 240 194 212 C192 194 186 180 176 170 Z" fill="${hoodLit}"/>
              <path d="M120 318 L204 318 L204 332 L118 330 Z" fill="#17191f"/><path d="M120 322 L204 322 M120 326 L204 326" stroke="#101216" stroke-width="1"/>
              <path d="M176 280 L206 280 L205 318 L172 318 Z" fill="#191c23"/><path d="M176 280 L206 280" stroke="#2c303a" stroke-width="2"/><path d="M178 284 L204 284" stroke="#23262e" stroke-width="1" stroke-dasharray="3 3"/>
              <path d="M196 186 C204 220 206 270 204 330" stroke="#2c303a" stroke-width="2" fill="none"/>
              <rect x="196" y="190" width="5" height="11" rx="2" fill="#6d7688"/>
              <path d="M150 234 C156 260 160 290 158 316" stroke="#15181e" stroke-width="1.6" fill="none"/>
              <!-- strap over the shoulder with a buckle -->
              <path d="M140 172 C156 170 170 192 172 230 L162 232 C160 200 150 186 136 184 Z" fill="#15181e"/>
              <rect x="160" y="214" width="14" height="9" rx="2" fill="#3a3f4c"/>
              <!-- hood bunched at the back -->
              <path d="M116 176 C112 152 136 140 158 146 C150 156 140 168 136 190 Z" fill="#23262f"/>
              <path d="M122 170 C124 158 136 150 148 150" stroke="#2f333e" stroke-width="2" fill="none"/>
              <!-- drawstrings -->
              <path id="${p}-cord1" d="M190 172 C192 190 190 206 192 220" stroke="#8a90a0" stroke-width="1.8" fill="none"/>
              <path id="${p}-cord2" d="M198 170 C201 188 200 202 203 214" stroke="#7a8090" stroke-width="1.8" fill="none"/>
              <rect x="190.5" y="219" width="3" height="6" rx="1" fill="#b8bfcc"/><rect x="201.5" y="213" width="3" height="6" rx="1" fill="#b8bfcc"/>
              <g id="${p}-head">
                <path d="M136 124 L206 120 C208 128 210 134 214 140 C216 143 214 146 210 147 C210 152 208 158 204 160 C200 168 190 172 176 172 C158 172 142 162 136 150 Z" fill="#5a3f2e"/>
                <!-- neck gaiter pulled over nose and mouth -->
                <path d="M148 140 L214 142 C214 156 206 168 194 174 C180 180 158 178 146 168 Z" fill="#101216"/>
                <path d="M152 150 L210 152 M156 160 L204 162" stroke="#1d2027" stroke-width="2"/>
                <path d="M200 143 C206 146 210 152 210 158" stroke="#262a33" stroke-width="1.6" fill="none"/>
                <!-- eye, visible between beanie and gaiter -->
                <path d="M184 131 Q193 125.5 203 130.5 Q194 135.5 184 131 Z" fill="#d9d3c9"/>
                <circle cx="195.5" cy="130.6" r="3.1" fill="#2a1a10"/><circle cx="196" cy="130.6" r="1.5" fill="#0a0706"/><circle cx="197" cy="129.4" r=".9" fill="#fff"/>
                <path d="M183.5 130.8 Q193 124.8 203.5 130" stroke="#120d0a" stroke-width="2" fill="none" stroke-linecap="round"/>
                <path d="M182 124 Q193 119.5 205 123" stroke="#1a120d" stroke-width="3" fill="none" stroke-linecap="round"/>
                <!-- beanie with ribbed fold -->
                <path d="M132 118 C130 88 152 70 176 72 C198 74 212 92 210 116 L132 122 Z" fill="#16181d"/>
                <path d="M150 80 C162 74 178 74 190 80 C176 80 162 84 152 92 Z" fill="#23262e"/>
                <path d="M130 110 L211 106 L212 124 L131 128 Z" fill="#1d2027"/>
                <path d="M140 112 L141 126 M152 111 L153 126 M164 110 L165 125 M176 109 L177 124 M188 109 L189 124 M200 108 L201 123" stroke="#15171c" stroke-width="2"/>
                <path id="${p}-faceLit" d="M204 122 C208 128 210 134 214 140 C216 143 214 146 210 147 L206 146 C208 138 206 130 202 124 Z" fill="#e8a45a" opacity="0"/>
              </g>
            </g>
            <g id="${p}-nearLegRoot" transform="translate(166 330)">${leg("near", pants, "#262a33", true)}</g>
            <g id="${p}-torsoB">
              <g id="${p}-nearArmRoot" transform="translate(168 190)">${arm("near", "#1e2129", "#2e323d", true)}</g>
            </g>
          </g>`;
        }
        // pose: {x,y,s,dir,lean,bob,head,nArm,nFore,fArm,fFore,nThigh,nShin,fThigh,fShin}
        function thiefApply(p, P) {
          const g = (id) => document.getElementById(p + id);
          setA(g(""), "transform", `translate(${f1(P.x)} ${f1(P.y)}) scale(${f2(P.s * P.dir)} ${f2(P.s)}) translate(-160 -580)`);
          const tor = `rotate(${f1(P.lean)} 160 330) translate(0 ${f1(P.bob)})`;
          setA(g("-torsoA"), "transform", tor);
          setA(g("-torsoB"), "transform", tor);
          setA(g("-head"), "transform", `rotate(${f1(P.head)} 166 164)`);
          setA(g("-nearArm"), "transform", `rotate(${f1(P.nArm)})`);
          setA(g("-nearFore"), "transform", `translate(0 92) rotate(${f1(P.nFore)})`);
          setA(g("-farArm"), "transform", `rotate(${f1(P.fArm)})`);
          setA(g("-farFore"), "transform", `translate(0 92) rotate(${f1(P.fFore)})`);
          setA(g("-nearThigh"), "transform", `rotate(${f1(P.nThigh)})`);
          setA(g("-nearShin"), "transform", `translate(0 120) rotate(${f1(P.nShin)})`);
          setA(g("-farThigh"), "transform", `rotate(${f1(P.fThigh)})`);
          setA(g("-farShin"), "transform", `translate(0 120) rotate(${f1(P.fShin)})`);
          setA(g("-faceLit"), "opacity", f2(P.faceLit || 0));
          const sw = P.cord || 0;
          setA(g("-cord1"), "transform", `rotate(${f1(sw)} 190 172)`);
          setA(g("-cord2"), "transform", `rotate(${f1(sw * 0.8)} 198 170)`);
        }
        function thiefArmMatrix(P, uptoFore) {
          const root = M.chain(M.t(P.x, P.y), M.s(P.s * P.dir, P.s), M.t(-160, -580));
          const tor = M.chain(M.t(160, 330), M.r(P.lean), M.t(-160, -330), M.t(0, P.bob));
          const armRoot = M.t(168, 190);
          const parent = M.chain(root, tor, armRoot);
          if (!uptoFore) return parent;
          return M.chain(parent, M.r(P.nArm), M.t(0, 92), M.r(P.nFore));
        }
        function aimArm(P, tx, ty, bend) {
          const parent = thiefArmMatrix(P, false);
          const loc = M.ap(M.inv(parent), tx, ty);
          P.nArm = (Math.atan2(-loc[0], loc[1]) * 180) / Math.PI - bend * 0.5;
          P.nFore = bend;
        }
        function walkPose(P, phase, amp, sneak) {
          const s = Math.sin(phase),
            c = Math.cos(phase);
          const stance = 9 * (1 - clamp(amp / 10, 0, 1));
          P.nThigh = -amp * s - sneak * 14 - stance;
          P.fThigh = amp * s - sneak * 14 + stance;
          P.nShin = sneak * 16 + Math.max(0, -c) * amp * 1.3 + Math.max(0, s) * 6;
          P.fShin = sneak * 16 + Math.max(0, c) * amp * 1.3 + Math.max(0, -s) * 6;
          P.bob = -Math.abs(c) * 5 * (amp / 24) + sneak * 12;
          P.fArm = -amp * 0.6 * s + 8;
          P.fFore = -22;
          P.nArm = amp * 0.5 * s - 10;
          P.nFore = -24 - Math.max(0, s) * 10;
          P.cord = -amp * 0.35 * c;
        }
        const baseThief = () => ({ x: 0, y: 0, s: 1, dir: 1, lean: 0, bob: 0, head: 0, nArm: 0, nFore: -10, fArm: 6, fFore: -20, nThigh: 0, nShin: 0, fThigh: 0, fShin: 0, faceLit: 0, cord: 0 });

        function artNear() {
          return `<svg width="1920" height="1080" viewBox="0 0 1920 1080">
            <defs>${guardDefs("ng")}
              <radialGradient id="ng-lensg"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".4" stop-color="#dfe9ff" stop-opacity=".45"/><stop offset="1" stop-color="#dfe9ff" stop-opacity="0"/></radialGradient>
              <radialGradient id="ng-pool"><stop offset="0" stop-color="#d9e4fa" stop-opacity=".22"/><stop offset="1" stop-color="#d9e4fa" stop-opacity="0"/></radialGradient>
              <radialGradient id="ng-shadow"><stop offset="0" stop-color="#02040a" stop-opacity=".7"/><stop offset="1" stop-color="#02040a" stop-opacity="0"/></radialGradient>
              <linearGradient id="ng-streak" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#dfe9ff" stop-opacity="0"/><stop offset=".5" stop-color="#f6f9ff" stop-opacity=".9"/><stop offset="1" stop-color="#dfe9ff" stop-opacity="0"/></linearGradient>
            </defs>
            <rect x="-1400" y="962" width="4600" height="900" fill="#090e19"/>
            <rect x="-1400" y="962" width="4600" height="3" fill="#161e31"/>
            <ellipse cx="330" cy="982" rx="260" ry="26" fill="url(#ng-pool)"/>
            <ellipse cx="190" cy="978" rx="140" ry="14" fill="url(#ng-shadow)"/>
            <g id="ng-post" transform="translate(126 642) scale(0.62)">
              ${guardSide("ng", { booth: true, pen: true })}
              ${guardDesk("ng")}
            </g>
            <circle id="ng-lensglow" cx="0" cy="0" r="46" fill="url(#ng-lensg)" opacity="0" style="mix-blend-mode:screen"/>
            <ellipse id="ng-streak" cx="0" cy="0" rx="300" ry="2.4" fill="url(#ng-streak)" opacity="0" style="mix-blend-mode:screen"/>
          </svg>`;
        }

        /* extreme foreground: a branch for the crane-down, a fence at the bottom right (blurred by CSS) */
        function artFg() {
          const r = mulberry32(41);
          let leaves = "";
          for (let i = 0; i < 70; i++) {
            const t = r();
            const x = -300 + t * 900 + (r() - 0.5) * 80,
              y = -1330 + t * 260 + (r() - 0.5) * 140;
            const a = r() * 180;
            leaves += `<ellipse cx="${f1(x)}" cy="${f1(y)}" rx="${f1(16 + r() * 16)}" ry="${f1(7 + r() * 6)}" transform="rotate(${f1(a)} ${f1(x)} ${f1(y)})" fill="#04070e"/>`;
          }
          let fence = "";
          for (let i = 0; i < 26; i++) fence += `<path d="M${1180 + i * 34} 880 L${1180 + i * 34 + 120} 1100 M${1180 + i * 34 + 120} 880 L${1180 + i * 34} 1100" stroke="#0a0f1b" stroke-width="2.4"/>`;
          return `<svg width="1920" height="1080" viewBox="0 0 1920 1080">
            <path d="M-400 -1150 C-100 -1210 200 -1250 620 -1330" stroke="#04070e" stroke-width="26" fill="none" stroke-linecap="round"/>
            <path d="M120 -1236 C180 -1180 240 -1140 330 -1120 M300 -1270 C340 -1320 400 -1350 470 -1360" stroke="#04070e" stroke-width="10" fill="none" stroke-linecap="round"/>
            ${leaves}
            <g opacity=".95">${fence}<rect x="1160" y="874" width="1000" height="8" fill="#0a0f1b"/><rect x="1150" y="860" width="14" height="260" fill="#070b15"/><rect x="1800" y="860" width="14" height="260" fill="#070b15"/></g>
          </svg>`;
        }

        function artRoom() {
          const room = (lit) => {
            const P = lit
              ? { wall: "#6b5034", wall2: "#5c432b", floor: "#4a3622", floorLine: "#5d4530", furn: "#7a6048", furnTop: "#b58a58", furnDk: "#4f3b28", metal: "#8a7258", metalDk: "#5f4c39", screen: "#2a2016", frame: "#9c7a52", paper: "#f3dcb4" }
              : { wall: "#121a2a", wall2: "#0f1624", floor: "#0c111d", floorLine: "#121a29", furn: "#18202f", furnTop: "#232d42", furnDk: "#10161f", metal: "#1b2436", metalDk: "#131a28", screen: "#0a0e17", frame: "#222c42", paper: "#2c3547" };
            let s = `<rect x="-200" y="-100" width="2320" height="830" fill="${P.wall}"/>`;
            s += `<rect x="-200" y="-100" width="2320" height="190" fill="${P.wall2}"/>`;
            for (let i = 0; i < 14; i++) s += `<rect x="${-200 + i * 170}" y="90" width="1" height="626" fill="${lit ? "#7a5c3c" : "#141d2e"}"/>`;
            s += `<rect x="-200" y="720" width="2320" height="500" fill="${P.floor}"/>`;
            for (let i = 0; i < 12; i++) s += `<path d="M${-200 + i * 220} 720 L${-600 + i * 300} 1200" stroke="${P.floorLine}" stroke-width="3"/>`;
            s += `<rect x="-200" y="716" width="2320" height="8" fill="${P.furnDk}"/>`;
            s += `<rect x="752" y="162" width="476" height="406" fill="${P.frame}"/>`;
            s += `<rect x="372" y="214" width="272" height="182" fill="${P.frame}"/><rect x="382" y="224" width="252" height="162" fill="${lit ? "#cdb28a" : "#171f30"}"/>`;
            if (lit) s += `<path d="M404 262 L560 262 M404 292 L520 292 M404 322 L590 322 M404 352 L480 352" stroke="#7a5d3b" stroke-width="5" stroke-linecap="round"/><rect x="590" y="236" width="30" height="22" fill="#e9c98e"/>`;
            s += `<circle cx="1330" cy="262" r="42" fill="${P.frame}"/><circle cx="1330" cy="262" r="34" fill="${lit ? "#e9d2aa" : "#161e2f"}"/><path d="M1330 262 L1330 238 M1330 262 L1346 270" stroke="${P.furnDk}" stroke-width="4" stroke-linecap="round"/>`;
            s += `<rect x="150" y="330" width="182" height="400" fill="${P.metal}"/><rect x="150" y="330" width="182" height="8" fill="${P.furnTop}"/>`;
            for (let i = 0; i < 4; i++) s += `<rect x="162" y="${346 + i * 96}" width="158" height="86" fill="${P.metalDk}"/><rect x="220" y="${382 + i * 96}" width="42" height="9" rx="3" fill="${P.furnTop}"/><rect x="226" y="${364 + i * 96}" width="30" height="12" fill="${lit ? "#efd7ad" : "#1d2537"}"/>`;
            s += `<rect x="186" y="300" width="60" height="30" fill="${P.furnDk}"/><rect x="250" y="310" width="40" height="20" fill="${P.furn}"/>`;
            s += `<rect x="380" y="606" width="352" height="16" fill="${P.furnTop}"/><rect x="392" y="622" width="330" height="96" fill="${P.furn}"/><rect x="392" y="622" width="120" height="96" fill="${P.furnDk}"/>`;
            s += `<rect x="468" y="470" width="160" height="112" rx="5" fill="${P.furnDk}"/><rect x="476" y="478" width="144" height="96" fill="${P.screen}"/><rect x="540" y="582" width="16" height="24" fill="${P.furnDk}"/><rect x="510" y="600" width="76" height="7" rx="3" fill="${P.furnDk}"/>`;
            s += `<rect x="640" y="590" width="70" height="16" rx="2" fill="${P.paper}" opacity="${lit ? 1 : 0.6}"/><rect x="420" y="594" width="40" height="12" rx="2" fill="${P.furnDk}"/>`;
            s += `<rect x="600" y="556" width="96" height="116" rx="12" fill="${P.furnDk}"/><rect x="590" y="664" width="120" height="20" rx="8" fill="${P.furn}"/><rect x="644" y="684" width="12" height="60" fill="${P.furnDk}"/><rect x="602" y="740" width="96" height="8" rx="4" fill="${P.furnDk}"/>`;
            s += `<rect x="1250" y="638" width="290" height="16" fill="${P.furnTop}"/><rect x="1262" y="654" width="266" height="70" fill="${P.furn}"/><rect x="1400" y="664" width="110" height="46" fill="${P.furnDk}"/><rect x="1440" y="684" width="30" height="5" rx="2" fill="${P.furnTop}"/>`;
            s += `<rect x="1396" y="566" width="62" height="72" fill="${P.frame}"/><rect x="1403" y="573" width="48" height="58" fill="${lit ? "#8fa0b6" : "#141b29"}"/>`;
            s += `<rect x="1284" y="620" width="84" height="18" rx="3" fill="${P.furnDk}"/>`;
            s += `<path d="M1584 760 L1620 760 L1614 700 L1590 700 Z" fill="${P.furnDk}"/><path d="M1602 700 C1580 660 1560 640 1570 610 C1590 630 1600 660 1602 700 C1606 650 1620 620 1640 606 C1640 640 1624 670 1602 700" fill="${lit ? "#7c7a3e" : "#131b22"}"/>`;
            s += `<rect x="1654" y="176" width="232" height="554" fill="${P.frame}"/><rect x="1666" y="188" width="208" height="542" fill="${P.furn}"/><circle cx="1690" cy="470" r="9" fill="${P.furnTop}"/>`;
            s += `<rect x="1712" y="330" width="112" height="56" rx="6" fill="${lit ? "#e9d2aa" : "#1c2438"}"/>`;
            if (!lit) s += `<text x="1768" y="370" text-anchor="middle" font-family="JetBrains Mono, monospace" font-weight="700" font-size="34" fill="#8e98b6">10</text>`;
            return s;
          };
          const r = mulberry32(5);
          let motes = "";
          for (let i = 0; i < 52; i++) motes += `<circle class="mote" r="${f2(0.9 + r() * 1.9)}" cx="0" cy="0" fill="#ffe7b8" opacity="0"/>`;
          let coolMotes = "";
          for (let i = 0; i < 26; i++) coolMotes += `<circle class="cmote" r="${f2(0.8 + r() * 1.3)}" cx="0" cy="0" fill="#cfe0ff" opacity="0"/>`;
          let stripes = "",
            shafts = "";
          for (let i = 0; i < 6; i++) {
            const x = 780 + i * 70;
            stripes += `<polygon points="${pts([[x, 730], [x + 40, 730], [x - 170 + 40, 1080], [x - 230 + 40, 1080]])}" fill="#8ea6d6" opacity=".08"/>`;
            shafts += `<polygon points="${pts([[x + 10, 380], [x + 44, 380], [x - 140, 900], [x - 196, 900]])}" fill="url(#rm-shaftg)"/>`;
          }
          return `<svg width="1920" height="1080" viewBox="0 0 1920 1080">
            <defs>
              <radialGradient id="rm-mg"><stop offset="0" stop-color="#fff"/><stop offset=".45" stop-color="#fff" stop-opacity=".85"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
              <linearGradient id="rm-mcg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity=".15"/></linearGradient>
              <linearGradient id="rm-coneg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff1c9" stop-opacity=".66"/><stop offset=".35" stop-color="#ffd48a" stop-opacity=".24"/><stop offset="1" stop-color="#f0a84a" stop-opacity=".05"/></linearGradient>
              <linearGradient id="rm-shaftg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a9bfe8" stop-opacity=".12"/><stop offset="1" stop-color="#a9bfe8" stop-opacity="0"/></linearGradient>
              <radialGradient id="rm-hotg"><stop offset="0" stop-color="#fff6dc" stop-opacity=".9"/><stop offset=".3" stop-color="#ffd690" stop-opacity=".5"/><stop offset="1" stop-color="#e59a3c" stop-opacity="0"/></radialGradient>
              <radialGradient id="rm-lensg"><stop offset="0" stop-color="#fffaf0"/><stop offset=".3" stop-color="#ffe2a0" stop-opacity=".8"/><stop offset="1" stop-color="#f5b04a" stop-opacity="0"/></radialGradient>
              <radialGradient id="rm-guardg"><stop offset="0" stop-color="#e8f0ff" stop-opacity=".9"/><stop offset="1" stop-color="#e8f0ff" stop-opacity="0"/></radialGradient>
              <radialGradient id="rm-ambg"><stop offset="0" stop-color="#ffb866" stop-opacity=".16"/><stop offset="1" stop-color="#ffb866" stop-opacity="0"/></radialGradient>
              <radialGradient id="rm-spillg"><stop offset="0" stop-color="#fff"/><stop offset=".5" stop-color="#fff" stop-opacity=".45"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
              <linearGradient id="rm-flare" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffe0a8" stop-opacity="0"/><stop offset=".5" stop-color="#fff4dc" stop-opacity=".9"/><stop offset="1" stop-color="#ffe0a8" stop-opacity="0"/></linearGradient>
              <linearGradient id="rm-skyg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1a2747"/><stop offset="1" stop-color="#0e1629"/></linearGradient>
              <filter id="rm-soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="7"/></filter>
              <filter id="rm-msoft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="18"/></filter>
              <filter id="rm-shblur" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="5"/></filter>
              <filter id="rm-warmF" x="-10%" y="-10%" width="120%" height="120%"><feFlood flood-color="#ffb35a"/><feComposite in2="SourceAlpha" operator="in"/></filter>
              <mask id="rm-mask" maskUnits="userSpaceOnUse" x="-400" y="-400" width="2800" height="2000">
                <polygon id="rm-mcone" points="0,0 0,0 0,0" fill="url(#rm-mcg)" filter="url(#rm-msoft)"/>
                <ellipse id="rm-mspot" cx="0" cy="0" rx="190" ry="160" fill="url(#rm-mg)"/>
              </mask>
              <mask id="rm-spillMask" maskUnits="userSpaceOnUse" x="-400" y="-400" width="2800" height="2000">
                <ellipse id="rm-spillSpot" cx="0" cy="0" rx="230" ry="260" fill="url(#rm-spillg)"/>
              </mask>
            </defs>
            <g id="rm-dark">${room(false)}</g>
            <g id="rm-window">
              <rect x="764" y="174" width="452" height="382" fill="url(#rm-skyg)"/>
              <path d="M764 470 Q820 440 880 462 Q940 430 1000 458 Q1070 432 1130 456 Q1180 440 1216 452 L1216 556 L764 556 Z" fill="#0a101f"/>
              <circle cx="962" cy="497" r="30" fill="url(#rm-guardg)" opacity=".55"/><circle cx="962" cy="497" r="3.2" fill="#f2f6ff"/>
              <polygon id="rm-outbeam" points="962,497 1216,300 1216,360" fill="#dfe9ff" opacity="0"/>
              ${Array.from({ length: 11 }, (_, i) => `<rect x="764" y="${178 + i * 20}" width="452" height="9" fill="#243050"/>`).join("")}
              <rect x="986" y="174" width="8" height="382" fill="#222c42"/>
            </g>
            <g id="rm-moon">${stripes}</g>
            <g id="rm-shafts" style="mix-blend-mode:screen">${shafts}</g>
            <g id="rm-cmotes" style="mix-blend-mode:screen">${coolMotes}</g>
            <g id="rm-lit" mask="url(#rm-mask)" opacity="0">${room(true)}
              <g fill="#1b1209" opacity=".62" filter="url(#rm-shblur)">
                <rect id="rm-sh-mon" x="468" y="470" width="160" height="112" rx="5"/>
                <rect id="rm-sh-chair" x="600" y="556" width="96" height="116" rx="12"/>
                <rect id="rm-sh-frame" x="1396" y="566" width="62" height="72"/>
              </g>
            </g>
            <rect x="-200" y="-100" width="2320" height="1300" fill="url(#rm-ambg)" id="rm-amb" opacity="0" style="mix-blend-mode:screen"/>
            <ellipse id="rm-hot" cx="0" cy="0" rx="120" ry="100" fill="url(#rm-hotg)" opacity="0" style="mix-blend-mode:screen"/>
            <g id="rm-thiefWrap">${thiefSVG("rt")}</g>
            <use id="rm-spill" href="#rt" filter="url(#rm-warmF)" mask="url(#rm-spillMask)" opacity="0"/>
            <polygon id="rm-cone" points="0,0 0,0 0,0" fill="url(#rm-coneg)" filter="url(#rm-soft)" opacity="0" style="mix-blend-mode:screen"/>
            <g id="rm-motes" style="mix-blend-mode:screen">${motes}</g>
            <circle id="rm-lensglow" cx="0" cy="0" r="46" fill="url(#rm-lensg)" opacity="0" style="mix-blend-mode:screen"/>
            <ellipse id="rm-flareline" cx="0" cy="0" rx="340" ry="2.6" fill="url(#rm-flare)" opacity="0" style="mix-blend-mode:screen"/>
            <g id="rm-glints" fill="#fff8e6">
              <path class="glint" data-x="547" data-y="524" d="M0 -26 L4 -4 L26 0 L4 4 L0 26 L-4 4 L-26 0 L-4 -4 Z" opacity="0"/>
              <path class="glint" data-x="1428" data-y="598" d="M0 -22 L3.5 -3.5 L22 0 L3.5 3.5 L0 22 L-3.5 3.5 L-22 0 L-3.5 -3.5 Z" opacity="0"/>
              <path class="glint" data-x="905" data-y="262" d="M0 -30 L4 -4 L30 0 L4 4 L0 30 L-4 4 L-30 0 L-4 -4 Z" opacity="0"/>
            </g>
          </svg>`;
        }

        /* the side wall, tracked: wall + door in #dr-wall, near props in #dr-fg (parallax) */
        function artDoor() {
          const r = mulberry32(31);
          let panels = "";
          for (let i = 0; i < 18; i++) panels += `<rect x="${-900 + i * 240}" y="0" width="236" height="860" fill="${i % 2 ? "#161e30" : "#172033"}"/><rect x="${-900 + i * 240 + 236}" y="0" width="4" height="860" fill="#0f1524"/>`;
          for (let j = 0; j < 4; j++) panels += `<rect x="-900" y="${200 + j * 200}" width="4400" height="3" fill="#10172a"/>`;
          let grime = "";
          for (let i = 0; i < 16; i++) grime += `<rect x="${f1(-800 + r() * 4000)}" y="${f1(40 + r() * 500)}" width="${f1(20 + r() * 50)}" height="${f1(120 + r() * 300)}" fill="url(#dr-grime)"/>`;
          let puddles = "";
          for (let i = 0; i < 6; i++) puddles += `<ellipse cx="${f1(-200 + r() * 2600)}" cy="${f1(930 + r() * 110)}" rx="${f1(90 + r() * 140)}" ry="${f1(10 + r() * 12)}" fill="#131b2e"/>`;
          return `<svg width="1920" height="1080" viewBox="0 0 1920 1080">
            <defs>
              <radialGradient id="dr-halo"><stop offset="0" stop-color="#e0e9fb" stop-opacity=".6"/><stop offset="1" stop-color="#e0e9fb" stop-opacity="0"/></radialGradient>
              <linearGradient id="dr-cone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#dfe8fa" stop-opacity=".24"/><stop offset="1" stop-color="#dfe8fa" stop-opacity="0"/></linearGradient>
              <radialGradient id="dr-refl"><stop offset="0" stop-color="#cfdcf5" stop-opacity=".38"/><stop offset="1" stop-color="#cfdcf5" stop-opacity="0"/></radialGradient>
              <linearGradient id="dr-grime" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a0f1c" stop-opacity=".35"/><stop offset="1" stop-color="#0a0f1c" stop-opacity="0"/></linearGradient>
              <linearGradient id="dr-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#101a33"/><stop offset="1" stop-color="#0b1224"/></linearGradient>
              <linearGradient id="dr-streak" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#dfe9ff" stop-opacity="0"/><stop offset=".5" stop-color="#f3f7ff" stop-opacity=".8"/><stop offset="1" stop-color="#dfe9ff" stop-opacity="0"/></linearGradient>
              <filter id="dr-shadowF" x="-20%" y="-20%" width="140%" height="140%"><feFlood flood-color="#02040a"/><feComposite in2="SourceAlpha" operator="in"/><feGaussianBlur stdDeviation="7"/></filter>
              <filter id="dr-reflF" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3.5"/></filter>
              <clipPath id="dr-groundClip"><rect x="-2000" y="868" width="6000" height="400"/></clipPath>
            </defs>
            <rect x="-300" y="-200" width="2600" height="1500" fill="url(#dr-sky)"/>
            <g id="dr-world">
            <g id="dr-wall">
              <g>${panels}</g>${grime}
              <rect x="-2000" y="860" width="6000" height="400" fill="#0a0f1b"/><rect x="-2000" y="860" width="6000" height="5" fill="#1b2438"/>
              ${puddles}
              <ellipse cx="1296" cy="952" rx="190" ry="17" fill="url(#dr-refl)"/>
              <rect x="880" y="0" width="12" height="860" fill="#0f1524"/><rect x="872" y="840" width="28" height="20" fill="#0f1524"/>
              <rect x="560" y="120" width="10" height="740" fill="#0e1422"/><rect x="540" y="560" width="50" height="70" rx="3" fill="#1b2336"/><rect x="546" y="568" width="38" height="12" fill="#0b101b"/><path d="M565 630 L565 860" stroke="#0e1422" stroke-width="4"/>
              <path d="M-900 150 L3400 150" stroke="#0c1220" stroke-width="3"/>
              <polygon points="1238,448 1354,448 1480,860 1112,860" fill="url(#dr-cone)"/>
              <rect x="1172" y="470" width="252" height="394" fill="#0b0f19"/>
              <rect id="dr-gap" x="1180" y="478" width="236" height="382" fill="#020308"/>
              <g id="dr-leaf">
                <rect x="1180" y="478" width="236" height="382" fill="#202a41"/>
                <rect x="1180" y="478" width="236" height="4" fill="#3a4768"/>
                <rect x="1224" y="524" width="70" height="92" fill="#0e1524"/><path d="M1224 524 L1294 616 M1294 524 L1224 616" stroke="#26314c" stroke-width="2"/>
                <rect x="1196" y="672" width="204" height="16" rx="6" fill="#2e3955"/><rect x="1196" y="672" width="204" height="4" rx="2" fill="#4a5780"/>
                <rect x="1392" y="640" width="14" height="60" rx="5" fill="#141b2c"/>
              </g>
              <rect x="1240" y="386" width="112" height="30" rx="4" fill="#1b2336"/><text x="1296" y="408" text-anchor="middle" font-family="Archivo, sans-serif" font-weight="800" font-size="16" letter-spacing="3" fill="#8e9bbb">FIRE EXIT</text>
              <rect x="1266" y="424" width="60" height="24" rx="6" fill="#1b2336"/><rect x="1276" y="444" width="40" height="8" rx="3" fill="#e9f0ff"/>
              <circle cx="1296" cy="450" r="150" fill="url(#dr-halo)"/>
              <ellipse cx="1296" cy="450" rx="340" ry="2.4" fill="url(#dr-streak)" style="mix-blend-mode:screen"/>
            </g>
            <use id="dr-shadow" href="#dt" filter="url(#dr-shadowF)" opacity="0"/>
            <g clip-path="url(#dr-groundClip)"><use id="dr-refl" href="#dt" filter="url(#dr-reflF)" opacity=".2"/></g>
            <g id="dr-thiefWrap">${thiefSVG("dt")}</g>
            </g>
            <g id="dr-fg">
              <rect x="1640" y="-40" width="34" height="1200" fill="#070b14"/><rect x="1640" y="-40" width="6" height="1200" fill="#141c2e"/>
              <rect x="1600" y="300" width="120" height="16" fill="#070b14"/><rect x="1600" y="760" width="120" height="16" fill="#070b14"/>
              <rect x="-420" y="700" width="380" height="190" rx="8" fill="#0a101c"/><rect x="-440" y="690" width="420" height="16" rx="4" fill="#111829"/>
              <rect x="-400" y="720" width="340" height="3" fill="#18203a"/>
              <rect x="2600" y="760" width="160" height="120" rx="6" fill="#0a101c"/>
            </g>
          </svg>`;
        }

        function artReact() {
          let wins = "";
          const cols = [1215, 1405, 1595, 1785],
            rows = [-12, 113, 238, 363];
          for (let rI = 0; rI < 4; rI++)
            for (let c = 0; c < 4; c++) wins += `<rect x="${cols[c]}" y="${rows[rI]}" width="150" height="84" fill="#0a0f1d"/><rect x="${cols[c] - 4}" y="${rows[rI] - 4}" width="158" height="92" fill="none" stroke="#2b3553" stroke-width="6"/>`;
          return `<svg width="1920" height="1080" viewBox="0 0 1920 1080">
            <defs>${guardDefs("rg")}
              <radialGradient id="rc-sky" gradientUnits="userSpaceOnUse" cx="300" cy="100" r="1600"><stop offset="0" stop-color="#1e2d55"/><stop offset=".6" stop-color="#0d152b"/><stop offset="1" stop-color="#070b16"/></radialGradient>
              <radialGradient id="rc-warm"><stop offset="0" stop-color="#ffe0a0" stop-opacity=".95"/><stop offset=".35" stop-color="#f5a845" stop-opacity=".6"/><stop offset="1" stop-color="#c8701c" stop-opacity="0"/></radialGradient>
              <radialGradient id="rc-face"><stop offset="0" stop-color="#dfe9ff" stop-opacity=".32"/><stop offset="1" stop-color="#dfe9ff" stop-opacity="0"/></radialGradient>
              <radialGradient id="rc-bokeh"><stop offset="0" stop-color="#dfe9ff" stop-opacity=".55"/><stop offset=".7" stop-color="#dfe9ff" stop-opacity=".25"/><stop offset="1" stop-color="#dfe9ff" stop-opacity="0"/></radialGradient>
              <linearGradient id="rc-fog" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#26365e" stop-opacity="0"/><stop offset=".5" stop-color="#26365e" stop-opacity=".5"/><stop offset="1" stop-color="#26365e" stop-opacity="0"/></linearGradient>
            </defs>
            <g id="rc-bg">
              <rect x="-200" y="-200" width="2400" height="1500" fill="url(#rc-sky)"/>
              <g transform="matrix(1 -0.06 0 1 0 90)">
                <rect x="1170" y="-80" width="820" height="620" fill="#1a2236"/>
                <rect x="1170" y="90" width="820" height="16" fill="#212b43"/><rect x="1170" y="214" width="820" height="16" fill="#212b43"/><rect x="1170" y="340" width="820" height="16" fill="#212b43"/>
                ${wins}
                <ellipse id="rc-glow" cx="1555" cy="322" rx="130" ry="92" fill="url(#rc-warm)" opacity="0"/>
              </g>
              <rect x="-200" y="560" width="2400" height="700" fill="#0b111f"/>
              <rect x="-200" y="470" width="2400" height="200" fill="url(#rc-fog)"/>
              <circle cx="300" cy="120" r="34" fill="#e8eef9" opacity=".8"/>
              <circle cx="980" cy="430" r="46" fill="url(#rc-bokeh)"/><circle cx="1090" cy="470" r="30" fill="url(#rc-bokeh)" opacity=".6"/>
            </g>
            <g id="rc-fg">
              <g transform="translate(360 150) scale(1.5)">
                ${guardSide("rg", { pen: true })}
                ${guardDesk("rg")}
              </g>
              <ellipse cx="700" cy="330" rx="260" ry="220" fill="url(#rc-face)" style="mix-blend-mode:screen"/>
            </g>
            <g id="rc-near">
              <path d="M1600 1200 L1620 870 C1624 840 1700 830 1760 836 C1820 842 1840 860 1842 890 L1860 1200 Z" fill="#0b101c"/>
              <path d="M1624 868 C1650 850 1740 846 1800 856" stroke="#3a4668" stroke-width="5" fill="none"/>
              <path d="M1842 900 C1900 900 1920 960 1880 1000" stroke="#0b101c" stroke-width="18" fill="none"/>
            </g>
          </svg>`;
        }

        /* insert: extreme close-up of the gloved thumb on the torch switch */
        function artInsert() {
          let knurl = "";
          for (let i = 0; i < 44; i++) knurl += `<path d="M${260 + i * 14} 470 L${248 + i * 14} 610" stroke="#5c6576" stroke-width="3"/>`;
          const r = mulberry32(55);
          let bok = "";
          for (let i = 0; i < 9; i++) bok += `<circle cx="${f1(100 + r() * 1700)}" cy="${f1(80 + r() * 300)}" r="${f1(30 + r() * 70)}" fill="url(#in-bokeh)" opacity="${f2(0.25 + r() * 0.4)}"/>`;
          return `<svg width="1920" height="1080" viewBox="0 0 1920 1080">
            <defs>
              <radialGradient id="in-bg" gradientUnits="userSpaceOnUse" cx="1100" cy="400" r="1300"><stop offset="0" stop-color="#1b2640"/><stop offset="1" stop-color="#05080f"/></radialGradient>
              <radialGradient id="in-bokeh"><stop offset="0" stop-color="#9fb4dd" stop-opacity=".35"/><stop offset=".8" stop-color="#9fb4dd" stop-opacity=".18"/><stop offset="1" stop-color="#9fb4dd" stop-opacity="0"/></radialGradient>
              <linearGradient id="in-metal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c7cfdd"/><stop offset=".3" stop-color="#8d97aa"/><stop offset=".75" stop-color="#4c5566"/><stop offset="1" stop-color="#2a303c"/></linearGradient>
              <radialGradient id="in-lens"><stop offset="0" stop-color="#fffdf6"/><stop offset=".25" stop-color="#ffe7b0"/><stop offset=".6" stop-color="#f5b04a" stop-opacity=".6"/><stop offset="1" stop-color="#f5b04a" stop-opacity="0"/></radialGradient>
              <linearGradient id="in-flare" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffe0a8" stop-opacity="0"/><stop offset=".5" stop-color="#fff7e6" stop-opacity=".95"/><stop offset="1" stop-color="#ffe0a8" stop-opacity="0"/></linearGradient>
              <linearGradient id="in-beam" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff0cc" stop-opacity=".7"/><stop offset="1" stop-color="#f5b04a" stop-opacity="0"/></linearGradient>
              <filter id="in-blur" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="18"/></filter>
            </defs>
            <rect x="-200" y="-200" width="2400" height="1500" fill="url(#in-bg)"/>
            <g filter="url(#in-blur)">${bok}</g>
            <g id="in-body">
              <rect x="-100" y="440" width="1420" height="200" rx="40" fill="url(#in-metal)"/>
              <g>${knurl}</g>
              <rect x="-100" y="452" width="1420" height="14" rx="7" fill="#e3e8f1" opacity=".5"/>
              <path d="M1300 400 L1500 360 L1500 720 L1300 680 Z" fill="url(#in-metal)"/>
              <rect x="1490" y="352" width="46" height="376" rx="12" fill="#3a4252"/>
              <ellipse id="in-lens" cx="1536" cy="540" rx="30" ry="172" fill="#262b35"/>
              <rect x="690" y="404" width="150" height="46" rx="18" fill="#15171c"/>
            </g>
            <g id="in-hand">
              <path d="M300 620 C360 740 620 780 900 760 C1040 750 1100 700 1080 640 L360 600 Z" fill="#0d0e11"/>
              <path d="M420 640 C430 700 470 730 520 740 M600 640 C610 706 650 736 700 744 M780 640 C790 700 830 728 880 732" stroke="#1d1f25" stroke-width="10" fill="none" stroke-linecap="round"/>
              <path d="M460 700 C520 720 560 730 600 732" stroke="#2a2d36" stroke-width="3" fill="none"/>
              <g id="in-thumb">
                <path d="M520 470 C560 380 720 350 830 380 C880 394 900 420 880 446 C850 470 760 470 700 468 C640 468 560 490 520 470 Z" fill="#101116"/>
                <path d="M560 420 C640 380 760 370 840 392" stroke="#3a3e4a" stroke-width="5" fill="none" stroke-linecap="round"/>
                <path d="M700 452 C740 446 800 446 850 440" stroke="#1d1f25" stroke-width="3" fill="none"/>
              </g>
              <path d="M300 620 C260 560 280 470 340 440 C400 420 470 440 520 470 L500 600 Z" fill="#0f1014"/>
            </g>
            <g id="in-light" opacity="0">
              <polygon points="1536,368 2400,-200 2400,1280 1536,712" fill="url(#in-beam)" style="mix-blend-mode:screen"/>
              <ellipse cx="1536" cy="540" rx="260" ry="260" fill="url(#in-lens)" style="mix-blend-mode:screen"/>
              <ellipse cx="1536" cy="540" rx="900" ry="5" fill="url(#in-flare)" style="mix-blend-mode:screen"/>
            </g>
          </svg>`;
        }

