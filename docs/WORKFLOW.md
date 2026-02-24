# FlexDash workflow (Phase 1)

This note documents the intended **day-to-day workflow** for keeping the dashboards up to date as new template returns arrive.

## Where to put data returns

By default, the pipeline reads Excel returns from:

- `../02 DATA RECEIVED` (relative to the `FlexDash/` repo root)

You can change this by editing `config/settings.yaml` (`source_data`) or passing an alternate config to `scripts/run_pipeline.py`.

## The drop-in and rerun loop

### Non-template TOU returns (automatic normalisation)

If a return arrives in a non-template layout for TOU or implicit flexibility, the pipeline will try to generate a sidecar workbook named `*_NORMALISED_V1.2.xlsx` in the same folder. The parser will prefer the normalised workbook and skip the raw input to prevent double-counting.

If the sidecar looks wrong, treat it as generated output. Fix the raw return (or request a template-shaped return) and re-run the pipeline.

When a new return arrives:

1. Save the `.xlsx` in `02 DATA RECEIVED`
2. Run the pipeline:

   - `python scripts/run_pipeline.py`

3. Re-open the dashboards in your browser

The pipeline regenerates dashboard data files under `dashboard/` and refreshes the standalone HTML builds.

## What gets generated

### Public dashboard

- `dashboard/index.html` (UI shell; does not change when you run the pipeline)
- `dashboard/js/data.js` (embedded data produced by the latest pipeline run)
- `dashboard/public_dashboard_standalone.html` (single-file build for offline sharing)
- `dashboard/public_dashboard_standalone_release_safe.html` (single-file build for steering-group sharing; safe splits only, no ranges or k-signals)
- `dashboard/public_dashboard_standalone_steering_safe.html` (single-file build for steering-group circulation; aggregates only, no breakdowns)

Use the release-safe build when you want some limited splits, and fall back to the steering-safe build when you need aggregates only.

### Admin QA outputs (strictly confidential)

The pipeline also produces admin-only artefacts to help troubleshoot parsing and completeness:

- `reports/admin/ingestion_coverage_latest.md` (per-file what we ingested checklist)
- `reports/admin/validation_report_latest.md` (annotated admin validation report)
- `reports/admin/dashboard/admin_validation_dashboard.html` (single-file admin dashboard)

These admin outputs may include contributor-level values and must not be circulated outside the authorised project team.

## Common reasons the admin dashboard requests manual review

These are the most common causes of manual review flags and missing values in the public dashboard:

- **No numeric values in Part 3.2 (MW):** the submission includes counts and/or ToU information, but provides no coincident/deduplicated MW capacity. In that case, the dashboard treats MW capacity as missing (it is not inferred from counts).
- **ToU Part 4.2 provided but Part 4.3 missing:** ToU period totals can be used for **energy (GWh)** reporting, but without Part 4.3 busiest-half-hour **MWh** we cannot derive **implicit MW** capacity.
- **ToU Part 4.3 MW blank/zero:** if Part 4.3 busiest-half-hour MWh is provided but the MW columns are blank or 0 (common placeholder), the pipeline derives MW automatically.

## What to check when something looks wrong

1. Open the ingestion coverage report: `reports/admin/ingestion_coverage_latest.md`
2. Confirm each file shows the expected sections as Yes (especially Part 3.2 for MW)
3. Review warnings listed per submission
4. If a number looks implausible, check unit conventions (kW vs MW) and confirm the contributor did not enter totals in a notes cell that the parser is accidentally treating as data.



