# FlexDash Data Governance Policy

## 1. Purpose

This document sets out the data governance framework for the ADE Flexibility Dashboard project. It ensures that commercially sensitive data from contributing organisations is protected while enabling meaningful aggregate statistics to be published.

## 2. Scope

This policy applies to:
- All data received from flexibility service providers
- All data processing within the FlexDash pipeline
- All published outputs including the dashboard and reports
- All personnel with access to raw or processed data

## 3. Legal Framework

### 3.1 Competition Law Compliance

The disclosure of individual company data could facilitate anti-competitive behaviour. This governance framework ensures:

- No individual contributor's commercial position can be inferred
- Market share information is not derivable from published statistics
- Pricing and contractual information is never disclosed

### 3.2 GDPR Considerations

While this project primarily handles organisational (not personal) data, any personal data encountered will be:
- Processed only for the stated purpose
- Minimised to what is necessary
- Protected with appropriate security measures
- Deleted when no longer required

## 4. Data Classification

### 4.1 Confidential (RAW)
- Original data submissions from contributors
- Contains identifiable organisation information
- Never published or shared externally
- Access restricted to authorised analysts

### 4.2 Internal (PROCESSED)
- Standardised and validated data
- Organisation identifiers replaced with pseudonyms
- Used for analysis and quality checking
- Not published externally

### 4.3 Public (ANONYMISED)
- Aggregated statistics meeting disclosure thresholds
- No organisation identifiable
- Safe for publication on dashboard
- May be shared freely

## 5. Statistical Disclosure Control

### 5.1 k-Anonymity Threshold

**Minimum contributors per cell: k = 3**

Any published statistic must aggregate data from at least 3 distinct contributors. This prevents:
- Identification through small cell sizes
- Differencing attacks (subtracting known values)
- Inference from marginal totals

### 5.2 Dominance Rule

A cell is suppressed if the top 2 contributors account for more than 85% of the total value. This prevents identification of dominant market participants.

### 5.3 Rounding

All published values are rounded to reduce precision:
- Capacity (MW): nearest 10 MW
- Energy (MWh): nearest 10 MWh
- Counts: nearest 10
- Percentages: nearest 1%

### 5.4 Suppression Strategy

When a cell fails disclosure checks:

1. **Primary action**: Suppress the cell (show as "-" or "N/A")
2. **Secondary action**: If suppression creates inference risk, use illustrative data
3. **Illustrative data**: Clearly labelled estimates based on sector averages

## 6. Anonymisation Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    ANONYMISATION PIPELINE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  RAW DATA                                                        │
│     │                                                            │
│     ▼                                                            │
│  ┌──────────────────┐                                           │
│  │  1. VALIDATION   │  Check completeness, data types, ranges   │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────┐                                           │
│  │ 2. PSEUDONYMISE  │  Replace org names with random IDs        │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────┐                                           │
│  │ 3. STANDARDISE   │  Map to taxonomy, normalise units         │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────┐                                           │
│  │  4. AGGREGATE    │  Sum/average by dimension                 │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────┐                                           │
│  │ 5. DISCLOSURE    │  Check k-threshold, dominance, apply      │
│  │    CONTROL       │  suppression or illustrative data         │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ┌──────────────────┐                                           │
│  │  6. ROUNDING     │  Apply precision reduction                │
│  └────────┬─────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  ANONYMISED OUTPUT                                               │
│                                                                  │
│  ════════════════════════════════════════════════════════════   │
│                        AUDIT LOG                                 │
│  (Records all decisions, contributor counts, suppressions)       │
└─────────────────────────────────────────────────────────────────┘
```

## 7. Illustrative Data

### 7.1 When Used

Illustrative data is used when:
- Fewer than 3 contributors exist for a dimension
- Real data would reveal individual positions
- Suppression would leave gaps that harm understanding

### 7.2 Generation Method

Illustrative values are derived from:
- Published industry research and benchmarks
- Aggregated patterns from compliant cells
- Expert judgment within plausible ranges

### 7.3 Labelling

All illustrative data MUST be clearly marked:
- Dashboard: Orange warning badge with "Illustrative" label
- Reports: Footnotes explaining illustrative nature
- Data exports: Column flag indicating data type

## 8. Audit Trail

### 8.1 Logged Information

The pipeline logs:
- Timestamp of each processing run
- Files ingested and validation results
- Contributor counts per dimension (internal only)
- Disclosure decisions (suppress/illustrative/safe)
- Any manual overrides or corrections

### 8.2 Retention

Audit logs are retained for 12 months after publication.

### 8.3 Access

Audit logs are accessible only to:
- ADE Data Lab analysts
- Project steering group on request
- Regulators if legally required

## 9. Roles and Responsibilities

### 9.1 Data Controller
**Association for Decentralised Energy**
- Determines purposes of processing
- Ensures compliance with this policy
- Responds to data subject requests

### 9.2 Data Processor
**ADE Data Lab Team**
- Implements technical safeguards
- Operates the data pipeline
- Maintains audit trail

### 9.3 Steering Group
- Approves methodology and thresholds
- Reviews disclosure decisions
- Provides governance oversight

## 10. Data Retention

| Data Type | Retention Period | Disposal Method |
|-----------|-----------------|-----------------|
| Raw submissions | Project duration + 6 months | Secure deletion |
| Processed data | Project duration + 6 months | Secure deletion |
| Anonymised outputs | Indefinite | Public archive |
| Audit logs | 12 months post-publication | Secure deletion |

## 11. Incident Response

### 11.1 Data Breach

If a potential disclosure of confidential data is identified:

1. Immediately suspend publication of affected outputs
2. Notify steering group within 24 hours
3. Assess scope and impact
4. Notify affected contributors if material
5. Implement remediation measures
6. Document lessons learned

### 11.2 Methodology Error

If an error in disclosure control is discovered:

1. Assess whether published data is affected
2. If affected, issue correction notice
3. Republish corrected data
4. Update pipeline to prevent recurrence

## 12. Review

This policy will be reviewed:
- Annually, or
- When methodology changes, or
- Following any incident

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-27 | ADE Data Lab | Initial version |

**Approval**

Approved by: Flex Dashboard Steering Group
Date: [Pending]
