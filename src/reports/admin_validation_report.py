"""
Admin-only validation report for FlexDash.

This report is intended for internal (administrator) use and deliberately lifts
public-facing disclosure controls to support QA, sense-checking, and steering
group preparation.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from src.analysis.cm_benchmark import build_cm_benchmark, load_verification_config


@dataclass(frozen=True)
class AdminValidationOutputs:
    report_path: Path
    latest_path: Path


def _safe_float(x: Any) -> float:
    try:
        if x is None:
            return 0.0
        return float(x)
    except Exception:
        return 0.0


def _fmt_num(x: Any, decimals: int = 0) -> str:
    v = _safe_float(x)
    fmt = f"{{:,.{decimals}f}}"
    return fmt.format(v)


def _fmt_mw(x: Any) -> str:
    return f"{_fmt_num(x, 2)} MW"


def _fmt_kw(x: Any) -> str:
    return f"{_fmt_num(x, 0)} kW"


def _fmt_pct(x: Any) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    try:
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return ""


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    header_row = "| " + " | ".join(headers) + " |"
    sep_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return "\n".join([header_row, sep_row, body]) + "\n"


def _wrap(s: str) -> str:
    return "\n".join(textwrap.wrap(s, width=110))


def _ascii_safe(s: Optional[str]) -> str:
    """
    Keep the admin report readable in environments that don't render some unicode punctuation well.
    """
    if not s:
        return ""
    return (
        s.replace("\u2013", "-")  # en dash
        .replace("\u2014", "-")  # em dash
        .replace("\u2212", "-")  # minus
    )


def _map_to_validation_asset_class(asset_class: str) -> str:
    a = (asset_class or "").strip().lower()
    if "ev" in a or "electric_vehicle" in a:
        return "EV"
    if "heat_pump" in a or a in {"hp", "heat pump", "heatpump"}:
        return "Heat pump"
    if "battery" in a or "storage" in a:
        return "Battery"
    return "I&C load"


def generate_admin_validation_report(
    *,
    project_root: Path,
    config: Dict[str, Any],
    combined_df: pd.DataFrame,
    parsed_data: Iterable[Any],
    sector_public_df: Optional[pd.DataFrame] = None,
    asset_public_df: Optional[pd.DataFrame] = None,
) -> AdminValidationOutputs:
    """
    Generate an admin-only validation report (Markdown).

    The report is written to:
      - reports/admin/validation_report_latest.md (overwritten)
      - reports/admin/validation_report_YYYY-MM-DD.md (timestamped snapshot)
    """
    project_root = Path(project_root)
    out_dir = project_root / "reports" / "admin"
    out_dir.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now()
    stamp = generated_at.strftime("%Y-%m-%d")
    latest_path = out_dir / "validation_report_latest.md"
    report_path = out_dir / f"validation_report_{stamp}.md"

    study_period = (
        config.get("project", {}).get("study_period")
        or "Nov 2024–Feb 2025"
    )
    study_period_display = _ascii_safe(study_period)

    # Build contributor lookup from ParsedData objects
    contributors = []
    for p in parsed_data:
        meta = getattr(p, "metadata", {}) or {}
        contributors.append(
            {
                "contributor_id": getattr(p, "contributor_id", None),
                "contributor_name": getattr(p, "contributor_name", None),
                "sector": getattr(p, "sector", None),
                "template_version": getattr(p, "template_version", None),
                "submission_date": getattr(p, "submission_date", None),
                "format": meta.get("format"),
                "parse_warnings": list(getattr(p, "parse_warnings", []) or []),
            }
        )
    contrib_df = pd.DataFrame(contributors)

    md: List[str] = []
    md.append("# Flex Dashboard - Admin Validation Report (STRICTLY CONFIDENTIAL)\n")
    md.append("**ADMIN EYES ONLY. Do not forward. Do not circulate outside the authorised project team.**\n")
    md.append(f"- Generated: {generated_at.strftime('%Y-%m-%d %H:%M')}\n")
    md.append(f"- Study period (dashboard): {study_period_display}\n")
    md.append("\n---\n")

    md.append("## 1) What this report is for\n")
    md.append(
        _wrap(
            "This report exists to help administrators sense-check the Flex Dashboard numbers using "
            "unsuppressed internal aggregates (raw contributor submissions) alongside a public benchmark "
            "(Capacity Market de-rated DSR awards for Delivery Year 2024/25). The public dashboard applies "
            "k-anonymity (k=3) and dominance rules; those controls are intentionally lifted here to make QA "
            "and troubleshooting possible."
        )
        + "\n\n"
    )

    md.append("## 2) What the public dashboard shows (and why it can look strange)\n")
    md.append(
        _wrap(
            "The published dashboard replaces any cell that fails disclosure control with illustrative "
            "values or buckets. This protects commercial confidentiality but can make the verification view "
            "misleading (for example: an asset class can appear to have large capacity even if the true "
            "underlying values are suppressed)."
        )
        + "\n\n"
    )

    # Raw totals (unsuppressed)
    md.append("## 3) Raw totals from contributors (UNSUPPRESSED)\n")
    if combined_df is None or combined_df.empty:
        md.append("No combined contributor dataset was available in this run.\n\n")
    else:
        df = combined_df.copy()
        if "capacity_mw" not in df.columns:
            df["capacity_mw"] = 0.0
        if "count" not in df.columns:
            df["count"] = 0
        if "asset_class" not in df.columns:
            df["asset_class"] = "unknown"
        if "sector" not in df.columns:
            df["sector"] = "unknown"

        df["capacity_mw"] = pd.to_numeric(df["capacity_mw"], errors="coerce").fillna(0.0)
        df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0.0)

        total_mw = float(df["capacity_mw"].sum())
        md.append(f"Total reported available capacity (sum of all asset rows): **{_fmt_mw(total_mw)}**\n\n")
        md.append(
            _wrap(
                "Important: some submissions provide counts and/or MWh but omit the requested MW capacity (Template V1.2 section 3.2: "
                "average daily coincident, deduplicated, peak deliverable MW). In Phase 1 we treat MW as missing rather than inferring "
                "it from counts. A 0 MW value here can therefore mean 'missing' rather than confirmed zero."
            )
            + "\n\n"
        )

        # By sector
        by_sector = (
            df.groupby("sector", dropna=False, as_index=False)
            .agg(capacity_mw=("capacity_mw", "sum"), rows=("capacity_mw", "size"), contributors=("contributor_id", "nunique"))
            .sort_values("capacity_mw", ascending=False)
        )
        md.append("### 3.1 Breakdown by sector (raw)\n")
        md.append(
            _md_table(
                ["Sector", "Capacity", "Contributors", "Rows"],
                [
                    [
                        str(r["sector"]),
                        _fmt_mw(r["capacity_mw"]),
                        str(int(r["contributors"])),
                        str(int(r["rows"])),
                    ]
                    for _, r in by_sector.iterrows()
                ],
            )
        )

        # By asset class
        by_asset = (
            df.groupby("asset_class", dropna=False, as_index=False)
            .agg(capacity_mw=("capacity_mw", "sum"), rows=("capacity_mw", "size"), contributors=("contributor_id", "nunique"))
            .sort_values("capacity_mw", ascending=False)
        )
        md.append("### 3.2 Breakdown by asset class (raw)\n")
        md.append(
            _md_table(
                ["Asset class", "Capacity", "Contributors", "Rows"],
                [
                    [
                        str(r["asset_class"]),
                        _fmt_mw(r["capacity_mw"]),
                        str(int(r["contributors"])),
                        str(int(r["rows"])),
                    ]
                    for _, r in by_asset.iterrows()
                ],
            )
        )

        # By contributor (topline)
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
        if not contrib_df.empty:
            by_contrib = by_contrib.merge(
                contrib_df[
                    [
                        "contributor_id",
                        "contributor_name",
                        "sector",
                        "template_version",
                        "format",
                        "parse_warnings",
                    ]
                ],
                how="left",
                on="contributor_id",
            )

        md.append("### 3.3 By contributor (raw topline)\n")
        md.append(
            _md_table(
                ["Contributor", "Name", "Sector", "Capacity", "Asset classes", "Rows", "Template"],
                [
                    [
                        str(r.get("contributor_id", "")),
                        str(r.get("contributor_name", "")) if pd.notna(r.get("contributor_name", None)) else "",
                        str(r.get("sector", "")) if pd.notna(r.get("sector", None)) else "",
                        _fmt_mw(r.get("capacity_mw", 0.0)),
                        str(int(_safe_float(r.get("asset_classes", 0)))),
                        str(int(_safe_float(r.get("rows", 0)))),
                        str(r.get("template_version", "")) if pd.notna(r.get("template_version", None)) else "",
                    ]
                    for _, r in by_contrib.iterrows()
                ],
            )
        )

        md.append("### 3.4 Contributor notes (how to interpret these numbers)\n")
        notes: List[str] = []
        for _, r in by_contrib.iterrows():
            cid = str(r.get("contributor_id", "") or "")
            name = str(r.get("contributor_name", "") or "")
            fmt = str(r.get("format", "") or "")
            warnings = r.get("parse_warnings", []) if isinstance(r.get("parse_warnings", None), list) else []

            note_bits: List[str] = []
            if fmt:
                note_bits.append(f"format=`{fmt}`")
            if warnings:
                note_bits.append("warnings=" + "; ".join(warnings))

            prefix = f"- **{cid}**"
            if name:
                prefix += f" ({name})"
            if note_bits:
                notes.append(prefix + ": " + " | ".join(note_bits))
            else:
                notes.append(prefix + ": (no parser warnings recorded)")

        md.append("\n".join(notes) + "\n\n")

    # Public aggregates snapshot (for explaining disclosure)
    md.append("## 4) Public-facing aggregates snapshot (DISCLOSURE-CONTROLLED)\n")
    md.append(
        _wrap(
            "The tables below are the disclosure-controlled aggregates that feed the public dashboard. "
            "They can diverge from the raw totals above because cells that fail k=3 or dominance thresholds "
            "are replaced by illustrative values or ranges."
        )
        + "\n\n"
    )

    if sector_public_df is None or sector_public_df.empty:
        md.append("No public sector aggregate was available.\n\n")
    else:
        sdf = sector_public_df.copy()
        md.append("### 4.1 Sector totals (published)\n")
        md.append(
            _md_table(
                ["Sector", "Capacity", "k", "Illustrative?"],
                [
                    [
                        str(r.get("sector", "")),
                        _fmt_mw(r.get("capacity_mw", 0.0)),
                        str(r.get("k", "")),
                        "Yes" if bool(r.get("capacity_mw_illustrative", False)) else "No",
                    ]
                    for _, r in sdf.iterrows()
                ],
            )
        )

    if asset_public_df is None or asset_public_df.empty:
        md.append("No public asset-class aggregate was available.\n\n")
    else:
        adf = asset_public_df.copy()
        md.append("### 4.2 Asset class totals (published)\n")
        md.append(
            _md_table(
                ["Asset class", "Capacity", "k", "Illustrative?"],
                [
                    [
                        str(r.get("asset_class", "")),
                        _fmt_mw(r.get("capacity_mw", 0.0)),
                        str(r.get("k", "")),
                        "Yes" if bool(r.get("capacity_mw_illustrative", False)) else "No",
                    ]
                    for _, r in adf.iterrows()
                ],
            )
        )

    # CM benchmark (public source) + comparison to raw contributor totals
    md.append("## 5) Capacity Market (CM) benchmark and comparison\n")
    md.append(
        _wrap(
            "We use the Capacity Market only as a sense-check. CM results are a transparent, audited view "
            "of capacity obligations; however, they are de-rated and defined for a Delivery Year, and they "
            "do not cover many routes-to-market used by flexibility providers."
        )
        + "\n\n"
    )

    cm_section_written = False
    try:
        ver_cfg, _ver_raw = load_verification_config(project_root)
        cm_bench = build_cm_benchmark(project_root, include_storage=ver_cfg.include_storage_default)
        if cm_bench is not None and not cm_bench.empty:
            cm_section_written = True
            cm_total_kw = float(pd.to_numeric(cm_bench.get("cm_benchmark_kw"), errors="coerce").fillna(0.0).sum())
            md.append(f"CM benchmark total (DSR de-rated, DY {ver_cfg.dy}): **{_fmt_kw(cm_total_kw)}**\n\n")

            md.append("### 5.1 CM benchmark by mapped asset class\n")
            md.append(
                _md_table(
                    ["Asset class (mapped)", "CM benchmark"],
                    [
                        [str(r["asset_class"]), _fmt_kw(r["cm_benchmark_kw"])]
                        for _, r in cm_bench.sort_values("cm_benchmark_kw", ascending=False).iterrows()
                    ],
                )
            )

            if combined_df is not None and not combined_df.empty:
                # Compare raw contributors (mapped to verification asset classes) to CM benchmark
                vdf = combined_df.copy()
                vdf["capacity_mw"] = pd.to_numeric(vdf.get("capacity_mw"), errors="coerce").fillna(0.0)
                vdf["asset_class_mapped"] = vdf.get("asset_class", "").apply(_map_to_validation_asset_class)
                contrib_raw = (
                    vdf.groupby("asset_class_mapped", as_index=False)
                    .agg(contributors_kw=("capacity_mw", lambda s: float(s.sum() * 1000.0)))
                )

                cmp_df = contrib_raw.merge(
                    cm_bench.rename(columns={"asset_class": "asset_class_mapped"}),
                    how="outer",
                    on="asset_class_mapped",
                )
                cmp_df["contributors_kw"] = pd.to_numeric(cmp_df.get("contributors_kw"), errors="coerce").fillna(0.0)
                cmp_df["cm_benchmark_kw"] = pd.to_numeric(cmp_df.get("cm_benchmark_kw"), errors="coerce").fillna(0.0)
                cmp_df["variance_kw"] = cmp_df["contributors_kw"] - cmp_df["cm_benchmark_kw"]
                cmp_df["variance_pct"] = cmp_df.apply(
                    lambda r: (r["variance_kw"] / r["cm_benchmark_kw"]) if r["cm_benchmark_kw"] else None,
                    axis=1,
                )

                md.append("### 5.2 Raw contributors vs CM benchmark (mapped)\n")
                md.append(
                    _md_table(
                        ["Asset class", "Contributors (raw)", "CM (DY)", "Delta kW", "Delta %"],
                        [
                            [
                                str(r["asset_class_mapped"]),
                                _fmt_kw(r["contributors_kw"]),
                                _fmt_kw(r["cm_benchmark_kw"]),
                                _fmt_kw(r["variance_kw"]),
                                _fmt_pct(r["variance_pct"]),
                            ]
                            for _, r in cmp_df.sort_values("asset_class_mapped").iterrows()
                        ],
                    )
                )

    except Exception as e:
        md.append(f"CM benchmark could not be built in this run: `{e}`\n\n")

    if not cm_section_written:
        md.append(
            _wrap(
                "CM benchmark tables are unavailable in this run (missing inputs or parsing issues). "
                "The rest of the report still provides raw contributor totals."
            )
            + "\n\n"
        )

    md.append("## 6) What we are missing (and why the CM benchmark is incomplete)\n")
    md.append(
        _wrap(
            "A CM-based sense-check will miss real flexibility where providers do not participate in the "
            "Capacity Market, or where flexibility is monetised via other channels. This is particularly "
            "true for domestic propositions, time-of-use optimisation, and DSO procurement. It also misses "
            "cases where capacity is technically available but not contracted."
        )
        + "\n\n"
    )
    md.append(
        "- Providers not in CM: domestic propositions (e.g., programme-based events), tariff-driven demand response, HEMS optimisation.\n"
        "- Non-CM routes to market: DFS, DSO flexibility tenders, Balancing Mechanism participation, ancillary services, bilateral contracts.\n"
        "- Definition mismatch: CM values are de-rated MW obligations for a Delivery Year; our dashboard capacity is a working definition of "
        "available/contracted flexibility over Nov-Feb.\n"
        "- Double counting risk: the same physical asset can appear in multiple services (CM + DSO + DFS) if not deduplicated with a unique asset identifier.\n"
        "- Deliverability gap: capacity nameplate does not guarantee dispatchable energy at the right times/locations; duration and response time matter.\n\n"
    )

    md.append("## 7) Why this validation approach works (and its limitations)\n")
    md.append(
        _wrap(
            "Why it works: CM results are one of the few public, audited, system-wide datasets that express "
            "a firm capacity obligation (de-rated for expected performance). Comparing our I&C-oriented "
            "submissions to CM helps identify possible overstatement, definition drift (e.g., nameplate vs "
            "deliverable), and missing segmentation (duration, availability windows)."
        )
        + "\n\n"
    )
    md.append(
        _wrap(
            "Limitations: (1) CM is not a complete representation of flexibility; (2) de-rating means CM MW "
            "is not directly comparable to undiscounted technical capacity; (3) DY vs Nov-Feb period mismatch; "
            "(4) CM technology taxonomy is coarse; (5) without asset-level IDs, overlap and double counting cannot be resolved."
        )
        + "\n\n"
    )

    md.append("## 8) Recommended next steps to strengthen validation\n")
    md.append(
        "- Add a template field for route-to-market per asset/service (CM, DFS, DSO, BM, ancillary, bilateral) and whether values are technical, contracted, or delivered.\n"
        "- Capture duration (MWh), response time, and availability windows to distinguish peak power from usable system flexibility.\n"
        "- Build additional external benchmarks: DFS dispatch summaries, DSO tender award registers, ancillary service volumes, and (where possible) BM unit participation.\n"
        "- Collect stable identifiers (CMU IDs for CM participants; internal asset IDs for others) to support de-duplication across services.\n"
        "- For domestic, validate via programme-level published numbers (participants, event counts, aggregate kWh) rather than CM.\n\n"
    )

    md_text = "\n".join(md).strip() + "\n"
    latest_path.write_text(md_text, encoding="utf-8")
    report_path.write_text(md_text, encoding="utf-8")

    return AdminValidationOutputs(report_path=report_path, latest_path=latest_path)
