"""Generate the profile's SVG assets, one light and one dark file per asset.

Run from the repo root:  python3 scripts/build_assets.py

Every colour lives in PALETTES, so the two themes can't drift apart. Every number
on a chart lives in a data block below with its source, and nothing here is
estimated. The SVGs are shown through <img>, so they can't use scripts, web fonts,
or external URLs; they rely on system font stacks only.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Chart accent/muted pairs were checked with the dataviz palette validator
# against their own surface. Every check passes except the chroma floor on
# "muted", which is intentional: it is the de-emphasis gray beside a single
# highlighted mark, not a categorical slot.
PALETTES: dict[str, dict[str, str]] = {
    "light": {
        "paper": "#fbf8f1",
        "grid": "#e8e1d1",
        "rule": "#d9d2c3",
        "ink": "#1d2433",
        "ink2": "#575d6b",
        "pencil": "#8a8578",
        "accent": "#2a5bd7",
        "muted": "#8c8678",
        "margin": "#d6534f",
        "stamp": "#c43d3a",
        "hole": "#e6dfcf",
        "tape": "#e8dcb5",
    },
    "dark": {
        "paper": "#12161d",
        "grid": "#1f2631",
        "rule": "#2a313c",
        "ink": "#e8ebf0",
        "ink2": "#a9b0bc",
        "pencil": "#7d8592",
        "accent": "#3987e5",
        "muted": "#646b77",
        "margin": "#b5524f",
        "stamp": "#e66767",
        "hole": "#0b0e13",
        "tape": "#2f3540",
    },
}

SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif'
SERIF = 'Georgia, "Times New Roman", Times, serif'
MONO = 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace'

# EXP-01 — Instant Notes, wait after releasing the hotkey until text appears.
# Source: github.com/bhutanibhanu/instant-notes, docs/benchmarks/tuning-summary.md
# (79 s CPU whisper; loop 11 "transcribe-while-recording (787→78 ms)").
LATENCY = [
    ("Local Whisper, CPU", 79.0, "79 s"),
    ("Groq Whisper, batch", 0.787, "787 ms"),
    ("Streamed during recording", 0.078, "78 ms"),
]

# EXP-02 — telegram-remote-claude, lines of Python.
# Source: job-agent docs/work-inventory-verified.md (git-verified, Tier 1).
TEST_LINES = 31_849
SOURCE_LINES = 21_898
TEST_FUNCTIONS = 1_509


def _svg(width: int, height: int, title: str, style: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-labelledby="t">\n'
        f'<title id="t">{title}</title>\n'
        f"<style>\n{style}\n</style>\n"
        f"{body}\n"
        "</svg>\n"
    )


def _fonts() -> str:
    return (
        f".sans {{ font-family: {SANS}; }}\n"
        f".serif {{ font-family: {SERIF}; }}\n"
        f".mono {{ font-family: {MONO}; }}"
    )


def cover(p: dict[str, str]) -> str:
    # 800 wide, not 1200: on a 390 px phone the content column is ~358 px, so every
    # essential line still lands at 9 px or more (tests/test_readme.py checks this).
    w, h = 800, 440
    style = (
        _fonts()
        + f"""
.label {{ font-size: 16px; letter-spacing: 3px; fill: {p["ink2"]}; }}
.page {{ font-size: 16px; fill: {p["pencil"]}; }}
.name {{ font-size: 68px; font-weight: 700; fill: {p["ink"]}; }}
.program {{ font-size: 27px; font-style: italic; fill: {p["ink"]}; }}
.thesis {{ font-size: 22px; fill: {p["ink2"]}; }}
.prompt {{ fill: {p["accent"]}; }}
.pencil {{ font-size: 21px; fill: {p["pencil"]}; }}
.stamp-big {{ font-size: 25px; font-weight: 700; letter-spacing: 2px; fill: {p["stamp"]}; }}
.stamp-small {{ font-size: 22px; font-weight: 700; letter-spacing: 2px; fill: {p["stamp"]}; }}
.ink-line {{
  fill: none; stroke: {p["accent"]}; stroke-width: 4.5; stroke-linecap: round;
  stroke-dasharray: 520; stroke-dashoffset: 0;
  animation: draw 1.6s ease-out 0.3s both;
}}
@keyframes draw {{ from {{ stroke-dashoffset: 520; }} to {{ stroke-dashoffset: 0; }} }}
@media (prefers-reduced-motion: reduce) {{ .ink-line {{ animation: none; }} }}"""
    )
    holes = "".join(
        f'<circle cx="40" cy="{y}" r="10" fill="{p["hole"]}" stroke="{p["rule"]}" stroke-width="1.5"/>'
        for y in (110, 220, 330)
    )
    body = f"""<defs>
  <pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse">
    <path d="M22 0H0V22" fill="none" stroke="{p["grid"]}" stroke-width="1"/>
  </pattern>
</defs>
<rect width="{w}" height="{h}" rx="16" fill="{p["paper"]}"/>
<rect width="{w}" height="{h}" rx="16" fill="url(#grid)"/>
<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="15.5" fill="none" stroke="{p["rule"]}" stroke-width="1.5"/>
<line x1="78" y1="0" x2="78" y2="{h}" stroke="{p["margin"]}" stroke-width="2" opacity="0.75"/>
<line x1="82" y1="0" x2="82" y2="{h}" stroke="{p["margin"]}" stroke-width="1" opacity="0.5"/>
{holes}
<text x="110" y="56" class="mono label">LAB NOTEBOOK</text>
<text x="772" y="56" class="mono page" text-anchor="end">No. 01 · 2026</text>
<text x="110" y="148" class="serif name">Bhanu Pratap</text>
<path class="ink-line" d="M114 172 C 230 162, 380 178, 588 164"/>
<text x="110" y="218" class="serif program">M.S. Artificial Intelligence · Northeastern University</text>
<text x="110" y="264" class="mono thesis"><tspan class="prompt">&gt;</tspan> I build ML and LLM systems, then measure them.</text>
<g transform="rotate(-4 250 352)" opacity="0.88">
  <rect x="110" y="306" width="280" height="92" rx="9" fill="none" stroke="{p["stamp"]}" stroke-width="4"/>
  <rect x="118" y="314" width="264" height="76" rx="5" fill="none" stroke="{p["stamp"]}" stroke-width="1.5"/>
  <text x="250" y="346" class="mono stamp-big" text-anchor="middle">OPEN TO ROLES</text>
  <text x="250" y="378" class="mono stamp-small" text-anchor="middle">FROM JAN 2027</text>
</g>
<text x="420" y="360" class="mono pencil">← graduating Dec 2026</text>
<text x="772" y="418" class="mono page" text-anchor="end">p. 01</text>"""
    title = "Lab notebook cover: Bhanu Pratap, M.S. Artificial Intelligence, Northeastern University, graduating December 2026. Stamped: open to roles from January 2027."
    return _svg(w, h, title, style, body)


def _card(p: dict[str, str], w: int, h: int) -> str:
    """Paper card with two strips of tape: the chart is pasted into the notebook."""
    return f"""<rect width="{w}" height="{h}" rx="14" fill="{p["paper"]}"/>
<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="13.25" fill="none" stroke="{p["rule"]}" stroke-width="1.5"/>
<rect x="16" y="-6" width="74" height="22" fill="{p["tape"]}" opacity="0.8" transform="rotate(-8 53 5)"/>
<rect x="{w - 90}" y="-6" width="74" height="22" fill="{p["tape"]}" opacity="0.8" transform="rotate(7 {w - 53} 5)"/>"""


def _chart_style(p: dict[str, str]) -> str:
    # Charts are 600 wide and shown at up to 640 px, so on a phone they scale by
    # about 0.6 and the smallest text (ticks, 16 px) still renders near 9.5 px.
    return (
        _fonts()
        + f"""
.title {{ font-size: 28px; font-weight: 600; fill: {p["ink"]}; }}
.sub {{ font-size: 17px; fill: {p["ink2"]}; }}
.row {{ font-size: 18px; fill: {p["ink"]}; }}
.tick {{ font-size: 16px; fill: {p["ink2"]}; font-variant-numeric: tabular-nums; }}
.value {{ font-size: 19px; font-weight: 600; fill: {p["ink"]}; }}
.note {{ font-size: 18px; font-weight: 400; fill: {p["ink2"]}; }}
.hero {{ font-size: 40px; font-weight: 600; fill: {p["ink"]}; }}
.caption {{ font-size: 17px; fill: {p["ink2"]}; }}"""
    )


def _fmt(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".")


def _one_sig_fig(x: float) -> float:
    """Round to one significant figure, so 1013 reads as 1,000 and 87 as 90."""
    scale = 10 ** math.floor(math.log10(x))
    return round(x / scale) * scale


def _check_domain(values: list[float], lo: float, hi: float, chart: str) -> None:
    """A value outside the axis would plot off the card, so fail the build instead."""
    outside = [v for v in values if not lo <= v <= hi]
    if outside:
        raise ValueError(
            f"{chart}: {outside} outside the axis range {lo}..{hi}; widen the axis"
        )


def latency_chart(p: dict[str, str]) -> str:
    w, h = 600, 330
    x0, x1 = 44, 566
    lo, hi = -2, 2  # log10 seconds: 10 ms .. 100 s

    _check_domain([s for _, s, _ in LATENCY], 10.0**lo, 10.0**hi, "exp01-latency")

    def x(seconds: float) -> float:
        return x0 + (math.log10(seconds) - lo) / (hi - lo) * (x1 - x0)

    parts = [_card(p, w, h)]
    parts.append(
        '<text x="28" y="48" class="sans title">Wait after you stop talking</text>'
    )
    parts.append(
        '<text x="28" y="76" class="sans sub">Instant Notes · log scale, lower is better</text>'
    )
    for exp, label in zip(
        range(lo, hi + 1), ["10 ms", "100 ms", "1 s", "10 s", "100 s"]
    ):
        gx = _fmt(x(10.0**exp))
        parts.append(
            f'<line x1="{gx}" y1="96" x2="{gx}" y2="282" stroke="{p["grid"]}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{gx}" y="308" class="mono tick" text-anchor="middle">{label}</text>'
        )
    # Each row's label sits above its track, so the axis gets the full card width.
    for i, (row, seconds, value) in enumerate(LATENCY):
        label_y = 116 + i * 60
        cy = label_y + 24
        cx = x(seconds)
        last = i == len(LATENCY) - 1
        fill = p["accent"] if last else p["muted"]
        parts.append(f'<text x="{x0}" y="{label_y}" class="sans row">{row}</text>')
        parts.append(
            f'<circle cx="{_fmt(cx)}" cy="{cy}" r="7" fill="{fill}" stroke="{p["paper"]}" stroke-width="2.5"/>'
        )
        if cx + 80 > w - 16:
            parts.append(
                f'<text x="{_fmt(cx - 16)}" y="{cy + 6}" class="sans value" text-anchor="end">{value}</text>'
            )
        elif last:
            ratio = _one_sig_fig(LATENCY[0][1] / seconds)
            parts.append(
                f'<text x="{_fmt(cx + 16)}" y="{cy + 6}" class="sans value">{value}'
                f'<tspan class="note" dx="8">· about {ratio:,.0f}× less waiting</tspan></text>'
            )
        else:
            parts.append(
                f'<text x="{_fmt(cx + 16)}" y="{cy + 6}" class="sans value">{value}</text>'
            )
    title = "Instant Notes, wait after you stop talking: local Whisper on CPU 79 s, Groq Whisper batch 787 ms, streamed during recording 78 ms."
    return _svg(w, h, title, _chart_style(p), "\n".join(parts))


def _bar(x0: float, y: float, length: float, thick: float, fill: str) -> str:
    """Bar with a 4px rounded data end, square at the baseline."""
    r = 4
    x1 = x0 + length
    return (
        f'<path d="M{_fmt(x0)} {_fmt(y)} H{_fmt(x1 - r)} Q{_fmt(x1)} {_fmt(y)} {_fmt(x1)} {_fmt(y + r)} '
        f'V{_fmt(y + thick - r)} Q{_fmt(x1)} {_fmt(y + thick)} {_fmt(x1 - r)} {_fmt(y + thick)} H{_fmt(x0)} Z" fill="{fill}"/>'
    )


def tests_chart(p: dict[str, str]) -> str:
    w, h = 600, 300
    x0, x1, domain = 100, 520, 35_000

    _check_domain([TEST_LINES, SOURCE_LINES], 0, domain, "exp02-tests")

    def length(v: float) -> float:
        return v / domain * (x1 - x0)

    ratio = TEST_LINES / SOURCE_LINES
    parts = [_card(p, w, h)]
    parts.append(
        '<text x="28" y="48" class="sans title">More test code than product code</text>'
    )
    parts.append(
        '<text x="28" y="76" class="sans sub">telegram-remote-claude · lines of Python</text>'
    )
    for v in range(0, 30_001, 10_000):
        gx = _fmt(x0 + length(v))
        parts.append(
            f'<line x1="{gx}" y1="92" x2="{gx}" y2="178" stroke="{p["grid"]}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{gx}" y="202" class="mono tick" text-anchor="middle">{v:,}</text>'
        )
    for i, (row, value, fill) in enumerate(
        [("Tests", TEST_LINES, p["accent"]), ("Source", SOURCE_LINES, p["muted"])]
    ):
        y = 100 + i * 44
        parts.append(f'<text x="28" y="{y + 17}" class="sans row">{row}</text>')
        parts.append(_bar(x0, y, length(value), 22, fill))
        parts.append(
            f'<text x="{_fmt(x0 + length(value) + 12)}" y="{y + 17}" class="sans value">{value:,}</text>'
        )
    parts.append(f'<text x="28" y="264" class="sans hero">{ratio:.2f} : 1</text>')
    parts.append(
        '<text x="222" y="244" class="sans caption">lines of tests per line of source</text>'
    )
    parts.append(
        f'<text x="222" y="268" class="sans caption">{TEST_FUNCTIONS:,} test functions</text>'
    )
    title = f"telegram-remote-claude: {TEST_LINES:,} lines of tests against {SOURCE_LINES:,} lines of source, a {ratio:.2f} to 1 ratio, {TEST_FUNCTIONS:,} test functions."
    return _svg(w, h, title, _chart_style(p), "\n".join(parts))


ASSETS = {
    "cover": cover,
    "exp01-latency": latency_chart,
    "exp02-tests": tests_chart,
}


def build(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, render in ASSETS.items():
        for theme, palette in PALETTES.items():
            path = out_dir / f"{name}-{theme}.svg"
            path.write_text(render(palette), encoding="utf-8")
            written.append(path)
    return written


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "assets"
    for path in build(target):
        print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
