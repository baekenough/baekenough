#!/usr/bin/env python3
"""Generate the profile's self-contained SVG artwork; no dependencies required."""

from pathlib import Path


OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "profile"
SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SFMono-Regular', Consolas, 'Liberation Mono', monospace"


def hero(dark: bool) -> str:
    background, ink, muted, line, panel = (
        ("#111c18", "#f0f2e8", "#aab9ae", "#35483b", "#1d342a")
        if dark
        else ("#f3f3eb", "#183c2a", "#546b5b", "#d1d8ca", "#183c2a")
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="480" viewBox="0 0 1440 480" role="img" aria-labelledby="title description">
  <title id="title">SangYi Baek — Real problems. Working systems.</title>
  <desc id="description">An editorial profile banner with a green and lime diagram connecting a problem, its implementation, and verification.</desc>
  <rect width="1440" height="480" fill="{background}"/>
  <path d="M64 82H1376M64 403H1376" stroke="{line}"/>
  <g font-family="{MONO}" font-size="19" letter-spacing="2" fill="{ink}">
    <text x="64" y="51">SANGYI BAEK</text>
    <text x="1376" y="51" text-anchor="end">BAEKENOUGH</text>
  </g>
  <g font-family="{SANS}" font-weight="600" font-size="83" letter-spacing="-3.6" fill="{ink}">
    <text x="59" y="206">Real problems.</text>
    <text x="59" y="303">Working systems.</text>
  </g>
  <text x="64" y="355" font-family="{SANS}" font-size="23" fill="{muted}">Software engineering, with people in mind.</text>
  <g transform="translate(1050 117)">
    <rect width="326" height="250" rx="10" fill="{panel}"/>
    <g stroke="#607953" stroke-width="1" opacity=".5">
      <path d="M22 48H304M22 96H304M22 144H304M22 192H304M70 22V226M118 22V226M166 22V226M214 22V226M262 22V226"/>
    </g>
    <path d="M68 68H162V124H258V192H162V124H68Z" fill="none" stroke="#c6e98a" stroke-width="3"/>
    <rect x="49" y="49" width="38" height="38" rx="4" fill="#c6e98a"/>
    <rect x="143" y="105" width="38" height="38" rx="4" fill="{panel}" stroke="#c6e98a" stroke-width="3"/>
    <circle cx="258" cy="124" r="19" fill="#c6e98a"/>
    <circle cx="162" cy="192" r="19" fill="{panel}" stroke="#c6e98a" stroke-width="3"/>
    <path d="m152 192 7 7 14-15" fill="none" stroke="#c6e98a" stroke-width="3"/>
    <circle cx="68" cy="124" r="5" fill="#c6e98a"/>
  </g>
  <g font-family="{MONO}" font-size="17" letter-spacing="1.1" fill="{muted}">
    <text x="64" y="448">AGENT SYSTEMS</text>
    <text x="394" y="448">KNOWLEDGE &amp; AUTOMATION</text>
    <text x="1376" y="448" text-anchor="end">DESIGN / BUILD / OPERATE</text>
  </g>
</svg>
'''


AGENT_STACK = f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="224" viewBox="0 0 720 224" role="img" aria-labelledby="title description">
  <title id="title">01 — Agent engineering</title>
  <desc id="description">Three reusable skills route into a specialist agent and a verification step.</desc>
  <rect width="720" height="224" fill="#183c2a"/>
  <text x="32" y="44" font-family="{MONO}" font-size="19" letter-spacing="1.7" fill="#c6e98a">01 / AGENT ENGINEERING</text>
  <path d="M32 65H688" stroke="#476348"/>
  <g fill="none" stroke="#c6e98a" stroke-width="2.5">
    <path d="M116 107H252V146H332M116 146H332M116 185H252V146M412 146H537"/>
    <rect x="64" y="94" width="52" height="26" rx="3"/>
    <rect x="64" y="133" width="52" height="26" rx="3"/>
    <rect x="64" y="172" width="52" height="26" rx="3"/>
    <rect x="332" y="112" width="80" height="68" rx="5" fill="#c6e98a"/>
    <circle cx="562" cy="146" r="25"/>
    <path d="m550 146 9 9 17-19"/>
  </g>
  <g fill="none" stroke="#183c2a" stroke-width="3" stroke-linecap="square">
    <path d="m362 134-11 12 11 12M382 134l11 12-11 12M376 132l-8 28"/>
  </g>
  <path d="M587 146H656" stroke="#476348" stroke-width="2.5"/>
  <circle cx="656" cy="146" r="5" fill="#c6e98a"/>
</svg>
'''


KNOWLEDGE_MAP = f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="224" viewBox="0 0 720 224" role="img" aria-labelledby="title description">
  <title id="title">02 — Knowledge systems</title>
  <desc id="description">Scattered documents are connected to a central knowledge index and a search result.</desc>
  <rect width="720" height="224" fill="#e7eccf"/>
  <text x="32" y="44" font-family="{MONO}" font-size="19" letter-spacing="1.7" fill="#183c2a">02 / KNOWLEDGE SYSTEMS</text>
  <path d="M32 65H688" stroke="#b8c6a0"/>
  <g fill="none" stroke="#6d875d" stroke-width="2">
    <path d="M122 111 338 143M150 181 338 143M248 95 338 143M416 143H554"/>
    <circle cx="248" cy="95" r="8" fill="#e7eccf"/>
    <circle cx="150" cy="181" r="8" fill="#e7eccf"/>
    <rect x="95" y="89" width="28" height="38" rx="3" fill="#e7eccf"/>
    <path d="M102 101h14M102 109h14M102 117h9"/>
  </g>
  <g stroke="#183c2a" stroke-width="2" fill="#183c2a">
    <path d="m377 103 40 21v40l-40 21-40-21v-40Z"/>
    <path d="m337 124 40 21 40-21M377 145v40" fill="none" stroke="#c6e98a"/>
  </g>
  <circle cx="575" cy="136" r="24" fill="none" stroke="#183c2a" stroke-width="4"/>
  <path d="m592 153 24 24" stroke="#183c2a" stroke-width="5"/>
  <path d="M647 103v74M638 112h18M638 133h18M638 154h18" stroke="#b8c6a0" stroke-width="2"/>
</svg>
'''


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, content in {
        "hero-light.svg": hero(False),
        "hero-dark.svg": hero(True),
        "agent-stack.svg": AGENT_STACK,
        "knowledge-map.svg": KNOWLEDGE_MAP,
    }.items():
        (OUTPUT / name).write_text(content, encoding="utf-8")
        print(f"Generated {name}")
