"""
Public standalone dashboard generator for FlexDash.

Creates a single HTML file that can be opened via file:// without a web server.
It inlines:
  - CSS (styles/themes/ade-brand)
  - Chart.js vendor bundle
  - dashboard JS (data.js, charts.js, main.js)
  - ADE logo (as a data URI)

The public dashboard HTML shell (dashboard/index.html) is intentionally kept
static; the pipeline normally updates dashboard/data/*.json and dashboard/js/data.js.
This generator produces a "baked" single-file version for easy sharing/presentation.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class PublicStandaloneOutputs:
    standalone_path: Path


_CHART_FALLBACK_BLOCK = """<script>
      // Fallback if the local vendor bundle is missing.
      if (typeof Chart === 'undefined') {
        var s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
        document.head.appendChild(s);
      }
    </script>"""


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _encode_png_data_uri(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return None


def generate_public_dashboard_standalone(*, project_root: Path) -> PublicStandaloneOutputs:
    project_root = Path(project_root)
    dashboard_dir = project_root / "dashboard"

    html_src = dashboard_dir / "index.html"
    if not html_src.exists():
        raise FileNotFoundError(f"Public dashboard HTML not found: {html_src}")

    css_paths = [
        dashboard_dir / "css" / "styles.css",
        dashboard_dir / "css" / "themes.css",
        dashboard_dir / "css" / "ade-brand.css",
    ]
    js_paths = [
        dashboard_dir / "js" / "vendor" / "chart.umd.min.js",
        dashboard_dir / "js" / "data.js",
        dashboard_dir / "js" / "charts.js",
        dashboard_dir / "js" / "main.js",
    ]

    inline_css = "\n\n".join(_read_text(p) for p in css_paths if p.exists())
    inline_js = "\n\n".join(_read_text(p) for p in js_paths if p.exists())

    html = _read_text(html_src)

    # Drop external asset links (we inline everything).
    html = html.replace('<link rel="stylesheet" href="css/styles.css">', "")
    html = html.replace('<link rel="stylesheet" href="css/themes.css">', "")
    html = html.replace('<link rel="stylesheet" href="css/ade-brand.css">', "")
    html = html.replace('<script src="js/vendor/chart.umd.min.js"></script>', "")
    html = html.replace(_CHART_FALLBACK_BLOCK, "")
    html = html.replace('    <script src="js/data.js"></script>', "")
    html = html.replace('    <script src="js/main.js"></script>', "")
    html = html.replace('    <script src="js/charts.js"></script>', "")

    # Embed logo for offline use.
    logo_path = dashboard_dir / "ADE Demand Logo.png"
    logo_data_uri = _encode_png_data_uri(logo_path)
    if logo_data_uri:
        html = html.replace('src="ADE Demand Logo.png"', f'src="{logo_data_uri}"')

    # Inline CSS into <head> and JS before </body>.
    html = html.replace("</head>", f"  <style>\n{inline_css}\n  </style>\n</head>")
    html = html.replace("</body>", f"  <script>\n{inline_js}\n  </script>\n</body>")

    out_path = dashboard_dir / "public_dashboard_standalone.html"
    out_path.write_text(html, encoding="utf-8")

    return PublicStandaloneOutputs(standalone_path=out_path)

