"""Cartoon cast for v11 (Infographics-Show style), generated as static SVG strings.

Every character is drawn in its own 400 x 800 viewBox with named, individually animatable
parts. Pivots (in viewBox units) are exported in PIVOTS so scene timelines can rotate limbs with
GSAP `svgOrigin` without measuring the DOM.

Part ids are "<prefix>-<part>", e.g. "s01-guard-arm-n" (near arm). Parts:
  body       whole figure (translate / bob)
  head       head group (pivot: neck)
  eyes       both eyes (blink with scaleY around PIVOTS[..]['eyes'])
  brows      both brows; brow-l / brow-r individually
  mouth-closed, mouth-open, mouth-o   mouth states (toggle opacity)
  arm-n, fore-n   near arm + forearm (viewer's left for the guard)
  arm-f, fore-f   far arm + forearm
  torso, legs
Optional props attached to hands: torch (guard / intruder), tablet (engineer), marker (engineer).
"""

from __future__ import annotations

C = {
    "ink": "#1F2340",
    "card": "#FDFCF8",
    "skin_g": "#C68A5E",
    "skin_g_sh": "#A9714A",
    "skin_e": "#A86B45",
    "skin_e_sh": "#8D5636",
    "navy": "#2D3A6B",
    "navy_sh": "#232E57",
    "cap": "#26325C",
    "gold": "#F2B632",
    "yellow": "#FFC43D",
    "coat": "#F4F6FA",
    "coat_sh": "#D8DEEA",
    "teal": "#1F9E89",
    "hair": "#1E1A1A",
    "intr": "#15142E",
    "intr_edge": "#2B2A6E",
    "mouth": "#5A1E24",
    "tongue": "#E0707A",
    "lip": "#6B2E2E",
    "beam": "#FFF3B0",
    "torch": "#FFE066",
    "glow": "#FFB703",
}

PIVOTS = {
    "guard": {
        "head": (204, 262), "eyes": (218, 158), "arm-n": (136, 300), "fore-n": (116, 410),
        "arm-f": (276, 300), "fore-f": (294, 410), "body": (204, 780),
    },
    "engineer": {
        "head": (196, 262), "eyes": (184, 162), "arm-n": (266, 300), "fore-n": (286, 410),
        "arm-f": (128, 300), "fore-f": (110, 410), "body": (196, 780),
    },
    "intruder": {
        "head": (150, 200), "eyes": (170, 150), "arm-n": (120, 250), "fore-n": (96, 330),
        "body": (150, 510),
    },
}


def _g(prefix: str, part: str, inner: str, extra: str = "") -> str:
    return f'<g id="{prefix}-{part}"{(" " + extra) if extra else ""}>{inner}</g>'


# --------------------------------------------------------------------------------------------
# GUARD: night-shift security guard, faces viewer-right (3/4), navy uniform, cap, moustache.
# --------------------------------------------------------------------------------------------

def guard(prefix: str, torch: bool = False, cls: str = "") -> str:
    p = prefix
    shadow = '<ellipse cx="204" cy="784" rx="122" ry="13" fill="rgba(20,18,60,0.22)"/>'

    legs = _g(p, "legs", f"""
      <path d="M122 506 L198 506 L190 752 Q189 760 181 760 L140 760 Q132 760 132 752 Z" fill="{C['navy_sh']}"/>
      <path d="M208 506 L288 506 L280 752 Q279 760 271 760 L230 760 Q222 760 222 752 Z" fill="#1E284C"/>
      <path d="M161 520 L158 745" stroke="#1E284C" stroke-width="4" stroke-linecap="round" opacity="0.6"/>
      <path d="M117 752 L190 752 Q204 752 206 766 L206 776 Q206 782 200 782 L112 782 Q104 782 104 774 Q104 756 117 752 Z" fill="{C['ink']}"/>
      <path d="M220 752 L286 752 Q304 754 310 772 Q312 782 302 782 L222 782 Q214 782 214 774 L214 760 Q214 752 220 752 Z" fill="{C['ink']}"/>
      <path d="M118 758 Q140 754 160 757" stroke="#3A3F7A" stroke-width="4" stroke-linecap="round" fill="none"/>
    """)

    torso = _g(p, "torso", f"""
      <path d="M126 292 C146 270 174 262 204 262 C236 262 264 270 284 292 L298 476 C299 500 284 512 258 514 L150 514 C124 512 108 500 110 476 Z" fill="{C['navy']}"/>
      <path d="M262 268 C276 275 282 284 284 292 L298 476 C299 500 286 511 264 513 C272 440 272 330 262 268 Z" fill="{C['navy_sh']}"/>
      <path d="M180 264 L204 316 L228 264 Q204 258 180 264 Z" fill="{C['skin_g_sh']}"/>
      <path d="M172 262 L204 318 L190 262 Z" fill="#3A4A86"/>
      <path d="M236 262 L204 318 L218 262 Z" fill="#26325C"/>
      <path d="M204 318 L196 332 L204 420 L212 332 Z" fill="{C['ink']}"/>
      <path d="M198 314 L210 314 L214 330 L194 330 Z" fill="{C['ink']}"/>
      <path d="M140 340 L178 340 L178 368 Q159 376 140 368 Z" fill="{C['navy_sh']}"/>
      <path d="M232 340 L270 340 L270 368 Q251 376 232 368 Z" fill="#1E284C"/>
      <path d="M150 316 L168 316 L168 330 Q159 342 150 330 Z" fill="{C['gold']}"/>
      <circle cx="159" cy="323" r="4" fill="#C98F12"/>
      <rect x="128" y="286" width="44" height="14" rx="7" fill="{C['navy_sh']}"/>
      <rect x="240" y="286" width="42" height="14" rx="7" fill="#1E284C"/>
      <rect x="132" y="290" width="36" height="4" rx="2" fill="{C['gold']}"/>
      <rect x="244" y="290" width="34" height="4" rx="2" fill="{C['gold']}"/>
      <path d="M110 472 Q204 482 298 472 L299 496 Q204 506 109 496 Z" fill="{C['ink']}"/>
      <rect x="190" y="470" width="30" height="30" rx="6" fill="{C['gold']}"/>
      <rect x="198" y="478" width="14" height="14" rx="3" fill="{C['ink']}"/>
    """)

    torch_near = ""
    if torch:
        torch_near = _g(p, "torch", f"""
          <rect x="96" y="470" width="28" height="70" rx="8" fill="#3A3F7A"/>
          <rect x="90" y="530" width="40" height="26" rx="8" fill="#4B519A"/>
          <ellipse cx="110" cy="556" rx="16" ry="5" fill="{C['torch']}"/>
        """)

    arm_n = _g(p, "arm-n", f"""
      <path d="M118 296 C108 334 102 374 102 410 L138 414 C138 380 144 340 156 302 Z" fill="{C['navy']}"/>
      {_g(p, "fore-n", f'''
        <path d="M102 404 L102 486 Q102 494 110 494 L130 494 Q138 494 138 486 L138 408 Z" fill="{C['navy']}"/>
        <rect x="100" y="478" width="40" height="12" rx="6" fill="{C['navy_sh']}"/>
        {torch_near}
        <path d="M100 492 Q98 520 118 526 Q140 526 140 504 Q140 490 128 488 L108 488 Q100 488 100 492 Z" fill="{C['skin_g']}"/>
        <path d="M134 494 Q146 500 142 512 Q138 516 132 510 Z" fill="{C['skin_g_sh']}"/>
      ''')}
    """, 'data-pivot="136 300"')

    arm_f = _g(p, "arm-f", f"""
      <path d="M258 300 C268 338 276 376 276 410 L312 410 C312 374 306 334 294 294 Z" fill="{C['navy_sh']}"/>
      {_g(p, "fore-f", f'''
        <path d="M276 404 L276 486 Q276 494 284 494 L304 494 Q312 494 312 486 L312 406 Z" fill="{C['navy_sh']}"/>
        <rect x="274" y="478" width="40" height="12" rx="6" fill="#1E284C"/>
        <path d="M274 492 Q272 520 292 526 Q314 526 314 504 Q314 490 302 488 L282 488 Q274 488 274 492 Z" fill="{C['skin_g_sh']}"/>
      ''')}
    """, 'data-pivot="276 300"')

    head = _g(p, "head", f"""
      <rect x="182" y="222" width="46" height="46" rx="12" fill="{C['skin_g_sh']}"/>
      <ellipse cx="136" cy="162" rx="17" ry="25" fill="{C['skin_g']}"/>
      <ellipse cx="138" cy="164" rx="8" ry="13" fill="{C['skin_g_sh']}"/>
      <path d="M204 66 C250 66 280 100 280 150 C280 192 262 226 228 240 C210 247 192 246 176 240 C148 228 132 198 132 154 C132 102 162 66 204 66 Z" fill="{C['skin_g']}"/>
      <path d="M266 118 C278 132 281 150 280 162 C278 196 262 224 232 238 C252 214 262 176 266 118 Z" fill="{C['skin_g_sh']}" opacity="0.55"/>
      <path d="M136 124 L154 122 L152 156 L138 150 Z" fill="{C['hair']}"/>
      {_g(p, "brows", f'''
        <path id="{p}-brow-l" d="M176 138 Q192 128 208 134" stroke="{C['hair']}" stroke-width="9" stroke-linecap="round" fill="none"/>
        <path id="{p}-brow-r" d="M232 132 Q248 126 262 136" stroke="{C['hair']}" stroke-width="9" stroke-linecap="round" fill="none"/>
      ''')}
      {_g(p, "eyes", f'''
        <ellipse cx="192" cy="160" rx="9.5" ry="12.5" fill="{C['ink']}"/>
        <ellipse cx="246" cy="158" rx="9" ry="12" fill="{C['ink']}"/>
        <circle cx="195" cy="155" r="3.4" fill="#FFFFFF"/>
        <circle cx="249" cy="153" r="3.2" fill="#FFFFFF"/>
      ''')}
      <path d="M226 160 Q246 176 240 192 Q232 198 216 192" fill="{C['skin_g_sh']}"/>
      <path d="M190 202 Q216 188 256 200 Q246 214 226 208 Q206 216 190 202 Z" fill="{C['hair']}"/>
      {_g(p, "mouth-closed", f'<path d="M206 220 Q224 230 242 220" stroke="{C["lip"]}" stroke-width="5" stroke-linecap="round" fill="none"/>')}
      {_g(p, "mouth-open", f'''
        <path d="M202 214 Q224 210 246 214 Q244 242 224 244 Q204 242 202 214 Z" fill="{C['mouth']}"/>
        <ellipse cx="224" cy="236" rx="11" ry="5" fill="{C['tongue']}"/>
        <path d="M206 215 Q224 213 242 215 L240 221 Q224 219 208 221 Z" fill="#FFFFFF"/>
      ''', 'opacity="0"')}
      {_g(p, "mouth-o", f'<ellipse cx="224" cy="224" rx="11" ry="14" fill="{C["mouth"]}"/>', 'opacity="0"')}
      <path d="M128 122 C124 74 160 46 206 46 C252 46 284 74 282 122 Z" fill="{C['cap']}"/>
      <path d="M150 70 Q180 54 212 56" stroke="#3A4A86" stroke-width="6" stroke-linecap="round" fill="none" opacity="0.8"/>
      <path d="M124 106 Q204 94 286 106 L286 126 Q204 114 124 126 Z" fill="{C['ink']}"/>
      <path d="M196 120 Q268 108 330 128 Q314 146 258 146 Q216 146 196 132 Z" fill="{C['ink']}"/>
      <path d="M198 72 L218 72 L218 90 Q208 102 198 90 Z" fill="{C['gold']}"/>
    """, 'data-pivot="204 262"')

    body = f"""{shadow}{legs}{arm_f}{torso}{arm_n}{head}"""
    return (f'<svg id="{p}" class="char char-guard {cls}" viewBox="0 0 400 800" xmlns="http://www.w3.org/2000/svg">'
            f'{_g(p, "body", body)}</svg>')


# --------------------------------------------------------------------------------------------
# ENGINEER: EW engineer in a lab coat, faces viewer-left (3/4), bun, round glasses.
# --------------------------------------------------------------------------------------------

def engineer(prefix: str, tablet: bool = False, marker: bool = False, cls: str = "") -> str:
    p = prefix
    shadow = '<ellipse cx="196" cy="784" rx="118" ry="13" fill="rgba(20,18,60,0.22)"/>'

    legs = _g(p, "legs", f"""
      <path d="M130 500 L196 500 L190 752 Q189 760 181 760 L146 760 Q138 760 138 752 Z" fill="{C['ink']}"/>
      <path d="M204 500 L270 500 L262 752 Q261 760 253 760 L218 760 Q210 760 210 752 Z" fill="#2A2E52"/>
      <path d="M96 754 Q98 742 116 742 L184 742 Q192 742 192 752 L192 776 Q192 782 186 782 L104 782 Q94 782 96 770 Z" fill="{C['teal']}"/>
      <path d="M208 752 Q208 742 216 742 L270 742 Q292 744 296 768 Q298 782 286 782 L214 782 Q208 782 208 776 Z" fill="#17806F"/>
    """)

    torso = _g(p, "torso", f"""
      <path d="M150 272 L246 272 L262 470 L134 470 Z" fill="{C['teal']}"/>
      <path d="M176 272 L198 318 L220 272 Z" fill="{C['skin_e_sh']}"/>
      <path d="M114 300 C124 280 146 268 170 264 L196 380 L186 560 L110 552 Q98 548 100 534 Z" fill="{C['coat']}"/>
      <path d="M282 300 C272 280 250 268 226 264 L200 380 L210 560 L284 552 Q298 548 296 534 Z" fill="{C['coat']}"/>
      <path d="M282 300 C290 360 296 450 296 534 Q298 548 284 552 L262 554 C274 470 276 380 268 286 Z" fill="{C['coat_sh']}"/>
      <path d="M170 264 L186 330 L164 316 L176 360 L196 380 Z" fill="{C['coat_sh']}"/>
      <path d="M226 264 L212 330 L232 316 L220 360 L200 380 Z" fill="{C['coat_sh']}" opacity="0.8"/>
      <rect x="226" y="420" width="48" height="52" rx="8" fill="{C['coat_sh']}"/>
      <rect x="236" y="404" width="7" height="30" rx="3" fill="{C['yellow']}"/>
      <rect x="124" y="420" width="46" height="52" rx="8" fill="{C['coat_sh']}" opacity="0.7"/>
    """)

    hold = ""
    if tablet:
        hold = _g(p, "tablet", f"""
          <rect x="222" y="420" width="150" height="104" rx="14" fill="{C['ink']}" transform="rotate(-8 297 472)"/>
          <rect x="232" y="430" width="130" height="84" rx="8" fill="{C['card']}" transform="rotate(-8 297 472)"/>
        """)
    if marker:
        hold = _g(p, "marker", f"""
          <rect x="296" y="470" width="16" height="66" rx="6" fill="{C['teal']}" transform="rotate(-30 304 500)"/>
          <rect x="296" y="520" width="16" height="30" rx="4" fill="#F4F6FA" transform="rotate(-30 304 500)"/>
        """)

    arm_n = _g(p, "arm-n", f"""
      <path d="M252 298 C272 330 286 372 290 410 L322 404 C316 366 304 328 282 290 Z" fill="{C['coat']}"/>
      {_g(p, "fore-n", f'''
        <path d="M290 402 L296 480 Q297 490 306 490 L318 490 Q328 490 328 480 L322 400 Z" fill="{C['coat']}"/>
        <path d="M312 402 L322 400 L328 480 Q328 490 318 490 L316 490 Z" fill="{C['coat_sh']}"/>
        {hold}
        <path d="M292 486 Q290 514 308 520 Q330 520 330 498 Q330 484 318 482 L300 482 Q292 482 292 486 Z" fill="{C['skin_e']}"/>
      ''')}
    """, 'data-pivot="266 300"')

    arm_f = _g(p, "arm-f", f"""
      <path d="M140 296 C120 330 108 372 104 410 L136 414 C140 378 150 340 166 300 Z" fill="{C['coat_sh']}"/>
      {_g(p, "fore-f", f'''
        <path d="M104 404 L98 480 Q97 490 106 490 L120 490 Q130 490 130 480 L136 408 Z" fill="{C['coat_sh']}"/>
        <path d="M94 486 Q92 514 110 520 Q132 520 132 498 Q132 484 120 482 L102 482 Q94 482 94 486 Z" fill="{C['skin_e_sh']}"/>
      ''')}
    """, 'data-pivot="128 300"')

    head = _g(p, "head", f"""
      <rect x="172" y="226" width="46" height="46" rx="12" fill="{C['skin_e_sh']}"/>
      <path d="M196 30 C230 30 250 52 246 78 C240 98 216 102 196 96 C176 102 152 98 146 78 C142 52 162 30 196 30 Z" fill="{C['hair']}"/>
      <ellipse cx="262" cy="170" rx="16" ry="24" fill="{C['skin_e']}"/>
      <ellipse cx="260" cy="172" rx="8" ry="13" fill="{C['skin_e_sh']}"/>
      <path d="M196 72 C152 72 122 106 122 156 C122 196 140 230 174 244 C192 251 210 250 226 244 C254 232 270 202 270 158 C270 106 240 72 196 72 Z" fill="{C['skin_e']}"/>
      <path d="M134 124 C122 140 120 158 122 170 C124 202 140 228 170 242 C150 218 140 180 134 124 Z" fill="{C['skin_e_sh']}" opacity="0.5"/>
      <path d="M118 158 C112 100 150 62 200 64 C250 66 282 104 274 166 C268 146 258 128 240 118 C214 128 176 126 150 110 C136 124 124 140 118 158 Z" fill="{C['hair']}"/>
      <path d="M150 110 C176 126 214 128 240 118 C222 112 196 98 176 92 C164 96 156 102 150 110 Z" fill="#2E2828"/>
      {_g(p, "brows", f'''
        <path id="{p}-brow-l" d="M140 136 Q154 128 170 132" stroke="{C['hair']}" stroke-width="8" stroke-linecap="round" fill="none"/>
        <path id="{p}-brow-r" d="M196 132 Q212 126 228 134" stroke="{C['hair']}" stroke-width="8" stroke-linecap="round" fill="none"/>
      ''')}
      {_g(p, "eyes", f'''
        <ellipse cx="156" cy="164" rx="9" ry="12" fill="{C['ink']}"/>
        <ellipse cx="210" cy="164" rx="9.5" ry="12.5" fill="{C['ink']}"/>
        <circle cx="159" cy="159" r="3.2" fill="#FFFFFF"/>
        <circle cx="213" cy="159" r="3.4" fill="#FFFFFF"/>
      ''')}
      <g fill="none" stroke="{C['ink']}" stroke-width="5">
        <circle cx="156" cy="164" r="24" fill="#FFFFFF" fill-opacity="0.16"/>
        <circle cx="212" cy="164" r="25" fill="#FFFFFF" fill-opacity="0.16"/>
        <path d="M180 162 Q184 156 188 162"/>
        <path d="M237 160 L262 154"/>
      </g>
      <path d="M176 168 Q158 186 166 198 Q174 204 188 198" fill="{C['skin_e_sh']}"/>
      {_g(p, "mouth-closed", f'<path d="M160 218 Q176 228 194 218" stroke="{C["lip"]}" stroke-width="5" stroke-linecap="round" fill="none"/>')}
      {_g(p, "mouth-open", f'''
        <path d="M156 212 Q176 208 198 212 Q196 240 176 242 Q158 240 156 212 Z" fill="{C['mouth']}"/>
        <ellipse cx="176" cy="234" rx="10" ry="5" fill="{C['tongue']}"/>
        <path d="M160 213 Q176 211 194 213 L192 219 Q176 217 162 219 Z" fill="#FFFFFF"/>
      ''', 'opacity="0"')}
      {_g(p, "mouth-o", f'<ellipse cx="176" cy="222" rx="10" ry="13" fill="{C["mouth"]}"/>', 'opacity="0"')}
    """, 'data-pivot="196 262"')

    body = f"""{shadow}{legs}{arm_f}{torso}{arm_n}{head}"""
    return (f'<svg id="{p}" class="char char-engineer {cls}" viewBox="0 0 400 800" xmlns="http://www.w3.org/2000/svg">'
            f'{_g(p, "body", body)}</svg>')


# --------------------------------------------------------------------------------------------
# INTRUDER: hooded sneaky silhouette with eye glints and a torch (stands for an unknown emitter).
# 300 x 520 viewBox, faces viewer-right, crouched.
# --------------------------------------------------------------------------------------------

def intruder(prefix: str, cls: str = "") -> str:
    p = prefix
    beam = _g(p, "beam", f"""
      <path d="M228 330 L300 290 L300 400 Z" fill="{C['beam']}" opacity="0.55"/>
      <circle cx="228" cy="334" r="26" fill="{C['torch']}" opacity="0.9"/>
    """, 'opacity="0"')
    body = f"""
      <ellipse cx="150" cy="506" rx="96" ry="10" fill="rgba(20,18,60,0.25)"/>
      {_g(p, "legs", f'''
        <path d="M96 380 L150 380 L138 486 Q136 496 126 496 L92 496 Q80 496 84 484 Z" fill="{C['intr']}"/>
        <path d="M150 380 L204 380 L214 480 Q216 496 202 496 L170 496 Q160 496 160 486 Z" fill="#0F0E24"/>
      ''')}
      <path d="M84 250 C86 220 114 196 150 196 C188 196 214 222 216 254 L224 392 Q224 404 212 404 L86 404 Q74 404 76 392 Z" fill="{C['intr']}"/>
      <path d="M190 212 C208 224 216 240 216 254 L224 392 Q224 404 212 404 L196 404 C204 330 204 262 190 212 Z" fill="#0F0E24"/>
      {_g(p, "head", f'''
        <path d="M150 64 C204 64 232 104 230 156 C228 200 196 226 150 226 C104 226 72 200 70 156 C68 104 96 64 150 64 Z" fill="{C['intr']}"/>
        <path d="M150 84 C188 84 208 114 206 152 C204 184 182 204 150 204 C118 204 98 184 96 152 C94 114 112 84 150 84 Z" fill="#0A0A1C"/>
        {_g(p, "eyes", '''
          <ellipse cx="146" cy="148" rx="11" ry="7" fill="#FFFFFF"/>
          <ellipse cx="188" cy="146" rx="10" ry="6.5" fill="#FFFFFF"/>
          <circle cx="150" cy="148" r="4" fill="#15142E"/>
          <circle cx="191" cy="146" r="3.6" fill="#15142E"/>
        ''')}
        <path d="M150 64 C120 64 96 82 84 110 C110 88 136 80 170 80 C196 80 214 90 226 108 C214 80 186 64 150 64 Z" fill="{C['intr_edge']}" opacity="0.8"/>
      ''', 'data-pivot="150 200"')}
      {_g(p, "arm-n", f'''
        <path d="M104 250 C92 290 90 322 96 344 L128 340 C124 316 128 288 136 258 Z" fill="#0F0E24"/>
        {_g(p, "fore-n", f'''
          <path d="M96 336 L200 318 Q212 316 214 328 L216 338 Q218 350 206 352 L100 368 Q88 370 88 358 L88 346 Q88 338 96 336 Z" fill="{C['intr']}"/>
          <rect x="196" y="312" width="42" height="30" rx="8" fill="#3A3F7A" transform="rotate(-10 217 327)"/>
          <circle cx="206" cy="340" r="16" fill="#0F0E24"/>
        ''')}
      ''', 'data-pivot="120 250"')}
      {beam}
    """
    return (f'<svg id="{p}" class="char char-intruder {cls}" viewBox="0 0 300 520" xmlns="http://www.w3.org/2000/svg">'
            f'{_g(p, "body", body)}</svg>')


CAST = {"guard": guard, "engineer": engineer, "intruder": intruder}
