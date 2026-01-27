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

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.template_parser import TemplateParser, parse_all_files
from src.ingestion.validators import DataValidator
from src.governance.disclosure import DisclosureController
from src.governance.anonymiser import Anonymiser
from src.governance.audit import AuditLogger
from src.analysis.aggregator import DataAggregator
from src.analysis.metrics import MetricsCalculator
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

    audit_logger = AuditLogger(audit_path)
    validator = DataValidator(config.get('quality', {}))
    disclosure = DisclosureController(config.get('disclosure', {}))
    anonymiser = Anonymiser(config.get('anonymisation', {}))
    aggregator = DataAggregator()
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
            logger.info(f"  Parsed: {data.contributor_name} ({len(data.assets)} assets)")

        # Step 2: Validate data
        logger.info("=" * 60)
        logger.info("STEP 2: Data Validation")
        logger.info("=" * 60)

        validation_results = []
        for data in parsed_data:
            result = validator.validate(data)
            validation_results.append(result)
            status = "PASS" if result.is_valid else "FAIL"
            logger.info(f"  {data.contributor_name}: {status} (completeness: {result.completeness_score:.1%})")

        quality_report = validator.generate_quality_report(validation_results)
        results['steps']['validation'] = {
            'valid_submissions': quality_report['valid_submissions'],
            'average_completeness': quality_report['average_completeness'],
            'success': True
        }

        # Step 3: Combine and aggregate data
        logger.info("=" * 60)
        logger.info("STEP 3: Data Aggregation")
        logger.info("=" * 60)

        combined_df = aggregator.combine_datasets(parsed_data)
        logger.info(f"  Combined {len(parsed_data)} datasets: {len(combined_df)} total records")

        # Aggregate by sector
        sector_result = aggregator.aggregate_by_dimension(combined_df, 'sector', ['capacity_mw', 'count'])
        logger.info(f"  Sector aggregation: {len(sector_result.data)} groups")

        # Aggregate by asset class
        asset_result = aggregator.aggregate_by_dimension(combined_df, 'asset_class', ['capacity_mw', 'count'])
        logger.info(f"  Asset class aggregation: {len(asset_result.data)} groups")

        results['steps']['aggregation'] = {
            'total_records': len(combined_df),
            'sector_groups': len(sector_result.data),
            'asset_groups': len(asset_result.data),
            'success': True
        }

        # Step 4: Apply disclosure controls
        logger.info("=" * 60)
        logger.info("STEP 4: Disclosure Control")
        logger.info("=" * 60)

        sector_safe, sector_report = disclosure.apply_disclosure_control(
            sector_result.data,
            contributor_col='contributor_id',
            dimension_cols=['sector'],
            metric_cols=['capacity_mw', 'count']
        )
        logger.info(f"  Sector: {sector_report.safe_cells}/{sector_report.total_cells} cells safe")

        asset_safe, asset_report = disclosure.apply_disclosure_control(
            asset_result.data,
            contributor_col='contributor_id',
            dimension_cols=['asset_class'],
            metric_cols=['capacity_mw', 'count']
        )
        logger.info(f"  Asset class: {asset_report.safe_cells}/{asset_report.total_cells} cells safe")

        audit_logger.log_disclosure_check(
            dimension='all',
            cell_count=sector_report.total_cells + asset_report.total_cells,
            safe_count=sector_report.safe_cells + asset_report.safe_cells,
            suppressed_count=sector_report.suppressed_cells + asset_report.suppressed_cells,
            illustrative_count=sector_report.illustrative_cells + asset_report.illustrative_cells
        )

        results['steps']['disclosure'] = {
            'total_cells': sector_report.total_cells + asset_report.total_cells,
            'safe_cells': sector_report.safe_cells + asset_report.safe_cells,
            'illustrative_cells': sector_report.illustrative_cells + asset_report.illustrative_cells,
            'success': True
        }

        # Step 5: Anonymise and fill illustrative data
        logger.info("=" * 60)
        logger.info("STEP 5: Anonymisation")
        logger.info("=" * 60)

        sector_anon = anonymiser.fill_illustrative_data(
            sector_safe, ['capacity_mw', 'count'], reference_df=combined_df
        )
        sector_anon = anonymiser.remove_identifying_columns(sector_anon)
        sector_final = anonymiser.prepare_for_publication(sector_anon, ['capacity_mw', 'count'])

        asset_anon = anonymiser.fill_illustrative_data(
            asset_safe, ['capacity_mw', 'count'], reference_df=combined_df
        )
        asset_anon = anonymiser.remove_identifying_columns(asset_anon)
        asset_final = anonymiser.prepare_for_publication(asset_anon, ['capacity_mw', 'count'])

        audit_logger.log_anonymisation(
            contributors_anonymised=anonymiser.get_pseudonym_count(),
            columns_removed=['contributor_id'],
            illustrative_values_generated=sector_report.illustrative_cells + asset_report.illustrative_cells
        )

        logger.info(f"  Anonymised {anonymiser.get_pseudonym_count()} contributors")

        results['steps']['anonymisation'] = {
            'contributors_anonymised': anonymiser.get_pseudonym_count(),
            'success': True
        }

        # Step 6: Calculate metrics
        logger.info("=" * 60)
        logger.info("STEP 6: Metrics Calculation")
        logger.info("=" * 60)

        metrics = metrics_calc.calculate_headline_metrics(combined_df)
        narratives = metrics_calc.generate_narrative(metrics)

        logger.info(f"  Total available: {metrics.total_available_mw:,.0f} MW")
        logger.info(f"  Domestic: {metrics.domestic_available_mw:,.0f} MW")
        logger.info(f"  I&C: {metrics.ic_available_mw:,.0f} MW")

        results['steps']['metrics'] = {
            'total_available_mw': metrics.total_available_mw,
            'contributor_count': metrics.contributor_count,
            'success': True
        }

        # Step 7: Export dashboard data
        logger.info("=" * 60)
        logger.info("STEP 7: Dashboard Export")
        logger.info("=" * 60)

        output_files = exporter.export_all(
            metrics=metrics,
            sector_data=sector_final,
            asset_data=asset_final,
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
            'quality': {'minimum_completeness': 0.5}
        }

    # Run pipeline
    results = run_pipeline(config)

    # Exit with appropriate code
    sys.exit(0 if results['status'] == 'completed' else 1)


if __name__ == '__main__':
    main()
