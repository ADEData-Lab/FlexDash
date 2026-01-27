# FlexDash Methodology

## Overview

This document describes the methodology used to calculate flexibility metrics for the ADE Flexibility Dashboard.

## Data Collection

### Data Sources

Data is collected from:
- **Energy Suppliers**: Customer flexibility portfolios (domestic)
- **Aggregators**: Flexibility service providers (domestic and I&C)
- **DSOs**: Network flexibility events and contracts
- **NESO**: National system operator data

### Data Template

Contributors submit data using the standardised ADE Data Template V1.2, which includes:

1. **Metadata Sheet**: Organisation details, submission date, coverage period
2. **Asset Portfolio Sheet**: Flexible asset inventory with capacity and counts
3. **Flexibility Events Sheet**: Historical flexibility dispatches
4. **Service Participation Sheet**: Registered services and delivered volumes

## Metric Definitions

### Total Available Capacity (MW)

The sum of all registered flexible capacity across the portfolio:

```
Total Available = Σ (Asset Capacity × Asset Count)
```

Where:
- Asset Capacity = Rated capacity of individual asset type (MW)
- Asset Count = Number of assets of that type

### Total Delivered Capacity (MW)

The sum of flexibility actually dispatched during the study period:

```
Total Delivered = Σ (Event Capacity × Event Duration / Study Period Hours)
```

### Delivery Factor (%)

The ratio of delivered to available capacity:

```
Delivery Factor = (Total Delivered / Total Available) × 100
```

## Aggregation Methodology

### Sector Classification

Assets are classified into two sectors:

**Domestic**
- Electric Vehicle Chargers
- Heat Pumps
- Home Battery Storage
- Smart Hot Water
- Wet Appliances

**Industrial & Commercial (I&C)**
- Cold Storage
- Water Treatment
- Manufacturing Processes
- Commercial HVAC
- Commercial Battery Storage
- Backup Generation
- EV Fleet Charging

### Geographic Aggregation

Data is aggregated to DNO/DSO region level. Site-level data is never published.

### Temporal Aggregation

Data is aggregated to annual totals for Phase 1. Monthly breakdowns will be available in future releases when data permits.

## Statistical Treatment

### Missing Data

Missing values are handled as follows:
- **Required fields**: Submission flagged for follow-up
- **Optional fields**: Excluded from calculations for that metric
- **Partial submissions**: Included with completeness score

### Outlier Detection

Values outside plausible ranges are flagged:
- Capacity: 0 - 10,000 MW per submission
- Counts: 0 - 10,000,000 assets
- Duration: 0 - 8,760 hours (1 year)

Outliers are reviewed manually before inclusion.

### Rounding

All published values are rounded to reduce precision:
- Capacity: Nearest 10 MW
- Energy: Nearest 10 MWh
- Counts: Nearest 10
- Percentages: Nearest 1%

## Disclosure Control

See [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) for full disclosure control methodology.

Key parameters:
- k-anonymity threshold: 3 contributors
- Dominance threshold: Top 2 < 85%
- Geographic maximum: DNO region level

## Limitations

### Data Coverage

- Not all flexibility providers contribute data
- Voluntary participation may introduce selection bias
- Historical data completeness varies by contributor

### Methodology Constraints

- Asset classification may vary between contributors
- Capacity definitions may differ (e.g., nameplate vs. available)
- Double-counting possible where assets serve multiple markets

### Future Improvements

Planned methodology enhancements:
- Temporal profiles (hourly/half-hourly)
- Regional breakdowns (where data permits)
- Service-specific analysis
- Trend analysis across multiple study periods

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-27 | Initial methodology |

## References

- ADE Methodology v7 (internal document)
- Ofgem Flexibility Market Guidance
- BEIS Flexibility Statistics
