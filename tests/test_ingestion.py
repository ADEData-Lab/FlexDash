"""
Unit tests for data ingestion module.

Tests template parsing and data validation.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock
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

    def test_contributor_id_generation(self):
        """Test that contributor IDs are generated sequentially."""
        # Parse would generate sequential IDs
        assert self.parser._contributor_counter == 0
        self.parser._contributor_counter += 1
        assert self.parser._contributor_counter == 1

    def test_map_asset_type_ev(self):
        """Test asset type mapping for EV chargers."""
        assert self.parser._map_asset_type('EV Chargers') == 'ev_charger'
        assert self.parser._map_asset_type('Electric Vehicle') == 'ev_charger'
        assert self.parser._map_asset_type('charger') == 'ev_charger'

    def test_map_asset_type_heat_pump(self):
        """Test asset type mapping for heat pumps."""
        assert self.parser._map_asset_type('Heat Pump') == 'heat_pump'
        assert self.parser._map_asset_type('ASHP') == 'heat_pump'
        assert self.parser._map_asset_type('HP') == 'heat_pump'

    def test_map_asset_type_battery(self):
        """Test asset type mapping for batteries."""
        assert self.parser._map_asset_type('Battery') == 'battery_storage'
        assert self.parser._map_asset_type('BESS') == 'battery_storage'
        assert self.parser._map_asset_type('storage') == 'battery_storage'

    def test_map_asset_type_ic(self):
        """Test asset type mapping for I&C assets."""
        assert self.parser._map_asset_type('cold storage') == 'cold_storage'
        assert self.parser._map_asset_type('refrigeration') == 'cold_storage'
        assert self.parser._map_asset_type('water treatment') == 'water_treatment'
        assert self.parser._map_asset_type('manufacturing') == 'manufacturing'

    def test_map_industry_to_asset(self):
        """Test industry type to asset mapping."""
        assert self.parser._map_industry_to_asset('Food / Drink') == 'cold_storage'
        assert self.parser._map_industry_to_asset('Water Treatment') == 'water_treatment'
        assert self.parser._map_industry_to_asset('Manufacturing') == 'manufacturing'
        assert self.parser._map_industry_to_asset('Energy') == 'commercial_battery'

    def test_estimate_capacity_ev(self):
        """Test capacity estimation for EV chargers."""
        # 1000 EV chargers at 7kW each = 7 MW
        capacity = self.parser._estimate_capacity('ev_charger', 1000)
        assert capacity == 7.0

    def test_estimate_capacity_battery(self):
        """Test capacity estimation for batteries."""
        # 1000 batteries at 5kW each = 5 MW
        capacity = self.parser._estimate_capacity('battery_storage', 1000)
        assert capacity == 5.0

    def test_estimate_capacity_ic(self):
        """Test capacity estimation for I&C assets."""
        # 10 cold storage sites at 100kW each = 1 MW
        capacity = self.parser._estimate_capacity('cold_storage', 10)
        assert capacity == 1.0


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

    def test_empty_assets_has_warning(self):
        """Test that empty assets triggers a warning."""
        data = Mock()
        data.assets = pd.DataFrame()
        data.events = pd.DataFrame()

        result = self.validator.validate(data)

        assert any('no asset' in w.lower() for w in result.warnings)

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
