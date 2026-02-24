/**
 * FlexDash Embedded Dashboard Data
 *
 * DEMONSTRATION DATA - All values are synthetic and fictional.
 * This file demonstrates dashboard functionality without real contributor data.
 *
 * Generated: 2026-02-17 16:07:39
 */

/**
 * Convert a value to a disclosure-safe range bucket
 * Used for cells with k < 3 contributors (where ranges are shown).
 */
function getDisclosureRange(valueMW) {
    if (valueMW === 0) return { label: '0 MW', min: 0, max: 0, midpoint: 0 };
    if (valueMW < 10) return { label: '<10 MW', min: 0, max: 10, midpoint: 5 };
    if (valueMW < 50) return { label: '10-50 MW', min: 10, max: 50, midpoint: 30 };
    if (valueMW < 100) return { label: '50-100 MW', min: 50, max: 100, midpoint: 75 };
    if (valueMW < 250) return { label: '100-250 MW', min: 100, max: 250, midpoint: 175 };
    if (valueMW < 500) return { label: '250-500 MW', min: 250, max: 500, midpoint: 375 };
    if (valueMW < 1000) return { label: '0.5-1 GW', min: 500, max: 1000, midpoint: 750 };
    if (valueMW < 2500) return { label: '1-2.5 GW', min: 1000, max: 2500, midpoint: 1750 };
    if (valueMW < 5000) return { label: '2.5-5 GW', min: 2500, max: 5000, midpoint: 3750 };
    if (valueMW < 10000) return { label: '5-10 GW', min: 5000, max: 10000, midpoint: 7500 };
    return { label: '>10 GW', min: 10000, max: 15000, midpoint: 12500 };
}

window.getDisclosureRange = getDisclosureRange;

const DASHBOARD_DATA = {
  "generated_at": "2026-02-17T16:07:39.615449",
  "version": "1.0.0-demo",
  "study_period": "Nov 2024-Feb 2025",
  "is_demo": true,
  "subtitle": "DEMONSTRATION - Synthetic Data",
  "metrics": {
    "total_available_mw": 1600,
    "total_delivered_mw": 720,
    "delivery_factor_pct": 45.0,
    "contributor_count": 20,
    "total_available_mw_illustrative": false,
    "total_available_range": null,
    "total_available_range_min": null,
    "total_available_range_max": null,
    "total_delivered_mw_illustrative": false,
    "total_delivered_range": null,
    "total_delivered_range_min": null,
    "total_delivered_range_max": null,
    "domestic": {
      "available_mw": 800,
      "delivered_mw": 360,
      "available_mw_illustrative": false,
      "available_range": null,
      "available_range_min": null,
      "available_range_max": null
    },
    "ic": {
      "available_mw": 800,
      "delivered_mw": 360,
      "available_mw_illustrative": false,
      "available_range": null,
      "available_range_min": null,
      "available_range_max": null
    }
  },
  "sector_breakdown": [
    {
      "sector": "domestic",
      "capacity_mw": 800,
      "delivered_mw": 360,
      "count": 295000,
      "k": 12,
      "k_capacity_mw": 12,
      "k_delivered_mw": 11,
      "k_count": 12,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "count_illustrative": false,
      "count_range": null
    },
    {
      "sector": "ic",
      "capacity_mw": 800,
      "delivered_mw": 360,
      "count": 950,
      "k": 12,
      "k_capacity_mw": 12,
      "k_delivered_mw": 11,
      "k_count": 12,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "count_illustrative": false,
      "count_range": null
    }
  ],
  "asset_breakdown": [
    {
      "asset_class": "ev_charger",
      "sector": "domestic",
      "capacity_mw": 295,
      "delivered_mw": 135,
      "count": 210000,
      "k": 4,
      "k_capacity_mw": 4,
      "k_delivered_mw": 4,
      "k_count": 4,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "count_illustrative": false,
      "count_range": null
    },
    {
      "asset_class": "heat_pump",
      "sector": "domestic",
      "capacity_mw": 140,
      "delivered_mw": 65,
      "count": 28000,
      "k": 3,
      "k_capacity_mw": 3,
      "k_delivered_mw": 3,
      "k_count": 3,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "count_illustrative": false,
      "count_range": null
    },
    {
      "asset_class": "battery_storage",
      "sector": "domestic",
      "capacity_mw": 125,
      "delivered_mw": 55,
      "count": 25000,
      "k": 3,
      "k_capacity_mw": 3,
      "k_delivered_mw": 3,
      "k_count": 3,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "count_illustrative": false,
      "count_range": null
    },
    {
      "asset_class": "storage_heater",
      "sector": "domestic",
      "capacity_mw": 170,
      "delivered_mw": 75,
      "count": 21000,
      "k": 3,
      "k_capacity_mw": 3,
      "k_delivered_mw": 3,
      "k_count": 3,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "count_illustrative": false,
      "count_range": null
    },
    {
      "asset_class": "smart_hot_water",
      "sector": "domestic",
      "capacity_mw": 70,
      "delivered_mw": 30,
      "count": 11000,
      "k": 3,
      "k_capacity_mw": 3,
      "k_delivered_mw": 3,
      "k_count": 3,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "count_illustrative": false,
      "count_range": null
    },
    {
      "asset_class": "cold_storage",
      "sector": "ic",
      "capacity_mw": 160,
      "delivered_mw": 75,
      "count": 205,
      "k": 3,
      "k_capacity_mw": 3,
      "k_delivered_mw": 3,
      "k_count": 3,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "count_illustrative": false,
      "count_range": null
    },
    {
      "asset_class": "water_treatment",
      "sector": "ic",
      "capacity_mw": 130,
      "delivered_mw": 55,
      "count": 95,
      "k": 3,
      "k_capacity_mw": 3,
      "k_delivered_mw": 3,
      "k_count": 3,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "count_illustrative": false,
      "count_range": null
    },
    {
      "asset_class": "manufacturing",
      "sector": "ic",
      "capacity_mw": 185,
      "delivered_mw": 85,
      "count": 150,
      "k": 3,
      "k_capacity_mw": 3,
      "k_delivered_mw": 3,
      "k_count": 3,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "count_illustrative": false,
      "count_range": null
    },
    {
      "asset_class": "commercial_hvac",
      "sector": "ic",
      "capacity_mw": 100,
      "delivered_mw": 50,
      "count": 295,
      "k": 3,
      "k_capacity_mw": 3,
      "k_delivered_mw": 3,
      "k_count": 3,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "count_illustrative": false,
      "count_range": null
    },
    {
      "asset_class": "commercial_battery",
      "sector": "ic",
      "capacity_mw": 150,
      "delivered_mw": 65,
      "count": 130,
      "k": 3,
      "k_capacity_mw": 3,
      "k_delivered_mw": 3,
      "k_count": 3,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "count_illustrative": false,
      "count_range": null
    },
    {
      "asset_class": "ev_fleet",
      "sector": "ic",
      "capacity_mw": 75,
      "delivered_mw": 30,
      "count": 75,
      "k": 3,
      "k_capacity_mw": 3,
      "k_delivered_mw": 3,
      "k_count": 3,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "count_illustrative": false,
      "count_range": null
    }
  ],
  "asset_group_breakdown": [
    {
      "asset_group": "EV charging",
      "capacity_mw": 370,
      "delivered_mw": 165,
      "count": 210075,
      "k": 7,
      "capacity_mw_illustrative": false,
      "count_illustrative": false
    },
    {
      "asset_group": "Heat",
      "capacity_mw": 380,
      "delivered_mw": 170,
      "count": 60000,
      "k": 6,
      "capacity_mw_illustrative": false,
      "count_illustrative": false
    },
    {
      "asset_group": "Battery storage",
      "capacity_mw": 275,
      "delivered_mw": 120,
      "count": 25130,
      "k": 6,
      "capacity_mw_illustrative": false,
      "count_illustrative": false
    },
    {
      "asset_group": "I&C load/process",
      "capacity_mw": 575,
      "delivered_mw": 265,
      "count": 745,
      "k": 9,
      "capacity_mw_illustrative": false,
      "count_illustrative": false
    }
  ],
  "sector_asset_breakdown": [
    {
      "sector": "domestic",
      "asset_class": "ev_charger",
      "capacity_mw": 295,
      "count": 210000,
      "k": 4
    },
    {
      "sector": "domestic",
      "asset_class": "heat_pump",
      "capacity_mw": 140,
      "count": 28000,
      "k": 3
    },
    {
      "sector": "domestic",
      "asset_class": "battery_storage",
      "capacity_mw": 125,
      "count": 25000,
      "k": 3
    },
    {
      "sector": "domestic",
      "asset_class": "storage_heater",
      "capacity_mw": 170,
      "count": 21000,
      "k": 3
    },
    {
      "sector": "domestic",
      "asset_class": "smart_hot_water",
      "capacity_mw": 70,
      "count": 11000,
      "k": 3
    },
    {
      "sector": "ic",
      "asset_class": "cold_storage",
      "capacity_mw": 160,
      "count": 205,
      "k": 3
    },
    {
      "sector": "ic",
      "asset_class": "water_treatment",
      "capacity_mw": 130,
      "count": 95,
      "k": 3
    },
    {
      "sector": "ic",
      "asset_class": "manufacturing",
      "capacity_mw": 185,
      "count": 150,
      "k": 3
    },
    {
      "sector": "ic",
      "asset_class": "commercial_hvac",
      "capacity_mw": 100,
      "count": 295,
      "k": 3
    },
    {
      "sector": "ic",
      "asset_class": "commercial_battery",
      "capacity_mw": 150,
      "count": 130,
      "k": 3
    },
    {
      "sector": "ic",
      "asset_class": "ev_fleet",
      "capacity_mw": 75,
      "count": 75,
      "k": 3
    }
  ],
  "sector_asset_group_breakdown": [
    {
      "sector": "domestic",
      "asset_group": "EV charging",
      "capacity_mw": 295,
      "count": 210000,
      "k": 4
    },
    {
      "sector": "domestic",
      "asset_group": "Heat",
      "capacity_mw": 380,
      "count": 60000,
      "k": 6
    },
    {
      "sector": "domestic",
      "asset_group": "Battery storage",
      "capacity_mw": 125,
      "count": 25000,
      "k": 3
    },
    {
      "sector": "ic",
      "asset_group": "I&C load/process",
      "capacity_mw": 575,
      "count": 745,
      "k": 9
    },
    {
      "sector": "ic",
      "asset_group": "Battery storage",
      "capacity_mw": 150,
      "count": 130,
      "k": 3
    },
    {
      "sector": "ic",
      "asset_group": "EV charging",
      "capacity_mw": 75,
      "count": 75,
      "k": 3
    }
  ],
  "energy_metrics": {
    "total": {
      "available_gwh": 940,
      "delivered_gwh": 420,
      "delivered_range": null,
      "k": 20
    },
    "explicit": {
      "available_gwh": 630,
      "delivered_gwh": 285,
      "delivered_range": null,
      "k": 13
    },
    "implicit": {
      "available_gwh": 310,
      "delivered_gwh": 135,
      "delivered_range": null,
      "k": 9
    }
  },
  "directional_breakdown": {
    "turn_up": {
      "capacity_mw": 610,
      "delivered_mw": 275,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "k": 16
    },
    "turn_down": {
      "capacity_mw": 990,
      "delivered_mw": 445,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "k": 19
    }
  },
  "flexibility_type_breakdown": {
    "explicit": {
      "capacity_mw": 1055,
      "delivered_mw": 475,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "k": 13
    },
    "implicit": {
      "capacity_mw": 545,
      "delivered_mw": 245,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "k": 9
    }
  },
  "utilisation": {
    "overall_rate_pct": 45,
    "overall_rate_note": "Average utilisation across all asset classes",
    "domestic_rate_pct": 45,
    "ic_rate_pct": 45,
    "by_asset_class": {
      "ev_charger": 46,
      "heat_pump": 46,
      "battery_storage": 44,
      "storage_heater": 44,
      "smart_hot_water": 43,
      "cold_storage": 47,
      "water_treatment": 42,
      "manufacturing": 46,
      "commercial_hvac": 50,
      "commercial_battery": 43,
      "ev_fleet": 40
    }
  },
  "coverage": {
    "contributors_total": 20,
    "capacity_mw_contributors": 20,
    "delivered_mw_contributors": 18,
    "energy_mwh_contributors": 17,
    "explicit_energy_contributors": 13,
    "implicit_energy_contributors": 9,
    "k_threshold": 3
  },
  "service_breakdown": [
    {
      "service_type": "frequency_response",
      "capacity_mw": 225,
      "k": 4
    },
    {
      "service_type": "capacity_market",
      "capacity_mw": 305,
      "k": 6
    },
    {
      "service_type": "balancing_mechanism",
      "capacity_mw": 150,
      "k": 3
    },
    {
      "service_type": "dso_flexibility",
      "capacity_mw": 125,
      "k": 3
    },
    {
      "service_type": "tou_tariff",
      "capacity_mw": 545,
      "k": 9
    },
    {
      "service_type": "wholesale_arbitrage",
      "capacity_mw": 255,
      "k": 5
    }
  ],
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
      "current_vs_2030_pct": 2.9,
      "label": "Current dashboard (1.6 GW) vs 2030 target (55 GW)"
    }
  },
  "narratives": {
    "headline": "20 contributors reporting 1.6 GW of flexibility capacity across domestic and I&C sectors.",
    "domestic": "Domestic flexibility is dominated by EV charging (295 MW) and storage heaters (170 MW), with growing contributions from heat pumps and home batteries.",
    "ic": "I&C flexibility shows strong contributions from manufacturing (185 MW), cold storage (160 MW), and commercial batteries (150 MW).",
    "utilisation": "Overall utilisation rate of 45% indicates significant untapped flexibility potential.",
    "growth": "Flexibility capacity is expected to grow significantly as EV adoption accelerates and heat pump installations increase."
  },
  "latent_potential": {
    "total_gw": 15.2,
    "by_asset_class": {
      "ev_charger": {
        "deployed_total": 1800000,
        "managed_pct": 35,
        "latent_gw": 8.2
      },
      "heat_pump": {
        "deployed_total": 250000,
        "managed_pct": 34,
        "latent_gw": 1.2
      },
      "battery_storage": {
        "deployed_total": 150000,
        "managed_pct": 51,
        "latent_gw": 0.5
      },
      "storage_heater": {
        "deployed_total": 1500000,
        "managed_pct": 4,
        "latent_gw": 5.3
      }
    },
    "sources": [
      "DfT vehicle statistics",
      "MCS certified installations",
      "DESNZ statistics"
    ],
    "methodology_note": "Latent potential = (Average flex per managed asset) \u00d7 (Unmanaged deployed assets)"
  },
  "future_potential": {
    "2030": {
      "central_gw": 55.2,
      "range_min_gw": 51,
      "range_max_gw": 66,
      "sources": [
        "NESO FES 2025",
        "Clean Power 2030 Action Plan"
      ],
      "key_drivers": [
        "EV growth (5.5M BEVs)",
        "Heat pump rollout (600k/year)",
        "Grid battery expansion"
      ]
    },
    "2050": {
      "central_gw": 204,
      "range_min_gw": 180,
      "range_max_gw": 220,
      "sources": [
        "NESO FES 2025"
      ],
      "key_drivers": [
        "Full transport electrification",
        "Hydrogen integration",
        "Smart grid maturity"
      ]
    }
  },
  "data_quality": {
    "total_submissions": 20,
    "valid_submissions": 20,
    "validation_rate": 1.0,
    "average_completeness": 0.87,
    "completeness": {
      "overall_pct": 87,
      "capacity_pct": 100,
      "delivered_pct": 90,
      "energy_pct": 83
    },
    "coverage_notes": [
      "20 contributors representing major aggregators, suppliers, and DSOs",
      "Domestic sector well represented with 210k managed EV chargers",
      "I&C coverage includes major industrial demand response providers"
    ]
  },
  "caveats": {
    "general": "This dashboard presents data from contributing organisations only and does not represent the full GB flexibility market.",
    "capacity_note": "Capacity values represent technical availability and may not all be simultaneously accessible.",
    "delivery_note": "Delivered flexibility depends on market conditions and dispatch instructions.",
    "latent_note": "Latent potential estimates are derived from public deployment data and contributor averages."
  },
  "colors": {
    "domestic": "#2E86AB",
    "ic": "#A23B72",
    "primary": "#c41230",
    "secondary": "#45c3d3",
    "accent": "#6eb43f"
  }
};
