"""
Metrics Calculation Module for FlexDash.

Calculates derived metrics for the flexibility dashboard
including delivery factors, utilization rates, and comparisons.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DashboardMetrics:
    """Container for dashboard headline metrics."""
    total_available_mw: float
    total_delivered_mw: float
    delivery_factor_pct: float

    domestic_available_mw: float
    domestic_delivered_mw: float
    domestic_delivery_factor_pct: float

    ic_available_mw: float
    ic_delivered_mw: float
    ic_delivery_factor_pct: float

    contributor_count: int
    study_period: str

    # Optional disclosure-safe range metadata (used when published values are illustrative)
    total_available_mw_illustrative: bool = False
    total_available_range: Optional[str] = None
    total_available_range_min: Optional[float] = None
    total_available_range_max: Optional[float] = None

    domestic_available_mw_illustrative: bool = False
    domestic_available_range: Optional[str] = None
    domestic_available_range_min: Optional[float] = None
    domestic_available_range_max: Optional[float] = None

    ic_available_mw_illustrative: bool = False
    ic_available_range: Optional[str] = None
    ic_available_range_min: Optional[float] = None
    ic_available_range_max: Optional[float] = None

    # Optional disclosure-safe delivered metadata (used when published values are illustrative)
    total_delivered_mw_illustrative: bool = False
    total_delivered_range: Optional[str] = None
    total_delivered_range_min: Optional[float] = None
    total_delivered_range_max: Optional[float] = None


class MetricsCalculator:
    """
    Calculates derived metrics for the flexibility dashboard.
    """

    # Policy targets for comparison
    POLICY_TARGETS = {
        '2030_domestic_flexibility_gw': 10.0,  # Hypothetical target
        '2030_ic_flexibility_gw': 5.0,
    }

    def __init__(self, config: Dict = None):
        """
        Initialize metrics calculator.

        Args:
            config: Configuration settings
        """
        self.config = config or {}
        self.study_period = (
            self.config.get('project', {}).get('study_period')
            or self.config.get('study_period')
            or 'Nov 2024–Feb 2025'
        )

    def calculate_headline_metrics(
        self,
        aggregated_data: pd.DataFrame,
        sector_col: str = 'sector'
    ) -> DashboardMetrics:
        """
        Calculate headline metrics for dashboard.

        Args:
            aggregated_data: Aggregated dataframe
            sector_col: Column containing sector information

        Returns:
            DashboardMetrics object
        """
        if aggregated_data.empty:
            return self._empty_metrics()

        # Total calculations
        total_available = aggregated_data['capacity_mw'].sum() if 'capacity_mw' in aggregated_data.columns else 0
        total_delivered = aggregated_data.get('delivered_mw', aggregated_data.get('energy_mwh', pd.Series([0]))).sum()

        # Sector breakdown
        domestic = aggregated_data[aggregated_data[sector_col] == 'domestic'] if sector_col in aggregated_data.columns else pd.DataFrame()
        ic = aggregated_data[aggregated_data[sector_col] == 'ic'] if sector_col in aggregated_data.columns else pd.DataFrame()

        domestic_available = domestic['capacity_mw'].sum() if not domestic.empty and 'capacity_mw' in domestic.columns else 0
        domestic_delivered = domestic.get('delivered_mw', domestic.get('energy_mwh', pd.Series([0]))).sum() if not domestic.empty else 0

        ic_available = ic['capacity_mw'].sum() if not ic.empty and 'capacity_mw' in ic.columns else 0
        ic_delivered = ic.get('delivered_mw', ic.get('energy_mwh', pd.Series([0]))).sum() if not ic.empty else 0

        # Contributor count
        contributor_count = aggregated_data['contributor_id'].nunique() if 'contributor_id' in aggregated_data.columns else 0

        return DashboardMetrics(
            total_available_mw=total_available,
            total_delivered_mw=total_delivered,
            delivery_factor_pct=self._calculate_delivery_factor(total_available, total_delivered),

            domestic_available_mw=domestic_available,
            domestic_delivered_mw=domestic_delivered,
            domestic_delivery_factor_pct=self._calculate_delivery_factor(domestic_available, domestic_delivered),

            ic_available_mw=ic_available,
            ic_delivered_mw=ic_delivered,
            ic_delivery_factor_pct=self._calculate_delivery_factor(ic_available, ic_delivered),

            contributor_count=contributor_count,
            study_period=self.study_period
        )

    def _calculate_delivery_factor(self, available: float, delivered: float) -> float:
        """Calculate delivery factor as percentage."""
        if available == 0:
            return 0.0
        return min((delivered / available) * 100, 100.0)

    def _empty_metrics(self) -> DashboardMetrics:
        """Return empty metrics object."""
        return DashboardMetrics(
            total_available_mw=0,
            total_delivered_mw=0,
            delivery_factor_pct=0,
            domestic_available_mw=0,
            domestic_delivered_mw=0,
            domestic_delivery_factor_pct=0,
            ic_available_mw=0,
            ic_delivered_mw=0,
            ic_delivery_factor_pct=0,
            contributor_count=0,
            study_period=self.study_period
        )

    def calculate_asset_breakdown(
        self,
        aggregated_data: pd.DataFrame,
        asset_col: str = 'asset_class'
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate metrics breakdown by asset class.

        Args:
            aggregated_data: Aggregated dataframe
            asset_col: Column containing asset class

        Returns:
            Dictionary of asset class -> metrics
        """
        if aggregated_data.empty or asset_col not in aggregated_data.columns:
            return {}

        breakdown = {}

        for asset_class in aggregated_data[asset_col].unique():
            asset_data = aggregated_data[aggregated_data[asset_col] == asset_class]

            breakdown[str(asset_class)] = {
                'capacity_mw': asset_data['capacity_mw'].sum() if 'capacity_mw' in asset_data.columns else 0,
                'count': asset_data['count'].sum() if 'count' in asset_data.columns else 0,
                'share_pct': 0  # Will be calculated after all assets processed
            }

        # Calculate shares
        total_capacity = sum(v['capacity_mw'] for v in breakdown.values())
        if total_capacity > 0:
            for asset_class in breakdown:
                breakdown[asset_class]['share_pct'] = (breakdown[asset_class]['capacity_mw'] / total_capacity) * 100

        return breakdown

    def calculate_service_breakdown(
        self,
        aggregated_data: pd.DataFrame,
        service_col: str = 'service_type'
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate metrics breakdown by service type.

        Args:
            aggregated_data: Aggregated dataframe
            service_col: Column containing service type

        Returns:
            Dictionary of service type -> metrics
        """
        if aggregated_data.empty or service_col not in aggregated_data.columns:
            return {}

        breakdown = {}

        for service_type in aggregated_data[service_col].unique():
            service_data = aggregated_data[aggregated_data[service_col] == service_type]

            breakdown[str(service_type)] = {
                'capacity_mw': service_data['capacity_mw'].sum() if 'capacity_mw' in service_data.columns else 0,
                'energy_mwh': service_data['energy_mwh'].sum() if 'energy_mwh' in service_data.columns else 0,
            }

        return breakdown

    def calculate_policy_comparison(
        self,
        metrics: DashboardMetrics
    ) -> Dict[str, Dict[str, float]]:
        """
        Compare current metrics against policy targets.

        Args:
            metrics: Dashboard metrics

        Returns:
            Dictionary of comparisons
        """
        comparisons = {}

        # Domestic comparison
        domestic_target_mw = self.POLICY_TARGETS['2030_domestic_flexibility_gw'] * 1000
        comparisons['domestic'] = {
            'current_mw': metrics.domestic_available_mw,
            'target_mw': domestic_target_mw,
            'progress_pct': (metrics.domestic_available_mw / domestic_target_mw) * 100 if domestic_target_mw > 0 else 0,
            'gap_mw': domestic_target_mw - metrics.domestic_available_mw
        }

        # I&C comparison
        ic_target_mw = self.POLICY_TARGETS['2030_ic_flexibility_gw'] * 1000
        comparisons['ic'] = {
            'current_mw': metrics.ic_available_mw,
            'target_mw': ic_target_mw,
            'progress_pct': (metrics.ic_available_mw / ic_target_mw) * 100 if ic_target_mw > 0 else 0,
            'gap_mw': ic_target_mw - metrics.ic_available_mw
        }

        return comparisons

    def generate_narrative(self, metrics: DashboardMetrics) -> Dict[str, str]:
        """
        Generate narrative text summaries for dashboard.

        Args:
            metrics: Dashboard metrics

        Returns:
            Dictionary of narrative texts
        """
        narratives = {}

        # Headline narrative
        narratives['headline'] = (
            f"This dashboard presents flexibility data from {metrics.contributor_count} "
            f"contributing organisations for the study period {metrics.study_period}. "
            f"Total available flexibility capacity is {metrics.total_available_mw:,.0f} MW."
        )

        # Sector narrative
        if metrics.domestic_available_mw > 0 and metrics.ic_available_mw > 0:
            domestic_share = (metrics.domestic_available_mw / metrics.total_available_mw) * 100
            narratives['sector'] = (
                f"Domestic flexibility accounts for {domestic_share:.0f}% of total capacity "
                f"({metrics.domestic_available_mw:,.0f} MW), with I&C contributing "
                f"{100-domestic_share:.0f}% ({metrics.ic_available_mw:,.0f} MW)."
            )
        else:
            narratives['sector'] = "Sector breakdown data is limited in this release."

        # Delivery narrative
        if metrics.delivery_factor_pct > 0:
            narratives['delivery'] = (
                f"The overall delivery factor is {metrics.delivery_factor_pct:.1f}%, "
                f"representing flexibility that was actually dispatched relative to "
                f"available capacity."
            )
        else:
            narratives['delivery'] = "Delivery factor data is not yet available."

        # Data coverage narrative
        narratives['coverage'] = (
            f"Data for this dashboard was provided by {metrics.contributor_count} "
            f"organisations. Where fewer than 3 contributors exist for a metric, "
            f"illustrative values are shown to protect commercial confidentiality."
        )

        return narratives

    def to_dict(self, metrics: DashboardMetrics) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON export."""
        return {
            'headline': {
                'total_available_mw': metrics.total_available_mw,
                'total_delivered_mw': metrics.total_delivered_mw,
                'delivery_factor_pct': metrics.delivery_factor_pct,
                'contributor_count': metrics.contributor_count,
                'study_period': metrics.study_period
            },
            'domestic': {
                'available_mw': metrics.domestic_available_mw,
                'delivered_mw': metrics.domestic_delivered_mw,
                'delivery_factor_pct': metrics.domestic_delivery_factor_pct
            },
            'ic': {
                'available_mw': metrics.ic_available_mw,
                'delivered_mw': metrics.ic_delivered_mw,
                'delivery_factor_pct': metrics.ic_delivery_factor_pct
            }
        }
