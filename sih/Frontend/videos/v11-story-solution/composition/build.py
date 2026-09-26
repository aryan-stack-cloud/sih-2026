"""Assemble v11 into one HyperFrames composition (index.html).

Inputs
  plan.json                   scene order, the voice clips each scene carries, and the gaps
  assets/voice/durations.json real clip durations (falls back to a words-per-second estimate)
  scenes/<id>.html            scene markup fragment with placeholders (see PLACEHOLDERS below)
  scenes/<id>.js              body of `function (tl, K) { ... }` building the scene timeline
  scenes/kit.css, kit.js      shared TIS kit

PLACEHOLDERS inside scene fragments
  {{guard id=s01-g [torch] [class=...]}}      cartoon guard (tools/cast.py)
  {{engineer id=s02-e [tablet|marker] [class=...]}}
  {{intruder id=s01-i [class=...]}}
  {{svg src=assets/art/props/dice.svg id=s05-dice [class=...] [style=...]}}
        inline an SVG file; every internal id becomes "<id>-<old id>" so parts are animatable
  {{icon name}}                               <img class="ico" src="assets/art/icons/name.svg">
  <sfx src="pop" at="s01_2+0.3" vol="0.6"></sfx>
        a sound effect at a scene-local time: a number, a cue ("s01_2"), a cue end ("s01_2@end"),
        each optionally +/- an offset. Emitted as a root-level <audio> clip.

Scene JS gets K = KIT helpers + { D, cue(id), end(id), dur(id) } with scene-local seconds.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "tools"))
from cast import PIVOTS, engineer, guard, intruder  # noqa: E402

FPS = 30


def q(x: float) -> float:
    """Quantise to the frame grid so clip boundaries land on whole frames."""
    return round(round(x * FPS) / FPS, 4)


def probe(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                          "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True)
    return float(out.stdout.strip())


def load_narration() -> dict[str, str]:
    lines = {}
    for line in (ROOT / "narration.txt").read_text(encoding="utf-8").splitlines():
        if "|" in line:
            k, v = line.split("|", 1)
            lines[k.strip()] = v.strip()
    return lines


def voice_durations(narr: dict[str, str]) -> dict[str, float]:
    f = ROOT / "assets/voice/durations.json"
    real = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    out = {}
    for k, text in narr.items():
        wav = ROOT / f"assets/voice/{k}.wav"
        if k in real and wav.exists():
            out[k] = float(real[k])
        else:
            out[k] = round(len(text.split()) / 2.75 + 0.25, 3)  # estimate until TTS lands
    return out


# ------------------------------------------------------------------------------ placeholders

ATTR = re.compile(r'(\w[\w-]*)(?:=("[^"]*"|\S+))?')


def parse_attrs(s: str) -> dict[str, str]:
    d = {}
    for m in ATTR.finditer(s):
        v = m.group(2)
        d[m.group(1)] = (v[1:-1] if v and v.startswith('"') else v) if v is not None else True
    return d


def inline_svg(src: str, pid: str, cls: str = "", style: str = "") -> str:
    text = (ROOT / src).read_text(encoding="utf-8")
    text = re.sub(r"<\?xml[^>]*>", "", text)
    text = re.sub(r"<!DOCTYPE[^>]*>", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    ids = set(re.findall(r'\sid="([^"]+)"', text))
    for old in sorted(ids, key=len, reverse=True):
        new = f"{pid}-{old}"
        text = text.replace(f'id="{old}"', f'id="{new}"')
        text = text.replace(f"url(#{old})", f"url(#{new})")
        text = text.replace(f'href="#{old}"', f'href="#{new}"')
    # root svg element: set id/class/style, drop width/height
    m = re.search(r"<svg\b[^>]*>", text)
    head = m.group(0)
    new_head = re.sub(r'\s(width|height|id|class|style)="[^"]*"', "", head)
    extra = f' id="{pid}" class="svgart {cls}"'.rstrip() + (f' style="{style}"' if style else "")
    new_head = new_head[:-1] + extra + ">"
    return text.replace(head, new_head, 1).strip()


def expand(fragment: str) -> str:
    def rep(m: re.Match) -> str:
        kind, rest = m.group(1), m.group(2) or ""
        a = parse_attrs(rest)
        if kind == "guard":
            return guard(a["id"], torch=bool(a.get("torch")), cls=a.get("class", ""))
        if kind == "engineer":
            return engineer(a["id"], tablet=bool(a.get("tablet")), marker=bool(a.get("marker")), cls=a.get("class", ""))
        if kind == "intruder":
            return intruder(a["id"], cls=a.get("class", ""))
        if kind == "svg":
            return inline_svg(a["src"], a["id"], a.get("class", ""), a.get("style", ""))
        if kind == "icon":
            name = rest.strip()
            return f'<img class="ico" src="assets/art/icons/{name}.svg" alt="">'
        if kind == "gen":
            from gen import GEN  # noqa: PLC0415
            name = rest.split()[0]
            args = {k: v for k, v in parse_attrs(rest[len(name):]).items() if k != "class"}
            return GEN[name](cls=a.get("class", ""), **args)
        raise ValueError(f"unknown placeholder {kind}")
    return re.sub(r"\{\{(\w+)\s*([^}]*)\}\}", rep, fragment)


SFX_TAG = re.compile(r'<sfx\s+([^>]*)>\s*</sfx>')


def resolve_at(expr: str, cues: dict[str, tuple[float, float]]) -> float:
    expr = expr.strip()
    m = re.fullmatch(r"([A-Za-z]\w*?)(@end)?\s*([+-]\s*[\d.]+)?", expr)
    if m and m.group(1) in cues:
        s, d = cues[m.group(1)]
        base = s + d if m.group(2) else s
        return base + (float(m.group(3).replace(" ", "")) if m.group(3) else 0.0)
    return float(expr)


# ------------------------------------------------------------------------------ build

def voice_sig(scenes) -> str:
    """Fingerprint of voice placement so a saved carve is only reused for identical timing."""
    return ";".join(f"{k}@{s['start'] + v[0]:.3f}+{v[1]:.3f}" for s in scenes for k, v in s["cues"].items())


def main() -> None:
    plan = json.loads((ROOT / "plan.json").read_text(encoding="utf-8"))
    narr = load_narration()
    vd = voice_durations(narr)

    scenes = []
    t = 0.0
    for sc in plan["scenes"]:
        local = float(sc.get("lead", 0.4))
        cues = {}
        for clip_id, gap in sc["clips"]:
            local += float(gap)
            cues[clip_id] = (q(local), vd[clip_id])
            local += vd[clip_id]
        local += float(sc.get("tail", 0.5))
        dur = q(max(local, float(sc.get("min", 0))))
        scenes.append({"id": sc["id"], "start": q(t), "dur": dur, "cues": cues})
        t += dur
    total = q(t)

    sections, js_blocks, audio = [], [], []
    sfx_n = 0
    for s in scenes:
        html = (ROOT / f"scenes/{s['id']}.html").read_text(encoding="utf-8")
        for m in SFX_TAG.finditer(html):
            a = parse_attrs(m.group(1))
            wav = ROOT / f"assets/sfx/{a['src']}.wav"
            if not wav.exists():
                continue
            at = s["start"] + resolve_at(a["at"], s["cues"])
            sfx_n += 1
            audio.append(f'<audio id="sfx-{sfx_n:03d}" src="assets/sfx/{a["src"]}.wav" data-start="{q(at)}" '
                         f'data-duration="{probe(wav):.3f}" data-track-index="{30 + sfx_n % 6}" '
                         f'data-volume="{a.get("vol", "0.6")}" data-audio-group="sfx"></audio>')
        html = SFX_TAG.sub("", html)
        body = expand(html)
        for c in ("tis-numcard", "tis-statement", "tis-stamp"):
            body = re.sub(r'class="(%s[^"]*)"' % c, r'class="" data-layout-allow-overlap', body)
        sections.append(f'<section class="clip scene" id="{s["id"]}" data-start="{s["start"]}" '
                        f'data-duration="{s["dur"]}" data-track-index="1">\n{body}\n</section>')
        js = (ROOT / f"scenes/{s['id']}.js").read_text(encoding="utf-8")
        cues_js = json.dumps({k: [v[0], round(v[1], 3)] for k, v in s["cues"].items()})
        js_blocks.append(f'SCENES.push({{id:"{s["id"]}",start:{s["start"]},dur:{s["dur"]},cues:{cues_js},'
                         f'build:function(tl,K){{\n{js}\n}}}});')
        for clip_id, (cs, cd) in s["cues"].items():
            wav = ROOT / f"assets/voice/{clip_id}.wav"
            if wav.exists():
                audio.append(f'<audio id="vo-{clip_id}" src="assets/voice/{clip_id}.wav" '
                             f'data-start="{q(s["start"] + cs)}" data-duration="{cd:.3f}" '
                             f'data-track-index="20" data-volume="1" data-audio-group="voiceover"></audio>')

    carve_file = ROOT / "assets/music/carve.json"
    carve_attrs = ""
    if carve_file.exists():
        saved = json.loads(carve_file.read_text(encoding="utf-8"))
        if abs(saved.get("total", -1) - total) < 1e-6 and saved.get("voice_sig") == voice_sig(scenes):
            for k in ("data-fx-carve", "data-fx-chain", "data-automation"):
                if saved.get(k):
                    carve_attrs += f" {k}='{saved[k]}'"
    bed = ROOT / "assets/music/bed.wav"
    if bed.exists():
        audio.append(f'<audio id="bed" src="assets/music/bed.wav" data-start="0" data-duration="{total}" '
                     f'data-track-index="21" data-volume="{plan.get("bed_volume", 0.42)}" data-audio-group="music"{carve_attrs}></audio>')

    logo_until = scenes[-1]["start"] if plan.get("logo_hide_last", True) else total
    css = (ROOT / "scenes/kit.css").read_text(encoding="utf-8")
    kit = (ROOT / "scenes/kit.js").read_text(encoding="utf-8")
    pivots = json.dumps({k: {p: list(v) for p, v in d.items()} for k, d in PIVOTS.items()})

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1920, height=1080" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
{css}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="1920" data-height="1080">
{chr(10).join(sections)}
<div class="clip hud" id="logo-bug" data-start="0" data-duration="{q(logo_until)}" data-track-index="2"><div class="tis-logo" id="logo-bug-inner"><i></i><div><b>PUSHPAK</b><small>SMART SCAN</small></div></div></div>
{chr(10).join(audio)}
</div>
<script>
window.CAST_PIVOTS = {pivots};
{kit}
const SCENES = [];
{chr(10).join(js_blocks)}
const root = gsap.timeline({{ paused: true }});
for (const s of SCENES) {{
  const tl = gsap.timeline();
  const K = Object.assign({{}}, KIT, {{
    D: s.dur,
    cue: (id) => (s.cues[id] ? s.cues[id][0] : 0),
    dur: (id) => (s.cues[id] ? s.cues[id][1] : 0),
    end: (id) => (s.cues[id] ? s.cues[id][0] + s.cues[id][1] : 0),
  }});
  s.build(tl, K);
  root.add(tl, s.start);
}}
window.__timelines["main"] = root;
</script>
</body>
</html>
"""
    (ROOT / "index.html").write_text(doc, encoding="utf-8")
    timing = {s["id"]: {"start": s["start"], "dur": s["dur"], "cues": s["cues"]} for s in scenes}
    (ROOT / "timing.json").write_text(json.dumps({"total": total, "scenes": timing}, indent=1), encoding="utf-8")
    print(f"built index.html: {len(scenes)} scenes, {total:.2f}s, {len(audio)} audio clips")
    for s in scenes:
        print(f"  {s['id']}: start {s['start']:7.2f}  dur {s['dur']:6.2f}")


if __name__ == "__main__":
    main()
