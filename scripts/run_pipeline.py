#!/usr/bin/env python3
"""
FlexDash Pipeline Runner

Main orchestration script that runs the complete data pipeline:
1. Ingest raw data files
2. Validate data quality
3. Apply disclosure controls
4. Generate anonymised outputs
5. Export dashboard data

Usage:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --config config/settings.yaml
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.template_parser import TemplateParser, parse_all_files
from src.ingestion.validators import DataValidator
from src.governance.disclosure import DisclosureController, DisclosureStatus
from src.governance.anonymiser import Anonymiser
from src.governance.audit import AuditLogger
from src.analysis.aggregator import DataAggregator
from src.analysis.cm_benchmark import build_cm_benchmark, build_verification_compare, load_verification_config
from src.analysis.metrics import MetricsCalculator, DashboardMetrics
from src.analysis.asset_grouping import assign_asset_group, load_asset_class_group_map
from src.export.dashboard_data import DashboardExporter
from src.reports.admin_validation_report import generate_admin_validation_report
from src.reports.admin_validation_dashboard import generate_admin_validation_dashboard
from src.reports.ingestion_coverage_report import generate_ingestion_coverage_report
from src.reports.public_dashboard_standalone import (
    generate_public_dashboard_standalone,
    generate_public_dashboard_standalone_steering_safe,
    generate_public_dashboard_standalone_release_safe,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def run_pipeline(config: dict) -> dict:
    """
    Run the complete FlexDash pipeline.

    Args:
        config: Configuration dictionary

    Returns:
        Pipeline results summary
    """
    results = {
        'start_time': datetime.now().isoformat(),
        'status': 'running',
        'steps': {}
    }

    # Initialize components
    project_root = Path(__file__).parent.parent
    data_source = project_root / config.get('source_data', '../02 DATA RECEIVED')
    output_dir = project_root / config['paths']['dashboard_data']
    audit_path = project_root / config['paths']['audit_logs'] / 'pipeline_audit.jsonl'

    # Ensure output directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    audit_logger = AuditLogger(audit_path)
    validator = DataValidator(config.get('quality', {}))
    k_threshold = config.get('disclosure', {}).get('k_threshold', 3)
    rounding = config.get('disclosure', {}).get('rounding_precision', 10)
    anonymiser = Anonymiser(config.get('anonymisation', {}))
    metrics_calc = MetricsCalculator(config)
    exporter = DashboardExporter(output_dir)

    # Populated later (used to add grouped asset breakdown to public dashboard extras)
    asset_group_export = pd.DataFrame()

    try:
        # Step 1: Ingest data
        logger.info("=" * 60)
        logger.info("STEP 1: Data Ingestion")
        logger.info("=" * 60)

        # Non-template TOU returns are normalised (best-effort) inside src.ingestion.template_parser.parse_all_files
        parsed_data = parse_all_files(data_source)
        results['steps']['ingestion'] = {
            'files_parsed': len(parsed_data),
            'success': True
        }

        for data in parsed_data:
            audit_logger.log_ingestion(
                filename=data.contributor_name,
                records_parsed=len(data.assets) + len(data.events),
                validation_result={'warnings': len(data.parse_warnings), 'errors': len(data.parse_errors)}
            )
            logger.info(f"  Parsed: {data.contributor_name} ({len(data.assets)} asset records)")

        # Admin-only ingestion coverage (helps catch parser gaps)
        try:
            coverage_outputs = generate_ingestion_coverage_report(
                project_root=project_root,
                config=config,
                parsed_data=parsed_data,
            )
            logger.info(f"  Ingestion coverage (latest): {coverage_outputs.latest_path}")
            results['steps']['ingestion_coverage_report'] = {
                'latest_path': str(coverage_outputs.latest_path),
                'snapshot_path': str(coverage_outputs.report_path),
                'success': True,
            }
        except Exception as e:
            logger.warning(f"  Ingestion coverage report failed: {e}")
            results['steps']['ingestion_coverage_report'] = {
                'success': False,
                'error': str(e),
            }

        # Step 2: Validate data
        logger.info("=" * 60)
        logger.info("STEP 2: Data Validation")
        logger.info("=" * 60)

        validation_results = []
        for data in parsed_data:
            result = validator.validate(data)
            validation_results.append(result)
            status = "PASS" if result.is_valid else "WARN"
            logger.info(f"  {data.contributor_name}: {status} (completeness: {result.completeness_score:.1%})")

        quality_report = validator.generate_quality_report(validation_results)
        results['steps']['validation'] = {
            'submissions': quality_report['total_submissions'],
            'average_completeness': quality_report['average_completeness'],
            'success': True
        }

        # Step 3: Combine data with contributor tracking
        logger.info("=" * 60)
        logger.info("STEP 3: Combine & Process Data")
        logger.info("=" * 60)

        # Build combined dataframe with contributor tracking
        all_records = []
        for data in parsed_data:
            if not data.assets.empty:
                for _, row in data.assets.iterrows():
                    record = row.to_dict()
                    record['contributor_id'] = data.contributor_id
                    # Use sector from row if available, otherwise from parsed data
                    if 'sector' not in record or pd.isna(record.get('sector')):
                        record['sector'] = data.sector
                    all_records.append(record)

        if not all_records:
            logger.warning("No asset data found in any file!")
            combined_df = pd.DataFrame()
        else:
            combined_df = pd.DataFrame(all_records)
            logger.info(f"  Combined: {len(combined_df)} total records from {len(parsed_data)} contributors")

        # Ensure required columns exist
        if not combined_df.empty:
            if 'capacity_mw' not in combined_df.columns:
                combined_df['capacity_mw'] = np.nan
            if 'count' not in combined_df.columns:
                combined_df['count'] = np.nan
            if 'asset_class' not in combined_df.columns:
                combined_df['asset_class'] = 'unknown'

            # Fill missing values
            combined_df['capacity_mw'] = pd.to_numeric(combined_df['capacity_mw'], errors='coerce')
            combined_df['count'] = pd.to_numeric(combined_df['count'], errors='coerce')

            # Broader asset grouping for disclosure-safe public reporting.
            asset_group_map = load_asset_class_group_map(project_root)
            combined_df["asset_group"] = combined_df["asset_class"].apply(lambda a: assign_asset_group(a, asset_group_map))

        results['steps']['combine'] = {
            'total_records': len(combined_df),
            'contributors': combined_df['contributor_id'].nunique() if not combined_df.empty else 0,
            'success': True
        }

        # Step 4: Aggregate with disclosure control
        logger.info("=" * 60)
        logger.info("STEP 4: Aggregation & Disclosure Control")
        logger.info("=" * 60)

        disclosure_controller = DisclosureController(config.get('disclosure', {}))

        def governed_aggregate(df: pd.DataFrame, dimension_cols: list[str]) -> pd.DataFrame:
            """
            Aggregate with disclosure control, replacing unsafe cells with illustrative values.

            This enforces k-anonymity (k=3) by ensuring that no cell with k < threshold
            publishes real underlying values.
            """
            if df.empty:
                return pd.DataFrame()

            metric_cols = [c for c in ['capacity_mw', 'count'] if c in df.columns]
            protected_df, _report = disclosure_controller.apply_disclosure_control(
                df=df,
                contributor_col='contributor_id',
                dimension_cols=dimension_cols,
                metric_cols=metric_cols
            )

            if protected_df.empty:
                return protected_df

            # Keep contributor counts for UI governance cues.
            # `k` is a legacy single value (based on capacity_mw where available).
            # Metric-specific k values are also exposed for UI components (e.g. counts charts).
            rename_cols = {}
            if "_contributor_count" in protected_df.columns:
                rename_cols["_contributor_count"] = "k"
            if "_k_capacity_mw" in protected_df.columns:
                rename_cols["_k_capacity_mw"] = "k_capacity_mw"
            if "_k_count" in protected_df.columns:
                rename_cols["_k_count"] = "k_count"
            if rename_cols:
                protected_df = protected_df.rename(columns=rename_cols)

            # Fill illustrative cells with disclosure-safe ranges (never real values).
            # This preserves order-of-magnitude without implying false precision.
            protected_df = anonymiser.fill_illustrative_ranges(
                protected_df,
                metric_cols=metric_cols,
            )

            # Apply rounding and standardise illustrative flags
            protected_df = anonymiser.prepare_for_publication(
                protected_df,
                metric_cols=metric_cols,
                rounding_precision=rounding
            )

            return protected_df

        # Aggregate by sector
        if not combined_df.empty and 'sector' in combined_df.columns:
            sector_df = governed_aggregate(combined_df, ['sector'])
            logger.info(f"  Sector aggregation: {len(sector_df)} groups")
            for _, row in sector_df.iterrows():
                logger.info(f"    {row['sector']}: {row.get('capacity_mw', 0):.0f} MW (k={row.get('k', 'n/a')})")
        else:
            sector_df = pd.DataFrame()
            logger.warning("  No sector data available")

        # Aggregate by asset class
        if not combined_df.empty and 'asset_class' in combined_df.columns:
            asset_df = governed_aggregate(combined_df, ['asset_class'])
            logger.info(f"  Asset class aggregation: {len(asset_df)} groups")
        else:
            asset_df = pd.DataFrame()
            logger.warning("  No asset class data available")

        # Aggregate by broader asset groups (disclosure-safe categories)
        if not combined_df.empty and "asset_group" in combined_df.columns:
            asset_group_df = governed_aggregate(combined_df, ["asset_group"])
            logger.info(f"  Asset group aggregation: {len(asset_group_df)} groups")
        else:
            asset_group_df = pd.DataFrame()
            logger.warning("  No asset group data available")

        # Stash for later export (used in public dashboard extras)
        asset_group_export = asset_group_df

        # Aggregate by sector + asset class
        if not combined_df.empty and 'sector' in combined_df.columns and 'asset_class' in combined_df.columns:
            sector_asset_df = governed_aggregate(combined_df, ['sector', 'asset_class'])
            logger.info(f"  Sector+Asset aggregation: {len(sector_asset_df)} groups")
        else:
            sector_asset_df = pd.DataFrame()

        # Aggregate by sector + asset group (preferred for sector-specific charts to improve k)
        if not combined_df.empty and "sector" in combined_df.columns and "asset_group" in combined_df.columns:
            sector_asset_group_df = governed_aggregate(combined_df, ["sector", "asset_group"])
            logger.info(f"  Sector+AssetGroup aggregation: {len(sector_asset_group_df)} groups")
        else:
            sector_asset_group_df = pd.DataFrame()

        results['steps']['aggregation'] = {
            'sector_groups': len(sector_df),
            'asset_groups': len(asset_df),
            'asset_group_groups': len(asset_group_df),
            'success': True
        }

        # Internal/admin validation report (unsuppressed; not published)
        logger.info("=" * 60)
        logger.info("STEP 4b: Admin Validation Report (CONFIDENTIAL)")
        logger.info("=" * 60)
        try:
            outputs = generate_admin_validation_report(
                project_root=project_root,
                config=config,
                combined_df=combined_df,
                parsed_data=parsed_data,
                sector_public_df=sector_df,
                asset_public_df=asset_df,
            )
            logger.info(f"  Admin report (latest): {outputs.latest_path}")
            results['steps']['admin_validation_report'] = {
                'latest_path': str(outputs.latest_path),
                'snapshot_path': str(outputs.report_path),
                'success': True,
            }

            dashboard_outputs = generate_admin_validation_dashboard(
                project_root=project_root,
                config=config,
                combined_df=combined_df,
                parsed_data=parsed_data,
                sector_public_df=sector_df,
                asset_public_df=asset_df,
            )
            logger.info(f"  Admin dashboard: {dashboard_outputs.index_path}")
            logger.info(f"  Admin dashboard (single file): {dashboard_outputs.standalone_path}")
            results['steps']['admin_validation_dashboard'] = {
                'index_path': str(dashboard_outputs.index_path),
                'data_json_path': str(dashboard_outputs.data_json_path),
                'data_js_path': str(dashboard_outputs.data_js_path),
                'standalone_path': str(dashboard_outputs.standalone_path),
                'success': True,
            }
        except Exception as e:
            logger.warning(f"  Admin validation report failed: {e}")
            results['steps']['admin_validation_report'] = {
                'success': False,
                'error': str(e),
            }
            results['steps']['admin_validation_dashboard'] = {
                'success': False,
                'error': str(e),
            }

        # Step 5: Calculate metrics
        logger.info("=" * 60)
        logger.info("STEP 5: Calculate Metrics")
        logger.info("=" * 60)

        contributor_count = combined_df['contributor_id'].nunique() if not combined_df.empty else 0

        def _headline_series(
            df_slice: pd.DataFrame,
            series: pd.Series,
            label: str,
            metric: str,
            bucket_fn,
            rounding_precision: int | None,
        ) -> dict:
            """
            Compute a disclosure-safe headline metric from an arbitrary series.

            The series must be aligned to df_slice rows and df_slice must contain contributor_id.
            """
            if df_slice is None or df_slice.empty or 'contributor_id' not in df_slice.columns:
                bucket = bucket_fn(0.0)
                return {
                    "value": 0.0,
                    "illustrative": True,
                    "range_label": bucket["label"],
                    "range_min": bucket["min"],
                    "range_max": bucket["max"],
                    "k": 0,
                    "reason": "no data",
                }

            metric_series = pd.to_numeric(series, errors='coerce')
            metric_df = df_slice[metric_series.notna()].copy()
            if metric_df.empty:
                bucket = bucket_fn(0.0)
                return {
                    "value": 0.0,
                    "illustrative": True,
                    "range_label": bucket["label"],
                    "range_min": bucket["min"],
                    "range_max": bucket["max"],
                    "k": 0,
                    "reason": "no numeric values",
                }

            metric_df["_metric"] = metric_series[metric_series.notna()].astype(float)
            # Treat zero as "not provided" for headline calculations to avoid counting blank cells as real zeros.
            metric_df = metric_df[metric_df["_metric"] > 0]
            if metric_df.empty:
                bucket = bucket_fn(0.0)
                return {
                    "value": 0.0,
                    "illustrative": True,
                    "range_label": bucket["label"],
                    "range_min": bucket["min"],
                    "range_max": bucket["max"],
                    "k": 0,
                    "reason": "all values zero/missing",
                }

            raw_total = float(metric_df["_metric"].sum())
            contributor_ids = metric_df["contributor_id"].astype(str).unique().tolist()
            contributor_values = metric_df.groupby("contributor_id")["_metric"].sum().astype(float).tolist()

            decision = disclosure_controller.check_cell(
                value=raw_total,
                contributor_ids=contributor_ids,
                dimension="headline",
                dimension_value=label,
                metric=metric,
                contributor_values=contributor_values,
            )

            if decision.status == DisclosureStatus.SAFE:
                safe_val = float(decision.final_value) if decision.final_value is not None else raw_total
                if rounding_precision:
                    safe_val = round(safe_val / rounding_precision) * rounding_precision
                return {
                    "value": safe_val,
                    "illustrative": False,
                    "range_label": None,
                    "range_min": None,
                    "range_max": None,
                    "k": decision.contributor_count,
                    "reason": decision.reason,
                }

            bucket = bucket_fn(raw_total)
            midpoint = float(bucket["midpoint"])
            if rounding_precision:
                midpoint = round(midpoint / rounding_precision) * rounding_precision
            return {
                "value": midpoint,
                "illustrative": True,
                "range_label": bucket["label"],
                "range_min": bucket["min"],
                "range_max": bucket["max"],
                "k": decision.contributor_count,
                "reason": decision.reason,
            }

        def _headline_capacity(df_slice: pd.DataFrame, label: str) -> dict:
            """
            Compute a disclosure-safe headline capacity figure for a slice of the raw combined data.

            Returns:
              - value_mw (published numeric; may be a range midpoint)
              - illustrative (bool)
              - range_label/min/max (optional; only set when illustrative)
            """
            if df_slice is None or df_slice.empty or 'capacity_mw' not in df_slice.columns:
                bucket = anonymiser._disclosure_range_mw(0.0)
                return {
                    "value_mw": 0.0,
                    "illustrative": True,
                    "range_label": bucket["label"],
                    "range_min": bucket["min"],
                    "range_max": bucket["max"],
                }

            cap_series = pd.to_numeric(df_slice['capacity_mw'], errors='coerce')
            cap_df = df_slice[cap_series.notna()].copy()
            if cap_df.empty:
                bucket = anonymiser._disclosure_range_mw(0.0)
                return {
                    "value_mw": 0.0,
                    "illustrative": True,
                    "range_label": bucket["label"],
                    "range_min": bucket["min"],
                    "range_max": bucket["max"],
                }

            raw_total = float(pd.to_numeric(cap_df['capacity_mw'], errors='coerce').sum())
            contributor_ids = cap_df['contributor_id'].astype(str).unique().tolist()
            contributor_values = (
                cap_df.groupby('contributor_id')['capacity_mw']
                .sum()
                .astype(float)
                .tolist()
            )

            decision = disclosure_controller.check_cell(
                value=raw_total,
                contributor_ids=contributor_ids,
                dimension="headline",
                dimension_value=label,
                metric="capacity_mw",
                contributor_values=contributor_values,
            )

            if decision.status == DisclosureStatus.SAFE:
                safe_val = float(decision.final_value) if decision.final_value is not None else raw_total
                safe_val = round(safe_val / rounding) * rounding
                return {
                    "value_mw": safe_val,
                    "illustrative": False,
                    "range_label": None,
                    "range_min": None,
                    "range_max": None,
                }

            bucket = anonymiser._disclosure_range_mw(raw_total)
            midpoint = round(float(bucket["midpoint"]) / rounding) * rounding
            return {
                "value_mw": midpoint,
                "illustrative": True,
                "range_label": bucket["label"],
                "range_min": bucket["min"],
                "range_max": bucket["max"],
            }

        headline_total = _headline_capacity(combined_df, "total")
        headline_domestic = (
            _headline_capacity(combined_df[combined_df['sector'] == 'domestic'], "domestic")
            if not combined_df.empty and 'sector' in combined_df.columns
            else _headline_capacity(pd.DataFrame(), "domestic")
        )
        headline_ic = (
            _headline_capacity(combined_df[combined_df['sector'] == 'ic'], "ic")
            if not combined_df.empty and 'sector' in combined_df.columns
            else _headline_capacity(pd.DataFrame(), "ic")
        )

        # Delivered MW (reported in template section 3.2 for a subset of contributors)
        if not combined_df.empty:
            delivered_series = pd.concat(
                [
                    pd.to_numeric(combined_df.get("delivered_turn_up_mw", pd.Series(index=combined_df.index)), errors="coerce"),
                    pd.to_numeric(combined_df.get("delivered_turn_down_mw", pd.Series(index=combined_df.index)), errors="coerce"),
                ],
                axis=1,
            ).max(axis=1, skipna=True)
            headline_delivered = _headline_series(
                combined_df,
                delivered_series,
                label="total_delivered",
                metric="delivered_mw",
                bucket_fn=anonymiser._disclosure_range_mw,
                rounding_precision=rounding,
            )
        else:
            headline_delivered = _headline_series(
                pd.DataFrame(),
                pd.Series(dtype=float),
                label="total_delivered",
                metric="delivered_mw",
                bucket_fn=anonymiser._disclosure_range_mw,
                rounding_precision=rounding,
            )

        delivery_factor_pct = 0.0
        if headline_total["value_mw"] and headline_delivered["value"]:
            delivery_factor_pct = min((headline_delivered["value"] / headline_total["value_mw"]) * 100.0, 100.0)

        metrics = DashboardMetrics(
            total_available_mw=headline_total["value_mw"],
            total_delivered_mw=float(headline_delivered["value"]),
            delivery_factor_pct=float(round(delivery_factor_pct, 1)),
            domestic_available_mw=headline_domestic["value_mw"],
            domestic_delivered_mw=0,
            domestic_delivery_factor_pct=0,
            ic_available_mw=headline_ic["value_mw"],
            ic_delivered_mw=0,
            ic_delivery_factor_pct=0,
            contributor_count=contributor_count,
            study_period=config.get('project', {}).get('study_period', 'Nov 2024-Feb 2025'),
            total_available_mw_illustrative=bool(headline_total["illustrative"]),
            total_available_range=headline_total["range_label"],
            total_available_range_min=headline_total["range_min"],
            total_available_range_max=headline_total["range_max"],
            total_delivered_mw_illustrative=bool(headline_delivered["illustrative"]),
            total_delivered_range=headline_delivered["range_label"],
            total_delivered_range_min=headline_delivered["range_min"],
            total_delivered_range_max=headline_delivered["range_max"],
            domestic_available_mw_illustrative=bool(headline_domestic["illustrative"]),
            domestic_available_range=headline_domestic["range_label"],
            domestic_available_range_min=headline_domestic["range_min"],
            domestic_available_range_max=headline_domestic["range_max"],
            ic_available_mw_illustrative=bool(headline_ic["illustrative"]),
            ic_available_range=headline_ic["range_label"],
            ic_available_range_min=headline_ic["range_min"],
            ic_available_range_max=headline_ic["range_max"],
        )

        # Methodology v7-style derived metrics used by the front-end overview cards.
        extras: dict = {}
        try:
            # --- Explicit delivered energy (GWh) from template section 3.1 (MWh)
            if not combined_df.empty:
                delivered_mwh_series = (
                    pd.to_numeric(combined_df.get("delivered_turn_up_mwh", pd.Series(index=combined_df.index)), errors="coerce").fillna(0)
                    + pd.to_numeric(combined_df.get("delivered_turn_down_mwh", pd.Series(index=combined_df.index)), errors="coerce").fillna(0)
                )
                explicit_energy_df = combined_df[["contributor_id"]].copy()
                explicit_energy_df["delivered_gwh"] = delivered_mwh_series / 1000.0
            else:
                explicit_energy_df = pd.DataFrame(columns=["contributor_id", "delivered_gwh"])

            headline_explicit_gwh = _headline_series(
                explicit_energy_df,
                explicit_energy_df.get("delivered_gwh", pd.Series(dtype=float)),
                label="explicit_delivered_gwh",
                metric="explicit_delivered_gwh",
                bucket_fn=anonymiser._disclosure_range_gwh,
                rounding_precision=1,
            )

            # --- Implicit (ToU) delivered energy (GWh) from supplier submissions (Part 4.2 totals)
            tou_rows: List[Dict[str, Any]] = []
            for d in parsed_data:
                if d.services is None or d.services.empty or "service_type" not in d.services.columns:
                    continue
                tou_df = d.services[d.services["service_type"] == "tou_tariff"]
                if tou_df.empty:
                    continue
                td = float(pd.to_numeric(tou_df.get("total_turn_down_mwh", 0), errors="coerce").fillna(0).sum())
                tu = float(pd.to_numeric(tou_df.get("total_turn_up_mwh", 0), errors="coerce").fillna(0).sum())
                cap = float(pd.to_numeric(tou_df.get("capacity_mw", 0), errors="coerce").fillna(0).sum())
                tou_rows.append(
                    {
                        "contributor_id": d.contributor_id,
                        "delivered_gwh": (td + tu) / 1000.0,
                        "capacity_mw": cap,
                    }
                )

            tou_df = pd.DataFrame(tou_rows) if tou_rows else pd.DataFrame(columns=["contributor_id", "delivered_gwh", "capacity_mw"])

            headline_implicit_gwh = _headline_series(
                tou_df,
                tou_df.get("delivered_gwh", pd.Series(dtype=float)),
                label="implicit_delivered_gwh",
                metric="implicit_delivered_gwh",
                bucket_fn=anonymiser._disclosure_range_gwh,
                rounding_precision=1,
            )

            # --- Total delivered energy = explicit + implicit (per contributor; then disclosure)
            energy_by_contrib = (
                pd.concat(
                    [
                        explicit_energy_df[["contributor_id", "delivered_gwh"]],
                        tou_df[["contributor_id", "delivered_gwh"]],
                    ],
                    ignore_index=True,
                )
                .groupby("contributor_id", as_index=False)["delivered_gwh"]
                .sum()
            )

            headline_total_gwh = _headline_series(
                energy_by_contrib,
                energy_by_contrib.get("delivered_gwh", pd.Series(dtype=float)),
                label="total_delivered_gwh",
                metric="total_delivered_gwh",
                bucket_fn=anonymiser._disclosure_range_gwh,
                rounding_precision=1,
            )

            # --- Utilisation rate (derived from published delivered/available MW)
            utilisation_obj = None
            if metrics.total_available_mw and metrics.total_delivered_mw:
                utilisation_rate_pct = int(
                    round(min((metrics.total_delivered_mw / metrics.total_available_mw) * 100.0, 100.0), 0)
                )
                utilisation_obj = {
                    "overall_rate_pct": utilisation_rate_pct,
                    "overall_rate_note": "Estimated from delivered MW reported in template section 3.2; treated as illustrative where disclosure rules apply.",
                }

            # --- Directional breakdown (turn-up vs turn-down capacity, MW)
            if not combined_df.empty:
                tu_by = (
                    pd.to_numeric(combined_df.get("available_turn_up_mw", pd.Series(index=combined_df.index)), errors="coerce")
                    .fillna(0)
                )
                td_by = (
                    pd.to_numeric(combined_df.get("available_turn_down_mw", pd.Series(index=combined_df.index)), errors="coerce")
                    .fillna(0)
                )
                turn_up_df = combined_df[["contributor_id"]].copy()
                turn_up_df["capacity_mw"] = tu_by
                turn_down_df = combined_df[["contributor_id"]].copy()
                turn_down_df["capacity_mw"] = td_by
            else:
                turn_up_df = pd.DataFrame(columns=["contributor_id", "capacity_mw"])
                turn_down_df = pd.DataFrame(columns=["contributor_id", "capacity_mw"])

            headline_turn_up = _headline_series(
                turn_up_df,
                turn_up_df.get("capacity_mw", pd.Series(dtype=float)),
                label="turn_up_capacity_mw",
                metric="turn_up_capacity_mw",
                bucket_fn=anonymiser._disclosure_range_mw,
                rounding_precision=rounding,
            )
            headline_turn_down = _headline_series(
                turn_down_df,
                turn_down_df.get("capacity_mw", pd.Series(dtype=float)),
                label="turn_down_capacity_mw",
                metric="turn_down_capacity_mw",
                bucket_fn=anonymiser._disclosure_range_mw,
                rounding_precision=rounding,
            )

            # --- Explicit vs implicit capacity (MW)
            headline_implicit_capacity = _headline_series(
                tou_df,
                tou_df.get("capacity_mw", pd.Series(dtype=float)),
                label="implicit_capacity_mw",
                metric="implicit_capacity_mw",
                bucket_fn=anonymiser._disclosure_range_mw,
                rounding_precision=rounding,
            )

            extras = {
                "energy_metrics": {
                    "total": {
                        "delivered_gwh": headline_total_gwh["value"],
                        "delivered_gwh_illustrative": bool(headline_total_gwh["illustrative"]),
                        "delivered_range": headline_total_gwh["range_label"],
                        "delivered_range_min": headline_total_gwh["range_min"],
                        "delivered_range_max": headline_total_gwh["range_max"],
                    },
                    "explicit": {
                        "delivered_gwh": headline_explicit_gwh["value"],
                        "delivered_gwh_illustrative": bool(headline_explicit_gwh["illustrative"]),
                        "delivered_range": headline_explicit_gwh["range_label"],
                        "delivered_range_min": headline_explicit_gwh["range_min"],
                        "delivered_range_max": headline_explicit_gwh["range_max"],
                    },
                    "implicit": {
                        "delivered_gwh": headline_implicit_gwh["value"],
                        "delivered_gwh_illustrative": bool(headline_implicit_gwh["illustrative"]),
                        "delivered_range": headline_implicit_gwh["range_label"],
                        "delivered_range_min": headline_implicit_gwh["range_min"],
                        "delivered_range_max": headline_implicit_gwh["range_max"],
                    },
                },
                "utilisation": utilisation_obj,
                "directional_breakdown": {
                    "turn_up": {
                        "capacity_mw": headline_turn_up["value"],
                        "capacity_mw_illustrative": bool(headline_turn_up["illustrative"]),
                        "capacity_range": headline_turn_up["range_label"],
                        "capacity_range_min": headline_turn_up["range_min"],
                        "capacity_range_max": headline_turn_up["range_max"],
                    },
                    "turn_down": {
                        "capacity_mw": headline_turn_down["value"],
                        "capacity_mw_illustrative": bool(headline_turn_down["illustrative"]),
                        "capacity_range": headline_turn_down["range_label"],
                        "capacity_range_min": headline_turn_down["range_min"],
                        "capacity_range_max": headline_turn_down["range_max"],
                    },
                    "asymmetry_explanation": "Turn-down capacity is typically more widely available than turn-up, reflecting the prevalence of load reduction and load shifting compared to sustained load increases.",
                },
                "flexibility_type_breakdown": {
                    "explicit": {
                        "capacity_mw": metrics.total_available_mw,
                        "capacity_mw_illustrative": bool(metrics.total_available_mw_illustrative),
                        "capacity_range": metrics.total_available_range,
                        "capacity_range_min": metrics.total_available_range_min,
                        "capacity_range_max": metrics.total_available_range_max,
                    },
                    "implicit": {
                        "capacity_mw": headline_implicit_capacity["value"],
                        "capacity_mw_illustrative": bool(headline_implicit_capacity["illustrative"]),
                        "capacity_range": headline_implicit_capacity["range_label"],
                        "capacity_range_min": headline_implicit_capacity["range_min"],
                        "capacity_range_max": headline_implicit_capacity["range_max"],
                    },
                },
            }

            # Grouped asset breakdown (broader categories) to improve k and reduce disaggregation risk.
            try:
                extras["asset_group_breakdown"] = (
                    json.loads(asset_group_export.to_json(orient="records"))
                    if asset_group_export is not None and not asset_group_export.empty
                    else []
                )
            except Exception:
                extras["asset_group_breakdown"] = []

            # Sector x asset breakdown for sector-specific charts/tables.
            try:
                extras["sector_asset_breakdown"] = (
                    json.loads(sector_asset_df.to_json(orient="records"))
                    if sector_asset_df is not None and not sector_asset_df.empty
                    else []
                )
            except Exception:
                extras["sector_asset_breakdown"] = []

            # Sector x asset-group breakdown (preferred for domestic/I&C pages)
            try:
                extras["sector_asset_group_breakdown"] = (
                    json.loads(sector_asset_group_df.to_json(orient="records"))
                    if sector_asset_group_df is not None and not sector_asset_group_df.empty
                    else []
                )
            except Exception:
                extras["sector_asset_group_breakdown"] = []

            # Coverage cues: how many contributors actually supplied each metric.
            try:
                def _n_contrib(df: pd.DataFrame, value_col: str) -> int:
                    if df is None or df.empty or value_col not in df.columns or "contributor_id" not in df.columns:
                        return 0
                    s = pd.to_numeric(df[value_col], errors="coerce").fillna(0.0)
                    return int(df.loc[s > 0, "contributor_id"].nunique())

                # MW capacity (Part 3.2)
                cap_contrib = 0
                if not combined_df.empty and "capacity_mw" in combined_df.columns:
                    cap_contrib = int(
                        combined_df.loc[pd.to_numeric(combined_df["capacity_mw"], errors="coerce").fillna(0.0) > 0, "contributor_id"].nunique()
                    )

                # Delivered MW (Part 3.2 delivered up/down)
                deliv_contrib = 0
                if not combined_df.empty:
                    del_series = pd.concat(
                        [
                            pd.to_numeric(combined_df.get("delivered_turn_up_mw", pd.Series(index=combined_df.index)), errors="coerce"),
                            pd.to_numeric(combined_df.get("delivered_turn_down_mw", pd.Series(index=combined_df.index)), errors="coerce"),
                        ],
                        axis=1,
                    ).max(axis=1, skipna=True).fillna(0.0)
                    deliv_contrib = int(combined_df.loc[del_series > 0, "contributor_id"].nunique())

                # Portfolio counts (Part 2)
                count_contrib = 0
                if not combined_df.empty and "count" in combined_df.columns:
                    count_contrib = int(
                        combined_df.loc[pd.to_numeric(combined_df["count"], errors="coerce").fillna(0.0) > 0, "contributor_id"].nunique()
                    )

                extras["coverage"] = {
                    "contributors_total": int(contributor_count),
                    "k_threshold": int(k_threshold),
                    "capacity_mw_contributors": cap_contrib,
                    "delivered_mw_contributors": deliv_contrib,
                    "explicit_energy_contributors": _n_contrib(explicit_energy_df, "delivered_gwh"),
                    "implicit_energy_contributors": _n_contrib(tou_df, "delivered_gwh"),
                    "implicit_capacity_contributors": _n_contrib(tou_df, "capacity_mw"),
                    "portfolio_count_contributors": count_contrib,
                }
            except Exception:
                pass

            # External benchmark (Capacity Market, DY 2024/25) for sense-checking only.
            try:
                cfg, verification_yaml = load_verification_config(project_root)
                cm_bench_df = build_cm_benchmark(project_root, include_storage=False)

                # Map our asset groups to the benchmark taxonomy.
                group_to_benchmark = {
                    "Battery storage": "Battery",
                    "EV charging": "EV",
                    "Heat": "Heat",
                    "I&C load/process": "I&C load",
                    "Other": "I&C load",
                }

                contrib_rows = combined_df.copy() if combined_df is not None else pd.DataFrame()
                if not contrib_rows.empty:
                    if "asset_group" in contrib_rows.columns:
                        contrib_rows["bench_asset_class"] = (
                            contrib_rows["asset_group"].astype(str).map(group_to_benchmark).fillna("I&C load")
                        )
                    else:
                        contrib_rows["bench_asset_class"] = "I&C load"

                    contrib_pub = governed_aggregate(contrib_rows, ["bench_asset_class"])
                    contrib_pub = contrib_pub.rename(columns={"bench_asset_class": "asset_class"})

                    base = pd.DataFrame()
                    base["asset_class"] = contrib_pub.get("asset_class")
                    base["contributors_kw"] = pd.to_numeric(contrib_pub.get("capacity_mw"), errors="coerce").fillna(0.0) * 1000.0
                    base["contributors_k"] = pd.to_numeric(contrib_pub.get("k"), errors="coerce").fillna(0).astype(int)
                    base["contributors_illustrative"] = contrib_pub.get("capacity_mw_illustrative").fillna(False).astype(bool)
                    base["contributors_range"] = contrib_pub.get("capacity_range")
                    base["contributors_range_min_kw"] = pd.to_numeric(contrib_pub.get("capacity_range_min"), errors="coerce") * 1000.0
                    base["contributors_range_max_kw"] = pd.to_numeric(contrib_pub.get("capacity_range_max"), errors="coerce") * 1000.0
                else:
                    base = pd.DataFrame(columns=["asset_class", "contributors_kw", "contributors_k", "contributors_illustrative"])

                compare_df = build_verification_compare(project_root, base, include_storage=False)

                extras["benchmarks"] = {
                    "dy": cfg.dy,
                    "unit": cfg.unit,
                    "non_additivity_notice": (verification_yaml.get("copy", {}) or {}).get("non_additivity_notice"),
                    "methods_summary": (verification_yaml.get("copy", {}) or {}).get("methods_summary"),
                    "sources": verification_yaml.get("sources", []) or [],
                    "cm_benchmark_by_asset": json.loads(cm_bench_df.to_json(orient="records")) if cm_bench_df is not None and not cm_bench_df.empty else [],
                    "comparison": json.loads(compare_df.to_json(orient="records")) if compare_df is not None and not compare_df.empty else [],
                }
            except Exception as e:
                logger.warning(f"  CM benchmark export skipped: {e}")
        except Exception as e:
            logger.warning(f"  Could not compute Methodology v7 metrics (continuing without): {e}")

        logger.info(f"  Total available: {metrics.total_available_mw:,.0f} MW")
        logger.info(f"  Domestic: {metrics.domestic_available_mw:,.0f} MW")
        logger.info(f"  I&C: {metrics.ic_available_mw:,.0f} MW")
        logger.info(f"  Contributors: {metrics.contributor_count}")

        results['steps']['metrics'] = {
            'total_mw': metrics.total_available_mw,
            'contributors': metrics.contributor_count,
            'success': True
        }

        # Step 6: Generate narratives
        logger.info("=" * 60)
        logger.info("STEP 6: Generate Narratives")
        logger.info("=" * 60)

        narratives = metrics_calc.generate_narrative(metrics)
        logger.info("  Generated narrative texts")

        # Step 7: Export dashboard data
        logger.info("=" * 60)
        logger.info("STEP 7: Export Dashboard Data")
        logger.info("=" * 60)

        # Remove internal columns before export
        def clean_for_export(df):
            if df.empty:
                return df
            cols_to_drop = [c for c in df.columns if c.startswith('_')]
            return df.drop(columns=cols_to_drop, errors='ignore')

        sector_export = clean_for_export(sector_df)
        asset_export = clean_for_export(asset_df)

        output_files = exporter.export_all(
            metrics=metrics,
            sector_data=sector_export,
            asset_data=asset_export,
            service_data=None,
            narratives=narratives,
            data_quality=quality_report,
            extras=extras,
        )

        for name, path in output_files.items():
            logger.info(f"  Exported: {path.name}")
            audit_logger.log_export(
                output_type=name,
                filename=str(path),
                records_exported=1
            )

        # Public standalone dashboard (single-file) for file:// sharing/presentations.
        try:
            pub_out = generate_public_dashboard_standalone(project_root=project_root)
            logger.info(f"  Public dashboard (standalone): {pub_out.standalone_path}")
            results['steps']['public_standalone_dashboard'] = {
                'success': True,
                'standalone_path': str(pub_out.standalone_path),
            }
        except Exception as e:
            logger.warning(f"  Public standalone dashboard generation failed: {e}")
            results['steps']['public_standalone_dashboard'] = {
                'success': False,
                'error': str(e),
            }

        # Release-safe public dashboard (single-file; safe splits only; no ranges/k-signals).
        try:
            release_disclosure = DisclosureController(config.get('disclosure', {}))

            def _release_safe_capacity_table(
                df_slice: pd.DataFrame,
                group_col: str,
                label_map: dict[str, str] | None = None,
            ) -> tuple[list[dict], set[str]]:
                if df_slice is None or df_slice.empty:
                    return [], set()
                if group_col not in df_slice.columns or "contributor_id" not in df_slice.columns:
                    return [], set()
                if "capacity_mw" not in df_slice.columns:
                    return [], set()

                cap = pd.to_numeric(df_slice["capacity_mw"], errors="coerce")
                working = df_slice.loc[cap.notna() & (cap > 0)].copy()
                if working.empty:
                    return [], set()
                working["capacity_mw"] = pd.to_numeric(working["capacity_mw"], errors="coerce").astype(float)

                rows: list[dict] = []
                unsafe: set[str] = set()

                for key, g in working.groupby(group_col):
                    per = (
                        g.groupby("contributor_id")["capacity_mw"]
                        .sum()
                        .astype(float)
                    )
                    raw_total = float(per.sum())
                    contributor_ids = per.index.astype(str).tolist()
                    contributor_values = per.tolist()

                    decision = release_disclosure.check_cell(
                        value=raw_total,
                        contributor_ids=contributor_ids,
                        dimension="release",
                        dimension_value=str(key),
                        metric="capacity_mw",
                        contributor_values=contributor_values,
                    )

                    if decision.status != DisclosureStatus.SAFE:
                        unsafe.add(str(key))
                        continue

                    safe_val = float(decision.final_value) if decision.final_value is not None else raw_total
                    safe_val = round(safe_val / rounding) * rounding

                    label = str(key)
                    if label_map:
                        label = label_map.get(label, label)

                    rows.append({group_col: label, "capacity_mw": safe_val})

                return rows, unsafe

            # Sector split: only publish if both sectors are safe (no partial publication).
            sector_label_map = {
                "domestic": "Domestic",
                "ic": "Industrial & Commercial",
            }
            sector_rows, sector_unsafe = _release_safe_capacity_table(
                combined_df,
                group_col="sector",
                label_map=sector_label_map,
            )
            if sector_unsafe:
                sector_rows = []

            # Asset-group split: attempt to collapse unsafe groups into "Other" once.
            asset_rows, asset_unsafe = _release_safe_capacity_table(
                combined_df,
                group_col="asset_group",
            )
            if asset_unsafe:
                collapsed = combined_df.copy()
                if "asset_group" in collapsed.columns:
                    collapsed["asset_group_release"] = collapsed["asset_group"].astype(str).apply(
                        lambda g: "Other" if g in asset_unsafe else g
                    )
                    asset_rows2, asset_unsafe2 = _release_safe_capacity_table(
                        collapsed,
                        group_col="asset_group_release",
                    )
                    if not asset_unsafe2 and asset_rows2:
                        # Normalise output key name for the dashboard template.
                        asset_rows = [
                            {"asset_group": r["asset_group_release"], "capacity_mw": r["capacity_mw"]}
                            for r in asset_rows2
                        ]
                    else:
                        asset_rows = []
                else:
                    asset_rows = []

            # Require at least 2 buckets for a meaningful split.
            if len(sector_rows) < 2:
                sector_rows = []
            if len(asset_rows) < 2:
                asset_rows = []

            release_payload = {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "study_period": str(config.get("project", {}).get("study_period") or "Nov 2024-Feb 2025"),
                "headline": {
                    "total_available_mw": (metrics.total_available_mw if not metrics.total_available_mw_illustrative else None),
                    "contributor_count": int(metrics.contributor_count),
                },
                "sector_breakdown": sector_rows,
                "asset_group_breakdown": asset_rows,
            }

            rel_out = generate_public_dashboard_standalone_release_safe(
                project_root=project_root,
                payload=release_payload,
            )
            logger.info(f"  Public dashboard (release-safe): {rel_out.standalone_path}")
            results['steps']['public_standalone_dashboard_release_safe'] = {
                'success': True,
                'standalone_path': str(rel_out.standalone_path),
            }
        except Exception as e:
            logger.warning(f"  Release-safe dashboard generation failed: {e}")
            results['steps']['public_standalone_dashboard_release_safe'] = {
                'success': False,
                'error': str(e),
            }

        # Steering-safe public dashboard (single-file, aggregates only; no k signals/breakdowns).
        try:
            safe_out = generate_public_dashboard_standalone_steering_safe(project_root=project_root)
            logger.info(f"  Public dashboard (steering-safe): {safe_out.standalone_path}")
            results['steps']['public_standalone_dashboard_steering_safe'] = {
                'success': True,
                'standalone_path': str(safe_out.standalone_path),
            }
        except Exception as e:
            logger.warning(f"  Steering-safe dashboard generation failed: {e}")
            results['steps']['public_standalone_dashboard_steering_safe'] = {
                'success': False,
                'error': str(e),
            }

        results['steps']['export'] = {
            'files_exported': len(output_files),
            'output_directory': str(output_dir),
            'success': True
        }

        # Final summary
        results['status'] = 'completed'
        results['end_time'] = datetime.now().isoformat()

        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"  Files ingested: {len(parsed_data)}")
        logger.info(f"  Contributors: {metrics.contributor_count}")
        logger.info(f"  Total capacity: {metrics.total_available_mw:,.0f} MW")
        logger.info(f"  Dashboard data: {output_dir}")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        results['status'] = 'failed'
        results['error'] = str(e)
        raise

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run FlexDash data pipeline')
    parser.add_argument(
        '--config',
        type=Path,
        default=Path(__file__).parent.parent / 'config' / 'settings.yaml',
        help='Path to configuration file'
    )
    args = parser.parse_args()

    # Load configuration
    if args.config.exists():
        config = load_config(args.config)
    else:
        logger.warning(f"Config file not found: {args.config}, using defaults")
        config = {
            'source_data': '../02 DATA RECEIVED',
            'paths': {
                'dashboard_data': 'dashboard/data',
                'audit_logs': 'data/audit'
            },
            'disclosure': {'k_threshold': 3, 'rounding_precision': 10},
            'quality': {'minimum_completeness': 0.5},
            'project': {'study_period': 'Nov 2024–Feb 2025'}
        }

    # Run pipeline
    results = run_pipeline(config)

    # Exit with appropriate code
    sys.exit(0 if results['status'] == 'completed' else 1)


if __name__ == '__main__':
    main()
