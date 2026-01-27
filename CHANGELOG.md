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
