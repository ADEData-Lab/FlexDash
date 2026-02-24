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
import json
import re
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


def _load_combined_dashboard_data(*, project_root: Path) -> dict:
    """
    Load the combined dashboard payload from the pipeline outputs.

    Prefer JSON under dashboard/data/; fall back to parsing dashboard/js/data.js.
    """
    project_root = Path(project_root)
    dashboard_dir = project_root / "dashboard"

    json_path = dashboard_dir / "data" / "dashboard_data.json"
    if json_path.exists():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    js_path = dashboard_dir / "js" / "data.js"
    if js_path.exists():
        try:
            text = js_path.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"const\s+DASHBOARD_DATA\s*=\s*(\{.*\});\s*$", text, flags=re.S | re.M)
            if m:
                return json.loads(m.group(1))
        except Exception:
            pass

    return {}


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


_STEERING_SAFE_FORBIDDEN_SUBSTRINGS = [
    # Data object / disclosure control internals (must not appear in steering-safe distribution build)
    "DASHBOARD_DATA",
    "asset_breakdown",
    "asset_group_breakdown",
    "sector_breakdown",
    "sector_asset_breakdown",
    "sector_asset_group_breakdown",
    "capacity_range",
    "contributors_k",
    "k=",
    "benchmarks",
]


def generate_public_dashboard_standalone_steering_safe(*, project_root: Path) -> PublicStandaloneOutputs:
    """
    Generate a steering-safe, single-file public dashboard.

    This build is intended for circulation to steering group members where disaggregation
    must be impossible. It intentionally includes only a small set of top-level aggregates
    and does not embed any suppressed values, breakdowns, contributor names, or k-signals.
    """
    project_root = Path(project_root)
    dashboard_dir = project_root / "dashboard"

    css_paths = [
        dashboard_dir / "css" / "styles.css",
        dashboard_dir / "css" / "themes.css",
        dashboard_dir / "css" / "ade-brand.css",
    ]
    inline_css = "\n\n".join(_read_text(p) for p in css_paths if p.exists())

    # Embed logo for offline use.
    logo_path = dashboard_dir / "ADE Demand Logo.png"
    logo_data_uri = _encode_png_data_uri(logo_path)
    logo_src = logo_data_uri or "ADE Demand Logo.png"

    combined = _load_combined_dashboard_data(project_root=project_root)
    metrics = (combined.get("metrics") or {}) if isinstance(combined, dict) else {}

    study_period = str(combined.get("study_period") or "Nov 2024–Feb 2025")
    generated_at = str(combined.get("generated_at") or "")

    total_available_mw = metrics.get("total_available_mw")
    total_available_is_illustrative = bool(metrics.get("total_available_mw_illustrative"))

    contributor_count = metrics.get("contributor_count")

    def _fmt_int(val) -> str:
        try:
            n = int(round(float(val)))
            return f"{n:,}"
        except Exception:
            return "--"

    total_available_display = "--"
    if not total_available_is_illustrative and total_available_mw is not None:
        total_available_display = _fmt_int(total_available_mw)

    contributor_display = _fmt_int(contributor_count)

    generated_display = generated_at or "--"

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dashboard-dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GB Flexibility Dashboard (Steering-Safe) | ADE</title>
  <style>
{inline_css}
  </style>
</head>
<body>
  <header class="header">
    <div class="header-content">
      <div class="logo">
        <img src="{logo_src}" alt="ADE Demand" class="logo-img">
      </div>
      <div class="header-actions">
        <span class="ade-badge ade-badge-illustrative">Steering-safe distribution build</span>
      </div>
    </div>
  </header>

  <main class="main">
    <section class="page active">
      <div class="page-header">
        <h1>GB Flexibility Dashboard</h1>
        <p class="subtitle">Phase 1 Baseline Assessment</p>
        <div class="study-badge">
          <span class="badge-label">Study Period:</span>
          <span class="badge-value">{study_period}</span>
        </div>
      </div>

      <div class="narrative-card">
        <h3>Important note (confidentiality and competition compliance)</h3>
        <p>
          This file is a steering-group circulation version designed to prevent disaggregation.
          It contains only high-level aggregates and does not include contributor identities,
          contributor-level values, k-threshold signals, or breakdowns by sector, asset class, or service.
          It is provided for research and policy discussion only and is not intended for commercial decision-making.
        </p>
      </div>

      <div class="metrics-section">
        <h3 class="section-title">Headline (aggregated)</h3>
        <div class="metrics-grid">
          <div class="metric-card primary">
            <div class="metric-icon">⚡</div>
            <div class="metric-value">{total_available_display}</div>
            <div class="metric-label">Total Available (MW)</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">🏢</div>
            <div class="metric-value">{contributor_display}</div>
            <div class="metric-label">Data Contributors (count)</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">🕒</div>
            <div class="metric-value" style="font-size: 1.1rem; line-height: 1.4;">{generated_display}</div>
            <div class="metric-label">Generated</div>
          </div>
        </div>
      </div>

      <div class="context-card">
        <h3>What is not shown in this version</h3>
        <ul class="caveat-list">
          <li><strong>No breakdowns:</strong> Sector, asset class/group, service, and benchmark comparisons are intentionally omitted.</li>
          <li><strong>No suppressed values:</strong> Metrics that fail disclosure rules are not published in any form (including ranges).</li>
          <li><strong>No inference:</strong> This version avoids totals + subtotals combinations that could enable back-calculation.</li>
        </ul>
      </div>

      <div class="footer" style="margin-top: 30px;">
        <p style="opacity: 0.8;">Contact: data@theade.co.uk</p>
      </div>
    </section>
  </main>
</body>
</html>
"""

    # Leak check (defence-in-depth): ensure no disallowed tokens are present.
    lowered = html.lower()
    for token in _STEERING_SAFE_FORBIDDEN_SUBSTRINGS:
        if token.lower() in lowered:
            raise ValueError(
                f"Steering-safe dashboard generation failed leak check: found forbidden token '{token}'."
            )

    out_path = dashboard_dir / "public_dashboard_standalone_steering_safe.html"
    out_path.write_text(html, encoding="utf-8")

    return PublicStandaloneOutputs(standalone_path=out_path)


_RELEASE_SAFE_PAYLOAD_FORBIDDEN_SUBSTRINGS = [
    # Do not embed the full dashboard payload or disclosure-control internals.
    "DASHBOARD_DATA",
    "asset_breakdown",
    "sector_asset_breakdown",
    "sector_asset_group_breakdown",
    "benchmarks",
    "contributors_k",
    # Do not embed per-cell disclosure cues or range buckets in a release-safe build.
    "\"k\":",
    "\"k_capacity_mw\":",
    "\"k_count\":",
    "capacity_range",
    "count_range",
    # Do not embed contributor identifiers.
    "contributor_id",
    "contributor_name",
    "CONTRIB_",
]


def generate_public_dashboard_standalone_release_safe(
    *,
    project_root: Path,
    payload: dict,
) -> PublicStandaloneOutputs:
    """
    Generate a release-safe, single-file public dashboard.

    This build is designed for circulation where disaggregation risk must be minimised.
    It:
      - embeds only disclosure-safe aggregates (no ranges, no k-signals)
      - omits any split unless every cell in that split is safe
      - contains no contributor identities or per-contributor values

    Note: This function does not compute disclosure; it assumes `payload` is already sanitised.
    """
    project_root = Path(project_root)
    dashboard_dir = project_root / "dashboard"

    css_paths = [
        dashboard_dir / "css" / "styles.css",
        dashboard_dir / "css" / "themes.css",
        dashboard_dir / "css" / "ade-brand.css",
    ]
    inline_css = "\n\n".join(_read_text(p) for p in css_paths if p.exists())

    vendor_path = dashboard_dir / "js" / "vendor" / "chart.umd.min.js"
    vendor_js = _read_text(vendor_path) if vendor_path.exists() else ""

    # Embed logo for offline use.
    logo_path = dashboard_dir / "ADE Demand Logo.png"
    logo_data_uri = _encode_png_data_uri(logo_path)
    logo_src = logo_data_uri or "ADE Demand Logo.png"

    # Leak check: validate payload does not include forbidden tokens.
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    lowered = payload_json.lower()
    for token in _RELEASE_SAFE_PAYLOAD_FORBIDDEN_SUBSTRINGS:
        if token.lower() in lowered:
            raise ValueError(
                f"Release-safe dashboard generation failed payload leak check: found forbidden token '{token}'."
            )

    study_period = str(payload.get("study_period") or "Nov 2024–Feb 2025")
    generated_at = str(payload.get("generated_at") or "--")

    headline = payload.get("headline") or {}
    total_available_mw = headline.get("total_available_mw")
    contributor_count = headline.get("contributor_count")

    def _fmt_int(val) -> str:
        try:
            n = int(round(float(val)))
            return f"{n:,}"
        except Exception:
            return "--"

    sector_rows = payload.get("sector_breakdown") or []
    asset_group_rows = payload.get("asset_group_breakdown") or []

    sector_enabled = bool(sector_rows)
    asset_groups_enabled = bool(asset_group_rows)

    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dashboard-dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GB Flexibility Dashboard (Release-Safe) | ADE</title>
  <style>
{inline_css}
  </style>
</head>
<body>
  <header class="header">
    <div class="header-content">
      <div class="logo">
        <img src="{logo_src}" alt="ADE Demand" class="logo-img">
      </div>
      <div class="header-actions">
        <span class="ade-badge ade-badge-illustrative">Release-safe distribution build</span>
      </div>
    </div>
  </header>

  <main class="main">
    <section class="page active">
      <div class="page-header">
        <h1>GB Flexibility Dashboard</h1>
        <p class="subtitle">Phase 1 Baseline Assessment</p>
        <div class="study-badge">
          <span class="badge-label">Study Period:</span>
          <span class="badge-value">{study_period}</span>
        </div>
      </div>

      <div class="narrative-card">
        <h3>Important note (confidentiality and competition compliance)</h3>
        <p>
          This file is a distribution version designed to minimise disaggregation risk. It contains only
          disclosure-safe aggregates and includes no contributor identities, no per-contributor values, no
          per-cell coverage counts, and no range buckets derived from suppressed totals.
        </p>
        <p style="margin-top: 10px; opacity: 0.9;">
          Where a split would not be disclosure-safe (minimum contributor threshold and dominance safeguards),
          it is withheld entirely in this version.
        </p>
      </div>

      <div class="metrics-section">
        <h3 class="section-title">Headline (aggregated)</h3>
        <div class="metrics-grid">
          <div class="metric-card primary">
            <div class="metric-icon">⚡</div>
            <div class="metric-value">{_fmt_int(total_available_mw)}</div>
            <div class="metric-label">Total Available (MW)</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">🏢</div>
            <div class="metric-value">{_fmt_int(contributor_count)}</div>
            <div class="metric-label">Data Contributors (count)</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">🕒</div>
            <div class="metric-value" style="font-size: 1.1rem; line-height: 1.4;">{generated_at}</div>
            <div class="metric-label">Generated</div>
          </div>
        </div>
      </div>

      <div class="metrics-section">
        <h3 class="section-title">Disclosure-safe splits</h3>
        <p class="chart-note">
          Splits are shown only when every cell in the split is disclosure-safe. No partial tables are shown.
        </p>

        <div class="two-column" style="display:grid; grid-template-columns: 1fr 1fr; gap: 18px;">
          <div class="context-card">
            <h3>By sector</h3>
            <div id="sector-suppressed" style="display:{'none' if sector_enabled else 'block'}; opacity: 0.9;">
              Not shown due to confidentiality safeguards.
            </div>
            <div id="sector-block" style="display:{'block' if sector_enabled else 'none'};">
              <div class="chart-container" style="height: 260px;">
                <canvas id="sector-chart"></canvas>
              </div>
              <div class="table-container" style="margin-top: 10px;">
                <table class="data-table">
                  <thead><tr><th>Sector</th><th style="text-align:right;">Available (MW)</th></tr></thead>
                  <tbody id="sector-table-body"></tbody>
                </table>
              </div>
            </div>
          </div>

          <div class="context-card">
            <h3>By asset group</h3>
            <div id="asset-group-suppressed" style="display:{'none' if asset_groups_enabled else 'block'}; opacity: 0.9;">
              Not shown due to confidentiality safeguards.
            </div>
            <div id="asset-group-block" style="display:{'block' if asset_groups_enabled else 'none'};">
              <div class="chart-container" style="height: 260px;">
                <canvas id="asset-group-chart"></canvas>
              </div>
              <div class="table-container" style="margin-top: 10px;">
                <table class="data-table">
                  <thead><tr><th>Asset group</th><th style="text-align:right;">Available (MW)</th></tr></thead>
                  <tbody id="asset-group-table-body"></tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="context-card" style="margin-top: 18px;">
        <h3>Methods and limitations (summary)</h3>
        <ul class="caveat-list">
          <li><strong>Scope:</strong> Phase 1 proof-of-concept covering contributors in the study period.</li>
          <li><strong>Disclosure controls:</strong> Splits are withheld when contributor coverage is low or where a small number of contributors account for most of a total (dominance safeguard).</li>
          <li><strong>Interpretation:</strong> Values represent a baseline view of currently available flexibility within the contributor sample; they should not be interpreted as a definitive GB-wide total.</li>
        </ul>
      </div>

      <div class="footer" style="margin-top: 30px;">
        <p style="opacity: 0.8;">Contact: data@theade.co.uk</p>
      </div>
    </section>
  </main>

  <script>
{vendor_js}
  </script>

  <script>
    const RELEASE_DATA = {payload_json};

    function fmtMW(v) {{
      try {{
        return new Intl.NumberFormat('en-GB', {{ maximumFractionDigits: 0 }}).format(v);
      }} catch (e) {{
        return String(v);
      }}
    }}

    function renderTableRows(tbodyId, rows, labelKey) {{
      const tbody = document.getElementById(tbodyId);
      if (!tbody) return;
      tbody.innerHTML = '';
      rows.forEach(r => {{
        const tr = document.createElement('tr');
        const td1 = document.createElement('td');
        td1.textContent = r[labelKey];
        const td2 = document.createElement('td');
        td2.textContent = fmtMW(r.capacity_mw);
        td2.style.textAlign = 'right';
        tr.appendChild(td1);
        tr.appendChild(td2);
        tbody.appendChild(tr);
      }});
    }}

    function maybeRenderSector(rows) {{
      const el = document.getElementById('sector-chart');
      if (!el || !rows || rows.length === 0) return;

      renderTableRows('sector-table-body', rows, 'sector');

      const labels = rows.map(r => r.sector);
      const values = rows.map(r => r.capacity_mw);

      new Chart(el, {{
        type: 'bar',
        data: {{
          labels: labels,
          datasets: [{{ label: 'Available (MW)', data: values, backgroundColor: ['#45c3d3', '#b45bd5'], borderRadius: 6 }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              callbacks: {{
                label: (ctx) => `${{ctx.label}}: ${{fmtMW(ctx.parsed.y)}} MW`
              }}
            }}
          }},
          scales: {{
            y: {{ beginAtZero: true, title: {{ display: true, text: 'MW' }} }},
            x: {{ grid: {{ display: false }} }}
          }}
        }}
      }});
    }}

    function maybeRenderAssetGroups(rows) {{
      const el = document.getElementById('asset-group-chart');
      if (!el || !rows || rows.length === 0) return;

      renderTableRows('asset-group-table-body', rows, 'asset_group');

      // Sort largest to smallest for readability.
      const sorted = [...rows].sort((a, b) => (b.capacity_mw || 0) - (a.capacity_mw || 0));
      const labels = sorted.map(r => r.asset_group);
      const values = sorted.map(r => r.capacity_mw);

      new Chart(el, {{
        type: 'bar',
        data: {{
          labels: labels,
          datasets: [{{ label: 'Available (MW)', data: values, backgroundColor: '#45c3d3', borderRadius: 6 }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ display: false }},
            tooltip: {{
              callbacks: {{
                label: (ctx) => `${{fmtMW(ctx.parsed.y)}} MW`
              }}
            }}
          }},
          scales: {{
            y: {{ beginAtZero: true, title: {{ display: true, text: 'MW' }} }},
            x: {{ grid: {{ display: false }} }}
          }}
        }}
      }});
    }}

    document.addEventListener('DOMContentLoaded', () => {{
      try {{
        maybeRenderSector(RELEASE_DATA.sector_breakdown || []);
        maybeRenderAssetGroups(RELEASE_DATA.asset_group_breakdown || []);
      }} catch (e) {{
        console.error('Release-safe dashboard render failed', e);
      }}
    }});
  </script>
</body>
</html>
"""

    out_path = dashboard_dir / "public_dashboard_standalone_release_safe.html"
    out_path.write_text(html, encoding="utf-8")

    return PublicStandaloneOutputs(standalone_path=out_path)
