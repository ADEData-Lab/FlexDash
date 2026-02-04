"""
Data validation module for FlexDash.

Validates data quality, completeness, and consistency
before further processing.
"""

import logging
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Container for validation results."""
    is_valid: bool
    completeness_score: float  # 0-1
    quality_score: float  # 0-1
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    field_stats: Dict[str, Dict] = field(default_factory=dict)


class DataValidator:
    """
    Validates flexibility data for completeness and quality.
    """

    # Required fields for different data types
    REQUIRED_ASSET_FIELDS = ['asset_class', 'capacity_mw']
    REQUIRED_EVENT_FIELDS = ['event_date', 'capacity_mw']

    # Valid ranges for numeric fields
    VALID_RANGES = {
        'capacity_mw': (0, 10000),  # 0-10 GW reasonable range
        'capacity_kw': (0, 10000000),  # 0-10 GW in kW
        'energy_mwh': (0, 100000),  # 0-100 GWh reasonable range
        'duration_hours': (0, 8760),  # 0-1 year
        'count': (0, 10000000),  # Reasonable count range
        'delivery_factor': (0, 1.5),  # 0-150%
    }

    def __init__(self, config: Dict = None):
        """
        Initialize validator with optional configuration.

        Args:
            config: Validation configuration settings
        """
        self.config = config or {}
        self.min_completeness = self.config.get('minimum_completeness', 0.5)

    def validate(self, data) -> ValidationResult:
        """
        Validate a ParsedData object.

        Args:
            data: ParsedData object to validate

        Returns:
            ValidationResult with scores and issues
        """
        errors = []
        warnings = []
        field_stats = {}

        # Validate assets
        if not data.assets.empty:
            asset_result = self._validate_dataframe(
                data.assets,
                'assets',
                self.REQUIRED_ASSET_FIELDS
            )
            errors.extend(asset_result['errors'])
            warnings.extend(asset_result['warnings'])
            field_stats['assets'] = asset_result['stats']
        else:
            warnings.append("No asset data provided")
            field_stats['assets'] = {'completeness': 0}

        # Validate events
        if not data.events.empty:
            event_result = self._validate_dataframe(
                data.events,
                'events',
                self.REQUIRED_EVENT_FIELDS
            )
            errors.extend(event_result['errors'])
            warnings.extend(event_result['warnings'])
            field_stats['events'] = event_result['stats']

        # Calculate overall scores
        completeness_score = self._calculate_completeness(data, field_stats)
        quality_score = self._calculate_quality_score(errors, warnings)

        # Determine if valid
        is_valid = (
            len(errors) == 0 and
            completeness_score >= self.min_completeness
        )

        return ValidationResult(
            is_valid=is_valid,
            completeness_score=completeness_score,
            quality_score=quality_score,
            errors=errors,
            warnings=warnings,
            field_stats=field_stats
        )

    def _validate_dataframe(
        self,
        df: pd.DataFrame,
        name: str,
        required_fields: List[str]
    ) -> Dict:
        """Validate a single dataframe."""
        errors = []
        warnings = []
        stats = {}

        # Check required fields
        missing_required = [f for f in required_fields if f not in df.columns]
        if missing_required:
            errors.append(f"{name}: Missing required fields: {missing_required}")

        # Calculate completeness per field
        for col in df.columns:
            non_null = df[col].notna().sum()
            total = len(df)
            completeness = non_null / total if total > 0 else 0
            stats[col] = {'completeness': completeness, 'count': int(non_null)}

            if completeness < 0.5:
                warnings.append(f"{name}.{col}: Low completeness ({completeness:.1%})")

        # Validate numeric ranges
        for col, (min_val, max_val) in self.VALID_RANGES.items():
            if col in df.columns:
                numeric_col = pd.to_numeric(df[col], errors='coerce')
                out_of_range = (
                    (numeric_col < min_val) | (numeric_col > max_val)
                ).sum()
                if out_of_range > 0:
                    warnings.append(
                        f"{name}.{col}: {out_of_range} values outside valid range "
                        f"[{min_val}, {max_val}]"
                    )

        # Check for duplicates
        if len(df) > 0:
            dup_count = df.duplicated().sum()
            if dup_count > 0:
                warnings.append(f"{name}: {dup_count} duplicate rows detected")

        # Check for negative values in capacity/energy fields
        for col in ['capacity_mw', 'energy_mwh', 'count']:
            if col in df.columns:
                numeric_col = pd.to_numeric(df[col], errors='coerce')
                negative = (numeric_col < 0).sum()
                if negative > 0:
                    errors.append(f"{name}.{col}: {negative} negative values")

        stats['completeness'] = np.mean([s['completeness'] for s in stats.values() if 'completeness' in s])

        return {
            'errors': errors,
            'warnings': warnings,
            'stats': stats
        }

    def _calculate_completeness(self, data, field_stats: Dict) -> float:
        """Calculate overall completeness score."""
        scores = []

        # Asset completeness (weighted higher)
        if 'assets' in field_stats:
            scores.append(field_stats['assets'].get('completeness', 0) * 2)

        # Events completeness
        if 'events' in field_stats:
            scores.append(field_stats['events'].get('completeness', 0))

        # Basic submission completeness
        has_data = 1 if not data.assets.empty else 0
        scores.append(has_data)

        return np.mean(scores) if scores else 0

    def _calculate_quality_score(self, errors: List, warnings: List) -> float:
        """Calculate quality score based on issues."""
        # Start with perfect score, deduct for issues
        score = 1.0
        score -= len(errors) * 0.2  # Errors heavily penalized
        score -= len(warnings) * 0.05  # Warnings lightly penalized
        return max(0, score)

    def generate_quality_report(self, results: List[ValidationResult]) -> Dict:
        """
        Generate aggregate quality report across all submissions.

        Args:
            results: List of ValidationResult objects

        Returns:
            Summary statistics
        """
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)

        avg_completeness = np.mean([r.completeness_score for r in results])
        avg_quality = np.mean([r.quality_score for r in results])

        all_errors = []
        all_warnings = []
        for r in results:
            all_errors.extend(r.errors)
            all_warnings.extend(r.warnings)

        return {
            'total_submissions': total,
            'valid_submissions': valid,
            'validation_rate': valid / total if total > 0 else 0,
            'average_completeness': avg_completeness,
            'average_quality': avg_quality,
            'total_errors': len(all_errors),
            'total_warnings': len(all_warnings),
            'common_errors': self._get_common_issues(all_errors),
            'common_warnings': self._get_common_issues(all_warnings),
        }

    def _get_common_issues(self, issues: List[str], top_n: int = 5) -> List[Tuple[str, int]]:
        """Get most common issues."""
        from collections import Counter
        return Counter(issues).most_common(top_n)
