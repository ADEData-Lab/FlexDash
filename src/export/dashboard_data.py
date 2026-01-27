"""
Dashboard Data Export Module for FlexDash.

Generates JSON data files for the interactive HTML dashboard.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ChartData:
    """Data structure for chart visualizations."""
    chart_type: str
    title: str
    labels: List[str]
    datasets: List[Dict[str, Any]]
    options: Dict[str, Any] = None


class DashboardExporter:
    """
    Exports processed data to JSON format for dashboard consumption.
    """

    # ADE brand colors
    COLORS = {
        'primary': '#2E86AB',      # Blue
        'secondary': '#A23B72',    # Magenta
        'tertiary': '#F18F01',     # Orange
        'success': '#4CAF50',      # Green
        'warning': '#FF9800',      # Amber
        'domestic': '#2E86AB',
        'ic': '#A23B72',
        'illustrative': '#FF9800'
    }

    def __init__(self, output_dir: Path):
        """
        Initialize exporter.

        Args:
            output_dir: Directory for output JSON files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        metrics: Any,
        sector_data: pd.DataFrame,
        asset_data: pd.DataFrame,
        service_data: pd.DataFrame = None,
        narratives: Dict[str, str] = None,
        data_quality: Dict = None
    ) -> Dict[str, Path]:
        """
        Export all dashboard data files.

        Args:
            metrics: DashboardMetrics object
            sector_data: Sector breakdown data
            asset_data: Asset class breakdown data
            service_data: Service type breakdown data
            narratives: Narrative text dictionary
            data_quality: Data quality scores

        Returns:
            Dictionary of output file paths
        """
        outputs = {}

        # Export main dashboard data
        outputs['main'] = self._export_main_data(metrics, narratives)

        # Export chart data
        outputs['sector_chart'] = self._export_sector_chart(sector_data)
        outputs['asset_chart'] = self._export_asset_chart(asset_data)

        if service_data is not None and not service_data.empty:
            outputs['service_chart'] = self._export_service_chart(service_data)

        # Export data quality info
        if data_quality:
            outputs['quality'] = self._export_quality_data(data_quality)

        # Export combined data file
        outputs['combined'] = self._export_combined(
            metrics, sector_data, asset_data, service_data, narratives, data_quality
        )

        logger.info(f"Exported {len(outputs)} data files to {self.output_dir}")
        return outputs

    def _export_main_data(
        self,
        metrics: Any,
        narratives: Dict[str, str] = None
    ) -> Path:
        """Export main dashboard metrics."""
        data = {
            'generated_at': datetime.now().isoformat(),
            'study_period': getattr(metrics, 'study_period', '2024-2025'),
            'metrics': {
                'headline': {
                    'total_available_mw': getattr(metrics, 'total_available_mw', 0),
                    'total_delivered_mw': getattr(metrics, 'total_delivered_mw', 0),
                    'delivery_factor_pct': getattr(metrics, 'delivery_factor_pct', 0),
                    'contributor_count': getattr(metrics, 'contributor_count', 0)
                },
                'domestic': {
                    'available_mw': getattr(metrics, 'domestic_available_mw', 0),
                    'delivered_mw': getattr(metrics, 'domestic_delivered_mw', 0),
                    'delivery_factor_pct': getattr(metrics, 'domestic_delivery_factor_pct', 0)
                },
                'ic': {
                    'available_mw': getattr(metrics, 'ic_available_mw', 0),
                    'delivered_mw': getattr(metrics, 'ic_delivered_mw', 0),
                    'delivery_factor_pct': getattr(metrics, 'ic_delivery_factor_pct', 0)
                }
            },
            'narratives': narratives or {}
        }

        output_path = self.output_dir / 'main_data.json'
        self._write_json(data, output_path)
        return output_path

    def _export_sector_chart(self, sector_data: pd.DataFrame) -> Path:
        """Export sector breakdown chart data."""
        if sector_data.empty:
            labels = ['Domestic', 'I&C']
            values = [0, 0]
        else:
            labels = sector_data['sector'].tolist() if 'sector' in sector_data.columns else []
            values = sector_data['capacity_mw'].tolist() if 'capacity_mw' in sector_data.columns else []

        # Check for illustrative flags
        illustrative_flags = []
        if 'capacity_mw_illustrative' in sector_data.columns:
            illustrative_flags = sector_data['capacity_mw_illustrative'].tolist()

        chart = {
            'type': 'doughnut',
            'title': 'Flexibility by Sector',
            'data': {
                'labels': [self._format_label(l) for l in labels],
                'datasets': [{
                    'data': values,
                    'backgroundColor': [self.COLORS['domestic'], self.COLORS['ic']],
                    'borderWidth': 2,
                    'borderColor': '#ffffff'
                }]
            },
            'options': {
                'responsive': True,
                'plugins': {
                    'legend': {'position': 'bottom'},
                    'title': {'display': True, 'text': 'Sector Split (MW)'}
                }
            },
            'illustrative_flags': illustrative_flags
        }

        output_path = self.output_dir / 'sector_chart.json'
        self._write_json(chart, output_path)
        return output_path

    def _export_asset_chart(self, asset_data: pd.DataFrame) -> Path:
        """Export asset class breakdown chart data."""
        if asset_data.empty:
            labels = []
            values = []
            illustrative_flags = []
        else:
            labels = asset_data['asset_class'].tolist() if 'asset_class' in asset_data.columns else []
            values = asset_data['capacity_mw'].tolist() if 'capacity_mw' in asset_data.columns else []
            illustrative_flags = asset_data['capacity_mw_illustrative'].tolist() if 'capacity_mw_illustrative' in asset_data.columns else []

        # Generate colors for each asset class
        colors = self._generate_color_palette(len(labels))

        chart = {
            'type': 'bar',
            'title': 'Flexibility by Asset Class',
            'data': {
                'labels': [self._format_label(l) for l in labels],
                'datasets': [{
                    'label': 'Capacity (MW)',
                    'data': values,
                    'backgroundColor': colors,
                    'borderWidth': 1
                }]
            },
            'options': {
                'indexAxis': 'y',
                'responsive': True,
                'plugins': {
                    'legend': {'display': False},
                    'title': {'display': True, 'text': 'Asset Class Breakdown (MW)'}
                },
                'scales': {
                    'x': {'beginAtZero': True}
                }
            },
            'illustrative_flags': illustrative_flags
        }

        output_path = self.output_dir / 'asset_chart.json'
        self._write_json(chart, output_path)
        return output_path

    def _export_service_chart(self, service_data: pd.DataFrame) -> Path:
        """Export service type breakdown chart data."""
        if service_data.empty:
            labels = []
            values = []
        else:
            labels = service_data['service_type'].tolist() if 'service_type' in service_data.columns else []
            values = service_data['capacity_mw'].tolist() if 'capacity_mw' in service_data.columns else []

        colors = self._generate_color_palette(len(labels))

        chart = {
            'type': 'bar',
            'title': 'Flexibility by Service Type',
            'data': {
                'labels': [self._format_label(l) for l in labels],
                'datasets': [{
                    'label': 'Registered Capacity (MW)',
                    'data': values,
                    'backgroundColor': colors
                }]
            },
            'options': {
                'responsive': True,
                'plugins': {
                    'legend': {'display': False},
                    'title': {'display': True, 'text': 'Service Type Breakdown (MW)'}
                }
            }
        }

        output_path = self.output_dir / 'service_chart.json'
        self._write_json(chart, output_path)
        return output_path

    def _export_quality_data(self, quality: Dict) -> Path:
        """Export data quality information."""
        data = {
            'generated_at': datetime.now().isoformat(),
            'quality_metrics': quality,
            'thresholds': {
                'k_anonymity': 3,
                'minimum_completeness': 0.5
            }
        }

        output_path = self.output_dir / 'quality_data.json'
        self._write_json(data, output_path)
        return output_path

    def _export_combined(
        self,
        metrics: Any,
        sector_data: pd.DataFrame,
        asset_data: pd.DataFrame,
        service_data: pd.DataFrame,
        narratives: Dict,
        quality: Dict
    ) -> Path:
        """Export combined data file for dashboard."""
        # Convert DataFrames to JSON-serializable format
        def df_to_records(df):
            if df is None or df.empty:
                return []
            return json.loads(df.to_json(orient='records'))

        combined = {
            'generated_at': datetime.now().isoformat(),
            'version': '1.0.0',
            'study_period': getattr(metrics, 'study_period', '2024-2025'),
            'metrics': {
                'total_available_mw': getattr(metrics, 'total_available_mw', 0),
                'total_delivered_mw': getattr(metrics, 'total_delivered_mw', 0),
                'delivery_factor_pct': getattr(metrics, 'delivery_factor_pct', 0),
                'contributor_count': getattr(metrics, 'contributor_count', 0),
                'domestic': {
                    'available_mw': getattr(metrics, 'domestic_available_mw', 0),
                    'delivered_mw': getattr(metrics, 'domestic_delivered_mw', 0),
                },
                'ic': {
                    'available_mw': getattr(metrics, 'ic_available_mw', 0),
                    'delivered_mw': getattr(metrics, 'ic_delivered_mw', 0),
                }
            },
            'sector_breakdown': df_to_records(sector_data),
            'asset_breakdown': df_to_records(asset_data),
            'service_breakdown': df_to_records(service_data),
            'narratives': narratives or {},
            'data_quality': quality or {},
            'colors': self.COLORS
        }

        output_path = self.output_dir / 'dashboard_data.json'
        self._write_json(combined, output_path)
        return output_path

    def _write_json(self, data: Dict, path: Path):
        """Write data to JSON file."""
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        logger.debug(f"Wrote {path}")

    def _format_label(self, label: str) -> str:
        """Format label for display."""
        if not label:
            return 'Unknown'
        return str(label).replace('_', ' ').title()

    def _generate_color_palette(self, n: int) -> List[str]:
        """Generate n colors for charts."""
        base_colors = [
            '#2E86AB', '#A23B72', '#F18F01', '#4CAF50',
            '#9C27B0', '#00BCD4', '#FF5722', '#607D8B'
        ]

        if n <= len(base_colors):
            return base_colors[:n]

        # Generate additional colors if needed
        colors = base_colors.copy()
        while len(colors) < n:
            colors.extend(base_colors)
        return colors[:n]
