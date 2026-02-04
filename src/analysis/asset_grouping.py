"""
Asset grouping helpers for disclosure-safe public reporting.

The public dashboard can struggle to show capacity by detailed asset class because:
  - many contributors omit MW in Template V1.2 section 3.2 (capacity treated as missing)
  - k-anonymity and dominance rules suppress small-N cells

Grouping asset classes into broader categories can increase k and reduce disaggregation risk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd


DEFAULT_GROUP_MAP: Dict[str, str] = {
    "ev_charger": "EV charging",
    "ev_fleet": "EV charging",
    "heat_pump": "Heat",
    "heat_network_thermal": "Heat",
    "storage_heater": "Heat",
    "smart_hot_water": "Heat",
    "commercial_hvac": "Heat",
    "battery_storage": "Battery storage",
    "commercial_battery": "Battery storage",
    "battery": "Battery storage",
    "cold_storage": "I&C load/process",
    "water_treatment": "I&C load/process",
    "manufacturing": "I&C load/process",
    "industrial_load": "I&C load/process",
    "ic_mixed": "I&C load/process",
    "other": "Other",
}


def load_asset_class_group_map(project_root: Path) -> Dict[str, str]:
    """
    Load the asset-class → asset-group mapping from `data/reference/asset_class_to_group.csv`.

    If the file is missing or invalid, falls back to `DEFAULT_GROUP_MAP`.
    """
    project_root = Path(project_root)
    csv_path = project_root / "data" / "reference" / "asset_class_to_group.csv"
    if not csv_path.exists():
        return dict(DEFAULT_GROUP_MAP)

    try:
        df = pd.read_csv(csv_path)
        if "asset_class" not in df.columns or "asset_group" not in df.columns:
            return dict(DEFAULT_GROUP_MAP)
        mapping = (
            df[["asset_class", "asset_group"]]
            .dropna()
            .astype(str)
            .assign(asset_class=lambda d: d["asset_class"].str.strip())
            .assign(asset_group=lambda d: d["asset_group"].str.strip())
        )
        out = {
            str(r.asset_class): str(r.asset_group)
            for r in mapping.itertuples(index=False)
            if str(r.asset_class) and str(r.asset_group)
        }
        return out or dict(DEFAULT_GROUP_MAP)
    except Exception:
        return dict(DEFAULT_GROUP_MAP)


def assign_asset_group(asset_class: str, mapping: Dict[str, str]) -> str:
    """
    Map an asset class string to an asset group label.
    """
    if not asset_class:
        return "Other"
    key = str(asset_class).strip()
    return mapping.get(key, "Other")

