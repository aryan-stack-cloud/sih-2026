# SVG Background Manifest

All assets use a `1920 × 1080` viewBox, the palette in `design.md`, flat vector surfaces, and no baked text.

| File | Description | Parallax groups | Animatable IDs | Empty zone |
|---|---|---|---|---|
| `night-sky.svg` | Indigo night sky, horizon glow, stars, colored dots, crescent moon, and layered city silhouette. | `night-sky-far`, `night-sky-mid`, `night-sky-near` | `sparkle-1`–`sparkle-8`, `moon` | None; used as a full-frame backdrop. |
| `night-building.svg` | Transparent four-storey office building with exact 4×4 searchlight window targets, street lamps, ground, and bushes. | `night-building-far`, `night-building-mid`, `night-building-near` | `win-1`–`win-16`, `win-1-dark`–`win-16-dark`, `win-1-lit`–`win-16-lit`, `lamp-glow-1`, `lamp-glow-2` | `x=80–640, y=420–1000`; no building, lamp, glow, or ground prop is placed there. |
| `control-room.svg` | Warm EW control room with wall screen, abstract side displays, desk, keyboards, monitor backs, chair, and ceiling lights. | `control-room-far`, `control-room-mid`, `control-room-near` | `cr-screen`, `side-monitor-left`, `side-monitor-right`, `keyboard`, `monitor-backs`, `office-chair` | `x=1350–1850, y=380–1080`; the engineer staging area remains free of foreground props. |
| `lab-wall.svg` | Pale equipment lab wall with edge shelves, test instruments, cable coils, plant, night window, and clock. | `lab-wall-far`, `lab-wall-mid`, `lab-wall-near` | `lab-clock-hand` (`data-pivot="1700 96"`), `lab-window` | `x=250–1350, y=150–1000`; kept clear for the whiteboard and engineer. |
| `desk-top.svg` | Top-down warm wooden desk with grain bands and edge-only stationery. | `desk-top-far`, `desk-top-mid`, `desk-top-near` | `binder-clip`, `pencil`, `sticky-note`, `coffee-ring-stain`, `paper-corner`, `smartphone` | `x=360–1560, y=140–940`; clear for the case file. |
| `casino-hall.svg` | Purple casino/arcade hall with wall panels, animated bokeh lamps, and patterned carpet. | `casino-hall-far`, `casino-hall-mid`, `casino-hall-near` | `casino-lights`, `casino-light-1`–`casino-light-23` | `x=200–1720, y=250–900`; free of slot machines or foreground props for later placement. |
| `exam-hall.svg` | Daylit classroom with empty chalkboard, windows, clock, and desks receding above the staging area. | `exam-hall-far`, `exam-hall-mid`, `exam-hall-near` | `exam-board`, `exam-clock-hand` (`data-pivot="980 78"`), `background-desk-rows` | `x=300–1620, y=540–1080`; clear for the hero desk and character. |
| `sunrise-sky.svg` | Dawn city backdrop built from flat color fields and soft radial glows, with sun, clouds, and purple skyline. | `sunrise-sky-far`, `sunrise-sky-mid`, `sunrise-sky-near` | `sunrise-sun`, `cloud-1`–`cloud-4` | None; used as a full-frame closing backdrop. |

## Night Building Window Contract

- Outer frame: `150 × 120`.
- Dark glass and lit overlay: `130 × 100`, inset by `10` pixels.
- Column starts: `760`, `960`, `1160`, `1360`.
- Row starts: `220`, `390`, `560`, `730`.
- IDs run left-to-right, top-to-bottom: `win-1` through `win-16`.
- `win-N-lit` starts at `opacity="0"` and overlays the matching dark-glass rectangle.
