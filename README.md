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
├── src/                    # Python data pipeline
│   ├── ingestion/         # Data loading and validation
│   ├── governance/        # Anonymisation and disclosure control
│   ├── analysis/          # Aggregation and metrics
│   └── export/            # Dashboard data generation
├── dashboard/             # Interactive HTML dashboard
├── config/                # Configuration files
├── docs/                  # Documentation
├── tests/                 # Unit tests
└── scripts/               # Orchestration scripts
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

# Generate dashboard data only
python scripts/generate_dashboard.py
```

### Viewing the Dashboard

Open `dashboard/index.html` in a web browser.

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
