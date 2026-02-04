# Contributing Data to FlexDash

## Overview

The ADE Flexibility Dashboard aggregates data from energy sector participants to provide a comprehensive view of GB flexibility. This guide explains how organisations can contribute their data.

For day-to-day operations (drop in new returns and re-run the pipeline), see `docs/WORKFLOW.md`.

## Who Can Contribute

We welcome data from:
- Energy suppliers with flexibility portfolios
- Flexibility aggregators
- Distribution System Operators (DSOs)
- National Energy System Operator (NESO)
- Other flexibility service providers

## Data Requirements

### Minimum Data

At minimum, we need:
- **Asset Portfolio**: Types and counts of flexible assets
- **Capacity Data**: Available flexibility capacity (MW)
- **Sector Classification**: Domestic or I&C

### Preferred Data

Additional valuable data includes:
- **Delivered Volumes**: Actual flexibility dispatched (MW/MWh)
- **Service Participation**: Which services assets are registered for
- **Geographic Distribution**: DNO region breakdown
- **Temporal Profiles**: When flexibility was delivered

## Data Template

Download the ADE Data Template V1.2 from the project repository or contact the ADE Data Lab team.

The template includes four sheets:
1. **Metadata**: Your organisation details and submission period
2. **Asset Portfolio**: Flexible asset inventory
3. **Flexibility Events**: Historical dispatch records
4. **Service Participation**: Service registrations

## How to Submit

1. Complete the data template
2. Email to: [data@theade.co.uk](mailto:data@theade.co.uk)
3. We'll validate and confirm receipt within 5 working days

## Data Protection

### Confidentiality

Your data is protected by:
- k-anonymity threshold (minimum 3 contributors per cell)
- Dominance rules (no single contributor > 85%)
- Rounding to reduce precision
- No organisation names in published data

### Data Handling

- Raw data is stored securely and never shared
- Only aggregated, anonymised statistics are published
- You can request deletion of your data at any time

### Audit Trail

All data transformations are logged for regulatory compliance. Audit logs do not identify individual contributors.

## Timeline

### Phase 1 (Current)

- Study period: Nov 2024-Feb 2025
- Submission deadline: Ongoing
- Publication: Quarterly updates

### Future Phases

We plan to expand coverage and frequency. Contributors will be consulted on methodology changes.

## Support

For questions about contributing:
- Email: [data@theade.co.uk](mailto:data@theade.co.uk)
- Visit: [theade.co.uk](https://www.theade.co.uk)

## FAQ

**Q: Will my competitors see my data?**
A: No. Only aggregated statistics are published. Individual contributor data is never disclosed.

**Q: What if I can't complete all fields?**
A: Partial submissions are valuable. Complete what you can, and we'll include it where disclosure rules permit.

**Q: Can I see my contribution in the dashboard?**
A: Not directly, as data is aggregated. However, you can verify your data influenced totals where you're one of 3+ contributors.

**Q: How often should I submit?**
A: We recommend quarterly updates, though annual submissions are also accepted.

**Q: What format should data be in?**
A: Use the Excel template provided. If you have data in a different format, contact us to discuss.



