"""
Admin-only validation dashboard generator for FlexDash.

Creates a standalone, file:// friendly HTML dashboard under:
  reports/admin/dashboard/

This is intended for internal (administrator) use only. It deliberately lifts
public disclosure controls and includes contributor-level values.
"""

from __future__ import annotations

import json
import shutil
import base64
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from src.analysis.cm_benchmark import build_cm_benchmark, load_verification_config


@dataclass(frozen=True)
class AdminDashboardOutputs:
    index_path: Path
    data_json_path: Path
    data_js_path: Path
    standalone_path: Path


def _ascii_safe(s: Optional[str]) -> str:
    if not s:
        return ""
    return (
        s.replace("\u2013", "-")  # en dash
        .replace("\u2014", "-")  # em dash
        .replace("\u2212", "-")  # minus
    )


def _df_records(df: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    cleaned = df.copy()
    cleaned = cleaned.astype(object).where(pd.notna(cleaned), None)
    return cleaned.to_dict(orient="records")


def _map_to_validation_asset_class(asset_class: str) -> str:
    a = (asset_class or "").strip().lower()
    if "ev" in a or "electric_vehicle" in a:
        return "EV"
    if "heat_pump" in a or a in {"hp", "heat pump", "heatpump"}:
        return "Heat pump"
    if "battery" in a or "storage" in a:
        return "Battery"
    return "I&C load"



def _capacity_source(meta: Dict[str, Any]) -> str:
    if not meta:
        return "unknown"
    if meta.get("capacity_source"):
        return str(meta.get("capacity_source"))
    if meta.get("capacity_mw_missing"):
        return "missing"
    return "unknown"


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.is_dir():
            _copy_tree(item, dst / item.name)
        else:
            shutil.copy2(item, dst / item.name)


def build_admin_validation_payload(
    *,
    project_root: Path,
    config: Dict[str, Any],
    combined_df: pd.DataFrame,
    parsed_data: Iterable[Any],
    sector_public_df: Optional[pd.DataFrame] = None,
    asset_public_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    project_root = Path(project_root)

    study_period = _ascii_safe(config.get("project", {}).get("study_period") or "Nov 2024-Feb 2025")
    generated_at = datetime.now().isoformat()

    # Contributor metadata
    contributor_rows: List[Dict[str, Any]] = []
    for p in parsed_data:
        meta = getattr(p, "metadata", {}) or {}
        contributor_rows.append(
            {
                "contributor_id": getattr(p, "contributor_id", None),
                "contributor_name": getattr(p, "contributor_name", None),
                "sector": getattr(p, "sector", None),
                "template_version": getattr(p, "template_version", None),
                "format": meta.get("format"),
                "capacity_source": _capacity_source(meta),
                "parse_warnings": list(getattr(p, "parse_warnings", []) or []),
            }
        )
    contributors_df = pd.DataFrame(contributor_rows)

    # Unmanaged ToU (template Part 4) - supplier-only data
    tou_rows: List[Dict[str, Any]] = []
    tou_totals: Dict[str, Any] = {
        "unmanaged_customers": 0,
        "total_turn_down_mwh": 0.0,
        "total_turn_up_mwh": 0.0,
        "busiest_hh_turn_down_mw": 0.0,
        "busiest_hh_turn_up_mw": 0.0,
        "capacity_mw": 0.0,
        "rows": 0,
        "contributors": 0,
    }
    try:
        tou_frames: List[pd.DataFrame] = []
        for p in parsed_data:
            sdf = getattr(p, "services", None)
            if not isinstance(sdf, pd.DataFrame) or sdf.empty:
                continue
            tmp = sdf.copy()
            tmp["contributor_id"] = getattr(p, "contributor_id", None)
            tmp["contributor_name"] = getattr(p, "contributor_name", None)
            tou_frames.append(tmp)

        if tou_frames:
            tou_df = pd.concat(tou_frames, ignore_index=True)
            for col in [
                "unmanaged_customers",
                "total_turn_down_mwh",
                "total_turn_up_mwh",
                "busiest_hh_turn_down_mw",
                "busiest_hh_turn_up_mw",
                "capacity_mw",
            ]:
                if col in tou_df.columns:
                    tou_df[col] = pd.to_numeric(tou_df[col], errors="coerce")

            tou_totals["rows"] = int(len(tou_df))
            tou_totals["contributors"] = int(tou_df["contributor_id"].nunique()) if "contributor_id" in tou_df.columns else 0
            if "unmanaged_customers" in tou_df.columns:
                tou_totals["unmanaged_customers"] = int(tou_df["unmanaged_customers"].fillna(0).sum())
            for col in ["total_turn_down_mwh", "total_turn_up_mwh", "busiest_hh_turn_down_mw", "busiest_hh_turn_up_mw", "capacity_mw"]:
                if col in tou_df.columns:
                    tou_totals[col] = float(tou_df[col].fillna(0.0).sum())

            tou_rows = _df_records(tou_df)
    except Exception:
        tou_rows = []

    raw: Dict[str, Any] = {
        "total_capacity_mw": 0.0,
        "by_sector": [],
        "by_asset_class": [],
        "by_contributor": [],
        "notes": [
            "Some submissions provide counts and/or MWh but omit the requested MW capacity (template section 3.2). In Phase 1 we treat MW as missing rather than inferring from counts.",
            "Use contributor-level numbers for QA only; do not circulate externally.",
        ],
    }

    df = combined_df.copy() if combined_df is not None else pd.DataFrame()
    if not df.empty:
        for col, default in [("capacity_mw", 0.0), ("count", 0), ("asset_class", "unknown"), ("sector", "unknown")]:
            if col not in df.columns:
                df[col] = default
        df["capacity_mw"] = pd.to_numeric(df["capacity_mw"], errors="coerce").fillna(0.0)
        df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0.0)

        raw["total_capacity_mw"] = float(df["capacity_mw"].sum())

        by_sector = (
            df.groupby("sector", dropna=False, as_index=False)
            .agg(capacity_mw=("capacity_mw", "sum"), rows=("capacity_mw", "size"), contributors=("contributor_id", "nunique"))
            .sort_values("capacity_mw", ascending=False)
        )
        raw["by_sector"] = _df_records(by_sector)

        by_asset = (
            df.groupby("asset_class", dropna=False, as_index=False)
            .agg(capacity_mw=("capacity_mw", "sum"), rows=("capacity_mw", "size"), contributors=("contributor_id", "nunique"))
            .sort_values("capacity_mw", ascending=False)
        )
        raw["by_asset_class"] = _df_records(by_asset)

        by_contrib = (
            df.groupby("contributor_id", as_index=False)
            .agg(
                capacity_mw=("capacity_mw", "sum"),
                rows=("capacity_mw", "size"),
                asset_classes=("asset_class", "nunique"),
                sectors=("sector", "nunique"),
            )
            .sort_values("capacity_mw", ascending=False)
        )
        if not contributors_df.empty:
            by_contrib = by_contrib.merge(
                contributors_df[
                    [
                        "contributor_id",
                        "contributor_name",
                        "sector",
                        "template_version",
                        "format",
                        "capacity_source",
                        "parse_warnings",
                    ]
                ],
                how="left",
                on="contributor_id",
            )
        raw["by_contributor"] = _df_records(by_contrib)

    # Public (disclosure-controlled) snapshot
    published: Dict[str, Any] = {
        "sector_breakdown": _df_records(sector_public_df),
        "asset_breakdown": _df_records(asset_public_df),
    }

    # CM benchmark + comparison
    cm: Dict[str, Any] = {
        "available": False,
        "delivery_year": "2024/25",
        "include_storage_default": False,
        "benchmark_by_asset": [],
        "comparison": [],
        "notes": [
            "CM values are de-rated capacity obligations for a Delivery Year, used as a sense-check only.",
            "CM will not represent many domestic propositions or non-CM routes-to-market (DFS, DSO tenders, BM/ancillary, bilateral).",
        ],
    }
    try:
        ver_cfg, ver_raw = load_verification_config(project_root)
        cm["delivery_year"] = _ascii_safe(ver_cfg.dy)
        cm["include_storage_default"] = bool(getattr(ver_cfg, "include_storage_default", False))
        cm_bench = build_cm_benchmark(project_root, include_storage=cm["include_storage_default"])
        cm["benchmark_by_asset"] = _df_records(cm_bench)

        if not df.empty:
            vdf = df.copy()
            vdf["asset_class_mapped"] = vdf["asset_class"].apply(_map_to_validation_asset_class)
            contrib_raw = (
                vdf.groupby("asset_class_mapped", as_index=False)
                .agg(contributors_kw=("capacity_mw", lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0.0).sum() * 1000.0)))
            )
        else:
            contrib_raw = pd.DataFrame(columns=["asset_class_mapped", "contributors_kw"])

        bench = cm_bench.rename(columns={"asset_class": "asset_class_mapped"}) if cm_bench is not None else pd.DataFrame()
        cmp_df = contrib_raw.merge(bench, how="outer", on="asset_class_mapped")
        cmp_df["contributors_kw"] = pd.to_numeric(cmp_df.get("contributors_kw"), errors="coerce").fillna(0.0)
        cmp_df["cm_benchmark_kw"] = pd.to_numeric(cmp_df.get("cm_benchmark_kw"), errors="coerce").fillna(0.0)
        cmp_df["variance_kw"] = cmp_df["contributors_kw"] - cmp_df["cm_benchmark_kw"]
        cmp_df["variance_pct"] = cmp_df.apply(
            lambda r: (r["variance_kw"] / r["cm_benchmark_kw"]) if r["cm_benchmark_kw"] else None,
            axis=1,
        )
        cm["comparison"] = _df_records(cmp_df.sort_values("asset_class_mapped"))

        cm["available"] = True
        if isinstance(ver_raw, dict):
            cm["sources"] = ver_raw.get("sources", [])
    except Exception as e:
        cm["available"] = False
        cm["error"] = str(e)

    return {
        "generated_at": generated_at,
        "study_period": study_period,
        "contributors_count": int(df["contributor_id"].nunique()) if not df.empty and "contributor_id" in df.columns else 0,
        "raw": raw,
        "published": published,
        "tou": {
            "rows": tou_rows,
            "totals": tou_totals,
            "notes": [
                "ToU values come from Template Part 4 (unmanaged tariffs). They are not included in capacity totals on this admin page unless explicitly added.",
                "Customer counts may double-count if the same customer appears across tariffs (should not happen in normal tariff portfolios).",
            ],
        },
        "cm": cm,
    }


def generate_admin_validation_dashboard(
    *,
    project_root: Path,
    config: Dict[str, Any],
    combined_df: pd.DataFrame,
    parsed_data: Iterable[Any],
    sector_public_df: Optional[pd.DataFrame] = None,
    asset_public_df: Optional[pd.DataFrame] = None,
) -> AdminDashboardOutputs:
    """
    Create an admin-only dashboard under reports/admin/dashboard.
    """
    project_root = Path(project_root)
    out_dir = project_root / "reports" / "admin" / "dashboard"
    (out_dir / "css").mkdir(parents=True, exist_ok=True)
    (out_dir / "js").mkdir(parents=True, exist_ok=True)
    (out_dir / "data").mkdir(parents=True, exist_ok=True)

    # Copy CSS assets from the main dashboard for consistent styling.
    _copy_tree(project_root / "dashboard" / "css", out_dir / "css")

    # Copy Chart.js vendor bundle (so charts work offline without a server).
    vendor_src = project_root / "dashboard" / "js" / "vendor" / "chart.umd.min.js"
    vendor_dst = out_dir / "js" / "vendor" / "chart.umd.min.js"
    if vendor_src.exists():
        vendor_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(vendor_src, vendor_dst)
    # Copy logo if present.
    logo_src = project_root / "dashboard" / "ADE Demand Logo.png"
    if logo_src.exists():
        shutil.copy2(logo_src, out_dir / "ADE Demand Logo.png")

    payload = build_admin_validation_payload(
        project_root=project_root,
        config=config,
        combined_df=combined_df,
        parsed_data=parsed_data,
        sector_public_df=sector_public_df,
        asset_public_df=asset_public_df,
    )

    data_json_path = out_dir / "data" / "admin_validation_data.json"
    data_js_path = out_dir / "js" / "data.js"
    index_path = out_dir / "index.html"
    standalone_path = out_dir / "admin_validation_dashboard.html"

    data_json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    js_payload = json.dumps(payload, indent=2, ensure_ascii=False)
    data_js = "\n".join(
        [
            "/**",
            " * FlexDash Admin Validation Dashboard Data",
            " *",
            " * STRICTLY CONFIDENTIAL - ADMIN EYES ONLY",
            f" * Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            " */",
            "",
            f"const ADMIN_DASHBOARD_DATA = {js_payload};",
            "",
        ]
    )
    _write_text(data_js_path, data_js)

    # HTML/JS assets (standalone, file:// friendly)
    _write_text(index_path, _ADMIN_INDEX_HTML)
    _write_text(out_dir / "js" / "main.js", _ADMIN_MAIN_JS)
    _write_text(out_dir / "js" / "charts.js", _ADMIN_CHARTS_JS)

    # Single-file version (useful when relative assets are blocked or the file is copied elsewhere).
    try:
        css_parts: List[str] = []
        for css_name in ["styles.css", "themes.css", "ade-brand.css"]:
            css_path = out_dir / "css" / css_name
            if css_path.exists():
                css_parts.append(css_path.read_text(encoding="utf-8", errors="ignore"))
        inline_css = "\n\n".join(css_parts)
        inline_js = "\n\n".join([data_js, _ADMIN_MAIN_JS, _ADMIN_CHARTS_JS])

        chart_js = ""
        chart_js_path = out_dir / "js" / "vendor" / "chart.umd.min.js"
        if chart_js_path.exists():
            chart_js = chart_js_path.read_text(encoding="utf-8", errors="ignore")

        logo_data_uri = None
        if logo_src.exists():
            try:
                encoded = base64.b64encode(logo_src.read_bytes()).decode("ascii")
                logo_data_uri = f"data:image/png;base64,{encoded}"
            except Exception:
                logo_data_uri = None

        html = _ADMIN_INDEX_HTML
        html = html.replace('<link rel="stylesheet" href="css/styles.css">', "")
        html = html.replace('<link rel="stylesheet" href="css/themes.css">', "")
        html = html.replace('<link rel="stylesheet" href="css/ade-brand.css">', "")
        html = html.replace('<script src="js/vendor/chart.umd.min.js"></script>', "")
        html = html.replace(_ADMIN_CHART_FALLBACK_JS, "")
        html = html.replace(
            "  <script src=\"js/data.js\"></script>\n  <script src=\"js/main.js\"></script>\n  <script src=\"js/charts.js\"></script>",
            "",
        )
        if logo_data_uri:
            html = html.replace('src="ADE Demand Logo.png"', f'src="{logo_data_uri}"')

        # Inline CSS into <head> and JS (including Chart.js) before </body>.
        html = html.replace("</head>", "  <style>\n" + inline_css + "\n  </style>\n</head>")
        html = html.replace("</body>", "  <script>\n" + chart_js + "\n\n" + inline_js + "\n  </script>\n</body>")
        _write_text(standalone_path, html)
    except Exception:
        # Best-effort: keep the multi-file dashboard even if standalone creation fails.
        pass

    return AdminDashboardOutputs(
        index_path=index_path,
        data_json_path=data_json_path,
        data_js_path=data_js_path,
        standalone_path=standalone_path,
    )


_ADMIN_INDEX_HTML = """<!DOCTYPE html>
<html lang="en" data-theme="dashboard-dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Flex Dashboard | Admin Validation</title>
  <link rel="stylesheet" href="css/styles.css">
  <link rel="stylesheet" href="css/themes.css">
  <link rel="stylesheet" href="css/ade-brand.css">
  <script src="js/vendor/chart.umd.min.js"></script>
  <script>
    // Fallback if the local vendor bundle is missing.
    if (typeof Chart === 'undefined') {
      var s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
      document.head.appendChild(s);
    }
  </script>
</head>
<body>
  <header class="header">
    <div class="header-content">
      <div class="logo">
        <img src="ADE Demand Logo.png" alt="ADE Demand" class="logo-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
        <div class="logo-fallback" style="display:none;">
          <span class="logo-text">ade</span>
          <span class="logo-text-bold">Demand</span>
        </div>
      </div>
      <nav class="nav">
        <a href="#overview" class="nav-link active" data-page="overview">Overview</a>
        <a href="#raw" class="nav-link" data-page="raw">Raw totals</a>
        <a href="#contributors" class="nav-link" data-page="contributors">Contributors</a>
        <a href="#tou" class="nav-link" data-page="tou">ToU</a>
        <a href="#benchmarks" class="nav-link" data-page="benchmarks">Benchmarks</a>
        <a href="#notes" class="nav-link" data-page="notes">Notes</a>
      </nav>
      <div class="theme-selector">
        <label for="theme-select">Theme:</label>
        <select id="theme-select">
          <option value="energy-flow">Energy Flow</option>
          <option value="data-grid">Data Grid</option>
          <option value="bold-blocks">Bold Blocks</option>
          <option value="light-airy">Light & Airy</option>
          <option value="dashboard-dark">Dark Mode</option>
        </select>
      </div>
    </div>
  </header>

  <main class="main">
    <section id="overview" class="page active">
      <div class="page-header">
        <h1>Admin validation dashboard</h1>
        <p class="subtitle">Confidential QA view (disclosure controls lifted)</p>
        <div class="study-badge">
          <span class="badge-label">Study Period:</span>
          <span class="badge-value" id="study-period">--</span>
        </div>
      </div>

      <div class="notice warning">
        <strong>STRICTLY CONFIDENTIAL - ADMIN EYES ONLY.</strong>
        This view includes contributor-level values (disclosure controls lifted).
        Do not circulate outside the authorised project team.
      </div>

      <div class="metrics-section">
        <h3 class="section-title">Topline (raw vs published)</h3>
        <div class="metrics-grid">
          <div class="metric-card primary">
            <div class="metric-icon">⚡</div>
            <div class="metric-value" id="raw-total-mw">--</div>
            <div class="metric-label">Raw total capacity (MW)</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">📊</div>
            <div class="metric-value" id="published-total-mw">--</div>
            <div class="metric-label">Published total (MW)</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">🏢</div>
            <div class="metric-value" id="contributors-count">--</div>
            <div class="metric-label">Contributors (count)</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">📋</div>
            <div class="metric-value" id="cm-total-mw">--</div>
            <div class="metric-label">CM DSR benchmark (MW, DY)</div>
          </div>
        </div>
      </div>
    </section>

    <section id="raw" class="page">
      <div class="page-header">
        <h1>Raw totals (unsuppressed)</h1>
        <p class="subtitle">Internal QA view of submitted + derived values</p>
      </div>

      <div class="data-table-card">
        <h3>By sector (raw)</h3>
        <div class="table-scroll">
          <table class="data-table" id="raw-by-sector-table"></table>
        </div>
      </div>

      <div class="data-table-card">
        <h3>By asset class (raw)</h3>
        <div class="table-scroll">
          <table class="data-table" id="raw-by-asset-table"></table>
        </div>
      </div>

      <div class="chart-card">
        <h3>Raw capacity by asset class</h3>
        <canvas id="raw-asset-chart" height="120"></canvas>
        <p class="context-note">Bar chart uses raw MW totals by asset class. Some values may be estimated from counts.</p>
      </div>
    </section>

    <section id="contributors" class="page">
      <div class="page-header">
        <h1>Contributors</h1>
        <p class="subtitle">Topline values, parsing notes, and capacity source flags</p>
      </div>

      <div class="data-table-card">
        <h3>Contributor topline (raw)</h3>
        <div class="table-scroll">
          <table class="data-table" id="contributors-table"></table>
        </div>
      </div>
    </section>

    <section id="tou" class="page">
      <div class="page-header">
        <h1>Time-of-use (ToU) tariffs</h1>
        <p class="subtitle">Unmanaged / implicit flexibility (Template Part 4)</p>
      </div>

      <div class="notice">
        ToU values are captured separately from managed flexibility. They are sensitive to baseline definition and are not directly comparable to Capacity Market results.
      </div>

      <div class="metrics-section">
        <h3 class="section-title">ToU totals (raw)</h3>
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-icon">ðŸ‘¥</div>
            <div class="metric-value" id="tou-customers">--</div>
            <div class="metric-label">Unmanaged customers</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">â†“</div>
            <div class="metric-value" id="tou-td-mwh">--</div>
            <div class="metric-label">Total turn-down (MWh)</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">â†‘</div>
            <div class="metric-value" id="tou-tu-mwh">--</div>
            <div class="metric-label">Total turn-up (MWh)</div>
          </div>
          <div class="metric-card">
            <div class="metric-icon">âš¡</div>
            <div class="metric-value" id="tou-capacity-mw">--</div>
            <div class="metric-label">Sum of busiest-HH capacity (MW)</div>
          </div>
        </div>
      </div>

      <div class="data-table-card">
        <h3>Tariffs (raw)</h3>
        <div class="table-scroll">
          <table class="data-table" id="tou-table"></table>
        </div>
      </div>
    </section>

    <section id="benchmarks" class="page">
      <div class="page-header">
        <h1>Benchmarks</h1>
        <p class="subtitle">Capacity Market DY benchmark as a sense-check (not additive)</p>
      </div>

      <div class="notice">
        CM values are used for context only and are <strong>not</strong> added to any dashboard totals. CM is incomplete for domestic and non-CM routes-to-market.
      </div>

      <div class="data-table-card">
        <h3>CM benchmark (mapped)</h3>
        <div class="table-scroll">
          <table class="data-table" id="cm-benchmark-table"></table>
        </div>
      </div>

      <div class="data-table-card">
        <h3>Raw contributors vs CM benchmark (mapped)</h3>
        <div class="table-scroll">
          <table class="data-table" id="cm-compare-table"></table>
        </div>
      </div>

      <div class="chart-card">
        <h3>Delta (contributors - CM) by mapped class</h3>
        <canvas id="cm-delta-chart" height="120"></canvas>
      </div>
    </section>

    <section id="notes" class="page">
      <div class="page-header">
        <h1>Notes and limitations</h1>
        <p class="subtitle">How to interpret what you are seeing</p>
      </div>

      <div class="method-card">
        <h3>What this is</h3>
        <p>This dashboard is an internal QA tool. It lifts disclosure control to show contributor-level values, parsing warnings, and benchmark comparisons.</p>
      </div>

      <div class="method-card">
        <h3>Why CM helps (and why it is limited)</h3>
        <ul class="source-list">
          <li><strong>Helps</strong>: CM results are a transparent, audited dataset expressing a firm capacity obligation (de-rated MW) for the Delivery Year.</li>
          <li><strong>Limits</strong>: CM is not a full map of flexibility. It will miss DFS/DSO/BM/ancillary/bilateral activity and most domestic propositions.</li>
          <li><strong>Definition mismatch</strong>: CM uses de-rated MW; project submissions may reflect technical nameplate, contracted MW, or estimated MW derived from device counts.</li>
          <li><strong>Period mismatch</strong>: CM is Delivery Year; the dashboard study period is a winter window.</li>
        </ul>
      </div>
    </section>
  </main>

  <footer class="footer">
    <div class="footer-content">
      <div class="footer-info">
        <p>Admin validation dashboard (local file)</p>
        <p class="footer-note">Generated: <span id="last-updated">--</span></p>
      </div>
    </div>
  </footer>

  <script src="js/data.js"></script>
  <script src="js/main.js"></script>
  <script src="js/charts.js"></script>
</body>
</html>
"""

_ADMIN_CHART_FALLBACK_JS = """  <script>
    // Fallback if the local vendor bundle is missing.
    if (typeof Chart === 'undefined') {
      var s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
      document.head.appendChild(s);
    }
  </script>"""


_ADMIN_MAIN_JS = """/**
 * Admin Validation Dashboard Controller (file:// friendly)
 */

const AdminState = {
  currentPage: 'overview',
  data: null,
  charts: {},
};

const ADMIN_CONFIG = {
  dataPath: 'data/admin_validation_data.json',
  formatOptions: { locale: 'en-GB', maximumFractionDigits: 0 },
};

function formatNumber(value, decimals = 0) {
  if (value === undefined || value === null || isNaN(value)) return '--';
  return new Intl.NumberFormat(ADMIN_CONFIG.formatOptions.locale, { maximumFractionDigits: decimals }).format(value);
}

function formatMW(value) {
  return `${formatNumber(value, 2)} MW`;
}

function formatKW(value) {
  return `${formatNumber(value, 0)} kW`;
}

function formatPct(value) {
  if (value === undefined || value === null || isNaN(value)) return '';
  return `${(value * 100).toFixed(1)}%`;
}

function setupTheme() {
  const themeSelect = document.getElementById('theme-select');
  if (!themeSelect) return;

  const savedTheme = localStorage.getItem('flexdash-admin-theme') || 'dashboard-dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  themeSelect.value = savedTheme;

  themeSelect.addEventListener('change', (e) => {
    const theme = e.target.value;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('flexdash-admin-theme', theme);

    if (typeof AdminCharts !== 'undefined') {
      AdminCharts.redrawAll();
    }
  });
}

function setupNavigation() {
  document.querySelectorAll('.nav-link, [data-page]').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const page = link.dataset.page || link.getAttribute('href').replace('#', '');
      navigateToPage(page);
    });
  });

  window.addEventListener('popstate', (e) => {
    const page = e.state?.page || 'overview';
    navigateToPage(page, false);
  });

  const hash = window.location.hash.replace('#', '');
  if (hash && ['overview', 'raw', 'contributors', 'benchmarks', 'notes'].includes(hash)) {
    navigateToPage(hash, false);
  }
}

function navigateToPage(pageId, pushState = true) {
  document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
  const target = document.getElementById(pageId);
  if (target) target.classList.add('active');

  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle('active', link.dataset.page === pageId);
  });

  AdminState.currentPage = pageId;
  if (pushState) history.pushState({ page: pageId }, '', `#${pageId}`);
  window.scrollTo(0, 0);
}

async function loadData() {
  const isFile = window.location.protocol === 'file:';
  if (isFile && typeof ADMIN_DASHBOARD_DATA !== 'undefined') {
    AdminState.data = ADMIN_DASHBOARD_DATA;
    return;
  }

  try {
    const resp = await fetch(ADMIN_CONFIG.dataPath, { cache: 'no-store' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    AdminState.data = await resp.json();
  } catch (e) {
    if (typeof ADMIN_DASHBOARD_DATA !== 'undefined') {
      AdminState.data = ADMIN_DASHBOARD_DATA;
    } else {
      console.error('Failed to load admin dashboard data:', e);
      AdminState.data = null;
    }
  }
}

function setTable(elId, headers, rows) {
  const table = document.getElementById(elId);
  if (!table) return;

  const thead = `<thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>`;
  const tbody = `<tbody>${rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody>`;
  table.innerHTML = thead + tbody;
}

function updateUI() {
  const d = AdminState.data;
  if (!d) return;

  const rawTotal = d.raw?.total_capacity_mw ?? 0;
  const publishedTotal = (d.published?.sector_breakdown || []).reduce((acc, r) => acc + (Number(r.capacity_mw) || 0), 0);

  document.getElementById('study-period').textContent = d.study_period || '--';
  document.getElementById('raw-total-mw').textContent = formatNumber(rawTotal, 2);
  document.getElementById('published-total-mw').textContent = formatNumber(publishedTotal, 2);
  document.getElementById('contributors-count').textContent = String(d.contributors_count ?? '--');

  // CM total MW
  if (d.cm?.available) {
    const cmTotalKW = (d.cm.benchmark_by_asset || []).reduce((acc, r) => acc + (Number(r.cm_benchmark_kw) || 0), 0);
    document.getElementById('cm-total-mw').textContent = formatNumber(cmTotalKW / 1000, 2);
  } else {
    document.getElementById('cm-total-mw').textContent = '--';
  }

  document.getElementById('last-updated').textContent = (d.generated_at || '').slice(0, 19).replace('T', ' ');

  // Raw by sector
  const rawSector = d.raw?.by_sector || [];
  setTable(
    'raw-by-sector-table',
    ['Sector', 'Capacity', 'Contributors', 'Rows'],
    rawSector.map(r => [
      String(r.sector ?? ''),
      formatMW(r.capacity_mw),
      String(r.contributors ?? ''),
      String(r.rows ?? ''),
    ])
  );

  // Raw by asset class
  const rawAsset = d.raw?.by_asset_class || [];
  setTable(
    'raw-by-asset-table',
    ['Asset class', 'Capacity', 'Contributors', 'Rows'],
    rawAsset.map(r => [
      String(r.asset_class ?? ''),
      formatMW(r.capacity_mw),
      String(r.contributors ?? ''),
      String(r.rows ?? ''),
    ])
  );

  // Contributors
  const contrib = d.raw?.by_contributor || [];
  setTable(
    'contributors-table',
    ['Contributor', 'Name', 'Sector', 'Capacity', 'Asset classes', 'Rows', 'Capacity source', 'Warnings'],
    contrib.map(r => [
      String(r.contributor_id ?? ''),
      String(r.contributor_name ?? ''),
      String(r.sector ?? ''),
      formatMW(r.capacity_mw),
      String(r.asset_classes ?? ''),
      String(r.rows ?? ''),
      String(r.capacity_source ?? ''),
      Array.isArray(r.parse_warnings) ? r.parse_warnings.join(' | ') : '',
    ])
  );

  // ToU tariffs (Template Part 4) - supplier data (raw, disclosure lifted)
  const touTotals = d.tou?.totals || {};
  const touCustomers = Number(touTotals.unmanaged_customers) || 0;
  const touTdMwh = Number(touTotals.total_turn_down_mwh) || 0;
  const touTuMwh = Number(touTotals.total_turn_up_mwh) || 0;
  const touCapMw = Number(touTotals.capacity_mw) || 0;

  const elTouCustomers = document.getElementById('tou-customers');
  if (elTouCustomers) elTouCustomers.textContent = formatNumber(touCustomers, 0);
  const elTouTd = document.getElementById('tou-td-mwh');
  if (elTouTd) elTouTd.textContent = formatNumber(touTdMwh, 0);
  const elTouTu = document.getElementById('tou-tu-mwh');
  if (elTouTu) elTouTu.textContent = formatNumber(touTuMwh, 0);
  const elTouCap = document.getElementById('tou-capacity-mw');
  if (elTouCap) elTouCap.textContent = formatMW(touCapMw);

  const touRows = d.tou?.rows || [];
  setTable(
    'tou-table',
    ['Contributor', 'Tariff', 'Sector', 'Asset', 'Customers', 'Turn-down (MWh)', 'Turn-up (MWh)', 'Busiest TD (MW)', 'Busiest TU (MW)', 'Capacity (MW)'],
    touRows.map(r => [
      String(r.contributor_name ?? ''),
      String(r.tariff_name ?? ''),
      String(r.target_sector ?? ''),
      String(r.target_asset ?? ''),
      r.unmanaged_customers == null ? '' : formatNumber(r.unmanaged_customers, 0),
      r.total_turn_down_mwh == null ? '' : formatNumber(r.total_turn_down_mwh, 2),
      r.total_turn_up_mwh == null ? '' : formatNumber(r.total_turn_up_mwh, 2),
      r.busiest_hh_turn_down_mw == null ? '' : formatNumber(r.busiest_hh_turn_down_mw, 2),
      r.busiest_hh_turn_up_mw == null ? '' : formatNumber(r.busiest_hh_turn_up_mw, 2),
      r.capacity_mw == null ? '' : formatNumber(r.capacity_mw, 2),
    ])
  );

  // CM benchmark
  const cmBench = d.cm?.benchmark_by_asset || [];
  setTable(
    'cm-benchmark-table',
    ['Mapped asset class', 'CM benchmark (kW)'],
    cmBench.map(r => [String(r.asset_class ?? ''), formatKW(r.cm_benchmark_kw)])
  );

  const cmCompare = d.cm?.comparison || [];
  setTable(
    'cm-compare-table',
    ['Mapped asset class', 'Contributors (kW)', 'CM (kW)', 'Delta kW', 'Delta %'],
    cmCompare.map(r => [
      String(r.asset_class_mapped ?? ''),
      formatKW(r.contributors_kw),
      formatKW(r.cm_benchmark_kw),
      formatKW(r.variance_kw),
      formatPct(r.variance_pct),
    ])
  );

  if (typeof AdminCharts !== 'undefined') {
    AdminCharts.renderRawAssetChart('raw-asset-chart', rawAsset);
    AdminCharts.renderCmDeltaChart('cm-delta-chart', cmCompare);
  }
}

async function init() {
  setupTheme();
  setupNavigation();
  await loadData();
  updateUI();
}

document.addEventListener('DOMContentLoaded', init);

window.AdminState = AdminState;
"""


_ADMIN_CHARTS_JS = """/**
 * Charts for Admin Validation Dashboard
 */

const AdminCharts = {
  _rawAssetChart: null,
  _cmDeltaChart: null,

  _destroy(chart) {
    if (chart && typeof chart.destroy === 'function') chart.destroy();
  },

  _getColors() {
    const styles = getComputedStyle(document.documentElement);
    return {
      primary: styles.getPropertyValue('--chart-domestic').trim() || '#45c3d3',
      secondary: styles.getPropertyValue('--chart-ic').trim() || '#6eb43f',
      highlight: styles.getPropertyValue('--chart-illustrative').trim() || '#eb8800',
      text: styles.getPropertyValue('--text-primary').trim() || '#111',
      grid: styles.getPropertyValue('--border-color').trim() || '#ccc',
    };
  },

  renderRawAssetChart(canvasId, rawAssetRows) {
    const el = document.getElementById(canvasId);
    if (!el) return;
    if (typeof Chart === 'undefined') return;

    const rows = (rawAssetRows || []).slice(0, 12);
    const labels = rows.map(r => String(r.asset_class || ''));
    const values = rows.map(r => Number(r.capacity_mw) || 0);
    const colors = this._getColors();

    this._destroy(this._rawAssetChart);
    this._rawAssetChart = new Chart(el, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Raw capacity (MW)',
          data: values,
          backgroundColor: colors.primary,
          borderColor: colors.primary,
          borderWidth: 1,
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) => `${ctx.parsed.y.toFixed(2)} MW` } },
        },
        scales: {
          x: { ticks: { color: colors.text }, grid: { color: colors.grid } },
          y: { ticks: { color: colors.text }, grid: { color: colors.grid } },
        }
      }
    });
  },

  renderCmDeltaChart(canvasId, compareRows) {
    const el = document.getElementById(canvasId);
    if (!el) return;
    if (typeof Chart === 'undefined') return;

    const rows = (compareRows || []);
    const labels = rows.map(r => String(r.asset_class_mapped || ''));
    const values = rows.map(r => Number(r.variance_kw) || 0);
    const colors = this._getColors();

    const bg = values.map(v => v >= 0 ? colors.highlight : colors.secondary);

    this._destroy(this._cmDeltaChart);
    this._cmDeltaChart = new Chart(el, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Delta (kW)',
          data: values,
          backgroundColor: bg,
          borderWidth: 0,
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: colors.text }, grid: { color: colors.grid } },
          y: { ticks: { color: colors.text }, grid: { color: colors.grid } },
        }
      }
    });
  },

  redrawAll() {
    try {
      const d = window.AdminState?.data;
      if (!d) return;
      this.renderRawAssetChart('raw-asset-chart', d.raw?.by_asset_class || []);
      this.renderCmDeltaChart('cm-delta-chart', d.cm?.comparison || []);
    } catch {}
  }
};

window.AdminCharts = AdminCharts;
"""
