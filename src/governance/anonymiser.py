"""
Anonymisation Module for FlexDash.

Handles pseudonymisation of contributor identities and
generation of illustrative data where disclosure is not safe.
"""

import logging
import hashlib
import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class IllustrativeDataConfig:
    """Configuration for illustrative data generation."""
    source: str = "sector_averages"  # 'sector_averages', 'random', 'fixed'
    variation_percent: float = 0.15
    seed: int = 42


class Anonymiser:
    """
    Handles anonymisation of flexibility data.

    - Pseudonymises contributor identities
    - Generates illustrative data for unsafe cells
    - Maintains consistency in illustrative data
    """

    def __init__(self, config: Dict = None):
        """
        Initialize anonymiser.

        Args:
            config: Anonymisation configuration
        """
        config = config or {}
        self.salt = config.get('salt', 'flex_dashboard_2025')
        self.illustrative_config = IllustrativeDataConfig(
            source=config.get('illustrative_source', 'sector_averages'),
            variation_percent=config.get('illustrative_variation', 0.15),
            seed=config.get('seed', 42)
        )
        self._pseudonym_map: Dict[str, str] = {}
        self._reverse_map: Dict[str, str] = {}  # For internal audit only
        random.seed(self.illustrative_config.seed)
        np.random.seed(self.illustrative_config.seed)

    def pseudonymise_id(self, original_id: str) -> str:
        """
        Create a pseudonymous identifier.

        Args:
            original_id: Original contributor identifier

        Returns:
            Pseudonymous identifier
        """
        if original_id in self._pseudonym_map:
            return self._pseudonym_map[original_id]

        # Create hash-based pseudonym
        hash_input = f"{self.salt}:{original_id}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
        pseudonym = f"CONTRIB_{hash_value.upper()}"

        self._pseudonym_map[original_id] = pseudonym
        self._reverse_map[pseudonym] = original_id

        return pseudonym

    def pseudonymise_dataframe(
        self,
        df: pd.DataFrame,
        id_columns: List[str]
    ) -> pd.DataFrame:
        """
        Pseudonymise identifier columns in a dataframe.

        Args:
            df: Input dataframe
            id_columns: Columns containing identifiers to pseudonymise

        Returns:
            Dataframe with pseudonymised identifiers
        """
        result = df.copy()

        for col in id_columns:
            if col in result.columns:
                result[col] = result[col].apply(
                    lambda x: self.pseudonymise_id(str(x)) if pd.notna(x) else x
                )

        return result

    def generate_illustrative_value(
        self,
        metric: str,
        sector: str,
        asset_class: str = None,
        reference_values: List[float] = None
    ) -> float:
        """
        Generate an illustrative value for an unsafe cell.

        Args:
            metric: Name of the metric
            sector: Sector (domestic/ic)
            asset_class: Optional asset class
            reference_values: Optional list of real values for calibration

        Returns:
            Illustrative value
        """
        # Default sector benchmarks (from methodology research)
        benchmarks = {
            'domestic': {
                'capacity_mw': {
                    'ev_charger': 7.0,
                    'heat_pump': 3.5,
                    'battery_storage': 5.0,
                    'default': 5.0
                },
                'energy_mwh': {
                    'ev_charger': 2.5,
                    'heat_pump': 3.0,
                    'battery_storage': 4.0,
                    'default': 3.0
                }
            },
            'ic': {
                'capacity_mw': {
                    'cold_storage': 500,
                    'water_treatment': 1000,
                    'manufacturing': 2000,
                    'default': 800
                },
                'energy_mwh': {
                    'cold_storage': 200,
                    'water_treatment': 500,
                    'manufacturing': 1000,
                    'default': 400
                }
            }
        }

        # Get base value from benchmarks or reference
        if reference_values and len(reference_values) > 0:
            base_value = np.mean(reference_values)
        else:
            sector_benchmarks = benchmarks.get(sector, benchmarks['domestic'])
            metric_benchmarks = sector_benchmarks.get(metric, {})
            base_value = metric_benchmarks.get(asset_class, metric_benchmarks.get('default', 100))

        # Add variation
        variation = random.uniform(
            -self.illustrative_config.variation_percent,
            self.illustrative_config.variation_percent
        )
        illustrative_value = base_value * (1 + variation)

        # Ensure positive
        illustrative_value = max(0, illustrative_value)

        logger.debug(
            f"Generated illustrative value for {metric}/{sector}/{asset_class}: "
            f"{illustrative_value:.2f}"
        )

        return illustrative_value

    def _disclosure_range_mw(self, value_mw: Any) -> Dict[str, Any]:
        """
        Convert a MW value to a disclosure-safe range bucket.

        The returned midpoint can be used for charting without revealing the exact value.
        """
        try:
            v = float(value_mw) if value_mw is not None and not pd.isna(value_mw) else 0.0
        except Exception:
            v = 0.0

        if v == 0:
            return {"label": "0 MW", "min": 0.0, "max": 0.0, "midpoint": 0.0}
        if v < 10:
            return {"label": "<10 MW", "min": 0.0, "max": 10.0, "midpoint": 5.0}
        if v < 50:
            return {"label": "10-50 MW", "min": 10.0, "max": 50.0, "midpoint": 30.0}
        if v < 100:
            return {"label": "50-100 MW", "min": 50.0, "max": 100.0, "midpoint": 75.0}
        if v < 250:
            return {"label": "100-250 MW", "min": 100.0, "max": 250.0, "midpoint": 175.0}
        if v < 500:
            return {"label": "250-500 MW", "min": 250.0, "max": 500.0, "midpoint": 375.0}
        if v < 1000:
            return {"label": "0.5-1 GW", "min": 500.0, "max": 1000.0, "midpoint": 750.0}
        if v < 2500:
            return {"label": "1-2.5 GW", "min": 1000.0, "max": 2500.0, "midpoint": 1750.0}
        if v < 5000:
            return {"label": "2.5-5 GW", "min": 2500.0, "max": 5000.0, "midpoint": 3750.0}
        if v < 10000:
            return {"label": "5-10 GW", "min": 5000.0, "max": 10000.0, "midpoint": 7500.0}
        return {"label": ">10 GW", "min": 10000.0, "max": 15000.0, "midpoint": 12500.0}

    def _disclosure_range_gwh(self, value_gwh: Any) -> Dict[str, Any]:
        """
        Convert a GWh value to a disclosure-safe range bucket.

        This is used for headline energy metrics (e.g. delivered flexibility energy) where
        k-anonymity or dominance rules prevent publishing point estimates.

        Note: Labels omit units because the dashboard cards already specify (GWh).
        """
        try:
            v = float(value_gwh) if value_gwh is not None and not pd.isna(value_gwh) else 0.0
        except Exception:
            v = 0.0

        if v == 0:
            return {"label": "0", "min": 0.0, "max": 0.0, "midpoint": 0.0}
        if v < 1:
            return {"label": "<1", "min": 0.0, "max": 1.0, "midpoint": 0.5}
        if v < 5:
            return {"label": "1-5", "min": 1.0, "max": 5.0, "midpoint": 3.0}
        if v < 10:
            return {"label": "5-10", "min": 5.0, "max": 10.0, "midpoint": 7.5}
        if v < 25:
            return {"label": "10-25", "min": 10.0, "max": 25.0, "midpoint": 17.5}
        if v < 50:
            return {"label": "25-50", "min": 25.0, "max": 50.0, "midpoint": 37.5}
        if v < 100:
            return {"label": "50-100", "min": 50.0, "max": 100.0, "midpoint": 75.0}
        if v < 250:
            return {"label": "100-250", "min": 100.0, "max": 250.0, "midpoint": 175.0}
        if v < 500:
            return {"label": "250-500", "min": 250.0, "max": 500.0, "midpoint": 375.0}
        if v < 1000:
            return {"label": "500-1000", "min": 500.0, "max": 1000.0, "midpoint": 750.0}
        if v < 2500:
            return {"label": "1000-2500", "min": 1000.0, "max": 2500.0, "midpoint": 1750.0}
        return {"label": ">2500", "min": 2500.0, "max": 5000.0, "midpoint": 3750.0}

    def _disclosure_range_count(self, value_count: Any) -> Dict[str, Any]:
        """
        Convert a count value to a disclosure-safe range bucket.

        Labels omit a unit because the UI context (assets/customers) provides it.
        """
        try:
            v = float(value_count) if value_count is not None and not pd.isna(value_count) else 0.0
        except Exception:
            v = 0.0

        if v <= 0:
            return {"label": "0", "min": 0.0, "max": 0.0, "midpoint": 0.0}
        if v < 10:
            return {"label": "<10", "min": 0.0, "max": 10.0, "midpoint": 5.0}
        if v < 50:
            return {"label": "10-50", "min": 10.0, "max": 50.0, "midpoint": 30.0}
        if v < 100:
            return {"label": "50-100", "min": 50.0, "max": 100.0, "midpoint": 75.0}
        if v < 500:
            return {"label": "100-500", "min": 100.0, "max": 500.0, "midpoint": 300.0}
        if v < 1000:
            return {"label": "500-1k", "min": 500.0, "max": 1000.0, "midpoint": 750.0}
        if v < 5000:
            return {"label": "1k-5k", "min": 1000.0, "max": 5000.0, "midpoint": 3000.0}
        if v < 10000:
            return {"label": "5k-10k", "min": 5000.0, "max": 10000.0, "midpoint": 7500.0}
        if v < 50000:
            return {"label": "10k-50k", "min": 10000.0, "max": 50000.0, "midpoint": 30000.0}
        if v < 100000:
            return {"label": "50k-100k", "min": 50000.0, "max": 100000.0, "midpoint": 75000.0}
        if v < 500000:
            return {"label": "100k-500k", "min": 100000.0, "max": 500000.0, "midpoint": 300000.0}
        if v < 1000000:
            return {"label": "500k-1m", "min": 500000.0, "max": 1000000.0, "midpoint": 750000.0}
        return {"label": ">1m", "min": 1000000.0, "max": 2000000.0, "midpoint": 1500000.0}

    def fill_illustrative_ranges(
        self,
        df: pd.DataFrame,
        metric_cols: List[str],
    ) -> pd.DataFrame:
        """
        Fill unsafe (illustrative) cells with disclosure-safe range midpoints and labels.

        This is preferred to generating random "illustrative" point estimates, because it:
          - preserves order-of-magnitude information
          - avoids implying false precision
          - aligns with the dashboard UI’s range tooltips

        Note: This uses internally-preserved `_orig_<metric>` aggregates computed during
        disclosure checking, and must be called before internal columns are removed.
        """
        result = df.copy()

        for metric in metric_cols:
            status_col = f"{metric}_status"
            orig_col = f"_orig_{metric}"

            if status_col not in result.columns:
                continue

            for idx, _row in result.iterrows():
                if result.at[idx, status_col] != "illustrative":
                    continue

                orig_val = result.at[idx, orig_col] if orig_col in result.columns else None

                if metric == "capacity_mw":
                    bucket = self._disclosure_range_mw(orig_val)
                    result.at[idx, metric] = bucket["midpoint"]
                    result.at[idx, "capacity_range"] = bucket["label"]
                    result.at[idx, "capacity_range_min"] = bucket["min"]
                    result.at[idx, "capacity_range_max"] = bucket["max"]
                elif metric == "count":
                    bucket = self._disclosure_range_count(orig_val)
                    result.at[idx, metric] = bucket["midpoint"]
                    result.at[idx, "count_range"] = bucket["label"]
                    result.at[idx, "count_range_min"] = bucket["min"]
                    result.at[idx, "count_range_max"] = bucket["max"]
                else:
                    # For now we range-bucket capacity and portfolio counts; other metrics remain null/hidden.
                    continue

        return result

    def fill_illustrative_data(
        self,
        df: pd.DataFrame,
        metric_cols: List[str],
        sector_col: str = 'sector',
        asset_col: str = 'asset_class',
        reference_df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Fill suppressed cells with illustrative data.

        Args:
            df: Dataframe with some null values to fill
            metric_cols: Columns to fill with illustrative data
            sector_col: Column containing sector
            asset_col: Column containing asset class
            reference_df: Optional reference dataframe for calibration

        Returns:
            Dataframe with illustrative values filled in
        """
        result = df.copy()

        # Calculate reference statistics if available
        reference_stats = {}
        if reference_df is not None:
            for metric in metric_cols:
                if metric in reference_df.columns:
                    reference_stats[metric] = {
                        'mean': reference_df[metric].mean(),
                        'std': reference_df[metric].std()
                    }

        for idx, row in result.iterrows():
            sector = row.get(sector_col, 'domestic')
            asset_class = row.get(asset_col, None)

            for metric in metric_cols:
                status_col = f'{metric}_status'

                # Check if this cell needs illustrative data
                if status_col in result.columns and result.at[idx, status_col] == 'illustrative':
                    # Get reference values for this metric
                    ref_values = None
                    if metric in reference_stats:
                        ref_values = [reference_stats[metric]['mean']]

                    # Generate illustrative value
                    illustrative_value = self.generate_illustrative_value(
                        metric=metric,
                        sector=sector,
                        asset_class=asset_class,
                        reference_values=ref_values
                    )

                    result.at[idx, metric] = illustrative_value

        return result

    def remove_identifying_columns(
        self,
        df: pd.DataFrame,
        columns_to_remove: List[str] = None
    ) -> pd.DataFrame:
        """
        Remove columns that could identify contributors.

        Args:
            df: Input dataframe
            columns_to_remove: Specific columns to remove

        Returns:
            Dataframe with identifying columns removed
        """
        default_remove = [
            'contributor_id', 'contributor_name', 'company', 'organisation',
            'email', 'contact', 'site_id', 'asset_id', '_contributor_count'
        ]

        columns_to_remove = columns_to_remove or default_remove

        result = df.copy()
        for col in columns_to_remove:
            if col in result.columns:
                result = result.drop(columns=[col])
                logger.debug(f"Removed identifying column: {col}")

        return result

    def prepare_for_publication(
        self,
        df: pd.DataFrame,
        metric_cols: List[str],
        rounding_precision: int = 10
    ) -> pd.DataFrame:
        """
        Final preparation of data for publication.

        - Rounds values
        - Removes internal columns
        - Adds data type indicators

        Args:
            df: Processed dataframe
            metric_cols: Columns containing metrics
            rounding_precision: Rounding precision

        Returns:
            Publication-ready dataframe
        """
        result = df.copy()

        # Round metric values
        for col in metric_cols:
            if col in result.columns:
                if col == "capacity_mw":
                    result[col] = result[col].apply(
                        lambda x: round(x / rounding_precision) * rounding_precision if pd.notna(x) else x
                    )
                elif col == "count":
                    # Do not round counts using MW precision; leave as-is (bucket midpoints already coarse).
                    result[col] = result[col].apply(lambda x: int(round(x)) if pd.notna(x) else x)

        # Create is_illustrative flags
        for col in metric_cols:
            status_col = f'{col}_status'
            flag_col = f'{col}_illustrative'

            if status_col in result.columns:
                result[flag_col] = result[status_col] == 'illustrative'
                result = result.drop(columns=[status_col])

        # Remove internal columns
        internal_cols = [c for c in result.columns if c.startswith('_')]
        result = result.drop(columns=internal_cols, errors='ignore')

        return result

    def get_pseudonym_count(self) -> int:
        """Return number of pseudonymised identities."""
        return len(self._pseudonym_map)
