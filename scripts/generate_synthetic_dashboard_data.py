"""
Generate comprehensive synthetic dashboard data directly.

This bypasses the Excel template complexity and creates a complete
dataset that demonstrates all dashboard features with k≥3 everywhere.

Usage:
    python scripts/generate_synthetic_dashboard_data.py

Output:
    dashboard/js/data.js - Embedded dashboard data
    dashboard/data/dashboard_data.json - JSON data file
"""

import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_JS = PROJECT_ROOT / "dashboard" / "js" / "data.js"
OUTPUT_JSON = PROJECT_ROOT / "dashboard" / "data" / "dashboard_data.json"


def generate_dashboard_data():
    """Generate comprehensive synthetic dashboard data."""

    # Target: k≥3 for every dimension, disaggregated asset classes
    # We need at least 3 contributors per asset class per sector

    # SYNTHETIC CONTRIBUTOR COUNTS (fictional)
    # Domestic EV chargers: 8 contributors
    # Domestic Heat pumps: 5 contributors
    # Domestic Battery storage: 6 contributors
    # Domestic Storage heaters: 4 contributors
    # Domestic Smart hot water: 3 contributors
    # I&C Cold storage: 5 contributors
    # I&C Water treatment: 4 contributors
    # I&C Manufacturing: 6 contributors
    # I&C Commercial HVAC: 4 contributors
    # I&C Commercial battery: 5 contributors
    # I&C EV fleet: 3 contributors

    data = {
        "generated_at": datetime.now().isoformat(),
        "version": "1.0.0-demo",
        "study_period": "Nov 2024-Feb 2025",
        "is_demo": True,
        "subtitle": "DEMONSTRATION - Synthetic Data",

        # ===== HEADLINE METRICS =====
        "metrics": {
            "total_available_mw": 4850,
            "total_delivered_mw": 2180,
            "delivery_factor_pct": 45.0,
            "contributor_count": 42,

            "total_available_mw_illustrative": False,
            "total_available_range": None,
            "total_available_range_min": None,
            "total_available_range_max": None,

            "total_delivered_mw_illustrative": False,
            "total_delivered_range": None,
            "total_delivered_range_min": None,
            "total_delivered_range_max": None,

            "domestic": {
                "available_mw": 2420,
                "delivered_mw": 1090,
                "available_mw_illustrative": False,
                "available_range": None,
                "available_range_min": None,
                "available_range_max": None
            },
            "ic": {
                "available_mw": 2430,
                "delivered_mw": 1090,
                "available_mw_illustrative": False,
                "available_range": None,
                "available_range_min": None,
                "available_range_max": None
            }
        },

        # ===== SECTOR BREAKDOWN =====
        "sector_breakdown": [
            {
                "sector": "domestic",
                "capacity_mw": 2420,
                "delivered_mw": 1090,
                "count": 892000,
                "k": 26,
                "k_capacity_mw": 26,
                "k_delivered_mw": 24,
                "k_count": 26,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "count_illustrative": False,
                "count_range": None
            },
            {
                "sector": "ic",
                "capacity_mw": 2430,
                "delivered_mw": 1090,
                "count": 2850,
                "k": 27,
                "k_capacity_mw": 27,
                "k_delivered_mw": 25,
                "k_count": 27,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "count_illustrative": False,
                "count_range": None
            }
        ],

        # ===== ASSET CLASS BREAKDOWN (disaggregated) =====
        "asset_breakdown": [
            # Domestic
            {
                "asset_class": "ev_charger",
                "sector": "domestic",
                "capacity_mw": 890,
                "delivered_mw": 400,
                "count": 635000,
                "k": 8,
                "k_capacity_mw": 8,
                "k_delivered_mw": 7,
                "k_count": 8,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "count_illustrative": False,
                "count_range": None
            },
            {
                "asset_class": "heat_pump",
                "sector": "domestic",
                "capacity_mw": 420,
                "delivered_mw": 190,
                "count": 84000,
                "k": 5,
                "k_capacity_mw": 5,
                "k_delivered_mw": 5,
                "k_count": 5,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "count_illustrative": False,
                "count_range": None
            },
            {
                "asset_class": "battery_storage",
                "sector": "domestic",
                "capacity_mw": 380,
                "delivered_mw": 170,
                "count": 76000,
                "k": 6,
                "k_capacity_mw": 6,
                "k_delivered_mw": 6,
                "k_count": 6,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "count_illustrative": False,
                "count_range": None
            },
            {
                "asset_class": "storage_heater",
                "sector": "domestic",
                "capacity_mw": 520,
                "delivered_mw": 230,
                "count": 65000,
                "k": 4,
                "k_capacity_mw": 4,
                "k_delivered_mw": 4,
                "k_count": 4,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "count_illustrative": False,
                "count_range": None
            },
            {
                "asset_class": "smart_hot_water",
                "sector": "domestic",
                "capacity_mw": 210,
                "delivered_mw": 100,
                "count": 32000,
                "k": 3,
                "k_capacity_mw": 3,
                "k_delivered_mw": 3,
                "k_count": 3,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "count_illustrative": False,
                "count_range": None
            },
            # I&C
            {
                "asset_class": "cold_storage",
                "sector": "ic",
                "capacity_mw": 480,
                "delivered_mw": 220,
                "count": 620,
                "k": 5,
                "k_capacity_mw": 5,
                "k_delivered_mw": 5,
                "k_count": 5,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "count_illustrative": False,
                "count_range": None
            },
            {
                "asset_class": "water_treatment",
                "sector": "ic",
                "capacity_mw": 390,
                "delivered_mw": 175,
                "count": 285,
                "k": 4,
                "k_capacity_mw": 4,
                "k_delivered_mw": 4,
                "k_count": 4,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "count_illustrative": False,
                "count_range": None
            },
            {
                "asset_class": "manufacturing",
                "sector": "ic",
                "capacity_mw": 560,
                "delivered_mw": 250,
                "count": 445,
                "k": 6,
                "k_capacity_mw": 6,
                "k_delivered_mw": 6,
                "k_count": 6,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "count_illustrative": False,
                "count_range": None
            },
            {
                "asset_class": "commercial_hvac",
                "sector": "ic",
                "capacity_mw": 340,
                "delivered_mw": 150,
                "count": 890,
                "k": 4,
                "k_capacity_mw": 4,
                "k_delivered_mw": 4,
                "k_count": 4,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "count_illustrative": False,
                "count_range": None
            },
            {
                "asset_class": "commercial_battery",
                "sector": "ic",
                "capacity_mw": 450,
                "delivered_mw": 200,
                "count": 385,
                "k": 5,
                "k_capacity_mw": 5,
                "k_delivered_mw": 5,
                "k_count": 5,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "count_illustrative": False,
                "count_range": None
            },
            {
                "asset_class": "ev_fleet",
                "sector": "ic",
                "capacity_mw": 210,
                "delivered_mw": 95,
                "count": 225,
                "k": 3,
                "k_capacity_mw": 3,
                "k_delivered_mw": 3,
                "k_count": 3,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "count_illustrative": False,
                "count_range": None
            }
        ],

        # ===== ASSET GROUP BREAKDOWN =====
        "asset_group_breakdown": [
            {
                "asset_group": "EV charging",
                "capacity_mw": 1100,
                "delivered_mw": 495,
                "count": 635225,
                "k": 11,
                "capacity_mw_illustrative": False,
                "count_illustrative": False
            },
            {
                "asset_group": "Heat",
                "capacity_mw": 1150,
                "delivered_mw": 520,
                "count": 181000,
                "k": 12,
                "capacity_mw_illustrative": False,
                "count_illustrative": False
            },
            {
                "asset_group": "Battery storage",
                "capacity_mw": 830,
                "delivered_mw": 370,
                "count": 76385,
                "k": 11,
                "capacity_mw_illustrative": False,
                "count_illustrative": False
            },
            {
                "asset_group": "I&C load/process",
                "capacity_mw": 1770,
                "delivered_mw": 795,
                "count": 2240,
                "k": 19,
                "capacity_mw_illustrative": False,
                "count_illustrative": False
            }
        ],

        # ===== SECTOR + ASSET CLASS BREAKDOWN =====
        "sector_asset_breakdown": [
            # Domestic
            {"sector": "domestic", "asset_class": "ev_charger", "capacity_mw": 890, "count": 635000, "k": 8},
            {"sector": "domestic", "asset_class": "heat_pump", "capacity_mw": 420, "count": 84000, "k": 5},
            {"sector": "domestic", "asset_class": "battery_storage", "capacity_mw": 380, "count": 76000, "k": 6},
            {"sector": "domestic", "asset_class": "storage_heater", "capacity_mw": 520, "count": 65000, "k": 4},
            {"sector": "domestic", "asset_class": "smart_hot_water", "capacity_mw": 210, "count": 32000, "k": 3},
            # I&C
            {"sector": "ic", "asset_class": "cold_storage", "capacity_mw": 480, "count": 620, "k": 5},
            {"sector": "ic", "asset_class": "water_treatment", "capacity_mw": 390, "count": 285, "k": 4},
            {"sector": "ic", "asset_class": "manufacturing", "capacity_mw": 560, "count": 445, "k": 6},
            {"sector": "ic", "asset_class": "commercial_hvac", "capacity_mw": 340, "count": 890, "k": 4},
            {"sector": "ic", "asset_class": "commercial_battery", "capacity_mw": 450, "count": 385, "k": 5},
            {"sector": "ic", "asset_class": "ev_fleet", "capacity_mw": 210, "count": 225, "k": 3},
        ],

        # ===== SECTOR + ASSET GROUP BREAKDOWN =====
        "sector_asset_group_breakdown": [
            {"sector": "domestic", "asset_group": "EV charging", "capacity_mw": 890, "count": 635000, "k": 8},
            {"sector": "domestic", "asset_group": "Heat", "capacity_mw": 1150, "count": 181000, "k": 12},
            {"sector": "domestic", "asset_group": "Battery storage", "capacity_mw": 380, "count": 76000, "k": 6},
            {"sector": "ic", "asset_group": "I&C load/process", "capacity_mw": 1770, "count": 2240, "k": 19},
            {"sector": "ic", "asset_group": "Battery storage", "capacity_mw": 450, "count": 385, "k": 5},
            {"sector": "ic", "asset_group": "EV charging", "capacity_mw": 210, "count": 225, "k": 3},
        ],

        # ===== ENERGY METRICS (GWh) =====
        "energy_metrics": {
            "total": {
                "available_gwh": 2850,
                "delivered_gwh": 1280,
                "delivered_range": None,
                "k": 42
            },
            "explicit": {
                "available_gwh": 1920,
                "delivered_gwh": 860,
                "delivered_range": None,
                "k": 28
            },
            "implicit": {
                "available_gwh": 930,
                "delivered_gwh": 420,
                "delivered_range": None,
                "k": 18
            }
        },

        # ===== DIRECTIONAL BREAKDOWN =====
        "directional_breakdown": {
            "turn_up": {
                "capacity_mw": 1850,
                "delivered_mw": 830,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "k": 35
            },
            "turn_down": {
                "capacity_mw": 3000,
                "delivered_mw": 1350,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "k": 40
            }
        },

        # ===== FLEXIBILITY TYPE BREAKDOWN =====
        "flexibility_type_breakdown": {
            "explicit": {
                "capacity_mw": 3200,
                "delivered_mw": 1440,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "k": 28
            },
            "implicit": {
                "capacity_mw": 1650,
                "delivered_mw": 740,
                "capacity_mw_illustrative": False,
                "capacity_range": None,
                "k": 18
            }
        },

        # ===== UTILISATION =====
        "utilisation": {
            "overall_rate_pct": 45,
            "overall_rate_note": "Average utilisation across all asset classes",
            "domestic_rate_pct": 45,
            "ic_rate_pct": 45,
            "by_asset_class": {
                "ev_charger": 45,
                "heat_pump": 45,
                "battery_storage": 45,
                "storage_heater": 44,
                "smart_hot_water": 48,
                "cold_storage": 46,
                "water_treatment": 45,
                "manufacturing": 45,
                "commercial_hvac": 44,
                "commercial_battery": 44,
                "ev_fleet": 45
            }
        },

        # ===== COVERAGE =====
        "coverage": {
            "contributors_total": 42,
            "capacity_mw_contributors": 42,
            "delivered_mw_contributors": 38,
            "energy_mwh_contributors": 35,
            "explicit_capacity_contributors": 28,
            "implicit_capacity_contributors": 18,
            "k_threshold": 3
        },

        # ===== SERVICE BREAKDOWN =====
        "service_breakdown": [
            {"service_type": "frequency_response", "capacity_mw": 680, "k": 8},
            {"service_type": "capacity_market", "capacity_mw": 920, "k": 12},
            {"service_type": "balancing_mechanism", "capacity_mw": 450, "k": 6},
            {"service_type": "dso_flexibility", "capacity_mw": 380, "k": 5},
            {"service_type": "tou_tariff", "capacity_mw": 1650, "k": 18},
            {"service_type": "wholesale_arbitrage", "capacity_mw": 770, "k": 9}
        ],

        # ===== BENCHMARKS =====
        "benchmarks": {
            "neso_fes_2025": {
                "flexibility_2030_gw": 55.2,
                "flexibility_2050_gw": 204,
                "source": "NESO Future Energy Scenarios 2025"
            },
            "clean_power_2030": {
                "flexibility_min_gw": 51,
                "flexibility_max_gw": 66,
                "source": "Clean Power 2030 Action Plan"
            },
            "capacity_market": {
                "dsr_awarded_gw": 1.8,
                "source": "NESO Capacity Market T-4 2028/29"
            },
            "dfs": {
                "mpans_registered": 1980000,
                "energy_mwh_delivered": 3917,
                "source": "NESO DFS Winter 2024/25"
            },
            "comparison": {
                "current_vs_2030_pct": 8.8,
                "label": "Current dashboard (4.9 GW) vs 2030 target (55 GW)"
            }
        },

        # ===== NARRATIVES =====
        "narratives": {
            "headline": "42 contributors reporting 4.9 GW of flexibility capacity across domestic and I&C sectors.",
            "domestic": "Domestic flexibility is dominated by EV charging (890 MW) and storage heaters (520 MW), with growing contributions from heat pumps and home batteries.",
            "ic": "I&C flexibility shows strong contributions from manufacturing (560 MW), cold storage (480 MW), and commercial batteries (450 MW).",
            "utilisation": "Overall utilisation rate of 45% indicates significant untapped flexibility potential.",
            "growth": "Flexibility capacity is expected to grow significantly as EV adoption accelerates and heat pump installations increase."
        },

        # ===== LATENT POTENTIAL =====
        "latent_potential": {
            "total_gw": 15.2,
            "by_asset_class": {
                "ev_charger": {"deployed_total": 1800000, "managed_pct": 35, "latent_gw": 8.2},
                "heat_pump": {"deployed_total": 250000, "managed_pct": 34, "latent_gw": 1.2},
                "battery_storage": {"deployed_total": 150000, "managed_pct": 51, "latent_gw": 0.5},
                "storage_heater": {"deployed_total": 1500000, "managed_pct": 4, "latent_gw": 5.3}
            },
            "sources": ["DfT vehicle statistics", "MCS certified installations", "DESNZ statistics"],
            "methodology_note": "Latent potential = (Average flex per managed asset) × (Unmanaged deployed assets)"
        },

        # ===== FUTURE POTENTIAL =====
        "future_potential": {
            "2030": {
                "central_gw": 55.2,
                "range_min_gw": 51,
                "range_max_gw": 66,
                "sources": ["NESO FES 2025", "Clean Power 2030 Action Plan"],
                "key_drivers": ["EV growth (5.5M BEVs)", "Heat pump rollout (600k/year)", "Grid battery expansion"]
            },
            "2050": {
                "central_gw": 204,
                "range_min_gw": 180,
                "range_max_gw": 220,
                "sources": ["NESO FES 2025"],
                "key_drivers": ["Full transport electrification", "Hydrogen integration", "Smart grid maturity"]
            }
        },

        # ===== DATA QUALITY =====
        "data_quality": {
            "completeness": {
                "overall_pct": 87,
                "capacity_pct": 100,
                "delivered_pct": 90,
                "energy_pct": 83
            },
            "coverage_notes": [
                "42 contributors representing major aggregators, suppliers, and DSOs",
                "Domestic sector well represented with 635k managed EV chargers",
                "I&C coverage includes major industrial demand response providers"
            ]
        },

        # ===== CAVEATS =====
        "caveats": {
            "general": "This dashboard presents data from contributing organisations only and does not represent the full GB flexibility market.",
            "capacity_note": "Capacity values represent technical availability and may not all be simultaneously accessible.",
            "delivery_note": "Delivered flexibility depends on market conditions and dispatch instructions.",
            "latent_note": "Latent potential estimates are derived from public deployment data and contributor averages."
        },

        # ===== COLORS =====
        "colors": {
            "domestic": "#2E86AB",
            "ic": "#A23B72",
            "primary": "#c41230",
            "secondary": "#45c3d3",
            "accent": "#6eb43f"
        }
    }

    return data


def write_js_file(data: dict, output_path: Path):
    """Write data as embedded JavaScript."""
    js_content = '''/**
 * FlexDash Embedded Dashboard Data
 *
 * DEMONSTRATION DATA - All values are synthetic and fictional.
 * This file demonstrates dashboard functionality without real contributor data.
 *
 * Generated: {timestamp}
 */

/**
 * Convert a value to a disclosure-safe range bucket
 * Used for cells with k < 3 contributors (where ranges are shown).
 */
function getDisclosureRange(valueMW) {{
    if (valueMW === 0) return {{ label: '0 MW', min: 0, max: 0, midpoint: 0 }};
    if (valueMW < 10) return {{ label: '<10 MW', min: 0, max: 10, midpoint: 5 }};
    if (valueMW < 50) return {{ label: '10-50 MW', min: 10, max: 50, midpoint: 30 }};
    if (valueMW < 100) return {{ label: '50-100 MW', min: 50, max: 100, midpoint: 75 }};
    if (valueMW < 250) return {{ label: '100-250 MW', min: 100, max: 250, midpoint: 175 }};
    if (valueMW < 500) return {{ label: '250-500 MW', min: 250, max: 500, midpoint: 375 }};
    if (valueMW < 1000) return {{ label: '0.5-1 GW', min: 500, max: 1000, midpoint: 750 }};
    if (valueMW < 2500) return {{ label: '1-2.5 GW', min: 1000, max: 2500, midpoint: 1750 }};
    if (valueMW < 5000) return {{ label: '2.5-5 GW', min: 2500, max: 5000, midpoint: 3750 }};
    if (valueMW < 10000) return {{ label: '5-10 GW', min: 5000, max: 10000, midpoint: 7500 }};
    return {{ label: '>10 GW', min: 10000, max: 15000, midpoint: 12500 }};
}}

window.getDisclosureRange = getDisclosureRange;

const DASHBOARD_DATA = {json_data};
'''.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        json_data=json.dumps(data, indent=2)
    )

    output_path.write_text(js_content)


def main():
    print("=" * 60)
    print("Generating Comprehensive Synthetic Dashboard Data")
    print("=" * 60)

    # Generate the data
    data = generate_dashboard_data()

    # Ensure output directories exist
    OUTPUT_JS.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    # Write JS file
    write_js_file(data, OUTPUT_JS)
    print(f"\nWritten: {OUTPUT_JS}")

    # Write JSON file
    OUTPUT_JSON.write_text(json.dumps(data, indent=2))
    print(f"Written: {OUTPUT_JSON}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print(f"  Total capacity: {data['metrics']['total_available_mw']:,} MW ({data['metrics']['total_available_mw']/1000:.1f} GW)")
    print(f"  Total delivered: {data['metrics']['total_delivered_mw']:,} MW")
    print(f"  Contributors: {data['metrics']['contributor_count']}")
    print(f"  Domestic: {data['metrics']['domestic']['available_mw']:,} MW")
    print(f"  I&C: {data['metrics']['ic']['available_mw']:,} MW")
    print(f"  Asset classes: {len(data['asset_breakdown'])}")
    print(f"  All k-values >= 3: Yes (no ranges needed)")
    print("=" * 60)


if __name__ == "__main__":
    main()
