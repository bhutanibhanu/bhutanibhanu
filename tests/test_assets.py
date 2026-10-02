"""Guards for the generated SVG assets: fresh, well-formed, and safe to show through <img>."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SVG_NS = "{http://www.w3.org/2000/svg}"


def test_assets_are_fresh(tmp_path, builder):
    built = {p.name: p.read_bytes() for p in builder.build(tmp_path)}
    committed = {p.name: p.read_bytes() for p in ASSETS.glob("*.svg")}
    assert built.keys() == committed.keys(), (
        "assets/ is out of sync with ASSETS in build_assets.py"
    )
    stale = [name for name in built if built[name] != committed[name]]
    assert not stale, f"rerun `python3 scripts/build_assets.py`; stale: {stale}"


@pytest.mark.parametrize("svg", sorted(ASSETS.glob("*.svg")), ids=lambda p: p.name)
def test_svg_is_safe_for_img(svg):
    text = svg.read_text(encoding="utf-8")
    root = ET.fromstring(text)
    assert root.tag == f"{SVG_NS}svg"
    assert root.get("viewBox"), "needs a viewBox to scale"
    tags = {el.tag.removeprefix(SVG_NS) for el in root.iter()}
    assert not tags & {"script", "foreignObject", "image", "a", "use", "iframe"}
    handlers = [
        (el.tag, a)
        for el in root.iter()
        for a in el.attrib
        if a.lower().startswith("on")
    ]
    assert not handlers, f"event handler attributes: {handlers}"
    stripped = text.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert "http" not in stripped, "no external URLs: GitHub serves SVGs sandboxed"
    assert "@import" not in stripped and "@font-face" not in stripped
    if "animation" in stripped:
        assert "prefers-reduced-motion" in stripped, (
            "animated SVGs must honour reduced motion"
        )


def test_ratio_label_rounds_to_one_significant_figure(builder):
    assert [builder._one_sig_fig(v) for v in (1012.8, 87, 9.4, 451)] == [
        1000,
        90,
        9,
        500,
    ]


def test_values_outside_the_axis_fail_the_build(monkeypatch, builder):
    monkeypatch.setattr(builder, "LATENCY", [("too slow", 250.0, "250 s")])
    with pytest.raises(ValueError, match="outside the axis"):
        builder.latency_chart(builder.PALETTES["light"])
