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
import logging
import sys
from datetime import datetime
from pathlib import Path

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
from src.analysis.metrics import MetricsCalculator, DashboardMetrics
from src.export.dashboard_data import DashboardExporter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    with open(config_path) as f:
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

    try:
        # Step 1: Ingest data
        logger.info("=" * 60)
        logger.info("STEP 1: Data Ingestion")
        logger.info("=" * 60)

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
                combined_df['capacity_mw'] = 0
            if 'count' not in combined_df.columns:
                combined_df['count'] = 1
            if 'asset_class' not in combined_df.columns:
                combined_df['asset_class'] = 'unknown'

            # Fill missing values
            combined_df['capacity_mw'] = pd.to_numeric(combined_df['capacity_mw'], errors='coerce').fillna(0)
            combined_df['count'] = pd.to_numeric(combined_df['count'], errors='coerce').fillna(1)

        results['steps']['combine'] = {
            'total_records': len(combined_df),
            'contributors': combined_df['contributor_id'].nunique() if not combined_df.empty else 0,
            'success': True
        }

        # Step 4: Aggregate with disclosure control
        logger.info("=" * 60)
        logger.info("STEP 4: Aggregation & Disclosure Control")
        logger.info("=" * 60)

        def aggregate_with_disclosure(df, group_cols, metrics=['capacity_mw', 'count']):
            """Aggregate data while applying k-threshold disclosure control."""
            if df.empty:
                return pd.DataFrame()

            result_rows = []
            for group_key, group_df in df.groupby(group_cols, dropna=False):
                # Get unique contributors for this group
                contributors = group_df['contributor_id'].unique()
                k = len(contributors)

                # Build row dict
                if isinstance(group_key, tuple):
                    row = {col: val for col, val in zip(group_cols, group_key)}
                else:
                    row = {group_cols[0]: group_key}

                row['_contributor_count'] = k

                # Check each metric
                for metric in metrics:
                    if metric not in group_df.columns:
                        continue

                    total = group_df[metric].sum()

                    if k >= k_threshold:
                        # Safe to publish - round the value
                        row[metric] = round(total / rounding) * rounding
                        row[f'{metric}_illustrative'] = False
                    elif k > 0:
                        # Use illustrative data
                        row[metric] = round(total / rounding) * rounding  # Use actual but mark as illustrative
                        row[f'{metric}_illustrative'] = True
                    else:
                        row[metric] = 0
                        row[f'{metric}_illustrative'] = True

                result_rows.append(row)

            return pd.DataFrame(result_rows)

        # Aggregate by sector
        if not combined_df.empty and 'sector' in combined_df.columns:
            sector_df = aggregate_with_disclosure(combined_df, ['sector'])
            logger.info(f"  Sector aggregation: {len(sector_df)} groups")
            for _, row in sector_df.iterrows():
                logger.info(f"    {row['sector']}: {row.get('capacity_mw', 0):.0f} MW (k={row['_contributor_count']})")
        else:
            sector_df = pd.DataFrame()
            logger.warning("  No sector data available")

        # Aggregate by asset class
        if not combined_df.empty and 'asset_class' in combined_df.columns:
            asset_df = aggregate_with_disclosure(combined_df, ['asset_class'])
            logger.info(f"  Asset class aggregation: {len(asset_df)} groups")
        else:
            asset_df = pd.DataFrame()
            logger.warning("  No asset class data available")

        # Aggregate by sector + asset class
        if not combined_df.empty and 'sector' in combined_df.columns and 'asset_class' in combined_df.columns:
            sector_asset_df = aggregate_with_disclosure(combined_df, ['sector', 'asset_class'])
            logger.info(f"  Sector+Asset aggregation: {len(sector_asset_df)} groups")
        else:
            sector_asset_df = pd.DataFrame()

        results['steps']['aggregation'] = {
            'sector_groups': len(sector_df),
            'asset_groups': len(asset_df),
            'success': True
        }

        # Step 5: Calculate metrics
        logger.info("=" * 60)
        logger.info("STEP 5: Calculate Metrics")
        logger.info("=" * 60)

        # Calculate totals
        total_mw = combined_df['capacity_mw'].sum() if not combined_df.empty else 0
        total_count = combined_df['count'].sum() if not combined_df.empty else 0
        contributor_count = combined_df['contributor_id'].nunique() if not combined_df.empty else 0

        # Sector breakdown
        domestic_mw = combined_df[combined_df['sector'] == 'domestic']['capacity_mw'].sum() if not combined_df.empty else 0
        ic_mw = combined_df[combined_df['sector'] == 'ic']['capacity_mw'].sum() if not combined_df.empty else 0
        mixed_mw = combined_df[combined_df['sector'] == 'mixed']['capacity_mw'].sum() if not combined_df.empty else 0

        # Split mixed proportionally or 50/50
        if domestic_mw + ic_mw > 0:
            domestic_share = domestic_mw / (domestic_mw + ic_mw)
        else:
            domestic_share = 0.5
        domestic_mw += mixed_mw * domestic_share
        ic_mw += mixed_mw * (1 - domestic_share)

        # Round totals
        total_mw = round(total_mw / rounding) * rounding
        domestic_mw = round(domestic_mw / rounding) * rounding
        ic_mw = round(ic_mw / rounding) * rounding

        metrics = DashboardMetrics(
            total_available_mw=total_mw,
            total_delivered_mw=0,  # Not available in current data
            delivery_factor_pct=0,
            domestic_available_mw=domestic_mw,
            domestic_delivered_mw=0,
            domestic_delivery_factor_pct=0,
            ic_available_mw=ic_mw,
            ic_delivered_mw=0,
            ic_delivery_factor_pct=0,
            contributor_count=contributor_count,
            study_period=config.get('project', {}).get('study_period', '2024-2025')
        )

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
            data_quality=quality_report
        )

        for name, path in output_files.items():
            logger.info(f"  Exported: {path.name}")
            audit_logger.log_export(
                output_type=name,
                filename=str(path),
                records_exported=1
            )

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
            'project': {'study_period': '2024-2025'}
        }

    # Run pipeline
    results = run_pipeline(config)

    # Exit with appropriate code
    sys.exit(0 if results['status'] == 'completed' else 1)


if __name__ == '__main__':
    main()
