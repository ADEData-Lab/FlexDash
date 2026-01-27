"""
Unit tests for data ingestion module.

Tests template parsing and data validation.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.template_parser import TemplateParser, ParsedData
from src.ingestion.validators import DataValidator, ValidationResult


class TestTemplateParser:
    """Tests for TemplateParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = TemplateParser()

    def test_pseudonymise_contributors(self):
        """Test that contributor IDs are pseudonymised."""
        # Simulate parsing two files
        with patch.object(self.parser, '_parse_standard_template') as mock_parse:
            mock_parse.return_value = ParsedData(
                contributor_id='CONTRIB_001',
                contributor_name='Test',
                submission_date=None,
                template_version='V1.2',
                sector='domestic',
                assets=pd.DataFrame(),
                events=pd.DataFrame(),
                services=pd.DataFrame()
            )

            result = self.parser.parse_file(Path('test.xlsx'))

            assert result.contributor_id.startswith('CONTRIB_')
            assert result.contributor_name != result.contributor_id

    def test_sector_inference_domestic(self):
        """Test sector inference for domestic assets."""
        assets = pd.DataFrame({
            'asset_class': ['ev_charger', 'heat_pump', 'battery']
        })

        sector = self.parser._infer_sector(assets)
        assert sector == 'domestic'

    def test_sector_inference_ic(self):
        """Test sector inference for I&C assets."""
        assets = pd.DataFrame({
            'asset_class': ['cold_storage', 'water_treatment']
        })

        sector = self.parser._infer_sector(assets)
        assert sector == 'ic'

    def test_sector_inference_empty(self):
        """Test sector inference with empty data."""
        assets = pd.DataFrame()
        sector = self.parser._infer_sector(assets)
        assert sector == 'unknown'

    def test_standardize_columns(self):
        """Test column name standardization."""
        df = pd.DataFrame({
            'Asset Type': [1],
            'Capacity (MW)': [100],
            'Number of Assets': [50]
        })

        result = self.parser._standardize_assets(df)

        assert 'asset_type' in result.columns
        assert 'capacity_(mw)' in result.columns or 'capacity_mw' in result.columns


class TestDataValidator:
    """Tests for DataValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataValidator({'minimum_completeness': 0.5})

    def test_valid_data_passes(self):
        """Test that complete valid data passes validation."""
        data = Mock()
        data.assets = pd.DataFrame({
            'asset_class': ['ev_charger', 'heat_pump'],
            'capacity_mw': [100, 50]
        })
        data.events = pd.DataFrame()

        result = self.validator.validate(data)

        assert result.is_valid
        assert result.completeness_score > 0

    def test_missing_required_fields_fails(self):
        """Test that missing required fields causes validation failure."""
        data = Mock()
        data.assets = pd.DataFrame({
            'some_other_field': [1, 2, 3]
        })
        data.events = pd.DataFrame()

        result = self.validator.validate(data)

        assert len(result.errors) > 0

    def test_negative_values_flagged(self):
        """Test that negative capacity values are flagged."""
        data = Mock()
        data.assets = pd.DataFrame({
            'asset_class': ['ev_charger'],
            'capacity_mw': [-100]
        })
        data.events = pd.DataFrame()

        result = self.validator.validate(data)

        assert any('negative' in e.lower() for e in result.errors)

    def test_completeness_calculation(self):
        """Test completeness score calculation."""
        data = Mock()
        data.assets = pd.DataFrame({
            'asset_class': ['ev_charger', None, 'heat_pump'],
            'capacity_mw': [100, 50, None]
        })
        data.events = pd.DataFrame()

        result = self.validator.validate(data)

        # Should have partial completeness
        assert 0 < result.completeness_score < 1

    def test_quality_report_aggregation(self):
        """Test aggregate quality report generation."""
        results = [
            ValidationResult(is_valid=True, completeness_score=0.9, quality_score=0.95),
            ValidationResult(is_valid=True, completeness_score=0.8, quality_score=0.85),
            ValidationResult(is_valid=False, completeness_score=0.3, quality_score=0.5)
        ]

        report = self.validator.generate_quality_report(results)

        assert report['total_submissions'] == 3
        assert report['valid_submissions'] == 2
        assert 0 < report['average_completeness'] < 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
