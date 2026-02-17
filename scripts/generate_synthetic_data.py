"""
Generate 15 synthetic provider datasets following ADE Data Template V1.2.

This creates fictional but realistic flexibility data for public demonstration
of the ADE Flex Dashboard without exposing confidential contributor data.

Usage:
    python scripts/generate_synthetic_data.py

Output:
    data/synthetic/SYNTH_*.xlsx (15 files)
"""

import copy
import random
from pathlib import Path
from typing import Dict, List, Any, Optional

import numpy as np
from openpyxl import load_workbook

# Seed for reproducibility
random.seed(42)
np.random.seed(42)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATE_PATH = PROJECT_ROOT.parent / "DATA REQUEST FORMS" / "Data Template V1.2.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "data" / "synthetic"


# =============================================================================
# Template Structure (from analysis of Data Template V1.2.xlsx)
# =============================================================================

# Part 1: Company info
PART1_NAME_ROW = 4
PART1_NAME_COL = 5  # Column E (after "Company name" label)
PART1_TYPE_ROW = 13
PART1_TYPE_COL = 5  # Column E (after "Company type" label)

# Part 2: Managed assets (Row 10 is header, data starts row 11)
# BUT - the template shows assets in rows 11-35 with predefined types
# Sector in col 13 (M), Asset type col 14 (N), Portfolio col 16 (P),
# Market share col 17 (Q), Winter active col 18 (R), Remarks col 19 (S)
PART2_START_ROW = 11
PART2_SECTOR_COL = 13      # M - Actually this shows category like "Domestic"
PART2_ASSET_COL = 14       # N - Asset type like "BESS"
PART2_PORTFOLIO_COL = 16   # P - No. in portfolio
PART2_SHARE_COL = 17       # Q - Market share
PART2_WINTER_COL = 18      # R - No. used in winter 2024-25
PART2_REMARKS_COL = 19     # S - Remarks

# Part 3.1: Energy MWh (Row 41 header, data rows 42+)
# Asset col 2 (B), Turn-up avail col 7 (G), Turn-down avail col 8 (H),
# Turn-up deliv col 9 (I), Turn-down deliv col 10 (J)
PART31_START_ROW = 42
PART31_ASSET_COL = 2
PART31_AVAIL_UP_COL = 7
PART31_AVAIL_DOWN_COL = 8
PART31_DELIV_UP_COL = 9
PART31_DELIV_DOWN_COL = 10

# Part 3.2: Capacity MW (Row 58 header, data rows 59+)
# Same column structure as 3.1
PART32_START_ROW = 59
PART32_ASSET_COL = 2
PART32_AVAIL_UP_COL = 7
PART32_AVAIL_DOWN_COL = 8
PART32_DELIV_UP_COL = 9
PART32_DELIV_DOWN_COL = 10

# Part 4: ToU tariffs
# 4.1 Tariff info (row 77 header, data row 78+)
# Tariff name col 2 (B), Sector col 6 (F), Asset col 9 (I),
# Static/Dynamic col 12 (L), Customers col 18 (R)
PART41_START_ROW = 78
PART41_NAME_COL = 2
PART41_SECTOR_COL = 6
PART41_ASSET_COL = 9
PART41_TYPE_COL = 12
PART41_CUSTOMERS_COL = 18

# 4.2 Total MWh (row 95 header, data row 96+)
# Tariff name col 2, Turn-down col 6 (F), Turn-up col 8 (H)
PART42_START_ROW = 96
PART42_NAME_COL = 2
PART42_DOWN_COL = 6
PART42_UP_COL = 8

# 4.3 Busiest half-hour (around row 110)
# Tariff name col 2, Down MWh col 6, Up MWh col 8, Down MW col 10, Up MW col 12
PART43_START_ROW = 112
PART43_NAME_COL = 2
PART43_DOWN_MWH_COL = 6
PART43_UP_MWH_COL = 8
PART43_DOWN_MW_COL = 10
PART43_UP_MW_COL = 12


# =============================================================================
# Provider Definitions
# =============================================================================

PROVIDERS = [
    {
        "id": 1,
        "name": "GreenCharge Home Solutions",
        "filename": "SYNTH_01_GreenChargeHomeSolutions",
        "type": "Supplier",
        "sector": "domestic",
        "flex_type": "implicit",
        "assets": [
            {"sector": "Domestic", "asset_class": "EV charger", "portfolio": 120000, "winter_active": 95000},
        ],
        "tou_tariffs": [
            {
                "name": "NightDrive Economy",
                "target_sector": "Domestic",
                "target_asset": "EV",
                "tariff_type": "Static",
                "customers": 85000,
                "total_turn_down_mwh": 12000,
                "total_turn_up_mwh": 8500,
                "busiest_hh_turn_down_mw": 320,
                "busiest_hh_turn_up_mw": 180,
            }
        ],
    },
    {
        "id": 2,
        "name": "Voltpoint Networks",
        "filename": "SYNTH_02_VoltpointNetworks",
        "type": "Aggregator",
        "sector": "ic",
        "flex_type": "explicit",
        "assets": [
            {"sector": "I&C", "asset_class": "EV charger", "portfolio": 5000, "winter_active": 4500,
             "avail_turn_up_mw": 30, "avail_turn_down_mw": 110, "deliv_turn_up_mw": 15, "deliv_turn_down_mw": 85,
             "avail_turn_up_mwh": 800, "avail_turn_down_mwh": 2400, "deliv_turn_up_mwh": 400, "deliv_turn_down_mwh": 1800},
        ],
    },
    {
        "id": 3,
        "name": "HomePower Storage",
        "filename": "SYNTH_03_HomePowerStorage",
        "type": "Aggregator",
        "sector": "domestic",
        "flex_type": "explicit",
        "assets": [
            {"sector": "Domestic", "asset_class": "BESS", "portfolio": 25000, "winter_active": 23500,
             "avail_turn_up_mw": 60, "avail_turn_down_mw": 60, "deliv_turn_up_mw": 45, "deliv_turn_down_mw": 40,
             "avail_turn_up_mwh": 180, "avail_turn_down_mwh": 180, "deliv_turn_up_mwh": 120, "deliv_turn_down_mwh": 110},
        ],
    },
    {
        "id": 4,
        "name": "BritishFlex Energy",
        "filename": "SYNTH_04_BritishFlexEnergy",
        "type": "Supplier",
        "sector": "mixed",
        "flex_type": "mixed",
        "assets": [
            {"sector": "Domestic", "asset_class": "EV charger", "portfolio": 180000, "winter_active": 145000,
             "avail_turn_down_mw": 400, "deliv_turn_down_mw": 280,
             "avail_turn_down_mwh": 8000, "deliv_turn_down_mwh": 5600},
            {"sector": "Domestic", "asset_class": "Heat pump", "portfolio": 85000, "winter_active": 78000,
             "avail_turn_down_mw": 300, "deliv_turn_down_mw": 200,
             "avail_turn_down_mwh": 6000, "deliv_turn_down_mwh": 4000},
            {"sector": "Domestic", "asset_class": "BESS", "portfolio": 35000, "winter_active": 32000,
             "avail_turn_up_mw": 100, "avail_turn_down_mw": 100, "deliv_turn_up_mw": 70, "deliv_turn_down_mw": 65,
             "avail_turn_up_mwh": 300, "avail_turn_down_mwh": 300, "deliv_turn_up_mwh": 200, "deliv_turn_down_mwh": 190},
        ],
        "tou_tariffs": [
            {
                "name": "FlexHome Saver",
                "target_sector": "Domestic",
                "target_asset": "Mixed",
                "tariff_type": "Dynamic",
                "customers": 200000,
                "total_turn_down_mwh": 15000,
                "total_turn_up_mwh": 12000,
                "busiest_hh_turn_down_mw": 400,
                "busiest_hh_turn_up_mw": 320,
            }
        ],
    },
    {
        "id": 5,
        "name": "FlexGrid Aggregation",
        "filename": "SYNTH_05_FlexGridAggregation",
        "type": "Aggregator",
        "sector": "ic",
        "flex_type": "explicit",
        "assets": [
            {"sector": "I&C", "asset_class": "Cold storage", "portfolio": 45, "winter_active": 42,
             "avail_turn_down_mw": 90, "deliv_turn_down_mw": 70,
             "avail_turn_down_mwh": 1800, "deliv_turn_down_mwh": 1400},
            {"sector": "I&C", "asset_class": "Water treatment", "portfolio": 35, "winter_active": 32,
             "avail_turn_down_mw": 120, "deliv_turn_down_mw": 90,
             "avail_turn_down_mwh": 2400, "deliv_turn_down_mwh": 1800},
            {"sector": "I&C", "asset_class": "Manufacturing", "portfolio": 70, "winter_active": 58,
             "avail_turn_down_mw": 140, "deliv_turn_down_mw": 100,
             "avail_turn_down_mwh": 2800, "deliv_turn_down_mwh": 2000},
        ],
    },
    {
        "id": 6,
        "name": "EcoHeat Supplier",
        "filename": "SYNTH_06_EcoHeatSupplier",
        "type": "Supplier",
        "sector": "domestic",
        "flex_type": "implicit",
        "assets": [
            {"sector": "Domestic", "asset_class": "Heat pump", "portfolio": 25000, "winter_active": 22000},
            {"sector": "Domestic", "asset_class": "EV charger", "portfolio": 8000, "winter_active": 6500},
        ],
        "tou_tariffs": [
            {
                "name": "HeatSmart Tariff",
                "target_sector": "Domestic",
                "target_asset": "Heat Pump",
                "tariff_type": "Static",
                "customers": 22000,
                "total_turn_down_mwh": 3500,
                "total_turn_up_mwh": 2800,
                "busiest_hh_turn_down_mw": 120,
                "busiest_hh_turn_up_mw": 95,
            },
            {
                "name": "EV Night Saver",
                "target_sector": "Domestic",
                "target_asset": "EV",
                "tariff_type": "Static",
                "customers": 6000,
                "total_turn_down_mwh": 1200,
                "total_turn_up_mwh": 900,
                "busiest_hh_turn_down_mw": 40,
                "busiest_hh_turn_up_mw": 30,
            }
        ],
    },
    {
        "id": 7,
        "name": "Midlands Power Networks",
        "filename": "SYNTH_07_MidlandsPowerNetworks",
        "type": "DSO",
        "sector": "ic",
        "flex_type": "explicit",
        "assets": [
            {"sector": "I&C", "asset_class": "Cold storage", "portfolio": 25, "winter_active": 22,
             "avail_turn_down_mw": 25, "deliv_turn_down_mw": 18,
             "avail_turn_down_mwh": 500, "deliv_turn_down_mwh": 360},
            {"sector": "I&C", "asset_class": "Manufacturing", "portfolio": 30, "winter_active": 25,
             "avail_turn_down_mw": 30, "deliv_turn_down_mw": 20,
             "avail_turn_down_mwh": 600, "deliv_turn_down_mwh": 400},
            {"sector": "I&C", "asset_class": "Commercial BESS", "portfolio": 15, "winter_active": 14,
             "avail_turn_up_mw": 20, "avail_turn_down_mw": 20, "deliv_turn_up_mw": 12, "deliv_turn_down_mw": 10,
             "avail_turn_up_mwh": 60, "avail_turn_down_mwh": 60, "deliv_turn_up_mwh": 36, "deliv_turn_down_mwh": 30},
        ],
    },
    {
        "id": 8,
        "name": "GB System Services",
        "filename": "SYNTH_08_GBSystemServices",
        "type": "Aggregator",
        "sector": "mixed",
        "flex_type": "explicit",
        "assets": [
            {"sector": "Domestic", "asset_class": "BESS", "portfolio": 45000, "winter_active": 40000,
             "avail_turn_up_mw": 150, "avail_turn_down_mw": 150, "deliv_turn_up_mw": 100, "deliv_turn_down_mw": 95,
             "avail_turn_up_mwh": 450, "avail_turn_down_mwh": 450, "deliv_turn_up_mwh": 300, "deliv_turn_down_mwh": 285},
            {"sector": "I&C", "asset_class": "Commercial BESS", "portfolio": 80, "winter_active": 75,
             "avail_turn_up_mw": 200, "avail_turn_down_mw": 200, "deliv_turn_up_mw": 140, "deliv_turn_down_mw": 130,
             "avail_turn_up_mwh": 600, "avail_turn_down_mwh": 600, "deliv_turn_up_mwh": 420, "deliv_turn_down_mwh": 390},
            {"sector": "I&C", "asset_class": "Manufacturing", "portfolio": 50, "winter_active": 42,
             "avail_turn_down_mw": 100, "deliv_turn_down_mw": 70,
             "avail_turn_down_mwh": 2000, "deliv_turn_down_mwh": 1400},
        ],
    },
    {
        "id": 9,
        "name": "FlexMatch Platform",
        "filename": "SYNTH_09_FlexMatchPlatform",
        "type": "Aggregator",
        "sector": "mixed",
        "flex_type": "mixed",
        "assets": [
            {"sector": "Domestic", "asset_class": "EV charger", "portfolio": 35000, "winter_active": 28000,
             "avail_turn_down_mw": 80, "deliv_turn_down_mw": 55,
             "avail_turn_down_mwh": 1600, "deliv_turn_down_mwh": 1100},
            {"sector": "Domestic", "asset_class": "BESS", "portfolio": 15000, "winter_active": 13500,
             "avail_turn_up_mw": 50, "avail_turn_down_mw": 50, "deliv_turn_up_mw": 35, "deliv_turn_down_mw": 32,
             "avail_turn_up_mwh": 150, "avail_turn_down_mwh": 150, "deliv_turn_up_mwh": 100, "deliv_turn_down_mwh": 96},
        ],
        "tou_tariffs": [
            {
                "name": "FlexMatch Dynamic",
                "target_sector": "Domestic",
                "target_asset": "Mixed",
                "tariff_type": "Dynamic",
                "customers": 40000,
                "total_turn_down_mwh": 4000,
                "total_turn_up_mwh": 3200,
                "busiest_hh_turn_down_mw": 100,
                "busiest_hh_turn_up_mw": 80,
            }
        ],
    },
    {
        "id": 10,
        "name": "Industrial Response Ltd",
        "filename": "SYNTH_10_IndustrialResponseLtd",
        "type": "Aggregator",
        "sector": "ic",
        "flex_type": "explicit",
        "assets": [
            {"sector": "I&C", "asset_class": "Cold storage", "portfolio": 65, "winter_active": 58,
             "avail_turn_down_mw": 130, "deliv_turn_down_mw": 100,
             "avail_turn_down_mwh": 2600, "deliv_turn_down_mwh": 2000},
            {"sector": "I&C", "asset_class": "Water treatment", "portfolio": 50, "winter_active": 45,
             "avail_turn_down_mw": 150, "deliv_turn_down_mw": 110,
             "avail_turn_down_mwh": 3000, "deliv_turn_down_mwh": 2200},
            {"sector": "I&C", "asset_class": "Manufacturing", "portfolio": 85, "winter_active": 70,
             "avail_turn_down_mw": 140, "deliv_turn_down_mw": 95,
             "avail_turn_down_mwh": 2800, "deliv_turn_down_mwh": 1900},
        ],
    },
    {
        "id": 11,
        "name": "WarmHome Tech",
        "filename": "SYNTH_11_WarmHomeTech",
        "type": "Supplier",
        "sector": "domestic",
        "flex_type": "implicit",
        "assets": [
            {"sector": "Domestic", "asset_class": "Heat pump", "portfolio": 60000, "winter_active": 52000},
        ],
        "tou_tariffs": [
            {
                "name": "Cosy Home",
                "target_sector": "Domestic",
                "target_asset": "Heat Pump",
                "tariff_type": "Dynamic",
                "customers": 48000,
                "total_turn_down_mwh": 8000,
                "total_turn_up_mwh": 6500,
                "busiest_hh_turn_down_mw": 260,
                "busiest_hh_turn_up_mw": 210,
            }
        ],
    },
    {
        "id": 12,
        "name": "Heritage Heating",
        "filename": "SYNTH_12_HeritageHeating",
        "type": "Supplier",
        "sector": "domestic",
        "flex_type": "implicit",
        "assets": [
            {"sector": "Domestic", "asset_class": "Storage heater", "portfolio": 200000, "winter_active": 180000},
        ],
        "tou_tariffs": [
            {
                "name": "Economy 7 Plus",
                "target_sector": "Domestic",
                "target_asset": "Storage Heater",
                "tariff_type": "Static",
                "customers": 175000,
                "total_turn_down_mwh": 25000,
                "total_turn_up_mwh": 20000,
                "busiest_hh_turn_down_mw": 500,
                "busiest_hh_turn_up_mw": 400,
            }
        ],
    },
    {
        "id": 13,
        "name": "GridScale Batteries",
        "filename": "SYNTH_13_GridScaleBatteries",
        "type": "Aggregator",
        "sector": "ic",
        "flex_type": "explicit",
        "assets": [
            {"sector": "I&C", "asset_class": "Commercial BESS", "portfolio": 50, "winter_active": 48,
             "avail_turn_up_mw": 125, "avail_turn_down_mw": 125, "deliv_turn_up_mw": 90, "deliv_turn_down_mw": 85,
             "avail_turn_up_mwh": 375, "avail_turn_down_mwh": 375, "deliv_turn_up_mwh": 270, "deliv_turn_down_mwh": 255},
        ],
    },
    {
        "id": 14,
        "name": "Riverside Energy Co-op",
        "filename": "SYNTH_14_RiversideEnergyCoop",
        "type": "Community",
        "sector": "domestic",
        "flex_type": "mixed",
        "assets": [
            {"sector": "Domestic", "asset_class": "EV charger", "portfolio": 2500, "winter_active": 2100,
             "avail_turn_down_mw": 8, "deliv_turn_down_mw": 5,
             "avail_turn_down_mwh": 160, "deliv_turn_down_mwh": 100},
            {"sector": "Domestic", "asset_class": "BESS", "portfolio": 1800, "winter_active": 1650,
             "avail_turn_up_mw": 6, "avail_turn_down_mw": 6, "deliv_turn_up_mw": 4, "deliv_turn_down_mw": 4,
             "avail_turn_up_mwh": 18, "avail_turn_down_mwh": 18, "deliv_turn_up_mwh": 12, "deliv_turn_down_mwh": 12},
            {"sector": "Domestic", "asset_class": "Heat pump", "portfolio": 1200, "winter_active": 1050,
             "avail_turn_down_mw": 5, "deliv_turn_down_mw": 3,
             "avail_turn_down_mwh": 100, "deliv_turn_down_mwh": 60},
        ],
        "tou_tariffs": [
            {
                "name": "Community Flex",
                "target_sector": "Domestic",
                "target_asset": "Mixed",
                "tariff_type": "Dynamic",
                "customers": 4500,
                "total_turn_down_mwh": 450,
                "total_turn_up_mwh": 350,
                "busiest_hh_turn_down_mw": 11,
                "busiest_hh_turn_up_mw": 9,
            }
        ],
    },
    {
        "id": 15,
        "name": "FleetPower V2G",
        "filename": "SYNTH_15_FleetPowerV2G",
        "type": "Aggregator",
        "sector": "ic",
        "flex_type": "explicit",
        "assets": [
            {"sector": "I&C", "asset_class": "EV fleet", "portfolio": 8000, "winter_active": 7200,
             "avail_turn_up_mw": 60, "avail_turn_down_mw": 60, "deliv_turn_up_mw": 40, "deliv_turn_down_mw": 45,
             "avail_turn_up_mwh": 180, "avail_turn_down_mwh": 180, "deliv_turn_up_mwh": 120, "deliv_turn_down_mwh": 135},
        ],
    },
]


def safe_write(ws, row: int, col: int, value):
    """Write to a cell, handling merged cells by writing to the top-left."""
    cell = ws.cell(row=row, column=col)
    coord = cell.coordinate

    # Check if this cell is part of a merged range
    for merged_range in list(ws.merged_cells.ranges):
        if coord in merged_range:
            # Get the top-left cell of the merge
            min_col, min_row, max_col, max_row = merged_range.bounds
            # Write to the top-left cell
            ws.cell(row=min_row, column=min_col).value = value
            return

    # Not merged, write directly
    cell.value = value


def write_provider_file(provider: Dict, template_path: Path, output_path: Path):
    """Generate a synthetic data file for one provider."""

    # Load template
    wb = load_workbook(template_path)
    ws = wb.active

    # --- Part 1: Company metadata ---
    # C4:I4 is merged for company name - write to C4
    safe_write(ws, 4, 3, provider["name"])  # C4
    # C13:I14 is merged for company type - write to C13
    safe_write(ws, 13, 3, provider["type"])  # C13

    # --- Part 2: Managed assets ---
    # Map asset classes to template row positions
    # The template has predefined rows for each asset type
    ASSET_ROW_MAP = {
        # Domestic
        "EV charger": 11,
        "Heat pump": 12,
        "BESS": 14,
        "Storage heater": 15,
        "Smart hot water": 16,
        "Wet appliances": 17,
        # I&C
        "Cold storage": 22,
        "Water treatment": 23,
        "Manufacturing": 24,
        "Commercial HVAC": 25,
        "Commercial BESS": 26,
        "Backup generation": 27,
        "EV fleet": 28,
    }

    for asset in provider.get("assets", []):
        asset_class = asset.get("asset_class", "")
        row = ASSET_ROW_MAP.get(asset_class)
        if row:
            safe_write(ws, row, PART2_PORTFOLIO_COL, asset.get("portfolio"))
            safe_write(ws, row, PART2_WINTER_COL, asset.get("winter_active"))
            if asset.get("market_share"):
                safe_write(ws, row, PART2_SHARE_COL, asset.get("market_share"))

    # --- Part 3.1: Energy MWh ---
    part31_row = PART31_START_ROW
    for asset in provider.get("assets", []):
        if any(k.endswith("_mwh") for k in asset.keys()):
            safe_write(ws, part31_row, PART31_ASSET_COL, asset.get("asset_class"))
            if asset.get("avail_turn_up_mwh") is not None:
                safe_write(ws, part31_row, PART31_AVAIL_UP_COL, asset.get("avail_turn_up_mwh"))
            if asset.get("avail_turn_down_mwh") is not None:
                safe_write(ws, part31_row, PART31_AVAIL_DOWN_COL, asset.get("avail_turn_down_mwh"))
            if asset.get("deliv_turn_up_mwh") is not None:
                safe_write(ws, part31_row, PART31_DELIV_UP_COL, asset.get("deliv_turn_up_mwh"))
            if asset.get("deliv_turn_down_mwh") is not None:
                safe_write(ws, part31_row, PART31_DELIV_DOWN_COL, asset.get("deliv_turn_down_mwh"))
            part31_row += 1

    # --- Part 3.2: Capacity MW ---
    part32_row = PART32_START_ROW
    for asset in provider.get("assets", []):
        if any(k.endswith("_mw") for k in asset.keys()):
            safe_write(ws, part32_row, PART32_ASSET_COL, asset.get("asset_class"))
            if asset.get("avail_turn_up_mw") is not None:
                safe_write(ws, part32_row, PART32_AVAIL_UP_COL, asset.get("avail_turn_up_mw"))
            if asset.get("avail_turn_down_mw") is not None:
                safe_write(ws, part32_row, PART32_AVAIL_DOWN_COL, asset.get("avail_turn_down_mw"))
            if asset.get("deliv_turn_up_mw") is not None:
                safe_write(ws, part32_row, PART32_DELIV_UP_COL, asset.get("deliv_turn_up_mw"))
            if asset.get("deliv_turn_down_mw") is not None:
                safe_write(ws, part32_row, PART32_DELIV_DOWN_COL, asset.get("deliv_turn_down_mw"))
            part32_row += 1

    # --- Part 4: ToU Tariffs ---
    tou_tariffs = provider.get("tou_tariffs", [])
    if tou_tariffs:
        # 4.1 Tariff info
        part41_row = PART41_START_ROW
        for tariff in tou_tariffs:
            safe_write(ws, part41_row, PART41_NAME_COL, tariff.get("name"))
            safe_write(ws, part41_row, PART41_SECTOR_COL, tariff.get("target_sector"))
            safe_write(ws, part41_row, PART41_ASSET_COL, tariff.get("target_asset"))
            safe_write(ws, part41_row, PART41_TYPE_COL, tariff.get("tariff_type"))
            safe_write(ws, part41_row, PART41_CUSTOMERS_COL, tariff.get("customers"))
            part41_row += 1

        # 4.2 Total MWh
        part42_row = PART42_START_ROW
        for tariff in tou_tariffs:
            safe_write(ws, part42_row, PART42_NAME_COL, tariff.get("name"))
            safe_write(ws, part42_row, PART42_DOWN_COL, tariff.get("total_turn_down_mwh"))
            safe_write(ws, part42_row, PART42_UP_COL, tariff.get("total_turn_up_mwh"))
            part42_row += 1

        # 4.3 Busiest half-hour
        part43_row = PART43_START_ROW
        for tariff in tou_tariffs:
            safe_write(ws, part43_row, PART43_NAME_COL, tariff.get("name"))
            # Convert MW to MWh for half-hour (MW * 0.5)
            down_mw = tariff.get("busiest_hh_turn_down_mw", 0)
            up_mw = tariff.get("busiest_hh_turn_up_mw", 0)
            safe_write(ws, part43_row, PART43_DOWN_MWH_COL, down_mw * 0.5 if down_mw else None)
            safe_write(ws, part43_row, PART43_UP_MWH_COL, up_mw * 0.5 if up_mw else None)
            safe_write(ws, part43_row, PART43_DOWN_MW_COL, down_mw)
            safe_write(ws, part43_row, PART43_UP_MW_COL, up_mw)
            part43_row += 1

    # Save
    wb.save(output_path)
    print(f"  Created: {output_path.name}")


def main():
    """Generate all synthetic data files."""
    print("=" * 60)
    print("FlexDash Synthetic Data Generator")
    print("=" * 60)

    # Verify template exists
    if not TEMPLATE_PATH.exists():
        print(f"ERROR: Template not found at {TEMPLATE_PATH}")
        return 1

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nTemplate: {TEMPLATE_PATH}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"\nGenerating {len(PROVIDERS)} synthetic provider files...\n")

    # Generate each provider file
    for provider in PROVIDERS:
        output_file = OUTPUT_DIR / f"{provider['filename']}.xlsx"
        write_provider_file(provider, TEMPLATE_PATH, output_file)

    # Create README
    readme_path = OUTPUT_DIR / "README.md"
    readme_content = """# Synthetic Demonstration Data

This directory contains **fictional** flexibility data for demonstration purposes.

## Important Notice

**All data in this directory is synthetic and does not represent any real organisation.**

The provider names, values, and all other data are entirely fictional and were
generated to demonstrate the ADE Flex Dashboard functionality without exposing
any confidential contributor data.

## Contents

15 synthetic provider files following the ADE Data Template V1.2 format:

| Provider | Type | Sector | Primary Assets |
|----------|------|--------|----------------|
"""

    for p in PROVIDERS:
        assets = ", ".join(a["asset_class"] for a in p.get("assets", []))
        readme_content += f"| {p['name']} | {p['type']} | {p['sector']} | {assets} |\n"

    readme_content += """
## Total Synthetic Capacity

Approximately 5 GW of flexibility across domestic and I&C sectors.

## Usage

This data is processed by the FlexDash pipeline using:

```bash
python scripts/run_pipeline.py --config config/settings_synthetic.yaml
```

---

*Generated by generate_synthetic_data.py*
"""

    readme_path.write_text(readme_content)
    print(f"\n  Created: README.md")

    print("\n" + "=" * 60)
    print("Generation complete!")
    print(f"Files created: {len(PROVIDERS)} provider files + README")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
