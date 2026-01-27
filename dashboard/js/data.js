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
  "version": "1.0.0",
  "study_period": "2024-2025",
  "metrics": {
    "total_available_mw": 13760,
    "total_delivered_mw": 0,
    "delivery_factor_pct": 0,
    "contributor_count": 6,
    "domestic": {
      "available_mw": 4550,
      "delivered_mw": 0
    },
    "ic": {
      "available_mw": 9210,
      "delivered_mw": 0
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
    "headline": "This dashboard presents flexibility data from 6 contributing organisations for the study period 2024-2025. Total available flexibility capacity is 13,760 MW.",
    "sector": "Domestic flexibility accounts for 33% of total capacity (4,550 MW), with I&C contributing 67% (9,210 MW).",
    "delivery": "Delivery factor data is not yet available.",
    "coverage": "Data for this dashboard was provided by 6 organisations. Where fewer than 3 contributors exist for a metric, illustrative values are shown to protect commercial confidentiality."
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
