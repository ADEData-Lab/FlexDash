"""
Data Aggregation Module for FlexDash.

Aggregates parsed data by various dimensions while preserving
contributor information for disclosure control.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AggregationResult:
    """Container for aggregation results."""
    data: pd.DataFrame
    contributor_counts: Dict[str, int]
    dimensions_used: List[str]
    metrics_aggregated: List[str]


class DataAggregator:
    """
    Aggregates flexibility data by various dimensions.

    Maintains contributor tracking for downstream disclosure control.
    """

    # Standard aggregation dimensions
    DIMENSIONS = {
        'sector': 'Domestic vs I&C',
        'asset_class': 'Type of flexible asset',
        'service_type': 'Flexibility service',
        'region': 'Geographic region (DNO/DSO)',
        'time_period': 'Temporal aggregation'
    }

    # Standard metrics to aggregate
    METRICS = {
        'capacity_mw': 'sum',
        'energy_mwh': 'sum',
        'count': 'sum',
        'availability_hours': 'mean',
        'delivery_factor': 'mean'
    }

    def __init__(self):
        """Initialize aggregator."""
        self.contributor_map = {}

    def combine_datasets(
        self,
        datasets: List,
        contributor_col: str = 'contributor_id'
    ) -> pd.DataFrame:
        """
        Combine multiple parsed datasets into a single dataframe.

        Args:
            datasets: List of ParsedData objects
            contributor_col: Column name for contributor tracking

        Returns:
            Combined dataframe with contributor tracking
        """
        all_assets = []

        for data in datasets:
            if not data.assets.empty:
                df = data.assets.copy()
                df[contributor_col] = data.contributor_id
                df['sector'] = data.sector
                all_assets.append(df)

        if not all_assets:
            logger.warning("No asset data to combine")
            return pd.DataFrame()

        combined = pd.concat(all_assets, ignore_index=True)
        logger.info(f"Combined {len(datasets)} datasets: {len(combined)} total records")

        return combined

    def aggregate_by_dimension(
        self,
        df: pd.DataFrame,
        dimension: str,
        metrics: List[str] = None,
        contributor_col: str = 'contributor_id'
    ) -> AggregationResult:
        """
        Aggregate data by a single dimension.

        Args:
            df: Input dataframe
            dimension: Dimension to aggregate by
            metrics: Metrics to aggregate (default: all standard metrics)
            contributor_col: Column containing contributor IDs

        Returns:
            AggregationResult with aggregated data and contributor counts
        """
        if df.empty:
            return AggregationResult(
                data=pd.DataFrame(),
                contributor_counts={},
                dimensions_used=[dimension],
                metrics_aggregated=[]
            )

        if dimension not in df.columns:
            logger.warning(f"Dimension '{dimension}' not found in data")
            return AggregationResult(
                data=pd.DataFrame(),
                contributor_counts={},
                dimensions_used=[dimension],
                metrics_aggregated=[]
            )

        # Determine which metrics to aggregate
        if metrics is None:
            metrics = [m for m in self.METRICS.keys() if m in df.columns]

        # Build aggregation dictionary
        agg_dict = {contributor_col: list}  # Keep contributor list for disclosure
        for metric in metrics:
            if metric in df.columns:
                agg_dict[metric] = self.METRICS.get(metric, 'sum')

        # Perform aggregation
        grouped = df.groupby(dimension).agg(agg_dict).reset_index()

        # Calculate contributor counts
        contributor_counts = {}
        for _, row in grouped.iterrows():
            dim_value = row[dimension]
            contributors = row[contributor_col] if isinstance(row[contributor_col], list) else [row[contributor_col]]
            contributor_counts[str(dim_value)] = len(set(contributors))

        logger.info(
            f"Aggregated by {dimension}: {len(grouped)} groups, "
            f"contributor range: {min(contributor_counts.values())}-{max(contributor_counts.values())}"
        )

        return AggregationResult(
            data=grouped,
            contributor_counts=contributor_counts,
            dimensions_used=[dimension],
            metrics_aggregated=metrics
        )

    def aggregate_by_multiple_dimensions(
        self,
        df: pd.DataFrame,
        dimensions: List[str],
        metrics: List[str] = None,
        contributor_col: str = 'contributor_id'
    ) -> AggregationResult:
        """
        Aggregate data by multiple dimensions (cross-tabulation).

        Args:
            df: Input dataframe
            dimensions: List of dimensions to aggregate by
            metrics: Metrics to aggregate
            contributor_col: Column containing contributor IDs

        Returns:
            AggregationResult with aggregated data
        """
        if df.empty:
            return AggregationResult(
                data=pd.DataFrame(),
                contributor_counts={},
                dimensions_used=dimensions,
                metrics_aggregated=[]
            )

        # Filter to valid dimensions
        valid_dims = [d for d in dimensions if d in df.columns]
        if not valid_dims:
            logger.warning(f"No valid dimensions found in data")
            return AggregationResult(
                data=pd.DataFrame(),
                contributor_counts={},
                dimensions_used=dimensions,
                metrics_aggregated=[]
            )

        if metrics is None:
            metrics = [m for m in self.METRICS.keys() if m in df.columns]

        # Build aggregation dictionary
        agg_dict = {contributor_col: list}
        for metric in metrics:
            if metric in df.columns:
                agg_dict[metric] = self.METRICS.get(metric, 'sum')

        # Perform aggregation
        grouped = df.groupby(valid_dims).agg(agg_dict).reset_index()

        # Calculate contributor counts per cell
        contributor_counts = {}
        for _, row in grouped.iterrows():
            key = '|'.join(str(row[d]) for d in valid_dims)
            contributors = row[contributor_col] if isinstance(row[contributor_col], list) else [row[contributor_col]]
            contributor_counts[key] = len(set(contributors))

        logger.info(
            f"Aggregated by {valid_dims}: {len(grouped)} cells, "
            f"contributor range: {min(contributor_counts.values())}-{max(contributor_counts.values())}"
        )

        return AggregationResult(
            data=grouped,
            contributor_counts=contributor_counts,
            dimensions_used=valid_dims,
            metrics_aggregated=metrics
        )

    def calculate_totals(
        self,
        df: pd.DataFrame,
        metrics: List[str] = None,
        contributor_col: str = 'contributor_id'
    ) -> Dict:
        """
        Calculate GB-wide totals across all data.

        Args:
            df: Input dataframe
            metrics: Metrics to total
            contributor_col: Column containing contributor IDs

        Returns:
            Dictionary of total values
        """
        if df.empty:
            return {}

        if metrics is None:
            metrics = [m for m in self.METRICS.keys() if m in df.columns]

        totals = {'total_contributors': df[contributor_col].nunique()}

        for metric in metrics:
            if metric in df.columns:
                agg_func = self.METRICS.get(metric, 'sum')
                if agg_func == 'sum':
                    totals[f'total_{metric}'] = df[metric].sum()
                elif agg_func == 'mean':
                    totals[f'avg_{metric}'] = df[metric].mean()

        return totals

    def create_pivot_table(
        self,
        df: pd.DataFrame,
        row_dim: str,
        col_dim: str,
        metric: str,
        contributor_col: str = 'contributor_id'
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Create a pivot table with contributor counts.

        Args:
            df: Input dataframe
            row_dim: Row dimension
            col_dim: Column dimension
            metric: Metric to pivot
            contributor_col: Column containing contributor IDs

        Returns:
            Tuple of (value pivot table, contributor count pivot table)
        """
        if df.empty or row_dim not in df.columns or col_dim not in df.columns:
            return pd.DataFrame(), pd.DataFrame()

        # Value pivot
        value_pivot = pd.pivot_table(
            df,
            values=metric,
            index=row_dim,
            columns=col_dim,
            aggfunc='sum',
            fill_value=0
        )

        # Contributor count pivot
        count_pivot = pd.pivot_table(
            df,
            values=contributor_col,
            index=row_dim,
            columns=col_dim,
            aggfunc=lambda x: len(set(x)),
            fill_value=0
        )

        return value_pivot, count_pivot
