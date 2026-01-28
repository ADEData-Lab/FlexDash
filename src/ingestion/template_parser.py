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
    sector: str  # 'domestic', 'ic', or 'mixed'

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

        filename = filepath.name.lower()

        # Route to specific parsers based on filename patterns
        if 'flexitricity' in filename:
            return self._parse_flexitricity(filepath, contributor_id)
        elif 'enel' in filename:
            return self._parse_enel(filepath, contributor_id)
        elif 'oe_ade' in filename or 'octopus' in filename:
            return self._parse_octopus(filepath, contributor_id)
        elif 'c-u-b' in filename or 'clf' in filename:
            return self._parse_cub(filepath, contributor_id)
        elif 'axle' in filename:
            return self._parse_axle(filepath, contributor_id)
        elif 'british gas' in filename or 'british_gas' in filename:
            return self._parse_british_gas(filepath, contributor_id)
        elif 'pp ' in filename or 'pod' in filename:
            return self._parse_pod_point(filepath, contributor_id)
        else:
            return self._parse_generic(filepath, contributor_id)

    def _parse_octopus(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse Octopus Energy (OE_ADE_Response) format."""
        logger.info("Using Octopus custom parser")

        df = pd.read_excel(filepath, sheet_name=0, header=0)

        # The Octopus file has 9 columns: [sector], Assets, 7th Dec (Current), 1st Nov, 28 Feb, blank, Description, blank, blank
        # Rename only the columns we need
        col_names = ['sector', 'asset_type', 'count_current', 'count_nov', 'count_feb'] + [f'col_{i}' for i in range(len(df.columns) - 5)]
        df.columns = col_names[:len(df.columns)]
        df = df.dropna(subset=['asset_type'])
        df['sector'] = df['sector'].ffill()

        # Create standardized asset records
        assets = []
        for _, row in df.iterrows():
            if pd.notna(row['asset_type']) and row['asset_type'] != 'Assets':
                asset_class = self._map_asset_type(str(row['asset_type']))
                sector = 'domestic' if str(row.get('sector', '')).lower() == 'domestic' else 'ic'
                count = row.get('count_current', 0)
                try:
                    count = int(float(count)) if pd.notna(count) else 0
                except (ValueError, TypeError):
                    count = 0
                if count > 0:
                    assets.append({
                        'asset_class': asset_class,
                        'sector': sector,
                        'count': count,
                        'capacity_mw': self._estimate_capacity(asset_class, count)
                    })

        assets_df = pd.DataFrame(assets) if assets else pd.DataFrame()

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name="Octopus",
            submission_date=datetime.now(),
            template_version="Custom",
            sector="mixed",
            assets=assets_df,
            events=pd.DataFrame(),
            services=pd.DataFrame(),
            metadata={'format': 'octopus_response'},
            parse_warnings=[],
            parse_errors=[]
        )

    def _parse_enel(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse ENEL demand data format."""
        logger.info("Using ENEL custom parser")

        df = pd.read_excel(filepath, sheet_name=0, header=0)

        # ENEL has: Industry, MWs, Sites
        df.columns = ['industry', 'capacity_mw', 'site_count']
        df = df.dropna(subset=['industry'])

        # Create standardized asset records
        assets = []
        for _, row in df.iterrows():
            if pd.notna(row['industry']) and row['industry'] != 'Industry':
                assets.append({
                    'asset_class': self._map_industry_to_asset(str(row['industry'])),
                    'sector': 'ic',
                    'count': int(row.get('site_count', 1)) if pd.notna(row.get('site_count')) else 1,
                    'capacity_mw': float(row.get('capacity_mw', 0)) if pd.notna(row.get('capacity_mw')) else 0
                })

        assets_df = pd.DataFrame(assets) if assets else pd.DataFrame()

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name="ENEL",
            submission_date=datetime.now(),
            template_version="Custom",
            sector="ic",
            assets=assets_df,
            events=pd.DataFrame(),
            services=pd.DataFrame(),
            metadata={'format': 'enel_demand'},
            parse_warnings=[],
            parse_errors=[]
        )

    def _parse_flexitricity(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse Flexitricity custom format."""
        logger.info("Using Flexitricity custom parser")

        # Flexitricity provides I&C aggregator data
        # Try to extract any capacity data from the file
        try:
            df = pd.read_excel(filepath, sheet_name=0, header=None)

            # Look for capacity values in the data
            assets = []
            total_capacity = 0

            # Search for numeric values that could be capacity
            for col in df.columns:
                for val in df[col]:
                    if isinstance(val, (int, float)) and not pd.isna(val) and 0 < val < 10000:
                        total_capacity += val

            if total_capacity > 0:
                assets.append({
                    'asset_class': 'ic_mixed',
                    'sector': 'ic',
                    'count': 1,
                    'capacity_mw': total_capacity
                })

            assets_df = pd.DataFrame(assets) if assets else pd.DataFrame()

        except Exception as e:
            logger.warning(f"Flexitricity parse error: {e}")
            assets_df = pd.DataFrame()

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name="Flexitricity",
            submission_date=datetime.now(),
            template_version="Custom",
            sector="ic",
            assets=assets_df,
            events=pd.DataFrame(),
            services=pd.DataFrame(),
            metadata={'format': 'flexitricity_custom'},
            parse_warnings=["Flexitricity data requires manual review"],
            parse_errors=[]
        )

    def _parse_cub(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse C-U-B CLF data format.

        C-U-B uses a custom horizontal layout:
        - Part 2 (cols 12-18): Asset portfolio data
        - Part 3 (cols 6-9): Flex MWh data (turn-up/turn-down)

        Note: They provided MWh energy values but no MW capacity.
        We extract asset counts and flag capacity as needing clarification.
        """
        logger.info("Using C-U-B custom parser")

        warnings = []
        errors = []

        try:
            df = pd.read_excel(filepath, sheet_name=0, header=None)

            assets = []

            # Part 2: Look for I&C BESS row (row 20, cols 12-18)
            # Structure: [12]=Sector, [13]=Asset, [15]=Count, [16]=Market%, [17]=WinterCount
            try:
                # Find I&C BESS row - search for 'I&C' in column 12 and 'BESS' in column 13
                for idx in range(15, 35):
                    col12 = df.iloc[idx, 12] if idx < len(df) else None
                    col13 = df.iloc[idx, 13] if idx < len(df) else None

                    if pd.notna(col12) and 'I&C' in str(col12):
                        # Found I&C section
                        if pd.notna(col13) and 'BESS' in str(col13):
                            count = df.iloc[idx, 15]  # No. in portfolio
                            market_share = df.iloc[idx, 16]  # Market share %
                            winter_count = df.iloc[idx, 17]  # Used in winter

                            if pd.notna(count) and float(count) > 0:
                                assets.append({
                                    'asset_class': 'battery',
                                    'sector': 'ic',
                                    'count': int(float(count)),
                                    'market_share_pct': float(market_share) if pd.notna(market_share) else None,
                                    'winter_active_count': int(float(winter_count)) if pd.notna(winter_count) else None,
                                    'capacity_mw': None  # Not provided - needs clarification
                                })
                                logger.info(f"C-U-B: Found I&C BESS with {count} assets")
                                break
            except Exception as e:
                logger.warning(f"C-U-B Part 2 parse error: {e}")

            # Part 3: Look for flex MWh data (rows 40-50, cols 6-9)
            # Structure: [6]=Available Turn-up, [7]=Available Turn-down, [8]=Delivered Turn-up, [9]=Delivered Turn-down
            energy_mwh = {}
            try:
                for idx in range(40, 55):
                    col1 = df.iloc[idx, 1] if idx < len(df) else None
                    col2 = df.iloc[idx, 2] if idx < len(df) else None

                    # Look for I&C BESS row
                    if pd.notna(col1) and 'I&C' in str(col1):
                        if pd.notna(col2) and 'BESS' in str(col2):
                            avail_up = df.iloc[idx, 6]
                            avail_down = df.iloc[idx, 7]
                            deliv_up = df.iloc[idx, 8]
                            deliv_down = df.iloc[idx, 9]

                            energy_mwh = {
                                'available_turn_up_mwh': float(avail_up) if pd.notna(avail_up) else 0,
                                'available_turn_down_mwh': float(avail_down) if pd.notna(avail_down) else 0,
                                'delivered_turn_up_mwh': float(deliv_up) if pd.notna(deliv_up) else 0,
                                'delivered_turn_down_mwh': float(deliv_down) if pd.notna(deliv_down) else 0
                            }
                            logger.info(f"C-U-B: Found flex data - Available down: {energy_mwh['available_turn_down_mwh']} MWh")
                            break
            except Exception as e:
                logger.warning(f"C-U-B Part 3 parse error: {e}")

            # Create assets DataFrame
            if assets:
                # Add energy data to first asset
                if energy_mwh:
                    assets[0].update(energy_mwh)
                assets_df = pd.DataFrame(assets)

                # Add warning about missing MW capacity
                warnings.append("C-U-B provided MWh energy values but no MW capacity - clarification requested")
                warnings.append(f"Extracted: {assets[0].get('count', 0)} I&C BESS assets, {energy_mwh.get('available_turn_down_mwh', 0)} MWh available turn-down")
            else:
                assets_df = pd.DataFrame()
                errors.append("Could not extract asset data from C-U-B custom format")

        except Exception as e:
            logger.warning(f"C-U-B parse error: {e}")
            assets_df = pd.DataFrame()
            errors.append(f"Parse error: {str(e)}")

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name="CUB",
            submission_date=datetime.now(),
            template_version="Custom",
            sector="ic",
            assets=assets_df,
            events=pd.DataFrame(),
            services=pd.DataFrame(),
            metadata={
                'format': 'cub_clf',
                'capacity_mw_missing': True,
                'energy_mwh_provided': bool(energy_mwh) if 'energy_mwh' in dir() else False
            },
            parse_warnings=warnings or ["C-U-B data requires manual review"],
            parse_errors=errors
        )

    def _parse_axle(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse Axle data format (ADE template V1.2)."""
        logger.info("Using Axle custom parser")
        return self._parse_ade_template(filepath, contributor_id, "Axle", "domestic")

    def _parse_british_gas(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse British Gas data format (ADE template V1.2)."""
        logger.info("Using British Gas custom parser")
        return self._parse_ade_template(filepath, contributor_id, "BritishGas", "domestic")

    def _parse_pod_point(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse Pod Point data format (ADE template V1.2)."""
        logger.info("Using Pod Point custom parser")
        return self._parse_ade_template(filepath, contributor_id, "PodPoint", "domestic")

    def _parse_ade_template(self, filepath: Path, contributor_id: str, name: str, default_sector: str) -> ParsedData:
        """Parse ADE template V1.2 format with complex structure."""
        try:
            df = pd.read_excel(filepath, sheet_name=0, header=None)

            assets = []

            # Look for the "Assets" row which contains headers
            asset_row_idx = None
            for idx, row in df.iterrows():
                row_str = ' '.join([str(v) for v in row if pd.notna(v)]).lower()
                if 'assets' in row_str and 'portfolio' in row_str:
                    asset_row_idx = idx
                    break

            if asset_row_idx is not None:
                # Parse asset data below the header
                for idx in range(asset_row_idx + 1, min(asset_row_idx + 20, len(df))):
                    row = df.iloc[idx]
                    # Look for asset type in column 12 (typical template position)
                    asset_type = None
                    count = None

                    for col_idx, val in enumerate(row):
                        if pd.notna(val):
                            val_str = str(val).lower()
                            # Check for known asset types
                            if any(at in val_str for at in ['ev', 'charger', 'heat pump', 'battery', 'bess', 'storage']):
                                asset_type = val_str
                            # Check for numeric counts
                            elif isinstance(val, (int, float)) and 0 < val < 10000000:
                                count = int(val)

                    if asset_type and count:
                        asset_class = self._map_asset_type(asset_type)
                        assets.append({
                            'asset_class': asset_class,
                            'sector': default_sector,
                            'count': count,
                            'capacity_mw': self._estimate_capacity(asset_class, count)
                        })

            # If no assets found via structure, try to find any EV charger counts
            if not assets:
                for idx, row in df.iterrows():
                    for col_idx, val in enumerate(row):
                        if isinstance(val, (int, float)) and not pd.isna(val) and 1000 < val < 10000000:
                            # Large number might be EV charger count
                            assets.append({
                                'asset_class': 'ev_charger',
                                'sector': default_sector,
                                'count': int(val),
                                'capacity_mw': self._estimate_capacity('ev_charger', int(val))
                            })
                            break
                    if assets:
                        break

            assets_df = pd.DataFrame(assets) if assets else pd.DataFrame()

        except Exception as e:
            logger.warning(f"{name} parse error: {e}")
            assets_df = pd.DataFrame()

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name=name,
            submission_date=datetime.now(),
            template_version="V1.2",
            sector=default_sector,
            assets=assets_df,
            events=pd.DataFrame(),
            services=pd.DataFrame(),
            metadata={'format': 'ade_template_v1.2'},
            parse_warnings=[],
            parse_errors=[]
        )

    def _parse_generic(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Generic parser for unknown formats."""
        logger.warning(f"Using generic parser for {filepath.name}")

        try:
            df = pd.read_excel(filepath, sheet_name=0, header=None)

            # Try to extract any meaningful data
            assets = []
            for idx, row in df.iterrows():
                for val in row:
                    if isinstance(val, (int, float)) and not pd.isna(val) and 100 < val < 10000000:
                        assets.append({
                            'asset_class': 'unknown',
                            'sector': 'unknown',
                            'count': int(val) if val > 100 else 1,
                            'capacity_mw': float(val) if val < 10000 else self._estimate_capacity('ev_charger', int(val))
                        })
                        break
                if assets:
                    break

            assets_df = pd.DataFrame(assets) if assets else pd.DataFrame()

        except Exception as e:
            logger.warning(f"Generic parse error: {e}")
            assets_df = pd.DataFrame()

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

    def _map_asset_type(self, raw_type: str) -> str:
        """Map raw asset type string to standardized asset class."""
        raw_lower = raw_type.lower()

        if any(x in raw_lower for x in ['ev', 'charger', 'vehicle']):
            return 'ev_charger'
        elif any(x in raw_lower for x in ['heat pump', 'hp', 'ashp', 'gshp']):
            return 'heat_pump'
        elif any(x in raw_lower for x in ['cold', 'refriger', 'freezer']):
            return 'cold_storage'
        elif any(x in raw_lower for x in ['bess', 'battery', 'storage']):
            return 'battery_storage'
        elif any(x in raw_lower for x in ['hot water', 'immersion', 'heater']):
            return 'smart_hot_water'
        elif any(x in raw_lower for x in ['water treatment', 'sewage', 'wastewater']):
            return 'water_treatment'
        elif any(x in raw_lower for x in ['manufactur', 'industrial', 'factory']):
            return 'manufacturing'
        elif any(x in raw_lower for x in ['hvac', 'air condition', 'cooling']):
            return 'commercial_hvac'
        else:
            return 'other'

    def _map_industry_to_asset(self, industry: str) -> str:
        """Map ENEL industry type to asset class."""
        ind_lower = industry.lower()

        if 'food' in ind_lower or 'drink' in ind_lower:
            return 'cold_storage'
        elif 'water' in ind_lower:
            return 'water_treatment'
        elif 'manufact' in ind_lower or 'metal' in ind_lower:
            return 'manufacturing'
        elif 'chemical' in ind_lower:
            return 'manufacturing'
        elif 'energy' in ind_lower:
            return 'commercial_battery'
        elif 'recycl' in ind_lower:
            return 'manufacturing'
        else:
            return 'ic_mixed'

    def _estimate_capacity(self, asset_class: str, count: int) -> float:
        """Estimate MW capacity from asset count using typical ratings."""
        # Typical capacity per unit in kW
        typical_kw = {
            'ev_charger': 7.0,  # Average of 3.6-22 kW
            'heat_pump': 5.0,  # Average domestic HP
            'battery_storage': 5.0,  # Average home battery
            'smart_hot_water': 3.0,
            'cold_storage': 100.0,  # Per site
            'water_treatment': 500.0,  # Per site
            'manufacturing': 200.0,  # Per site
            'commercial_hvac': 50.0,
            'commercial_battery': 100.0,
            'ic_mixed': 100.0,
            'other': 5.0,
            'unknown': 5.0
        }

        kw_per_unit = typical_kw.get(asset_class, 5.0)
        return (count * kw_per_unit) / 1000  # Convert to MW


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
        # Skip temporary files and files in Notes subfolder
        if filepath.name.startswith('~$'):
            continue
        if 'notes' in str(filepath.parent).lower():
            continue

        try:
            result = parser.parse_file(filepath)
            results.append(result)
            logger.info(f"Successfully parsed: {filepath.name}")
        except Exception as e:
            logger.error(f"Failed to parse {filepath.name}: {e}")

    return results
