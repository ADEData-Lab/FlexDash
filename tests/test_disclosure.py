"""
Unit tests for disclosure control module.

Tests k-anonymity threshold checking, dominance rules,
and cell suppression logic.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.governance.disclosure import (
    DisclosureController,
    DisclosureStatus,
    check_disclosure_safety
)
import pandas as pd


class TestDisclosureController:
    """Tests for DisclosureController class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.controller = DisclosureController({
            'k_threshold': 3,
            'rounding_precision': 10,
            'dominance_enabled': True,
            'dominance_top_n': 2,
            'dominance_threshold': 0.85
        })

    def test_safe_cell_meets_threshold(self):
        """Test that cells with k >= threshold are marked safe."""
        decision = self.controller.check_cell(
            value=100,
            contributor_ids=['A', 'B', 'C'],
            dimension='sector',
            dimension_value='domestic',
            metric='capacity_mw'
        )

        assert decision.status == DisclosureStatus.SAFE
        assert decision.contributor_count == 3

    def test_illustrative_cell_below_threshold(self):
        """Test that cells with 0 < k < threshold are marked illustrative."""
        decision = self.controller.check_cell(
            value=100,
            contributor_ids=['A', 'B'],
            dimension='sector',
            dimension_value='domestic',
            metric='capacity_mw'
        )

        assert decision.status == DisclosureStatus.ILLUSTRATIVE
        assert decision.contributor_count == 2

    def test_suppress_cell_no_contributors(self):
        """Test that cells with no contributors are suppressed."""
        decision = self.controller.check_cell(
            value=0,
            contributor_ids=[],
            dimension='sector',
            dimension_value='domestic',
            metric='capacity_mw'
        )

        assert decision.status == DisclosureStatus.SUPPRESS
        assert decision.contributor_count == 0

    def test_duplicate_contributors_counted_once(self):
        """Test that duplicate contributor IDs are de-duplicated."""
        decision = self.controller.check_cell(
            value=100,
            contributor_ids=['A', 'A', 'B', 'B'],
            dimension='sector',
            dimension_value='domestic',
            metric='capacity_mw'
        )

        assert decision.contributor_count == 2
        assert decision.status == DisclosureStatus.ILLUSTRATIVE

    def test_dominance_rule_triggers(self):
        """Test that dominance rule marks cells as illustrative."""
        decision = self.controller.check_cell(
            value=100,
            contributor_ids=['A', 'B', 'C', 'D'],
            dimension='sector',
            dimension_value='domestic',
            metric='capacity_mw',
            contributor_values=[80, 15, 3, 2]  # Top 2 = 95%
        )

        assert decision.status == DisclosureStatus.ILLUSTRATIVE
        assert 'top' in decision.reason.lower() and 'exceed' in decision.reason.lower()

    def test_dominance_rule_passes(self):
        """Test that cells passing dominance rule are safe."""
        decision = self.controller.check_cell(
            value=100,
            contributor_ids=['A', 'B', 'C', 'D'],
            dimension='sector',
            dimension_value='domestic',
            metric='capacity_mw',
            contributor_values=[40, 30, 20, 10]  # Top 2 = 70%
        )

        assert decision.status == DisclosureStatus.SAFE

    def test_rounding_applied(self):
        """Test that values are rounded to configured precision."""
        decision = self.controller.check_cell(
            value=127,
            contributor_ids=['A', 'B', 'C'],
            dimension='sector',
            dimension_value='domestic',
            metric='capacity_mw'
        )

        assert decision.final_value == 130  # Rounded to nearest 10

    def test_apply_disclosure_control_ignores_missing_values_for_k(self):
        """k-counting should ignore contributors with missing metric values."""
        df = pd.DataFrame(
            {
                "sector": ["domestic", "domestic", "domestic"],
                "contributor_id": ["A", "B", "C"],
                "capacity_mw": [None, 10.0, 20.0],
            }
        )

        protected, report = self.controller.apply_disclosure_control(
            df=df,
            contributor_col="contributor_id",
            dimension_cols=["sector"],
            metric_cols=["capacity_mw"],
        )

        assert report.total_cells == 1
        assert report.decisions[0].contributor_count == 2
        assert report.decisions[0].status == DisclosureStatus.ILLUSTRATIVE
        # UI k should reflect metric-specific k
        assert int(protected.loc[0, "_contributor_count"]) == 2

    def test_apply_disclosure_control_suppresses_when_all_missing(self):
        """If all values are missing for a metric, the cell should be suppressed (k=0)."""
        df = pd.DataFrame(
            {
                "sector": ["domestic", "domestic"],
                "contributor_id": ["A", "B"],
                "capacity_mw": [None, None],
            }
        )

        protected, report = self.controller.apply_disclosure_control(
            df=df,
            contributor_col="contributor_id",
            dimension_cols=["sector"],
            metric_cols=["capacity_mw"],
        )

        assert report.total_cells == 1
        assert report.decisions[0].contributor_count == 0
        assert report.decisions[0].status == DisclosureStatus.SUPPRESS
        assert int(protected.loc[0, "_contributor_count"]) == 0


class TestCheckDisclosureSafety:
    """Tests for simple check_disclosure_safety function."""

    def test_safe_above_threshold(self):
        """Test safe result when k >= threshold."""
        result = check_disclosure_safety(
            cell_value=100,
            contributor_ids=['A', 'B', 'C'],
            k_threshold=3
        )
        assert result == "safe"

    def test_illustrative_below_threshold(self):
        """Test illustrative result when 0 < k < threshold."""
        result = check_disclosure_safety(
            cell_value=100,
            contributor_ids=['A', 'B'],
            k_threshold=3
        )
        assert result == "illustrative"

    def test_suppress_no_contributors(self):
        """Test suppress result when k = 0."""
        result = check_disclosure_safety(
            cell_value=0,
            contributor_ids=[],
            k_threshold=3
        )
        assert result == "suppress"

    def test_custom_threshold(self):
        """Test with custom k threshold."""
        result = check_disclosure_safety(
            cell_value=100,
            contributor_ids=['A', 'B', 'C', 'D', 'E'],
            k_threshold=5
        )
        assert result == "safe"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
