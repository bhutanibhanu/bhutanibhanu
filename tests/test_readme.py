"""Guards for the profile README.

GitHub's actual rendering isn't covered here. That gets checked with preview
screenshots before the push and screenshots of the live profile after it.
"""

from __future__ import annotations

import re
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")

ALLOWED_LINKS = {
    "github.com": "/bhutanibhanu",
    "www.linkedin.com": "/in/bhanu-pratap24",
}
EMAIL = "pratap.b@northeastern.edu"
TEXT_SUFFIXES = {".md", ".svg", ".py", ".toml", ".yml", ".json", ".txt"}


def _slug(heading: str) -> str:
    """GitHub's heading anchor: lowercase, punctuation and symbols dropped, spaces to hyphens."""
    kept = [
        c
        for c in heading.strip().lower()
        if c in "-_ " or unicodedata.category(c)[0] in "LNM"
    ]
    return "".join(kept).replace(" ", "-")


def _heading_text(raw: str) -> str:
    """The visible text of a markdown heading, which is what GitHub slugs."""
    text = re.sub(r"\s+#+\s*$", "", raw)  # closing hashes
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # [text](url) -> text
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"[*`]", "", text)


def _headings(markdown: str) -> list[str]:
    slugs, seen, fenced = [], {}, False
    for line in markdown.splitlines():
        if line.startswith("```"):
            fenced = not fenced
            continue
        m = re.match(r"#{1,6}\s+(.*)", line)
        if m and not fenced:
            base = _slug(_heading_text(m.group(1)))
            n = seen.get(base, 0)
            slugs.append(base if n == 0 else f"{base}-{n}")
            seen[base] = n + 1
    return slugs


def _tracked_text_files():
    names = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    for name in names:
        path = ROOT / name
        if path.suffix in TEXT_SUFFIXES and path.is_file():
            yield path


def _picture(asset: str) -> str:
    block = re.search(
        rf"<picture>(?:(?!</picture>).)*{re.escape(asset)}.*?</picture>",
        README,
        re.DOTALL,
    )
    assert block, f"no <picture> for {asset}"
    return block.group(0)


def test_slug_matches_github_rules():
    assert _slug(_heading_text("EXP-04 · Fraud at 0.172%")) == "exp-04--fraud-at-0172"
    assert _slug(_heading_text("snake_case `code` ##")) == "snake_case-code"
    assert _slug(_heading_text("See [the repo](https://example.com)")) == "see-the-repo"


def test_every_picture_pairs_dark_and_light():
    pictures = re.findall(r"<picture>(.*?)</picture>", README, re.DOTALL)
    assert len(pictures) >= 3
    for block in pictures:
        dark = re.search(
            r'<source media="\(prefers-color-scheme: dark\)" srcset="([^"]+)"', block
        )
        light = re.search(r'<img[^>]*\bsrc="([^"]+)"', block)
        assert dark and light, block
        assert dark.group(1).replace("-dark.", "-light.") == light.group(1)


def test_every_image_has_real_alt_text():
    images = re.findall(r"<img\b[^>]*>", README)
    assert images
    for tag in images:
        alt = re.search(r'\balt="([^"]+)"', tag)
        assert alt and len(alt.group(1)) > 20, f"alt text must carry the content: {tag}"


def test_chart_numbers_in_readme_match_the_generator(builder):
    latency = _picture("exp01-latency")
    for _, _, label in builder.LATENCY:
        assert label in latency, f"latency alt text is missing {label}"
    tests = _picture("exp02-tests")
    ratio = builder.TEST_LINES / builder.SOURCE_LINES
    for value in (
        f"{builder.TEST_LINES:,}",
        f"{builder.SOURCE_LINES:,}",
        f"{builder.TEST_FUNCTIONS:,}",
        f"{ratio:.2f}",
    ):
        assert value in tests, f"tests alt text is missing {value}"
    body = README.replace("&nbsp;", " ")
    for value in (
        builder.LATENCY[0][2],
        builder.LATENCY[-1][2],
        f"{builder.TEST_FUNCTIONS:,}",
    ):
        assert value in body.replace(latency, "").replace(tests, ""), (
            f"prose is missing {value}"
        )


def test_local_images_exist():
    refs = re.findall(r'(?:src|srcset)="([^"]+)"', README)
    assert refs
    for ref in refs:
        assert not ref.startswith("http"), f"use a repo-relative path: {ref}"
        assert (ROOT / ref).is_file(), ref


def test_anchor_links_resolve():
    # GitHub prefixes heading ids with "user-content-". On a repo page its JS maps
    # "#slug" to that id, but the profile page doesn't, so links name the real id.
    slugs = set(_headings(README))
    links = re.findall(r"\]\(#([^)]+)\)", README) + re.findall(
        r'href="#([^"]+)"', README
    )
    assert links
    unprefixed = sorted(link for link in links if not link.startswith("user-content-"))
    assert not unprefixed, (
        f"use #user-content-<slug> so links work on the profile page: {unprefixed}"
    )
    missing = sorted({link.removeprefix("user-content-") for link in links} - slugs)
    assert not missing, f"anchors with no matching heading: {missing}"


def test_external_links_are_expected():
    for url in re.findall(r"https?://[^\s)\"'<>]+", README):
        parsed = urlparse(url)
        assert parsed.scheme == "https", url
        assert parsed.netloc in ALLOWED_LINKS, url
        prefix = ALLOWED_LINKS[parsed.netloc]
        assert parsed.path == prefix or parsed.path.startswith(prefix + "/"), url
    assert not re.findall(r"(?<![/\w.])www\.", README), (
        "bare www. autolinks bypass the allowlist"
    )
    mails = set(re.findall(r"mailto:([^\s)\"'>]+)", README))
    assert mails == {EMAIL}


def test_no_phone_number_in_tracked_files():
    phone = re.compile(r"\(?\b\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b|\+?\d{10,}")
    hits = [
        f"{path.relative_to(ROOT)}: {m.group(0)}"
        for path in _tracked_text_files()
        for m in phone.finditer(path.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert not hits, hits


def test_pipeline_notes_stay_out_of_the_public_repo():
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout
    assert "docs/features/" not in tracked, (
        "planning notes are private; keep docs/features/ gitignored"
    )


PHONE_CONTENT_PX = 358  # a 390 px phone minus GitHub's 16 px side padding
MIN_TEXT_PX = 9
DECORATIVE = {
    "label",
    "page",
}  # "LAB NOTEBOOK", "No. 01", "p. 01": ornament, not content


def test_svg_text_is_legible_on_a_phone():
    for block in re.findall(r"<picture>.*?</picture>", README, re.DOTALL):
        img = re.search(r'<img[^>]*\bsrc="([^"]+)"[^>]*\bwidth="([^"]+)"', block)
        assert img, f"every chart needs an explicit width: {block}"
        src, width = img.groups()
        shown = (
            PHONE_CONTENT_PX if width == "100%" else min(int(width), PHONE_CONTENT_PX)
        )
        svg = (ROOT / src).read_text(encoding="utf-8")
        view_w = float(re.search(r'viewBox="0 0 ([\d.]+) ', svg).group(1))
        sizes = re.findall(r"\.([\w-]+) \{[^}]*?font-size: ([\d.]+)px", svg)
        assert sizes, src
        for cls, size in sizes:
            if cls in DECORATIVE:
                continue
            px = float(size) * shown / view_w
            assert px >= MIN_TEXT_PX, f"{src} .{cls} renders at {px:.1f}px on a phone"
