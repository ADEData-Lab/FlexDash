"""
Capacity Market (CM) benchmark ETL for FlexDash verification.

This module builds an *external* benchmark (CM DSR awards, DY 2024/25) which is
used only to sanity-check contributor totals. It must never be added into
dashboard totals.

Inputs are expected to be placed locally (no network download):
  - data/external/cm/T1_DY2024_25_AppendixA.xlsx
  - data/external/cm/T4_DY2024_25_AppendixA.xlsx
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import pandas as pd
import yaml


@dataclass(frozen=True)
class CMBenchmarkConfig:
    dy: str
    unit: str
    include_storage_default: bool
    t1_appendix_a: Path
    t4_appendix_a: Path
    mapping_csv: Path


REQUIRED_OUTPUT_COLUMNS = ["asset_class", "cm_benchmark_kw"]


def load_verification_config(project_root: Path) -> Tuple[CMBenchmarkConfig, Dict[str, Any]]:
    """
    Load verification settings and return a typed config plus the raw YAML.
    """
    cfg_path = project_root / "config" / "verification.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    bench = raw.get("benchmark", {})
    input_files = bench.get("input_files", {})

    return (
        CMBenchmarkConfig(
            dy=str(bench.get("dy", "2024/25")),
            unit=str(bench.get("unit", "kW")),
            include_storage_default=bool(bench.get("include_storage_default", False)),
            t1_appendix_a=project_root / input_files.get("t1_appendix_a", "data/external/cm/T1_DY2024_25_AppendixA.xlsx"),
            t4_appendix_a=project_root / input_files.get("t4_appendix_a", "data/external/cm/T4_DY2024_25_AppendixA.xlsx"),
            mapping_csv=project_root / "data" / "reference" / "cmu_to_asset_class.csv",
        ),
        raw,
    )


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    def first_present(*candidates: str) -> Optional[str]:
        for c in candidates:
            if c in df.columns:
                return c
        return None

    cmu_id_col = first_present("cmu id", "cmu_id", "cmu reference", "cmu ref", "cmu")
    derated_col = first_present(
        "capacity (mw)",
        "de-rated capacity (mw)",
        "derated capacity (mw)",
        "de rated capacity (mw)",
        "derated_capacity_mw",
        "de-rated capacity mw",
        "derated mw",
        "derated_mw",
    )
    classification_col = first_present("cmu classification", "cmu_classification", "cmu type", "cmu_type")
    fuel_col = first_present("fuel type", "fuel_type", "technology", "technology class", "technology/type", "type")
    name_col = first_present("cmu name", "cmu_name", "name")
    company_col = first_present(
        "company",
        "company name",
        "bidding group",
        "company/bidding group",
        "bidding_group",
        "applicant company",
        "parent company",
    )

    missing = [
        k
        for k, v in {
            "cmu_id": cmu_id_col,
            "derated_mw": derated_col,
            "classification_or_fuel": (classification_col or fuel_col),
        }.items()
        if v is None
    ]
    if missing:
        raise ValueError(
            "CM Appendix A is missing required columns: "
            + ", ".join(missing)
            + ". Expected columns like 'CMU ID' and 'Capacity (MW)'."
        )

    df = df.rename(
        columns={
            cmu_id_col: "cmu_id",
            derated_col: "derated_mw",
            name_col or "cmu_name": "cmu_name",
            company_col or "company": "company",
            classification_col or "cmu classification": "cmu_classification",
            fuel_col or "fuel type": "fuel_type",
        }
    )

    # Ensure required columns exist
    for c in ["cmu_name", "company"]:
        if c not in df.columns:
            df[c] = None

    if "cmu_classification" not in df.columns:
        df["cmu_classification"] = None
    if "fuel_type" not in df.columns:
        df["fuel_type"] = None

    df["technology"] = (
        df["cmu_classification"].fillna("").astype(str).str.strip()
        + " | "
        + df["fuel_type"].fillna("").astype(str).str.strip()
    ).str.strip(" |")

    return df[["cmu_id", "cmu_name", "technology", "company", "derated_mw"]]


def _detect_header_row(path: Path, sheet_name: str) -> int:
    preview = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=50)
    for idx in range(len(preview)):
        row = preview.iloc[idx].astype(str).str.strip().str.lower().tolist()
        if "cmu id" in row and ("capacity (mw)" in row or "de-rated capacity (mw)" in row or "derated capacity (mw)" in row):
            return idx
    # Fallback: look for CMU ID alone (some sheets omit capacity string in header row)
    for idx in range(len(preview)):
        row = preview.iloc[idx].astype(str).str.strip().str.lower().tolist()
        if "cmu id" in row:
            return idx
    raise ValueError("Could not detect header row for CM Appendix A.")


def load_appendix_a(path: Path) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    sheet = xls.sheet_names[0]
    header_row = _detect_header_row(path, sheet)
    df = pd.read_excel(path, sheet_name=sheet, header=header_row)
    df = _normalise_columns(df)
    df["cmu_id"] = df["cmu_id"].astype(str).str.strip()
    df["technology"] = df["technology"].astype(str).str.strip()
    df["derated_mw"] = pd.to_numeric(df["derated_mw"], errors="coerce").fillna(0.0)
    return df


def _filter_dsr(df: pd.DataFrame, include_storage: bool) -> pd.DataFrame:
    tech = df["technology"].astype(str)
    is_dsr = tech.str.contains(r"dsr|demand\\s*side\\s*response", case=False, na=False)
    if include_storage:
        is_storage = tech.str.contains(r"storage|battery", case=False, na=False)
        return df[is_dsr | is_storage].copy()
    return df[is_dsr].copy()


def _load_mapping(mapping_csv: Path) -> list[tuple[re.Pattern[str], str]]:
    mapping_df = pd.read_csv(mapping_csv)
    patterns: list[tuple[re.Pattern[str], str]] = []
    for _, row in mapping_df.iterrows():
        pat = str(row.get("technology_pattern", "")).strip()
        target = str(row.get("asset_class", "")).strip()
        if not pat or not target:
            continue
        patterns.append((re.compile(pat), target))
    return patterns


def _map_asset_class(technology: str, patterns: Iterable[tuple[re.Pattern[str], str]]) -> str:
    for pat, target in patterns:
        if pat.search(technology or ""):
            return target
    # Safe fallback
    tech = (technology or "").lower()
    if "storage" in tech or "battery" in tech:
        return "Battery"
    if "dsr" in tech or "demand" in tech:
        return "I&C load"
    return "Other DSR"


def build_cm_benchmark(project_root: Path, include_storage: Optional[bool] = None) -> pd.DataFrame:
    """
    Build the CM benchmark table aggregated to dashboard verification asset classes.

    Returns a dataframe with columns:
      - asset_class
      - cm_benchmark_kw
    """
    cfg, _raw = load_verification_config(project_root)
    include_storage = cfg.include_storage_default if include_storage is None else bool(include_storage)

    if not cfg.t1_appendix_a.exists() or not cfg.t4_appendix_a.exists():
        return pd.DataFrame(columns=REQUIRED_OUTPUT_COLUMNS)

    t1 = load_appendix_a(cfg.t1_appendix_a)
    t4 = load_appendix_a(cfg.t4_appendix_a)

    cmu = pd.concat([t4, t1], ignore_index=True)

    # Union + incremental top-up rule: sum by CMU for the same delivery year.
    cmu = (
        cmu.groupby(["cmu_id"], as_index=False)
        .agg(
            {
                "cmu_name": "first",
                "technology": "first",
                "company": "first",
                "derated_mw": "sum",
            }
        )
    )

    cmu = _filter_dsr(cmu, include_storage=include_storage)

    patterns = _load_mapping(cfg.mapping_csv) if cfg.mapping_csv.exists() else []
    cmu["asset_class"] = cmu["technology"].apply(lambda t: _map_asset_class(str(t), patterns))

    cmu["cm_benchmark_kw"] = cmu["derated_mw"] * 1000.0

    bench = cmu.groupby("asset_class", as_index=False).agg({"cm_benchmark_kw": "sum"})
    bench["cm_benchmark_kw"] = pd.to_numeric(bench["cm_benchmark_kw"], errors="coerce").fillna(0.0)

    return bench


def write_cm_outputs(project_root: Path, benchmark_df: pd.DataFrame) -> Dict[str, Path]:
    """
    Write benchmark outputs under data/processed.

    Tries Parquet first; falls back to CSV if Parquet engine isn't available.
    """
    out_dir = project_root / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs: Dict[str, Path] = {}
    parquet_path = out_dir / "cm_benchmark_dy2024_25.parquet"
    csv_path = out_dir / "cm_benchmark_dy2024_25.csv"

    try:
        benchmark_df.to_parquet(parquet_path, index=False)
        outputs["cm_benchmark_parquet"] = parquet_path
    except Exception:
        benchmark_df.to_csv(csv_path, index=False)
        outputs["cm_benchmark_csv"] = csv_path

    return outputs


def build_verification_compare(
    project_root: Path,
    contributors_df: pd.DataFrame,
    include_storage: Optional[bool] = None,
) -> pd.DataFrame:
    """
    Join CM benchmark to contributor totals (asset_class-level) and compute variance.

    Expected contributor columns (minimum):
      - asset_class
      - contributors_kw

    Optional contributor columns:
      - contributors_k
      - contributors_illustrative
    """
    bench = build_cm_benchmark(project_root, include_storage=include_storage)
    if bench.empty:
        return pd.DataFrame(
            columns=[
                "asset_class",
                "cm_benchmark_kw",
                "contributors_kw",
                "variance_kw",
                "variance_pct",
            ]
        )

    base = contributors_df.copy()
    if "asset_class" not in base.columns or "contributors_kw" not in base.columns:
        raise ValueError("contributors_df must include columns: asset_class, contributors_kw")

    base["contributors_kw"] = pd.to_numeric(base["contributors_kw"], errors="coerce").fillna(0.0)

    out = base.merge(bench, on="asset_class", how="outer")
    out["cm_benchmark_kw"] = pd.to_numeric(out["cm_benchmark_kw"], errors="coerce").fillna(0.0)
    out["contributors_kw"] = pd.to_numeric(out["contributors_kw"], errors="coerce").fillna(0.0)

    out["variance_kw"] = out["contributors_kw"] - out["cm_benchmark_kw"]
    out["variance_pct"] = out.apply(
        lambda r: (r["variance_kw"] / r["cm_benchmark_kw"]) if r["cm_benchmark_kw"] else None,
        axis=1,
    )

    # Stable ordering for UI
    out = out.sort_values(["asset_class"], kind="stable").reset_index(drop=True)
    return out


def write_verification_outputs(project_root: Path, compare_df: pd.DataFrame) -> Dict[str, Path]:
    """
    Write verification compare outputs under data/processed.
    """
    out_dir = project_root / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs: Dict[str, Path] = {}
    parquet_path = out_dir / "verification_compare.parquet"
    csv_path = out_dir / "verification_compare.csv"

    try:
        compare_df.to_parquet(parquet_path, index=False)
        outputs["verification_compare_parquet"] = parquet_path
    except Exception:
        compare_df.to_csv(csv_path, index=False)
        outputs["verification_compare_csv"] = csv_path

    return outputs
