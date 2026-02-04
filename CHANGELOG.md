# Changelog

All notable changes to the FlexDash project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Initial project structure and repository setup
- Data governance framework with k=3 disclosure threshold
- Python data pipeline for Excel template ingestion
- Interactive HTML dashboard with Chart.js visualisations
- Configuration files for disclosure rules and taxonomy
- Comprehensive documentation

### Data sources (high level)
- Multiple ADE Template V1.2 submissions (mixed domestic and I&C)
- One supplier Time-of-Use submission (normalised into the V1.2 layout for parsing)
- One industry-level I&C summary table (custom format)

---

## Development Log

### 2025-01-27 - Project Initialisation

**Actions:**
- Cloned empty GitHub repository from ADEData-Lab/FlexDash
- Created folder structure per approved plan
- Implemented core Python modules for data ingestion
- Built data governance layer with k-threshold checks
- Created interactive dashboard with ADE branding
- Documented data governance policy

**Design Decisions:**
- Static HTML dashboard (no server required)
- Single anonymised view for all users
- Chart.js for visualisations (lightweight, accessible)
- k=3 disclosure threshold per steering group guidance
- Rounding to nearest 10 MW/MWh for additional protection

**Data files (pseudonymised examples):**
1. Template_V1.2_Return_01.xlsx
2. Template_V1.2_Return_02.xlsx
3. Template_V1.2_Return_03.xlsx
4. Industry_Summary_Table.xlsx
5. Supplier_ToU_Return.xlsx

### 2025-01-27 - Pipeline Testing & Debugging

**Actions:**
- Ran initial pipeline test and iterated parsing and validation
- Implemented routing and parsing for multiple submission layouts
- Fixed supplier ToU normalisation to handle variable column counts
- Fixed type conversion errors in count fields
- Rewrote run_pipeline.py orchestration and export outputs
- Updated unit tests to match implementation

**Test Results:**
- Automated ingestion and disclosure tests passing

**Key Fixes:**
1. Data flow: Aggregation happens with disclosure checks and audit logging
2. Column handling: Dynamic column naming for variable Excel layouts
3. Type safety: Robust string-to-numeric conversions
4. Mapping: Consistent asset taxonomy mapping for domestic and I&C categories
