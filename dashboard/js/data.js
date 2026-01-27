/**
 * FlexDash Embedded Dashboard Data
 *
 * This file contains the dashboard data embedded directly to allow
 * the dashboard to work when opened as a local file (file:// protocol).
 *
 * Generated: 2026-01-27
 */

/**
 * Convert a value to a disclosure-safe range bucket
 * Used for cells with k < 3 contributors
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

// Export for use
window.getDisclosureRange = getDisclosureRange;

const DASHBOARD_DATA = {
  "generated_at": "2026-01-27T15:34:57.264480",
  "version": "2.0.0",
  "methodology_version": "v7",
  "study_period": "2024-2025",
  "metrics": {
    "total_available_mw": 13760,
    "total_delivered_mw": 6880,
    "delivery_factor_pct": 50,
    "contributor_count": 6,
    "domestic": {
      "available_mw": 4550,
      "delivered_mw": 2275
    },
    "ic": {
      "available_mw": 9210,
      "delivered_mw": 4605
    }
  },

  // Methodology v7: Energy Metrics (GWh)
  // Note: Total aggregates from multiple contributors (k>=3).
  // Explicit/implicit breakdown uses ranges due to k<3 for those dimensions.
  "energy_metrics": {
    "total": {
      "available_gwh": 700,
      "delivered_gwh": 650,
      "utilisation_pct": 50,
      "k": 3,
      "note": "Total aggregated from multiple contributors"
    },
    "explicit": {
      "illustrative": true,
      "k": 1,
      "delivered_gwh_range": "250-750 GWh",
      "delivered_gwh_min": 250,
      "delivered_gwh_max": 750,
      "note": "Range estimate - managed flexibility from explicit contracts (k<3)"
    },
    "implicit": {
      "illustrative": true,
      "k": 1,
      "delivered_gwh_range": "50-250 GWh",
      "delivered_gwh_min": 50,
      "delivered_gwh_max": 250,
      "note": "Range estimate - behavioral response from ToU tariffs (k<3)"
    }
  },

  // Methodology v7: Directional Breakdown (Turn-up/Turn-down)
  // Note: Capacity values meet k>=3 threshold. Energy values use ranges (k<3).
  "directional_breakdown": {
    "turn_up": {
      "capacity_mw": 4550,
      "capacity_k": 3,
      "energy_gwh_illustrative": true,
      "energy_gwh_range": "50-250 GWh",
      "energy_k": 1,
      "primary_source": "ToU tariff load shifting",
      "note": "Turn-up appears higher when ToU included as customers shift load into off-peak periods. This reflects demand flexibility, not new generation."
    },
    "turn_down": {
      "capacity_mw": 9210,
      "capacity_k": 5,
      "energy_gwh_illustrative": true,
      "energy_gwh_range": "250-750 GWh",
      "energy_k": 1,
      "primary_source": "Managed demand reduction",
      "note": "Turn-down dominated by explicit DSR contracts and aggregator-managed assets."
    },
    "asymmetry_explanation": "When Time-of-Use tariffs are included, turn-up capacity appears higher because customers shift load into off-peak periods. This reflects demand flexibility, not new generation. Managed assets are predominantly turn-down (demand reduction)."
  },

  // Methodology v7: Explicit/Implicit Split
  // Note: Energy GWh values are ranges due to k<3 for energy metrics
  "flexibility_type_breakdown": {
    "explicit": {
      "capacity_mw": 9210,
      "capacity_k": 5,
      "energy_gwh_illustrative": true,
      "energy_gwh_range": "250-750 GWh",
      "energy_gwh_min": 250,
      "energy_gwh_max": 750,
      "energy_k": 1,
      "description": "Contracted flexibility with defined dispatch/payment mechanisms"
    },
    "implicit": {
      "capacity_mw": 4550,
      "capacity_k": 3,
      "energy_gwh_illustrative": true,
      "energy_gwh_range": "50-250 GWh",
      "energy_gwh_min": 50,
      "energy_gwh_max": 250,
      "energy_k": 1,
      "description": "Price-responsive behavioral changes from ToU tariffs"
    }
  },

  // Methodology v7: Utilisation Metrics
  "utilisation": {
    "overall_rate_pct": 50,
    "overall_rate_note": "Estimated from contributor subset with event-level delivery data",
    "by_type": {
      "explicit": {
        "rate_pct": 52,
        "available_mw": 9210,
        "delivered_mw": 4790,
        "note": "Based on contributor data with available + delivered metrics"
      },
      "implicit": {
        "rate_pct": 100,
        "available_mw": 4550,
        "delivered_mw": 4550,
        "note": "For ToU response, available = delivered by definition"
      }
    },
    "benchmark_dfs": {
      "participation_mpans": 1980000,
      "delivery_rate_pct": 70,
      "energy_delivered_mwh": 3917,
      "source": "NESO DFS 2024-25"
    }
  },

  // Methodology v7: Latent Potential (derived from public data)
  "latent_potential": {
    "total_gw": 15.35,
    "calculation_method": "Average flex per managed asset × Total GB deployed assets",
    "by_asset_class": [
      {
        "asset_class": "ev_charging",
        "display_name": "Electric Vehicles",
        "managed_sample": 635000,
        "avg_kw_per_asset": 7,
        "gb_deployed": 1800000,
        "latent_gw": 12.6,
        "source": "Zapmap, SMMT",
        "note": "1.8M BEVs registered, assumes 7kW average smart charging capability"
      },
      {
        "asset_class": "heat_pumps",
        "display_name": "Heat Pumps",
        "managed_sample": 80,
        "avg_kw_per_asset": 7,
        "gb_deployed": 250000,
        "latent_gw": 1.75,
        "source": "MCS",
        "note": "250k installed heat pumps, growing at 75%+ annually"
      },
      {
        "asset_class": "battery_domestic",
        "display_name": "Domestic Batteries",
        "managed_sample": 19540,
        "avg_kw_per_asset": 9.2,
        "gb_deployed": 50000,
        "latent_gw": 0.46,
        "source": "DESNZ, MCS",
        "note": "~22k new installations per year, ~50k total installed"
      },
      {
        "asset_class": "battery_grid",
        "display_name": "Grid-Scale Batteries",
        "current_gw": 6.8,
        "consented_gw": 60,
        "projection_2030_gw": 27,
        "source": "RenewableUK, Energy Storage News",
        "note": "6.8 GW / 10.5 GWh operational, 60+ GW consented"
      }
    ],
    "data_sources": [
      {"name": "Zapmap", "url": "https://zapmap.com/ev-stats", "metric": "1.8M BEVs, 87k public chargers"},
      {"name": "MCS", "url": "https://mcscertified.com", "metric": "250k heat pumps installed"},
      {"name": "DESNZ", "url": "https://gov.uk/statistics", "metric": "22k domestic batteries/year"},
      {"name": "RenewableUK", "url": "https://renewableuk.com", "metric": "6.8 GW grid batteries"}
    ],
    "note": "Latent potential uses public deployment data, not contributor-specific data, to avoid k-threshold issues."
  },

  // Methodology v7: Future Projections (2030/2050)
  "future_potential": {
    "2030": {
      "central_gw": 55.2,
      "range_min_gw": 51,
      "range_max_gw": 66,
      "scenarios": {
        "current_participation": {
          "gw": 35,
          "description": "Future deployment at today's participation rates"
        },
        "full_participation": {
          "gw": 66,
          "description": "Future deployment with expanded market participation"
        }
      },
      "sources": [
        {"name": "NESO FES 2025", "figure": "55.2 GW central case"},
        {"name": "Clean Power 2030 Action Plan", "figure": "51-66 GW flexibility range"}
      ],
      "by_technology": [
        {"technology": "EV Smart Charging", "gw": 18, "note": "5.5M V2G-capable EVs"},
        {"technology": "Heat Pumps", "gw": 8, "note": "600k/year by 2028"},
        {"technology": "Battery Storage", "gw": 23, "note": "Grid + domestic"},
        {"technology": "I&C Flexibility", "gw": 6, "note": "Expanded DSR"}
      ]
    },
    "2050": {
      "central_gw": 204,
      "range_min_gw": 180,
      "range_max_gw": 220,
      "scenarios": {
        "current_participation": {
          "gw": 120,
          "description": "Future deployment at today's participation rates"
        },
        "full_participation": {
          "gw": 220,
          "description": "Future deployment with expanded market participation"
        }
      },
      "sources": [
        {"name": "NESO FES 2025", "figure": "204 GW central case"}
      ]
    },
    "policy_drivers": [
      {"policy": "ZEV Mandate", "target": "80% EV sales by 2030, 100% by 2035"},
      {"policy": "Heat Pump Target", "target": "600k installations/year by 2028"},
      {"policy": "Clean Power 2030", "target": "Decarbonised grid by 2030"}
    ]
  },

  // Market Benchmarks
  "market_benchmarks": {
    "capacity_market_dsr": {
      "value_gw": 1.8,
      "period": "T-4 2028/29",
      "source": "NESO Capacity Market"
    },
    "dso_markets": {
      "tendered_gw": 31,
      "contracted_gw": 9,
      "source": "ENA, UKPN"
    },
    "dfs_participation": {
      "mpans": 1980000,
      "delivered_mwh": 3917,
      "source": "NESO DFS 2024-25"
    }
  },
  "sector_breakdown": [
    {
      "sector": "domestic",
      "capacity_mw": 4550,
      "capacity_mw_illustrative": false,
      "count": 655030,
      "count_illustrative": false
    },
    {
      "sector": "ic",
      "capacity_mw": 9210,
      "capacity_mw_illustrative": false,
      "count": 36890,
      "count_illustrative": false
    }
  ],
  "asset_breakdown": [
    {
      "asset_class": "ev_charging",
      "display_name": "EV Charging",
      "capacity_mw": 4450,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "k": 3,
      "count": 635420,
      "count_illustrative": false,
      "includes": ["Smart EV chargers (domestic)"],
      "sector": "domestic"
    },
    {
      "asset_class": "battery_storage",
      "display_name": "Battery Storage",
      "capacity_mw": 180,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "k": 3,
      "count": 19540,
      "count_illustrative": false,
      "includes": ["Domestic batteries", "Commercial batteries"],
      "sector": "mixed"
    },
    {
      "asset_class": "ic_process_loads",
      "display_name": "I&C Process Loads",
      "capacity_mw": 140,
      "capacity_mw_illustrative": false,
      "capacity_range": null,
      "k": 4,
      "count": 210,
      "count_illustrative": false,
      "includes": ["Cold storage", "Water treatment", "Manufacturing"],
      "sector": "ic"
    },
    {
      "asset_class": "ic_aggregated",
      "display_name": "I&C Aggregated",
      "capacity_mw": 8810,
      "capacity_mw_illustrative": true,
      "capacity_range": "5-10 GW",
      "capacity_range_min": 5000,
      "capacity_range_max": 10000,
      "k": 2,
      "count": 270,
      "count_illustrative": true,
      "includes": ["Mixed I&C portfolios from aggregators"],
      "sector": "ic"
    },
    {
      "asset_class": "heat_pumps",
      "display_name": "Heat Pumps",
      "capacity_mw": 0,
      "capacity_mw_illustrative": true,
      "capacity_range": "<10 MW",
      "capacity_range_min": 0,
      "capacity_range_max": 10,
      "k": 1,
      "count": 80,
      "count_illustrative": true,
      "includes": ["ASHP", "GSHP"],
      "sector": "domestic"
    },
    {
      "asset_class": "other_domestic",
      "display_name": "Other Domestic",
      "capacity_mw": 180,
      "capacity_mw_illustrative": true,
      "capacity_range": "100-250 MW",
      "capacity_range_min": 100,
      "capacity_range_max": 250,
      "k": 1,
      "count": 36400,
      "count_illustrative": true,
      "includes": ["Smart appliances", "Other flexible loads"],
      "sector": "domestic"
    }
  ],
  "service_breakdown": [],
  "narratives": {
    "headline": "This dashboard presents flexibility data from 6 contributing organisations for the study period 2024-2025. Total available flexibility capacity is 13.8 GW, with approximately 653 GWh of energy flexibility delivered.",
    "sector": "Domestic flexibility accounts for 33% of total capacity (4,550 MW), with I&C contributing 67% (9,210 MW).",
    "delivery": "Utilisation rate estimated at approximately 50%, based on contributor subset with both available and delivered data.",
    "coverage": "Data for this dashboard was provided by 6 organisations. Where fewer than 3 contributors exist for a metric, illustrative values are shown to protect commercial confidentiality.",
    "energy": "Energy metrics (GWh) derived from contributor subset with explicit (managed) and implicit (ToU) delivery data.",
    "asymmetry": "Turn-up capacity appears higher when ToU tariffs are included because customers shift load into off-peak periods. This represents demand flexibility, not new generation.",
    "latent": "Latent potential estimates are derived from public deployment data multiplied by average flexibility per managed asset. These are industry estimates, not contributor-specific data.",
    "future": "Future projections are based on NESO Future Energy Scenarios 2025 and Clean Power 2030 Action Plan targets."
  },

  // Methodology v7: Mandatory Caveats
  "caveats": {
    "contributor_aggregate": {
      "text": "Based on 6 contributing organisations",
      "applies_to": ["total_available", "sector_breakdown", "asset_breakdown"]
    },
    "utilisation_rate": {
      "text": "Estimated from contributor subset with event-level delivery data",
      "applies_to": ["utilisation", "delivery_factor"]
    },
    "turn_up_capacity": {
      "text": "Includes load shifting; not new generation",
      "applies_to": ["turn_up", "implicit"]
    },
    "latent_potential": {
      "text": "Derived from public deployment data × average impact",
      "applies_to": ["latent_potential"]
    },
    "future_projections": {
      "text": "Based on NESO/government scenarios",
      "applies_to": ["future_potential"]
    },
    "k_threshold": {
      "text": "Range estimate due to limited contributors (k<3)",
      "applies_to": ["illustrative_values"]
    }
  },
  "data_quality": {
    "total_submissions": 7,
    "valid_submissions": 6,
    "validation_rate": 0.857,
    "average_completeness": 0.85,
    "average_quality": 0.986
  },
  "colors": {
    "primary": "#2E86AB",
    "secondary": "#A23B72",
    "tertiary": "#F18F01",
    "success": "#4CAF50",
    "warning": "#FF9800",
    "domestic": "#2E86AB",
    "ic": "#A23B72",
    "illustrative": "#FF9800"
  }
};

// Export for use by other modules
window.DASHBOARD_DATA = DASHBOARD_DATA;
