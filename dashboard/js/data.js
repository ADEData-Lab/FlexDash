/**
 * FlexDash Embedded Dashboard Data
 *
 * This file contains the dashboard data embedded directly to allow
 * the dashboard to work when opened as a local file (file:// protocol).
 *
 * Generated: 2026-01-27
 */

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
      "asset_class": "battery_storage",
      "capacity_mw": 100,
      "capacity_mw_illustrative": false,
      "count": 19530,
      "count_illustrative": false
    },
    {
      "asset_class": "cold_storage",
      "capacity_mw": 40,
      "capacity_mw_illustrative": true,
      "count": 20,
      "count_illustrative": true
    },
    {
      "asset_class": "commercial_battery",
      "capacity_mw": 80,
      "capacity_mw_illustrative": true,
      "count": 10,
      "count_illustrative": true
    },
    {
      "asset_class": "ev_charger",
      "capacity_mw": 4450,
      "capacity_mw_illustrative": false,
      "count": 635420,
      "count_illustrative": false
    },
    {
      "asset_class": "heat_pump",
      "capacity_mw": 0,
      "capacity_mw_illustrative": true,
      "count": 80,
      "count_illustrative": true
    },
    {
      "asset_class": "ic_mixed",
      "capacity_mw": 8810,
      "capacity_mw_illustrative": true,
      "count": 270,
      "count_illustrative": true
    },
    {
      "asset_class": "manufacturing",
      "capacity_mw": 70,
      "capacity_mw_illustrative": true,
      "count": 100,
      "count_illustrative": true
    },
    {
      "asset_class": "other",
      "capacity_mw": 180,
      "capacity_mw_illustrative": true,
      "count": 36400,
      "count_illustrative": true
    },
    {
      "asset_class": "water_treatment",
      "capacity_mw": 30,
      "capacity_mw_illustrative": true,
      "count": 90,
      "count_illustrative": true
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
