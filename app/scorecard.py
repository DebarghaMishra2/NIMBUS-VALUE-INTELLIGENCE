from __future__ import annotations
from datetime import date
import math
import pandas as pd
from .cleaning import CleanResult


def _div(a, b):
    if b is None or b == 0 or pd.isna(b):
        return None
    v = float(a) / float(b)
    return v if math.isfinite(v) else None


def calculate_scorecard(clean: CleanResult) -> pd.DataFrame:
    rows = []
    as_of = clean.as_of_date
    for _, initiative in clean.initiatives.iterrows():
        iid = initiative.initiative_id
        usage = clean.usage[clean.usage.initiative_id == iid].sort_values("week_start")
        first_wau = float(usage.iloc[0].value) if len(usage) else None
        latest_wau = float(usage.iloc[-1].value) if len(usage) else None
        licensed = float(initiative.licensed_users)
        adoption = _div(latest_wau, licensed)
        wau_change = _div(latest_wau - first_wau, first_wau) if first_wau not in (None, 0) and latest_wau is not None else None
        months_exact = (as_of - initiative.go_live_date).days / 30.44
        months_live = round(months_exact, 4)
        benefit = float(clean.benefit_by_id.get(iid, 0.0))
        cost = float(clean.cost_by_id.get(iid, 0.0))
        avg_monthly = _div(benefit, months_exact) if months_exact > 0 else None
        roi = _div(benefit - cost, cost)
        payback = _div(cost, avg_monthly) if avg_monthly not in (None, 0) else None
        run_rate = _div((avg_monthly or 0.0) * 12.0, float(initiative.planned_annual_benefit))
        if adoption is None or roi is None:
            status = "Insufficient data"
        elif adoption < 0.30 or roi < 0:
            status = "Red"
        elif adoption >= 0.60 and roi > 0:
            status = "Green"
        else:
            status = "Amber"
        rows.append({
            "initiative_id": iid, "name": initiative["name"], "business_unit": initiative["business_unit"],
            "initiative_type": initiative["type"], "months_live": months_live,
            "licensed_users": licensed, "first_week_wau": first_wau, "latest_week_wau": latest_wau,
            "adoption": adoption, "wau_change": wau_change, "benefit_to_date": benefit,
            "cost_to_date": cost, "roi": roi, "avg_monthly_benefit": avg_monthly,
            "payback_months": payback, "run_rate_vs_plan": run_rate, "status": status,
            "reporting_date": as_of.isoformat(),
            "source_refs": ["raw/initiatives.csv", "raw/weekly_usage.csv", "raw/financials.xlsx"],
        })
    return pd.DataFrame(rows)


def portfolio_summary(scorecard: pd.DataFrame) -> dict:
    if scorecard.empty:
        return {"initiative_count": 0, "total_benefit": 0, "total_cost": 0, "portfolio_roi": None,
                "status_counts": {"Green": 0, "Amber": 0, "Red": 0, "Insufficient data": 0}}
    total_benefit = float(scorecard.benefit_to_date.fillna(0).sum())
    total_cost = float(scorecard.cost_to_date.fillna(0).sum())
    portfolio_roi = (total_benefit - total_cost) / total_cost if total_cost else None
    counts = scorecard.status.value_counts().to_dict()
    return {
        "initiative_count": int(len(scorecard)), "total_benefit": total_benefit, "total_cost": total_cost,
        "portfolio_roi": portfolio_roi,
        "average_adoption": float(scorecard.adoption.dropna().mean()) if scorecard.adoption.notna().any() else None,
        "status_counts": {k: int(counts.get(k, 0)) for k in ["Green", "Amber", "Red", "Insufficient data"]},
        "red_initiatives": scorecard.loc[scorecard.status == "Red", "initiative_id"].tolist(),
        "amber_initiatives": scorecard.loc[scorecard.status == "Amber", "initiative_id"].tolist(),
        "source": "Governed initiative scorecards calculated from cleaned source data.",
    }
