"""
Ingestion coverage report (admin-only) for FlexDash.

This report answers: for each received file, which template sections/fields were
actually parsed into the pipeline dataset.

It is intended for internal troubleshooting and must not be circulated.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd


@dataclass(frozen=True)
class IngestionCoverageOutputs:
    report_path: Path
    latest_path: Path


def _ascii_safe(s: Optional[str]) -> str:
    if not s:
        return ""
    return (
        s.replace("\u2013", "-")  # en dash
        .replace("\u2014", "-")  # em dash
        .replace("\u2212", "-")  # minus
    )


def _wrap(s: str) -> str:
    return "\n".join(textwrap.wrap(s, width=110))


def _md_table(headers: List[str], rows: List[List[str]]) -> str:
    header_row = "| " + " | ".join(headers) + " |"
    sep_row = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return "\n".join([header_row, sep_row, body]) + "\n"


def _nonnull_count(df: pd.DataFrame, col: str) -> int:
    if df is None or df.empty or col not in df.columns:
        return 0
    try:
        return int(pd.to_numeric(df[col], errors="coerce").notna().sum())
    except Exception:
        return int(df[col].notna().sum())


def _has_any_nonnull(df: pd.DataFrame, cols: List[str]) -> bool:
    return any(_nonnull_count(df, c) > 0 for c in cols)


def generate_ingestion_coverage_report(
    *,
    project_root: Path,
    config: Dict[str, Any],
    parsed_data: Iterable[Any],
) -> IngestionCoverageOutputs:
    """
    Generate an admin-only ingestion coverage report (Markdown).

    Written to:
      - reports/admin/ingestion_coverage_latest.md (overwritten)
      - reports/admin/ingestion_coverage_YYYY-MM-DD.md (timestamped snapshot)
    """
    project_root = Path(project_root)
    out_dir = project_root / "reports" / "admin"
    out_dir.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now()
    stamp = generated_at.strftime("%Y-%m-%d")
    latest_path = out_dir / "ingestion_coverage_latest.md"
    report_path = out_dir / f"ingestion_coverage_{stamp}.md"

    study_period = (
        config.get("project", {}).get("study_period")
        or "Nov 2024-Feb 2025"
    )
    study_period_display = _ascii_safe(study_period)

    md: List[str] = []
    md.append("# Flex Dashboard - Ingestion Coverage Report (STRICTLY CONFIDENTIAL)\n")
    md.append("**ADMIN EYES ONLY. Do not forward. Do not circulate outside the authorised project team.**\n")
    md.append(f"- Generated: {generated_at.strftime('%Y-%m-%d %H:%M')}\n")
    md.append(f"- Study period (dashboard): {study_period_display}\n")
    md.append("\n---\n")

    md.append("## 1) What this report is\n")
    md.append(
        _wrap(
            "A per-file checklist of what was actually ingested from the returned spreadsheets. "
            "This is intended to catch cases where a contributor filled a section, but our parser "
            "did not extract it (or extracted it into unexpected fields)."
        )
        + "\n\n"
    )

    rows: List[List[str]] = []

    # Template section indicators (based on the V1.2 spec)
    part2_cols = ["portfolio_count", "market_share_pct", "winter_active_count", "count", "count_basis"]
    part31_cols = [
        "available_turn_up_mwh",
        "available_turn_down_mwh",
        "delivered_turn_up_mwh",
        "delivered_turn_down_mwh",
    ]
    part32_cols = [
        "available_turn_up_mw",
        "available_turn_down_mw",
        "delivered_turn_up_mw",
        "delivered_turn_down_mw",
        "capacity_mw",
    ]

    for p in parsed_data:
        df = getattr(p, "assets", None)
        df = df if isinstance(df, pd.DataFrame) else pd.DataFrame()

        contributor_name = str(getattr(p, "contributor_name", "") or "")
        contributor_id = str(getattr(p, "contributor_id", "") or "")
        template_version = str(getattr(p, "template_version", "") or "")
        sector = str(getattr(p, "sector", "") or "")
        meta = getattr(p, "metadata", {}) or {}
        fmt = str(meta.get("format") or "")

        part2_ok = _has_any_nonnull(df, part2_cols)
        p31_ok = _has_any_nonnull(df, part31_cols)
        p32_ok = _has_any_nonnull(df, part32_cols)

        services_df = getattr(p, "services", None)
        services_df = services_df if isinstance(services_df, pd.DataFrame) else pd.DataFrame()
        part4_ok = not services_df.empty
        tou_rows = 0
        tou_capacity_sum = 0.0
        if not services_df.empty:
            tou_rows = int(len(services_df))
            if "capacity_mw" in services_df.columns:
                try:
                    tou_capacity_sum = float(pd.to_numeric(services_df["capacity_mw"], errors="coerce").fillna(0.0).sum())
                except Exception:
                    tou_capacity_sum = 0.0

        capacity_nonnull = _nonnull_count(df, "capacity_mw")
        cap_sum = 0.0
        if not df.empty and "capacity_mw" in df.columns:
            try:
                cap_sum = float(pd.to_numeric(df["capacity_mw"], errors="coerce").fillna(0.0).sum())
            except Exception:
                cap_sum = 0.0

        warnings = list(getattr(p, "parse_warnings", []) or [])
        warnings_short = "; ".join(_ascii_safe(w) for w in warnings[:3]) if warnings else ""

        rows.append(
            [
                contributor_id,
                contributor_name,
                sector,
                template_version,
                fmt,
                str(len(df)),
                "Yes" if part2_ok else "No",
                "Yes" if p31_ok else "No",
                "Yes" if p32_ok else "No",
                "Yes" if part4_ok else "No",
                f"{cap_sum:,.2f}",
                str(capacity_nonnull),
                str(tou_rows),
                f"{tou_capacity_sum:,.2f}",
                warnings_short,
            ]
        )

    md.append("## 2) Coverage checklist (per submission)\n")
    md.append(
        _md_table(
            [
                "ID",
                "Contributor",
                "Sector",
                "Template",
                "Parser format",
                "Rows",
                "Part 2 (counts)",
                "Part 3.1 (MWh)",
                "Part 3.2 (MW)",
                "Part 4 (ToU)",
                "Capacity sum (MW)",
                "Capacity rows",
                "ToU rows",
                "ToU capacity sum (MW)",
                "Warnings (truncated)",
            ],
            rows,
        )
    )

    md.append("## 3) What to look for\n")
    md.append(
        "- If **Part 3.2 (MW)** is `No` for a contributor, their capacity is treated as missing unless they supplied MW via a custom format.\n"
        "- If **Capacity sum (MW)** looks implausibly high, check for unit confusion (kW vs MW) or accidental parsing of totals/notes.\n"
        "- If a supplier provides ToU/implicit flexibility, ensure we ingest the correct ToU section rather than forcing it into managed flex.\n"
    )

    content = "\n".join(md).strip() + "\n"
    latest_path.write_text(content, encoding="utf-8")
    report_path.write_text(content, encoding="utf-8")

    return IngestionCoverageOutputs(report_path=report_path, latest_path=latest_path)
