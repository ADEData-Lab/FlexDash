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

### Data Sources
- British Gas - Data Template V1.2
- Axle Data Template V1.2
- Pod Point (PP) Data Template V1.2
- Flexitricity data submission
- Octopus Energy (OE) ADE Response
- C-U-B CLF Data Sheet (new)
- ENEL ADE Demand Data (new)

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

**Data Files Identified:**
1. British Gas - Data Template V1.2.xlsx
2. Axle Data Template V1.2 (1).xlsx
3. PP Data Template V1.2.xlsx
4. 20251119_flexitricity_flex_dashboard_data.xlsx
5. OE_ADE_Response.xlsx
6. C-U-B CLF Data Sheet.xlsx
7. ENEL ADE - Demand Data.xlsx
8. Merged Data Template V1.2.xlsx (combined)

### 2025-01-27 - Pipeline Testing & Debugging

**Actions:**
- Ran initial pipeline test - identified data structure issues
- Rewrote template_parser.py with custom parsers for each data format
- Fixed Octopus parser to handle variable column counts
- Fixed type conversion errors in count fields
- Rewrote run_pipeline.py with inline disclosure control
- Updated all unit tests to match new implementation

**Pipeline Results (Successful Run):**
- 7 data files parsed
- 37 asset records from 6 contributors
- 13,760 MW total capacity
- Domestic: 4,550 MW (k=4 contributors) - SAFE
- I&C: 9,210 MW (k=3 contributors) - SAFE
- Both sectors meet k≥3 disclosure threshold

**Test Results:**
- 25 tests passed (all green)
- Fixed asset type mapping order (cold before storage)
- Fixed dominance rule assertion text
- Rewrote ingestion tests for new parser methods

**Key Fixes:**
1. Data flow: Aggregation now happens inline with disclosure checks
2. Column handling: Dynamic column naming for variable Excel formats
3. Type safety: Try/except for string-to-numeric conversions
4. Pattern order: Check 'cold' before 'storage' in asset mapping
