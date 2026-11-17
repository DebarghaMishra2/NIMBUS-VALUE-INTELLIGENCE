# Metric definitions, assumptions and clarification log

## Metric definitions in our own words (FR-01)

1. **Adoption** - the latest available week's active users divided by the initiative's licensed-user population. This is a ratio, displayed as a percentage.
2. **Weekly active user change** - the relative change from the first available week to the latest available week: (latest WAU - first WAU) / first WAU. The benchmark supplies a three-week window; if a middle week is absent, the first and latest available observations are still used.
3. **Return on investment (ROI)** - realised benefit accumulated to the reporting date, less total cost accumulated to the reporting date, divided by total cost. A positive ratio means benefit exceeds cost; a negative ratio means cost exceeds benefit.
4. **Average monthly benefit** - realised benefit to date divided by elapsed months since go-live.
5. **Payback period** - total cost to date divided by average monthly benefit. If average monthly benefit is zero or unavailable, payback is unavailable.
6. **Run-rate versus plan** - average monthly benefit annualised (multiplied by 12) divided by planned annual benefit.
7. **Portfolio status** - Green when adoption is at least 60% and ROI is above zero; Red when adoption is below 30% or ROI is below zero; Amber for every other valid combination.

## Benchmark assumptions supplied with the Nimbus practice data

- Reporting/as-of date: **2026-11-15** (the end of the latest usage week in the practice dataset).
- Months live: elapsed calendar days from go-live to as-of date divided by **30.44**.
- Numeric dates are interpreted day-first (DD/MM/YYYY). ISO dates are parsed as ISO before applying day-first parsing to other formats.
- All monetary amounts are USD. A unit containing `000` (for example, `USD '000`) means the numeric value is in thousands and must be multiplied by 1,000.
- Benefit measure aliases are standardised to `benefit_to_date`: `Benefit to date`, `realised_benefit`, `value_delivered`.
- Cost measure aliases are standardised to `cost_to_date`: `Cost to date`, `total_cost`, `spend`, `monthly_cost`.
- Monthly cost records are summed to cost-to-date through the reporting date.
- `reported_roi_pct` is not a valid source for the scorecard. It is ignored; ROI is recomputed from benefit and cost.
- WAU aliases are standardised to `weekly_active_users`.
- Exact duplicate usage rows are removed.
- A negative WAU value in this synthetic practice dataset is documented as a sign typo and converted to its absolute value. This must not be generalised to other enterprise datasets without confirmation.
- A usage value greater than licensed users is treated as invalid and excluded, with the reason logged.
- When a middle usage week is missing, WAU change uses first and latest available valid weeks; the missing observation is logged, not imputed.
- No answer-key file is read by the production ingestion, cleaning, scorecard or retrieval paths. Answer keys are used only by the offline evaluation script.

## One material client clarification question (FR-01)

**For live Nimbus reporting, should all `basis = monthly` cost rows be treated as additive monthly actuals and summed through the report date, while any `basis = cumulative` rows are treated as already-to-date totals (and never added to monthly rows for the same cost period)?**

The practice dataset's answer key assumes monthly cost rows are summed and that the relevant initiative has those monthly rows instead of a single cumulative total. This question should be confirmed before applying the logic to production finance feeds.

## Additional implementation assumptions

- The supplied benchmark date remains the default in the app so its scorecard can be reproduced. The user may choose another as-of date, but only records on or before that date are considered.
- An initiative with insufficient inputs is labelled `Insufficient data` by the application instead of forcing an unsupported Green/Amber/Red label. All benchmark rows have the required inputs and should match the supplied G/A/R answer key.
- Currency conversion is not performed. The supplied data says all money is USD. Multi-currency support requires an approved FX source and reporting-date convention.
- The document assistant uses only extracted charter passages. No general-model knowledge is used to fill missing facts.
- Recommendations are prompts for human review only. The app does not change source data, approve funding or execute portfolio decisions.
