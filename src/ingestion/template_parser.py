"""
Template Parser for V1.2 Excel data templates and custom formats.

Handles standardised ADE Data Template V1.2 format as well as
custom submissions from various contributors.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ParsedData:
    """Container for parsed data from a single submission."""
    contributor_id: str
    contributor_name: str
    submission_date: datetime
    template_version: str
    sector: str  # 'domestic' or 'ic'

    # Core data
    assets: pd.DataFrame = field(default_factory=pd.DataFrame)
    events: pd.DataFrame = field(default_factory=pd.DataFrame)
    services: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    parse_warnings: List[str] = field(default_factory=list)
    parse_errors: List[str] = field(default_factory=list)


class TemplateParser:
    """
    Parser for ADE Flexibility Dashboard data templates.

    Supports V1.2 standard format and custom formats from various contributors.
    """

    # Expected columns in V1.2 template
    ASSET_COLUMNS = [
        'asset_class', 'asset_type', 'capacity_mw', 'count',
        'availability_hours', 'region', 'sector'
    ]

    EVENT_COLUMNS = [
        'event_date', 'event_type', 'service_type', 'duration_hours',
        'capacity_mw', 'energy_mwh', 'region'
    ]

    SERVICE_COLUMNS = [
        'service_type', 'product', 'registered_capacity_mw',
        'delivered_capacity_mw', 'delivery_factor'
    ]

    def __init__(self, taxonomy: Dict = None):
        """
        Initialize parser with optional taxonomy for field mapping.

        Args:
            taxonomy: Asset and service taxonomy for standardization
        """
        self.taxonomy = taxonomy or {}
        self._contributor_counter = 0

    def parse_file(self, filepath: Path) -> ParsedData:
        """
        Parse a single Excel file and return structured data.

        Args:
            filepath: Path to the Excel file

        Returns:
            ParsedData object with extracted information
        """
        filepath = Path(filepath)
        logger.info(f"Parsing file: {filepath.name}")

        # Generate pseudonymous ID
        self._contributor_counter += 1
        contributor_id = f"CONTRIB_{self._contributor_counter:03d}"

        # Detect format and route to appropriate parser
        if self._is_standard_template(filepath):
            return self._parse_standard_template(filepath, contributor_id)
        else:
            return self._parse_custom_format(filepath, contributor_id)

    def _is_standard_template(self, filepath: Path) -> bool:
        """Check if file follows V1.2 standard template format."""
        try:
            xl = pd.ExcelFile(filepath)
            expected_sheets = {'Metadata', 'Asset Portfolio', 'Flexibility Events'}
            return expected_sheets.issubset(set(xl.sheet_names))
        except Exception:
            return False

    def _parse_standard_template(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse V1.2 standard template format."""
        xl = pd.ExcelFile(filepath)
        warnings = []
        errors = []

        # Parse metadata sheet
        try:
            metadata_df = pd.read_excel(xl, sheet_name='Metadata', header=None)
            metadata = self._extract_metadata(metadata_df)
        except Exception as e:
            metadata = {}
            errors.append(f"Failed to parse Metadata: {e}")

        # Parse asset portfolio
        try:
            assets_df = pd.read_excel(xl, sheet_name='Asset Portfolio')
            assets_df = self._standardize_assets(assets_df)
        except Exception as e:
            assets_df = pd.DataFrame()
            errors.append(f"Failed to parse Asset Portfolio: {e}")

        # Parse flexibility events
        try:
            events_df = pd.read_excel(xl, sheet_name='Flexibility Events')
            events_df = self._standardize_events(events_df)
        except Exception as e:
            events_df = pd.DataFrame()
            warnings.append(f"No Flexibility Events data: {e}")

        # Parse service participation if present
        try:
            if 'Service Participation' in xl.sheet_names:
                services_df = pd.read_excel(xl, sheet_name='Service Participation')
                services_df = self._standardize_services(services_df)
            else:
                services_df = pd.DataFrame()
        except Exception as e:
            services_df = pd.DataFrame()
            warnings.append(f"No Service Participation data: {e}")

        # Determine sector from metadata or data
        sector = metadata.get('sector', self._infer_sector(assets_df))

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name=filepath.stem,  # Will be pseudonymised
            submission_date=datetime.now(),
            template_version="V1.2",
            sector=sector,
            assets=assets_df,
            events=events_df,
            services=services_df,
            metadata=metadata,
            parse_warnings=warnings,
            parse_errors=errors
        )

    def _parse_custom_format(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse non-standard submission formats."""
        filename = filepath.name.lower()
        warnings = []
        errors = []

        # Route to specific parsers based on filename patterns
        if 'flexitricity' in filename:
            return self._parse_flexitricity(filepath, contributor_id)
        elif 'enel' in filename:
            return self._parse_enel(filepath, contributor_id)
        elif 'oe_ade' in filename or 'octopus' in filename:
            return self._parse_octopus(filepath, contributor_id)
        elif 'c-u-b' in filename or 'clf' in filename:
            return self._parse_cub(filepath, contributor_id)
        else:
            # Generic fallback parser
            return self._parse_generic(filepath, contributor_id)

    def _parse_flexitricity(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse Flexitricity custom format."""
        logger.info("Using Flexitricity custom parser")

        xl = pd.ExcelFile(filepath)
        assets_df = pd.DataFrame()
        events_df = pd.DataFrame()

        # Flexitricity typically provides event-level data
        for sheet in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sheet)
            if 'capacity' in df.columns.str.lower().tolist():
                events_df = pd.concat([events_df, df], ignore_index=True)

        events_df = self._standardize_events(events_df)

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name="Flexitricity",
            submission_date=datetime.now(),
            template_version="Custom",
            sector="ic",  # Flexitricity is I&C aggregator
            assets=assets_df,
            events=events_df,
            services=pd.DataFrame(),
            metadata={'format': 'flexitricity_custom'},
            parse_warnings=[],
            parse_errors=[]
        )

    def _parse_enel(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse ENEL demand data format."""
        logger.info("Using ENEL custom parser")

        xl = pd.ExcelFile(filepath)
        df = pd.read_excel(xl, sheet_name=0)  # Read first sheet

        # Map ENEL columns to standard format
        assets_df = self._standardize_assets(df)

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name="ENEL",
            submission_date=datetime.now(),
            template_version="Custom",
            sector="domestic",
            assets=assets_df,
            events=pd.DataFrame(),
            services=pd.DataFrame(),
            metadata={'format': 'enel_demand'},
            parse_warnings=[],
            parse_errors=[]
        )

    def _parse_octopus(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse Octopus Energy format."""
        logger.info("Using Octopus custom parser")

        xl = pd.ExcelFile(filepath)
        df = pd.read_excel(xl, sheet_name=0)

        assets_df = self._standardize_assets(df)

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name="Octopus",
            submission_date=datetime.now(),
            template_version="Custom",
            sector="domestic",
            assets=assets_df,
            events=pd.DataFrame(),
            services=pd.DataFrame(),
            metadata={'format': 'octopus_response'},
            parse_warnings=[],
            parse_errors=[]
        )

    def _parse_cub(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse C-U-B CLF data format."""
        logger.info("Using C-U-B custom parser")

        xl = pd.ExcelFile(filepath)
        df = pd.read_excel(xl, sheet_name=0)

        assets_df = self._standardize_assets(df)

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name="CUB",
            submission_date=datetime.now(),
            template_version="Custom",
            sector="ic",
            assets=assets_df,
            events=pd.DataFrame(),
            services=pd.DataFrame(),
            metadata={'format': 'cub_clf'},
            parse_warnings=[],
            parse_errors=[]
        )

    def _parse_generic(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Generic parser for unknown formats."""
        logger.warning(f"Using generic parser for {filepath.name}")

        xl = pd.ExcelFile(filepath)
        df = pd.read_excel(xl, sheet_name=0)

        # Try to identify asset and capacity columns
        assets_df = self._standardize_assets(df)

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name=filepath.stem,
            submission_date=datetime.now(),
            template_version="Unknown",
            sector="unknown",
            assets=assets_df,
            events=pd.DataFrame(),
            services=pd.DataFrame(),
            metadata={'format': 'generic'},
            parse_warnings=["Using generic parser - manual review recommended"],
            parse_errors=[]
        )

    def _extract_metadata(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract key-value pairs from metadata sheet."""
        metadata = {}
        for _, row in df.iterrows():
            if pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                key = str(row.iloc[0]).strip().lower().replace(' ', '_')
                metadata[key] = row.iloc[1]
        return metadata

    def _standardize_assets(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize asset dataframe columns."""
        if df.empty:
            return df

        # Normalize column names
        df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')

        # Map common column name variations
        column_mapping = {
            'asset': 'asset_class',
            'type': 'asset_type',
            'capacity': 'capacity_mw',
            'capacity_kw': 'capacity_mw',  # Will need conversion
            'number': 'count',
            'quantity': 'count',
            'dno': 'region',
            'dso': 'region',
        }

        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # Convert kW to MW if needed
        if 'capacity_kw' in df.columns:
            df['capacity_mw'] = df['capacity_kw'] / 1000

        return df

    def _standardize_events(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize events dataframe columns."""
        if df.empty:
            return df

        df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')

        column_mapping = {
            'date': 'event_date',
            'type': 'event_type',
            'service': 'service_type',
            'duration': 'duration_hours',
            'capacity': 'capacity_mw',
            'energy': 'energy_mwh',
        }

        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        return df

    def _standardize_services(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize services dataframe columns."""
        if df.empty:
            return df

        df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')

        return df

    def _infer_sector(self, assets_df: pd.DataFrame) -> str:
        """Infer sector from asset types."""
        if assets_df.empty:
            return "unknown"

        domestic_indicators = {'ev', 'heat_pump', 'battery', 'hot_water'}
        ic_indicators = {'cold_storage', 'manufacturing', 'water_treatment'}

        if 'asset_class' in assets_df.columns:
            asset_types = set(assets_df['asset_class'].str.lower())
            if asset_types & domestic_indicators:
                return "domestic"
            elif asset_types & ic_indicators:
                return "ic"

        return "unknown"


def parse_all_files(data_dir: Path, taxonomy: Dict = None) -> List[ParsedData]:
    """
    Parse all Excel files in a directory.

    Args:
        data_dir: Directory containing data files
        taxonomy: Optional taxonomy for standardization

    Returns:
        List of ParsedData objects
    """
    parser = TemplateParser(taxonomy=taxonomy)
    results = []

    data_dir = Path(data_dir)
    excel_files = list(data_dir.glob("*.xlsx")) + list(data_dir.glob("*.xls"))

    for filepath in excel_files:
        # Skip temporary files
        if filepath.name.startswith('~$'):
            continue

        try:
            result = parser.parse_file(filepath)
            results.append(result)
            logger.info(f"Successfully parsed: {filepath.name}")
        except Exception as e:
            logger.error(f"Failed to parse {filepath.name}: {e}")

    return results
