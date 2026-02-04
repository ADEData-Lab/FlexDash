"""
Disclosure Control Module for FlexDash.

Implements k-anonymity threshold checking, dominance rules,
and cell suppression logic to protect contributor confidentiality.
"""

import logging
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DisclosureStatus(Enum):
    """Status of disclosure safety for a cell."""
    SAFE = "safe"  # Can publish real value
    SUPPRESS = "suppress"  # Must suppress (remove cell)
    ILLUSTRATIVE = "illustrative"  # Use illustrative data


@dataclass
class DisclosureDecision:
    """Record of a disclosure control decision."""
    dimension: str
    dimension_value: str
    metric: str
    original_value: float
    contributor_count: int
    status: DisclosureStatus
    reason: str
    final_value: Optional[float] = None


@dataclass
class DisclosureReport:
    """Summary of disclosure control decisions."""
    total_cells: int
    safe_cells: int
    suppressed_cells: int
    illustrative_cells: int
    decisions: List[DisclosureDecision] = field(default_factory=list)


class DisclosureController:
    """
    Controls statistical disclosure to protect contributor confidentiality.

    Implements:
    - k-anonymity threshold checking
    - Dominance rule (top-N contributors)
    - Cell suppression
    - Rounding
    """

    def __init__(self, config: Dict = None):
        """
        Initialize disclosure controller.

        Args:
            config: Disclosure rules configuration
        """
        config = config or {}

        # Core thresholds
        self.k_threshold = config.get('k_threshold', 3)
        self.rounding_precision = config.get('rounding_precision', 10)

        # Dominance rule parameters
        self.dominance_enabled = config.get('dominance_enabled', True)
        self.dominance_top_n = config.get('dominance_top_n', 2)
        self.dominance_threshold = config.get('dominance_threshold', 0.85)

        # Audit trail
        self.decisions: List[DisclosureDecision] = []

    def check_cell(
        self,
        value: float,
        contributor_ids: List[str],
        dimension: str,
        dimension_value: str,
        metric: str,
        contributor_values: List[float] = None
    ) -> DisclosureDecision:
        """
        Check if a single cell is safe to publish.

        Args:
            value: The aggregate value for the cell
            contributor_ids: List of contributor IDs in this cell
            dimension: Name of the dimension (e.g., 'sector', 'asset_class')
            dimension_value: Value of the dimension (e.g., 'domestic', 'ev_charger')
            metric: Name of the metric (e.g., 'capacity_mw')
            contributor_values: Individual contributor values (for dominance check)

        Returns:
            DisclosureDecision with status and reason
        """
        unique_contributors = set(contributor_ids)
        k = len(unique_contributors)

        # Check k-anonymity threshold
        if k < self.k_threshold:
            status = DisclosureStatus.SUPPRESS if k == 0 else DisclosureStatus.ILLUSTRATIVE
            reason = f"k={k} below threshold of {self.k_threshold}"

            decision = DisclosureDecision(
                dimension=dimension,
                dimension_value=dimension_value,
                metric=metric,
                original_value=value,
                contributor_count=k,
                status=status,
                reason=reason
            )
            self.decisions.append(decision)
            logger.debug(f"Disclosure check: {dimension}={dimension_value}, {metric}: {status.value} ({reason})")
            return decision

        # Check dominance rule
        if self.dominance_enabled and contributor_values:
            if self._check_dominance(contributor_values):
                status = DisclosureStatus.ILLUSTRATIVE
                reason = f"Top {self.dominance_top_n} contributors exceed {self.dominance_threshold:.0%} of total"

                decision = DisclosureDecision(
                    dimension=dimension,
                    dimension_value=dimension_value,
                    metric=metric,
                    original_value=value,
                    contributor_count=k,
                    status=status,
                    reason=reason
                )
                self.decisions.append(decision)
                logger.debug(f"Disclosure check: {dimension}={dimension_value}, {metric}: {status.value} ({reason})")
                return decision

        # Cell is safe
        rounded_value = self._round_value(value)
        decision = DisclosureDecision(
            dimension=dimension,
            dimension_value=dimension_value,
            metric=metric,
            original_value=value,
            contributor_count=k,
            status=DisclosureStatus.SAFE,
            reason=f"k={k} meets threshold, no dominance issue",
            final_value=rounded_value
        )
        self.decisions.append(decision)
        logger.debug(f"Disclosure check: {dimension}={dimension_value}, {metric}: SAFE")
        return decision

    def _check_dominance(self, values: List[float]) -> bool:
        """
        Check if top N contributors dominate the total.

        Args:
            values: List of individual contributor values

        Returns:
            True if dominance threshold is exceeded
        """
        if not values or len(values) <= self.dominance_top_n:
            return False

        total = sum(values)
        if total == 0:
            return False

        sorted_values = sorted(values, reverse=True)
        top_n_sum = sum(sorted_values[:self.dominance_top_n])

        return (top_n_sum / total) > self.dominance_threshold

    def _round_value(self, value: float) -> float:
        """Round value to configured precision."""
        if pd.isna(value):
            return value
        return round(value / self.rounding_precision) * self.rounding_precision

    def apply_disclosure_control(
        self,
        df: pd.DataFrame,
        contributor_col: str,
        dimension_cols: List[str],
        metric_cols: List[str]
    ) -> Tuple[pd.DataFrame, DisclosureReport]:
        """
        Apply disclosure control to an aggregated dataframe.

        Args:
            df: Dataframe with aggregated data
            contributor_col: Column containing contributor IDs
            dimension_cols: Columns defining the aggregation dimensions
            metric_cols: Columns containing values to protect

        Returns:
            Tuple of (protected dataframe, disclosure report)
        """
        # Reset decisions for this run
        self.decisions = []

        # Group by dimensions and check each cell
        safe_rows = []
        illustrative_rows = []

        for group_key, group_df in df.groupby(dimension_cols):
            row_data = {col: val for col, val in zip(dimension_cols, group_key)} \
                if isinstance(group_key, tuple) else {dimension_cols[0]: group_key}

            # Track k-anonymity per metric based on *non-missing* values for that metric.
            # This avoids treating contributors with missing values as contributing to k.
            metric_k: Dict[str, int] = {}
            is_safe = True

            for metric in metric_cols:
                if metric not in group_df.columns:
                    # Missing metric column entirely (treat as no data)
                    contributors_for_metric: List[str] = []
                    metric_df = group_df.iloc[0:0]
                else:
                    metric_series = pd.to_numeric(group_df[metric], errors='coerce')
                    metric_df = group_df[metric_series.notna()]
                    contributors_for_metric = metric_df[contributor_col].unique().tolist()

                k_metric = len(set(contributors_for_metric))
                metric_k[metric] = k_metric

                agg_value = metric_df[metric].sum() if not metric_df.empty else 0.0
                contributor_values = (
                    metric_df.groupby(contributor_col)[metric].sum().tolist()
                    if not metric_df.empty
                    else []
                )

                # Preserve the original aggregate value for internal downstream processing.
                # This must never be exported publicly; internal columns are removed before export.
                row_data[f"_orig_{metric}"] = float(agg_value) if agg_value is not None else 0.0

                decision = self.check_cell(
                    value=agg_value,
                    contributor_ids=contributors_for_metric,
                    dimension='|'.join(map(str, dimension_cols)),
                    dimension_value='|'.join(map(str, group_key)) if isinstance(group_key, tuple) else str(group_key),
                    metric=metric,
                    contributor_values=contributor_values
                )

                if decision.status == DisclosureStatus.SAFE:
                    row_data[metric] = decision.final_value
                    row_data[f'{metric}_status'] = 'real'
                elif decision.status == DisclosureStatus.ILLUSTRATIVE:
                    is_safe = False
                    row_data[metric] = None  # Will be filled with illustrative data
                    row_data[f'{metric}_status'] = 'illustrative'
                else:  # SUPPRESS
                    is_safe = False
                    row_data[metric] = None
                    row_data[f'{metric}_status'] = 'suppressed'

            # Back-compat: expose a single contributor count for UI (k) based on capacity_mw where possible.
            if 'capacity_mw' in metric_k:
                row_data['_contributor_count'] = metric_k['capacity_mw']
            elif metric_k:
                row_data['_contributor_count'] = max(metric_k.values())
            else:
                row_data['_contributor_count'] = 0

            # Keep metric-specific k values for internal QA/debugging if needed.
            for metric, k_val in metric_k.items():
                row_data[f'_k_{metric}'] = k_val

            if is_safe:
                safe_rows.append(row_data)
            else:
                illustrative_rows.append(row_data)

        # Combine results
        result_df = pd.DataFrame(safe_rows + illustrative_rows)

        # Generate report
        report = DisclosureReport(
            total_cells=len(self.decisions),
            safe_cells=sum(1 for d in self.decisions if d.status == DisclosureStatus.SAFE),
            suppressed_cells=sum(1 for d in self.decisions if d.status == DisclosureStatus.SUPPRESS),
            illustrative_cells=sum(1 for d in self.decisions if d.status == DisclosureStatus.ILLUSTRATIVE),
            decisions=self.decisions.copy()
        )

        logger.info(
            f"Disclosure control complete: {report.safe_cells}/{report.total_cells} cells safe, "
            f"{report.illustrative_cells} illustrative, {report.suppressed_cells} suppressed"
        )

        return result_df, report

    def generate_audit_log(self) -> List[Dict]:
        """Generate audit log of all disclosure decisions."""
        return [
            {
                'dimension': d.dimension,
                'dimension_value': d.dimension_value,
                'metric': d.metric,
                'contributor_count': d.contributor_count,
                'status': d.status.value,
                'reason': d.reason,
            }
            for d in self.decisions
        ]


def check_disclosure_safety(
    cell_value: float,
    contributor_ids: List[str],
    k_threshold: int = 3
) -> str:
    """
    Simple function to check if a cell is safe to publish.

    Args:
        cell_value: The aggregate value
        contributor_ids: List of contributor IDs
        k_threshold: Minimum contributors required

    Returns:
        "safe", "suppress", or "illustrative"
    """
    k = len(set(contributor_ids))

    if k >= k_threshold:
        return "safe"
    elif k == 0:
        return "suppress"
    else:
        return "illustrative"
