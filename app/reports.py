from __future__ import annotations
from .assistant import _fmt_money, _fmt_pct


def build_weekly_report(bundle) -> str:
    df = bundle.scorecard.copy()
    p = bundle.portfolio
    lines = [
        f"# Nimbus Group — Weekly AI Portfolio Value Report",
        f"**Dataset:** `{bundle.dataset_id}`  ",
        f"**Reporting date:** {bundle.as_of_date}",
        "",
        "## Executive summary",
        f"- Initiatives assessed: **{p['initiative_count']}**",
        f"- Portfolio realised benefit: **{_fmt_money(p['total_benefit'])}**",
        f"- Portfolio total cost: **{_fmt_money(p['total_cost'])}**",
        f"- Portfolio ROI: **{_fmt_pct(p['portfolio_roi'])}**",
        f"- Average initiative adoption: **{_fmt_pct(p.get('average_adoption'))}**",
        f"- Health: **{p['status_counts']['Green']} Green / {p['status_counts']['Amber']} Amber / {p['status_counts']['Red']} Red**",
        "",
        "Source for all figures: governed scorecard calculated from `raw/initiatives.csv`, `raw/weekly_usage.csv` and `raw/financials.xlsx` using the metric definitions in this project.",
        "",
        "## Portfolio scorecard",
        "| Initiative | Business unit | Adoption | WAU change | ROI | Avg monthly benefit | Payback (months) | Run-rate vs plan | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, r in df.sort_values(["status", "initiative_id"]).iterrows():
        payback = f"{r.payback_months:.1f}" if r.payback_months is not None and str(r.payback_months) != "nan" else "N/A"
        lines.append(f"| {r.initiative_id} {r['name']} | {r.business_unit} | {_fmt_pct(r.adoption)} | {_fmt_pct(r.wau_change)} | {_fmt_pct(r.roi)} | {_fmt_money(r.avg_monthly_benefit)} | {payback} | {_fmt_pct(r.run_rate_vs_plan)} | **{r.status}** |")
    lines += ["", "## Initiatives requiring attention", ""]
    attention = df[df.status.isin(["Red", "Amber"])].sort_values(["status", "initiative_id"])
    if attention.empty:
        lines.append("No Red or Amber initiatives were identified in the supplied scorecard.")
    for _, r in attention.iterrows():
        reasons = []
        if r.adoption is not None and r.adoption < 0.30:
            reasons.append("adoption is below the 30% Red threshold")
        if r.roi is not None and r.roi < 0:
            reasons.append("ROI is negative")
        if r.status == "Amber":
            reasons.append("the initiative does not meet the Green rule (adoption at least 60% and ROI above 0) and does not meet the Red rule")
        lines.append(f"### {r.initiative_id} — {r['name']} ({r.status})")
        lines.append(f"- **Scorecard evidence:** adoption {_fmt_pct(r.adoption)}, ROI {_fmt_pct(r.roi)}, run-rate vs plan {_fmt_pct(r.run_rate_vs_plan)}. Reasons: {'; '.join(reasons) if reasons else 'review the full scorecard metrics'}. [Source: governed scorecard; raw/initiatives.csv, raw/weekly_usage.csv, raw/financials.xlsx]")
        # Narrative evidence is drawn directly from charter chunks, without model-generated claims.
        risks = [c for c in bundle.chunks if c["initiative_id"] == r.initiative_id and c["section"].lower() == "risks and mitigations"]
        if risks:
            excerpt = risks[0]["content"].replace("\n", " ")
            if len(excerpt) > 440:
                excerpt = excerpt[:437] + "..."
            lines.append(f"- **Charter context:** {excerpt} [Source: `{risks[0]['source_filename']}`, section `Risks and Mitigations`]")
        else:
            lines.append("- **Charter context:** I do not have that in the data provided for a Risks and Mitigations section.")
        lines.append("- **Suggested management review:** Review the scorecard driver(s) above alongside the cited charter evidence. This is a recommendation for human review, not an investment or approval decision.")
        lines.append("")
    lines += [
        "## Metric definitions and reporting assumptions",
        "- Adoption = latest-week weekly active users / licensed users.",
        "- WAU change = (latest-week WAU - first-week WAU) / first-week WAU over the available three-week period.",
        "- ROI = (realised benefit to date - total cost to date) / total cost to date.",
        "- Average monthly benefit = realised benefit to date / months live.",
        "- Payback = total cost to date / average monthly benefit.",
        "- Run-rate vs plan = average monthly benefit × 12 / planned annual benefit.",
        "- Green: adoption >= 60% and ROI > 0. Red: adoption < 30% or ROI < 0. Amber: all other cases.",
        "- Benchmark as-of date is taken from the selected report date; months live uses days live / 30.44.",
        "- USD '000 values are converted to USD; pre-computed reported ROI is ignored and recomputed.",
        "",
        "## Limitations",
        "- The supplied Nimbus data is synthetic practice data.",
        "- A charter describes planned scope, benefits and risks; it does not prove that a risk caused a financial outcome.",
        "- Recommendations are review prompts only. The application does not approve investments or change source data.",
    ]
    return "\n".join(lines)
