from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import pandas as pd
import numpy as np
from .utils import normalize_id, parse_date, parse_number, normalise_title

AS_OF_DEFAULT = date(2026, 11, 15)
BENEFIT_ALIASES = {
    "benefit_to_date": "benefit_to_date",
    "benefit to date": "benefit_to_date",
    "realised_benefit": "benefit_to_date",
    "realized_benefit": "benefit_to_date",
    "value_delivered": "benefit_to_date",
}
COST_ALIASES = {
    "cost_to_date": "cost_to_date",
    "cost to date": "cost_to_date",
    "total_cost": "cost_to_date",
    "spend": "cost_to_date",
    "monthly_cost": "cost_to_date",
}
WAU_ALIASES = {"wau", "weekly_active_users", "weekly active users", "active users (weekly)"}

@dataclass
class CleanResult:
    initiatives: pd.DataFrame
    usage: pd.DataFrame
    financials: pd.DataFrame
    benefit_by_id: dict[str, float]
    cost_by_id: dict[str, float]
    change_log: list[dict]
    as_of_date: date
    source_files: dict[str, str]


def _log(log, *, rule, file, record, field, old, new, effect, severity="info"):
    log.append({
        "rule": rule, "source_file": file, "record": str(record), "field": field,
        "old_value": str(old), "new_value": str(new), "effect": effect,
        "severity": severity,
    })


def _normalise_field(value, fn, log, rule, file, record, field, effect):
    new = fn(value)
    if str(new) != str(value):
        _log(log, rule=rule, file=file, record=record, field=field,
             old=value, new=new, effect=effect)
    return new


def clean_dataset(dataset_dir: Path, as_of_date: date = AS_OF_DEFAULT) -> CleanResult:
    dataset_dir = Path(dataset_dir)
    log: list[dict] = []
    source_files = {
        "initiatives": "raw/initiatives.csv",
        "usage": "raw/weekly_usage.csv",
        "financials": "raw/financials.xlsx",
    }

    # Initiatives master
    ini_raw = pd.read_csv(dataset_dir / "raw/initiatives.csv", dtype=object)
    ini_rows = []
    for idx, row in ini_raw.iterrows():
        r = row.to_dict()
        old_id = r["initiative_id"]
        iid = _normalise_field(old_id, normalize_id, log, "ID_NORMALIZED", source_files["initiatives"], idx + 2, "initiative_id", "Joined variant identifiers to one initiative key.")
        old_name = r["name"]
        name = normalise_title(old_name)
        if name != str(old_name):
            _log(log, rule="NAME_NORMALIZED", file=source_files["initiatives"], record=idx + 2,
                 field="name", old=old_name, new=name, effect="Standardized presentation name; no KPI input changed.")
        old_date = r["go_live_date"]
        go_live = parse_date(old_date)
        if str(old_date).strip() != go_live.isoformat():
            _log(log, rule="DATE_NORMALIZED", file=source_files["initiatives"], record=idx + 2,
                 field="go_live_date", old=old_date, new=go_live.isoformat(),
                 effect="Enabled reproducible months-live and monthly-benefit calculations.")
        licensed = parse_number(r["licensed_users"])
        if str(licensed) != str(r["licensed_users"]):
            _log(log, rule="NUMERIC_NORMALIZED", file=source_files["initiatives"], record=idx + 2,
                 field="licensed_users", old=r["licensed_users"], new=licensed,
                 effect="Converted text-formatted user count to numeric for adoption denominator.")
        planned = parse_number(r["planned_annual_benefit"])
        if str(planned) != str(r["planned_annual_benefit"]):
            _log(log, rule="NUMERIC_NORMALIZED", file=source_files["initiatives"], record=idx + 2,
                 field="planned_annual_benefit", old=r["planned_annual_benefit"], new=planned,
                 effect="Converted planned annual benefit to numeric USD for run-rate comparison.")
        ini_rows.append({**r, "initiative_id": iid, "name": name, "go_live_date": go_live,
                         "licensed_users": licensed, "planned_annual_benefit": planned,
                         "currency": str(r.get("currency", "USD")).strip().upper()})
    initiatives = pd.DataFrame(ini_rows)
    if initiatives["initiative_id"].duplicated().any():
        dups = initiatives[initiatives["initiative_id"].duplicated(keep=False)]["initiative_id"].tolist()
        raise ValueError(f"Duplicate initiative identifiers after normalization: {dups}")

    licensed_map = initiatives.set_index("initiative_id")["licensed_users"].to_dict()

    # Weekly usage
    usage_raw = pd.read_csv(dataset_dir / "raw/weekly_usage.csv", dtype=object)
    before = len(usage_raw)
    usage_raw = usage_raw.drop_duplicates().copy()
    dropped = before - len(usage_raw)
    if dropped:
        _log(log, rule="EXACT_DUPLICATE_REMOVED", file=source_files["usage"], record="multiple",
             field="row", old=dropped, new=0, effect="Removed exact duplicate rows to prevent double-counting WAU.")
    usage_rows = []
    for idx, row in usage_raw.iterrows():
        r = row.to_dict()
        iid = _normalise_field(r["initiative_id"], normalize_id, log, "ID_NORMALIZED", source_files["usage"], idx + 2,
                               "initiative_id", "Joined identifier variants to the initiative master.")
        week = parse_date(r["week_start"])
        if str(r["week_start"]).strip() != week.isoformat():
            _log(log, rule="DATE_NORMALIZED", file=source_files["usage"], record=idx + 2,
                 field="week_start", old=r["week_start"], new=week.isoformat(), effect="Standardized weekly period for chronological comparisons.")
        metric = str(r["metric_name"]).strip().lower()
        if metric in WAU_ALIASES:
            if str(r["metric_name"]).strip() != "weekly_active_users":
                _log(log, rule="METRIC_ALIAS_MAPPED", file=source_files["usage"], record=idx + 2,
                     field="metric_name", old=r["metric_name"], new="weekly_active_users",
                     effect="Standardized usage metric name for consistent adoption calculations.")
            metric = "weekly_active_users"
        else:
            _log(log, rule="UNKNOWN_USAGE_METRIC", file=source_files["usage"], record=idx + 2,
                 field="metric_name", old=r["metric_name"], new="excluded",
                 effect="Unknown metric alias was excluded from the WAU scorecard.", severity="warning")
            continue
        value = parse_number(r["value"])
        if str(value) != str(r["value"]):
            _log(log, rule="NUMERIC_NORMALIZED", file=source_files["usage"], record=idx + 2,
                 field="value", old=r["value"], new=value, effect="Converted WAU to numeric for adoption and trend calculations.")
        if value < 0:
            corrected = abs(value)
            _log(log, rule="NEGATIVE_WAU_SIGN_CORRECTED", file=source_files["usage"], record=idx + 2,
                 field="value", old=value, new=corrected,
                 effect="Applied the practice-dataset assumption that negative WAU is a sign typo; correction is auditable.", severity="warning")
            value = corrected
        if iid not in licensed_map:
            _log(log, rule="UNKNOWN_INITIATIVE_EXCLUDED", file=source_files["usage"], record=idx + 2,
                 field="initiative_id", old=iid, new="excluded", effect="No matching initiative master record.", severity="error")
            continue
        if value > licensed_map[iid]:
            _log(log, rule="WAU_EXCEEDS_LICENSED_USERS", file=source_files["usage"], record=idx + 2,
                 field="value", old=value, new="excluded",
                 effect=f"WAU exceeds licensed users ({licensed_map[iid]:g}); invalid row excluded from all usage metrics.", severity="warning")
            continue
        usage_rows.append({"initiative_id": iid, "week_start": week, "metric_name": metric, "value": value})
    usage = pd.DataFrame(usage_rows, columns=["initiative_id", "week_start", "metric_name", "value"])
    if not usage.empty:
        # After ID/date normalization, remove duplicates that became identical.
        before = len(usage)
        usage = usage.drop_duplicates(subset=["initiative_id", "week_start", "metric_name", "value"])
        if len(usage) < before:
            _log(log, rule="NORMALIZED_DUPLICATE_REMOVED", file=source_files["usage"], record="multiple",
                 field="row", old=before-len(usage), new=0, effect="Removed rows that became duplicates after identifier/date normalization.")
        expected_weeks = sorted(usage["week_start"].unique())
        for iid in initiatives["initiative_id"]:
            present = set(usage.loc[usage.initiative_id == iid, "week_start"].tolist())
            for missing in expected_weeks:
                if missing not in present:
                    _log(log, rule="MISSING_USAGE_WEEK", file=source_files["usage"], record=iid,
                         field="week_start", old="missing", new=missing.isoformat(),
                         effect="Logged missing observation; WAU change uses first and latest available weeks per benchmark assumption.", severity="warning")
    usage = usage[usage.week_start <= as_of_date].copy() if not usage.empty else usage
    usage = usage.sort_values(["initiative_id", "week_start"]).reset_index(drop=True) if not usage.empty else usage

    # Financials
    fin_raw = pd.read_excel(dataset_dir / "raw/financials.xlsx", dtype=object)
    fin_rows = []
    for idx, row in fin_raw.iterrows():
        r = row.to_dict()
        iid = _normalise_field(r["initiative_id"], normalize_id, log, "ID_NORMALIZED", source_files["financials"], idx + 2,
                               "initiative_id", "Joined financial record to the initiative master.")
        report_date = parse_date(r["report_date"])
        if str(r["report_date"]).strip() != report_date.isoformat():
            _log(log, rule="DATE_NORMALIZED", file=source_files["financials"], record=idx + 2,
                 field="report_date", old=r["report_date"], new=report_date.isoformat(), effect="Standardized financial reporting period.")
        measure_raw = str(r["measure"]).strip()
        measure_key = measure_raw.lower()
        if measure_key in BENEFIT_ALIASES:
            measure = "benefit_to_date"
        elif measure_key in COST_ALIASES:
            measure = "cost_to_date"
        elif measure_key == "reported_roi_pct":
            # Preserve it for mismatch logging, but never use it in governed calculations.
            val = parse_number(r["value"])
            fin_rows.append({"initiative_id": iid, "report_date": report_date, "measure": "reported_roi_pct",
                             "value": val, "unit": str(r.get("unit", "%")), "basis": str(r.get("basis", "cumulative")),
                             "raw_measure": measure_raw})
            _log(log, rule="PRECOMPUTED_ROI_IGNORED", file=source_files["financials"], record=idx + 2,
                 field="measure", old=measure_raw, new="ignored",
                 effect="Pre-computed ROI is excluded; the scorecard independently recomputes (benefit - cost) / cost.")
            continue
        else:
            _log(log, rule="UNKNOWN_FINANCIAL_MEASURE", file=source_files["financials"], record=idx + 2,
                 field="measure", old=measure_raw, new="excluded", effect="Measure is not in the approved benefit/cost mapping.", severity="warning")
            continue
        if measure_raw != measure:
            _log(log, rule="FINANCIAL_MEASURE_ALIAS_MAPPED", file=source_files["financials"], record=idx + 2,
                 field="measure", old=measure_raw, new=measure,
                 effect="Standardized financial measure to the governed benefit or cost definition.")
        value = parse_number(r["value"])
        if str(value) != str(r["value"]):
            _log(log, rule="FINANCIAL_VALUE_PARSED", file=source_files["financials"], record=idx + 2,
                 field="value", old=r["value"], new=value, effect="Parsed formatted financial value into numeric amount.")
        unit = str(r.get("unit", "USD")).strip()
        if "000" in unit:
            old_value = value
            value *= 1000
            _log(log, rule="USD_THOUSANDS_CONVERTED", file=source_files["financials"], record=idx + 2,
                 field="value", old=f"{old_value} {unit}", new=f"{value} USD", effect="Converted thousands of USD to USD before aggregation.")
        if report_date > as_of_date:
            _log(log, rule="FUTURE_FINANCIAL_EXCLUDED", file=source_files["financials"], record=idx + 2,
                 field="report_date", old=report_date.isoformat(), new="excluded", effect=f"Record is after reporting date {as_of_date.isoformat()}.", severity="warning")
            continue
        fin_rows.append({"initiative_id": iid, "report_date": report_date, "measure": measure,
                         "value": value, "unit": "USD", "basis": str(r.get("basis", "cumulative")),
                         "raw_measure": measure_raw})
    financials = pd.DataFrame(fin_rows)
    if financials.empty:
        financials = pd.DataFrame(columns=["initiative_id", "report_date", "measure", "value", "unit", "basis", "raw_measure"])
    else:
        financials = financials[financials.report_date <= as_of_date].copy()

    benefit_by_id = financials[financials.measure == "benefit_to_date"].groupby("initiative_id").value.sum().to_dict()
    cost_by_id = financials[financials.measure == "cost_to_date"].groupby("initiative_id").value.sum().to_dict()

    # Log monthly-cost roll-ups explicitly.
    monthly_counts = financials[(financials.measure == "cost_to_date") & (financials.basis.astype(str).str.lower() == "monthly")].groupby("initiative_id").agg(rows=("value", "size"), total=("value", "sum"))
    for iid, r in monthly_counts.iterrows():
        _log(log, rule="MONTHLY_COST_AGGREGATED", file=source_files["financials"], record=iid,
             field="cost_to_date", old=f"{int(r['rows'])} monthly rows", new=float(r["total"]),
             effect="Summed monthly cost records up to reporting date into cumulative cost-to-date.")

    # Log supplied ROI mismatches against the governed result.
    reported = financials[financials.measure == "reported_roi_pct"]
    for iid, rows in reported.groupby("initiative_id"):
        b, c = benefit_by_id.get(iid, 0.0), cost_by_id.get(iid, 0.0)
        calc = ((b - c) / c * 100.0) if c else None
        for _, r in rows.iterrows():
            if calc is None or abs(float(r.value) - calc) > 1e-6:
                _log(log, rule="REPORTED_ROI_MISMATCH", file=source_files["financials"], record=iid,
                     field="reported_roi_pct", old=float(r.value), new=calc,
                     effect="Reported ROI was not used; displayed ROI comes only from governed scorecard calculation.", severity="warning")

    return CleanResult(initiatives, usage, financials, benefit_by_id, cost_by_id, log, as_of_date, source_files)
