"""Render README.md with GitHub's own markdown API into preview/index.html.

Run from the repo root:  python3 scripts/preview.py
Then serve the repo root (python3 -m http.server) and open /preview/index.html.
The page follows the OS colour scheme, the same as the <picture> elements in the
README, so you can check light and dark by switching the scheme.

It uses `gh` (authenticated) for rendering and github-markdown-css for styling.
This is close to GitHub's rendering, not identical to it. The live profile is the final check.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = "https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.9.0/github-markdown.min.css"

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Profile preview</title>
<link rel="stylesheet" href="{css}">
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin: 0; background: #ffffff; }}
  @media (prefers-color-scheme: dark) {{ body {{ background: #0d1117; }} }}
  .card {{ box-sizing: border-box; max-width: 896px; margin: 24px auto; padding: 24px;
          border: 1px solid #d1d9e0; border-radius: 6px; }}
  @media (prefers-color-scheme: dark) {{ .card {{ border-color: #3d444d; }} }}
  @media (max-width: 600px) {{ .card {{ margin: 0; border: 0; padding: 16px; }} }}
</style>
</head>
<body>
<article class="card markdown-body">
{html}
</article>
</body>
</html>
"""


def render() -> Path:
    html = subprocess.run(
        [
            "gh",
            "api",
            "markdown",
            "-f",
            "mode=gfm",
            "-F",
            f"text=@{ROOT / 'README.md'}",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    # The page lives in preview/, so repo-relative asset paths need one level up.
    html = html.replace('src="assets/', 'src="../assets/').replace(
        'srcset="assets/', 'srcset="../assets/'
    )
    out = ROOT / "preview" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(PAGE.format(css=CSS, html=html), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(render().relative_to(ROOT))
