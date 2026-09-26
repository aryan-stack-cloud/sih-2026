---
name: "Smart Scan: Night Watch (Infographics-Show style)"
canvas: { width: 1920, height: 1080, fps: 30, safe_margin: 80 }
colors:
  # night exterior
  sky_deep: "#1D1B4F"
  sky_mid: "#2B2A6E"
  sky_glow: "#3D3C8F"
  star: "#F7F4FF"
  dot_magenta: "#E0457B"
  dot_teal: "#2EC4B6"
  building_wall: "#3A3F7A"
  building_shadow: "#2C3066"
  building_trim: "#4B519A"
  window_dark: "#20224A"
  window_frame: "#5A62B5"
  window_lit: "#FFD166"
  beam: "#FFF3B0"
  torch_core: "#FFE066"
  torch_glow: "#FFB703"
  ground: "#252456"
  # interiors
  wall_beige: "#EFE3CF"
  wall_beige_dark: "#D9C7AA"
  floor_wood: "#B98B5E"
  desk_wood: "#8C5A3C"
  desk_top: "#A86F4C"
  screen_navy: "#16204A"
  screen_cyan: "#3DDCFF"
  # UI and meaning
  card: "#FDFCF8"
  ink: "#1F2340"
  label_grey: "#6B7090"
  accent_yellow: "#FFC43D"   # where the receiver looks / highlights / arrows
  hit_green: "#2DB86B"       # caught signal
  miss_red: "#E63946"        # missed signal
  info_blue: "#3A86FF"
  # characters
  skin_guard: "#C68A5E"
  skin_guard_shade: "#A9714A"
  skin_engineer: "#A86B45"
  skin_engineer_shade: "#8D5636"
  uniform_navy: "#2D3A6B"
  uniform_shade: "#232E57"
  cap_navy: "#26325C"
  badge_gold: "#F2B632"
  labcoat: "#F4F6FA"
  labcoat_shade: "#D8DEEA"
  shirt_teal: "#1F9E89"
  hair_dark: "#1E1A1A"
  intruder: "#15142E"
  # dawn (closing scene only)
  dawn_top: "#5B5BA8"
  dawn_pink: "#F07B9B"
  dawn_orange: "#FF9F5A"
  dawn_gold: "#FFD58A"
  # casino / exam interiors
  casino_purple: "#4A1F6B"
  casino_magenta: "#8E2C80"
  chalk_green: "#2F5D4A"
  classroom_wall: "#CFE3E8"
  # kit extensions (UI devices)
  shadow_ink: "rgba(20, 18, 60, a)"   # every drop shadow / scrim uses this ink at alpha a (0.18-0.78)
  scrim_numcard: "rgba(29, 27, 79, 0.42)"
  band_text: "#C9CCEA"
  chip_blue: "#7FB2FF"
  stamp_green_text: "#1E8A4F"
  stripe_navy_a: "#2B2A6E"
  stripe_navy_b: "#25245F"
  stripe_red_a: "#7A1F2B"
  stripe_red_b: "#6C1B26"
  stripe_green_a: "#17613F"
  stripe_green_b: "#145536"
  beam_glow: "rgba(255, 196, 61, a)"  # accent_yellow glow at alpha a
  dice_face_edge: "#E9ECF3"            # CSS 3D dice face rim
  dice_face_side: "#EEF0F6"            # CSS 3D dice side-face tint
  todo_meter_bg: "#E3E6F0"             # empty meter track on the Index to-do list
  todo_top: "#E4F6EC"                  # highlighted (winning) to-do row
  # shadow_ink ramp: the exact alphas in use (drop shadows, text shadows, scrims, backing panels)
  shadow_ink_12: "rgba(20, 18, 60, 0.12)"
  shadow_ink_18: "rgba(20, 18, 60, 0.18)"
  shadow_ink_20: "rgba(20, 18, 60, 0.2)"
  shadow_ink_22: "rgba(20, 18, 60, 0.22)"
  shadow_ink_25: "rgba(20, 18, 60, 0.25)"
  shadow_ink_28: "rgba(20, 18, 60, 0.28)"
  shadow_ink_30: "rgba(20, 18, 60, 0.3)"
  shadow_ink_35: "rgba(20, 18, 60, 0.35)"
  shadow_ink_38: "rgba(20, 18, 60, 0.38)"
  shadow_ink_45: "rgba(20, 18, 60, 0.45)"
  shadow_ink_50: "rgba(20, 18, 60, 0.5)"
  shadow_ink_60: "rgba(20, 18, 60, 0.6)"
  shadow_ink_62: "rgba(20, 18, 60, 0.62)"   # logo-bug backing
  shadow_ink_66: "rgba(20, 18, 60, 0.66)"   # name-plate backing
  shadow_ink_78: "rgba(20, 18, 60, 0.78)"   # source-chip backing
  # light tints
  card_glass_08: "rgba(253, 252, 248, 0.08)"  # family panel fill
  card_glass_18: "rgba(253, 252, 248, 0.18)"  # family panel border
  card_stamp_94: "rgba(253, 252, 248, 0.94)"  # stamp paper
  accent_glow_45: "rgba(255, 196, 61, 0.45)"
  accent_glow_50: "rgba(255, 196, 61, 0.5)"
  accent_glow_80: "rgba(255, 196, 61, 0.8)"
  accent_glow_90: "rgba(255, 196, 61, 0.9)"
  torch_glow_00: "rgba(255, 183, 3, 0)"
  torch_glow_60: "rgba(255, 183, 3, 0.6)"
  torch_core_95: "rgba(255, 224, 102, 0.95)"
  beam_25: "rgba(255, 243, 176, 0.25)"
  beam_70: "rgba(255, 243, 176, 0.7)"
  beam_95: "rgba(255, 243, 176, 0.95)"
fonts:
  display: "Fredoka"      # big #N numerals, statement cards, name plates (600-700)
  body: "Montserrat"      # tags, bubbles, labels, captions (500-900)
  files:
    Fredoka: "assets/fonts/fredoka-latin-var.woff2"
    Montserrat: "assets/fonts/montserrat-latin-var.woff2"
type_scale:
  number_card: "300-360px Fredoka 700, white, soft drop shadow"
  statement_card: "86-110px Fredoka 700 caps, 2-4 lines"
  name_plate_title: "96px Fredoka 700"
  bubble_text: "44-54px Montserrat 700, ink"
  tag_label: "22px Montserrat 700 caps, label_grey, letter-spacing 2px"
  tag_value: "38-44px Montserrat 800, ink"
  arrow_label: "58-72px Montserrat 800 caps, white with ink shadow"
  minimum: "28px for any text a viewer must read"
radii: { card: 22, bubble: 34, tag: 16, chip: 999 }
shadows:
  card: "0 10px 0 rgba(20,18,60,0.18), 0 22px 40px rgba(20,18,60,0.25)"
  sticker: "0 6px 0 rgba(20,18,60,0.22)"
---

# Smart Scan: Night Watch

The v11 solution chapter is told like an Infographics Show episode. A narrator carries a short
cartoon story (the night guard from the problem video, an engineer, sneaky signals), with TIS
devices on top: white info tags, speech bubbles, giant "#N" number cards, bold arrow labels,
held-up props, full-screen statement cards, and a new picture every 2 to 4 seconds.

## Concept angle

One guard, one searchlight that lights only 2 of 16 rooms. The story is about how he decides
*where to point it next*. Every technical idea gets a household object first (dice, to-do list,
slot machine, cheat sheet, robot brain, prize wheel), then the real name on a name plate.

## Style rules (every asset and scene)

- **Flat vector illustration.** No outlines on characters or props. Build shapes from 2-3 flat
  tones: base, one darker shade on the side away from the light, and an optional small highlight.
  No gradients on characters; soft radial glows only for light sources (searchlight, torch, screens).
- **Rounded, friendly geometry.** Corner radii everywhere; circles and capsules over sharp polygons.
- **Readable silhouettes.** Every prop must be recognisable as a silhouette at 300px wide.
- **Palette only.** Use the hex tokens above. Never invent new colours per element.
- **Meaning colours are fixed:** yellow = where the receiver looks / highlight, green = caught,
  red = missed, blue = information.
- **No text baked into SVG art.** All words, numbers, and labels are HTML added by scenes, so they
  stay sharp and editable. (Exception: tiny decorative marks such as dial ticks.)
- **Depth:** backgrounds carry 2-3 parallax layers (far / mid / near) as separate SVG groups.
- **Life:** every scene has ambient motion (twinkling 4-point stars, drifting dots, breathing
  glows, blinking characters) plus a slow camera push (scale 1.00 -> 1.06).

## TIS devices (implemented in `assets/js/cast.js`)

| Device | Look | Use |
|---|---|---|
| Info tag | White card, icon on the left, small grey caps label + bold value | Top-left context: `LOCATION`, `TEST`, `SOURCE`, `MEASURED` |
| Speech bubble | White rounded bubble with a tail, bold ink text | Characters' short lines and jokes |
| Number card | Giant white "#1".."#6" in Fredoka over a blurred scene | Opens each of the six methods |
| Name plate | Capsule with the method name + a category chip | "CTMC" + "FOLLOWS RULES" |
| Statement card | Bold white caps on a diagonal-striped colour field | One big takeaway line |
| Arrow label | Big white caps label with a thick yellow arrow | Naming a part of the picture |
| Fact source chip | Small dark chip bottom-right: "SOURCE: ..." | Where a number comes from |
| Logo bug | Bottom-left "PUSHPAK · SMART SCAN" badge | Every scene |

## Characters

- **Guard** — night-shift security guard, navy uniform and cap, gold badge, moustache, friendly,
  a little tired. Operates the searchlight.
- **Engineer** — EW engineer in a white lab coat over a teal shirt, dark hair in a bun, round
  glasses. Explains with props (tablet, whiteboard, clipboard).
- **Intruder / signal** — hooded dark silhouette with two white eye glints and a torch; stands for
  an unknown emitter. Never scary; slightly comic.

Proportions: big heads (head height ~ 1/3.2 of body), simple dot eyes with white glints, bold
brows, small nose, open mouth shapes when talking. Half-body framing in close-ups.

## Facts shown on screen (source-locked, do not change)

- Receiver hears **2 of 16** bands per step in the simulator; problem statement: instantaneous
  bandwidth typically **at least 10x narrower** than the monitored band.
- Decision step: **10 ms**.
- Rhythm-trap test (8 bands, one periodic signal, 4 seeds): fixed sweep **0** detections; CTMC and
  Index intercepted the signal in **every** run.
- Scenario B (unseen test runs): detection **11 -> 13 of every 100** signal moments (0.1092 ->
  0.1334, **+22%**); emitters reached **97%** for both fixed sweep and Index.
- Bandit (separate 20-run test): **34 of 100** signal moments, but only **71%** of emitters reached.
- Training time, measured on this laptop (Intel i5-13420H CPU), Scenario B, shipped settings:
  Bandit **1.3 min**, Q-learning **3.6 min**, DQN **5.4 min**, PPO **7.5 min**; CTMC and Index need no
  training.
- Decision latency: **6.6 ms** (95th percentile, warm scheduler API).
- Data: our simulator's emitter worlds + the **Alan Turing Institute synthetic radar dataset**,
  replayed through the same virtual receiver. Simulation only, not field hardware.
