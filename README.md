# FlexDash - ADE Flexibility Dashboard

A production-grade data pipeline and interactive dashboard for the Association for Decentralised Energy (ADE) Flexibility Dashboard project.

## Overview

FlexDash processes flexibility data from UK energy sector participants to produce anonymised, publication-ready statistics and visualisations. The system implements robust data governance to protect commercially sensitive information while enabling transparency in the flexibility market.

## Key Features

- **Data Pipeline**: Ingests Excel templates from 7+ energy sector contributors
- **Data Governance**: Competition law compliance with k=3 disclosure threshold
- **Statistical Safeguarding**: Cell suppression, rounding, and illustrative data generation
- **Interactive Dashboard**: HTML/CSS/JS with filtering, charts, and narrative insights
- **Audit Trail**: Full logging of all data transformations

## Project Structure

```
FlexDash/
|-- src/                    # Python data pipeline
|   |-- ingestion/          # Data loading and validation
|   |-- governance/         # Anonymisation and disclosure control
|   |-- analysis/           # Aggregation and metrics
|   `-- export/             # Dashboard data generation
|-- dashboard/              # Interactive HTML dashboard
|-- config/                 # Configuration files
|-- docs/                   # Documentation
|-- tests/                  # Unit tests
`-- scripts/                # Orchestration scripts
```

## Quick Start

### Prerequisites

- Python 3.9+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/ADEData-Lab/FlexDash.git
cd FlexDash

# Install dependencies
pip install -r requirements.txt
```

### Running the Pipeline

```bash
# Process data and generate dashboard
python scripts/run_pipeline.py
```

### Viewing the Dashboard

FlexDash produces two public-friendly entrypoints:

- `dashboard/index.html` (multi-page dashboard; loads the latest pipeline output via `dashboard/js/data.js`)
- `dashboard/public_dashboard_standalone.html` (single-file build for offline sharing)

Open either file in a web browser. No server is required.

### Updating with new returns (drop-in workflow)

By default, the pipeline reads contributor returns from the folder next to the repo:

- `../02 DATA RECEIVED` (relative to `FlexDash/`)

When new returns arrive:

1. Drop the new `.xlsx` files into `02 DATA RECEIVED`
2. Run `python scripts/run_pipeline.py`
3. Re-open the dashboard file(s) in your browser

The pipeline regenerates the data outputs under `dashboard/` and refreshes the standalone HTML.

Note: If a return arrives in a non-template TOU or implicit flexibility layout, the pipeline will try to generate a `*_NORMALISED_V1.2.xlsx` sidecar workbook and will prefer it over the raw file to prevent double-counting.

### Admin QA outputs (not for circulation)

The pipeline also generates admin-only QA artefacts to help spot parsing gaps and missing sections:

- `reports/admin/ingestion_coverage_latest.md` (per-file checklist)
- `reports/admin/validation_report_latest.md` (annotated report)
- `reports/admin/dashboard/admin_validation_dashboard.html` (single-file admin dashboard)

These outputs may include contributor-level values and must not be circulated outside the authorised team.

## Data Governance

This project implements strict data governance to protect contributor confidentiality:

- **k-anonymity threshold**: Minimum 3 contributors per published cell
- **Rounding**: Values rounded to nearest 10 MW/MWh
- **Suppression**: Unsafe cells are suppressed or replaced with illustrative data
- **Audit logging**: All transformations are logged for regulatory compliance

See [docs/DATA_GOVERNANCE.md](docs/DATA_GOVERNANCE.md) for full governance policy.

## Data Contributors

This dashboard aggregates data from energy sector participants including:
- Energy suppliers
- Flexibility aggregators
- Distribution System Operators
- National Energy System Operator

Individual contributor data is never disclosed.

## Documentation

- [Data Governance Policy](docs/DATA_GOVERNANCE.md)
- [Methodology](docs/METHODOLOGY.md)
- [Asset Taxonomy](docs/TAXONOMY.md)
- [Contributing Data](docs/CONTRIBUTING.md)

## Development

### Running Tests

```bash
pytest tests/
```

### Code Structure

- `src/ingestion/`: Parse V1.2 Excel templates and custom formats
- `src/governance/`: Apply disclosure controls and anonymisation
- `src/analysis/`: Calculate metrics and aggregations
- `src/export/`: Generate JSON for dashboard consumption

## License

Copyright (c) 2025 Association for Decentralised Energy. All rights reserved.

## Contact

For questions about this project, contact the ADE Data Lab team.






