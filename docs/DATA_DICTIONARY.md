# Data dictionary and canonical fields

## initiatives.csv

| Canonical field | Meaning | Used by |
|---|---|---|
| initiative_id | Unique initiative key in `INIT-NNN` format | Joins, filters, scorecard, RAG metadata |
| name | Initiative display name | UI and reporting |
| type | Copilot, conversational bot, predictive model, etc. | Portfolio filtering |
| business_unit | Owning business unit | Portfolio reporting |
| go_live_date | Initiative go-live date | Months live |
| licensed_users | Eligible/licensed user denominator | Adoption |
| planned_annual_benefit | Planned annual value in USD | Run-rate versus plan |
| currency | Supplied currency | Validation; current practice set uses USD |

## weekly_usage.csv

| Canonical field | Meaning | Used by |
|---|---|---|
| initiative_id | Initiative key | Join |
| week_start | Start date of usage week | First/latest available usage week |
| metric_name | Canonicalised to `weekly_active_users` | Metric validation |
| value | Numeric WAU | Adoption and WAU change |

## financials.xlsx

| Canonical field | Meaning | Used by |
|---|---|---|
| initiative_id | Initiative key | Join |
| report_date | Financial reporting date | As-of cutoff |
| measure | `benefit_to_date`, `cost_to_date`, or ignored `reported_roi_pct` | ROI, benefit and cost metrics |
| value | Numeric USD after parsing | Financial calculations |
| unit | USD or USD '000 | Unit normalisation |
| basis | Cumulative or monthly | Monthly cost aggregation |

## Charter chunk metadata

`dataset_id`, `initiative_id`, `source_filename`, `section`, `page_number`, `chunk_id`, `content`, and `contains_instruction_like_text`.
