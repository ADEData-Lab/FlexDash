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
                result[col] = result[col].apply(
                    lambda x: round(x / rounding_precision) * rounding_precision
                    if pd.notna(x) else x
                )

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
