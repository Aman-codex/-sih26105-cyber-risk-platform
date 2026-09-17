"""
Module 12: AI Decision Support (kept intentionally minimal).

This is a deterministic, keyword-routed assistant — NOT a call to an
external LLM API. That's a deliberate scope decision, not a shortcut:
the spec's hard requirement is "the assistant must not invent risk
values; all numerical results must come from the platform's calculation
engines." A rule-based router that calls the same Risk Engine /
Optimizer / Compliance services already built in Phases 3-6 can
literally never hallucinate a number, because every figure it reports is
read straight from a real calculation. A real LLM could be swapped in
later as the natural-language layer on TOP of this same intent→data
routing, without changing anything below it.
"""
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.crud import compliance as compliance_crud
from app.crud import investment as investment_crud
from app.crud import risk as risk_crud
from app.models.compliance import ComplianceFramework
from app.services.investment_optimizer import estimate_investment_candidates


@dataclass
class AssistantAnswer:
    intent: str
    answer: str
    supporting_data: dict


# Ordered so more specific phrases are checked before generic ones.
_INTENT_KEYWORDS = [
    ("main_risk_drivers", ["risk driver", "why is", "what is driving", "main factor", "contributing factor", "driving the risk", "drivers"]),
    ("highest_financial_risk", ["highest risk", "biggest risk", "most risk", "top risk", "financial exposure", "financial risk", "highest financial"]),
    ("recommended_controls", ["recommend", "should we invest", "which control", "best investment", "what control"]),
    ("compliance_gaps", ["compliance gap", "compliant", "compliance status", "audit", "framework"]),
    ("risk_trend", ["over time", "trend", "history", "change since", "compared to last"]),
]


def classify_intent(question: str) -> Optional[str]:
    q = question.lower()
    for intent, keywords in _INTENT_KEYWORDS:
        if any(kw in q for kw in keywords):
            return intent
    return None


def answer_question(db: Session, org_id: int, question: str) -> AssistantAnswer:
    intent = classify_intent(question)

    if intent == "highest_financial_risk":
        return _answer_highest_financial_risk(db, org_id)
    if intent == "main_risk_drivers":
        return _answer_main_risk_drivers(db, org_id)
    if intent == "recommended_controls":
        return _answer_recommended_controls(db, org_id)
    if intent == "compliance_gaps":
        return _answer_compliance_gaps(db, org_id)
    if intent == "risk_trend":
        return _answer_risk_trend()

    return AssistantAnswer(
        intent="unrecognized",
        answer=(
            "I can only answer questions from a fixed set of categories right now: "
            "the highest financial risk, main risk drivers, recommended controls, "
            "compliance gaps, or risk trends over time. Try rephrasing your question "
            "around one of those topics."
        ),
        supporting_data={},
    )


def _answer_highest_financial_risk(db: Session, org_id: int) -> AssistantAnswer:
    summary = risk_crud.get_risk_summary(db, org_id, top_n=1)
    if not summary["top_risks"]:
        return AssistantAnswer("highest_financial_risk", "No risk calculations exist yet — run a recalculation first.", {})

    top = summary["top_risks"][0]
    answer = (
        f"Your highest financial cyber risk is on '{top.asset.name}', with a risk score of "
        f"{top.risk_score:.1f}/100 and an Expected Annual Loss of ${top.expected_annual_loss:,.0f}. "
        f"Across the whole organization, total Expected Annual Loss is ${summary['total_expected_annual_loss']:,.0f}."
    )
    return AssistantAnswer("highest_financial_risk", answer, {
        "asset_name": top.asset.name, "risk_score": top.risk_score,
        "expected_annual_loss": top.expected_annual_loss,
        "total_expected_annual_loss": summary["total_expected_annual_loss"],
    })


def _answer_main_risk_drivers(db: Session, org_id: int) -> AssistantAnswer:
    summary = risk_crud.get_risk_summary(db, org_id, top_n=1)
    if not summary["top_risks"]:
        return AssistantAnswer("main_risk_drivers", "No risk calculations exist yet — run a recalculation first.", {})

    top = summary["top_risks"][0]
    driver_lines = [f"{d['factor']} ({d['impact_pct']:+.1f}%)" for d in top.risk_drivers]
    answer = (
        f"For '{top.asset.name}' (your highest-risk asset), the main risk drivers are: "
        + "; ".join(driver_lines) + "."
    ) if driver_lines else f"'{top.asset.name}' has no notable risk drivers recorded."
    return AssistantAnswer("main_risk_drivers", answer, {"asset_name": top.asset.name, "risk_drivers": top.risk_drivers})


def _answer_recommended_controls(db: Session, org_id: int) -> AssistantAnswer:
    candidates = estimate_investment_candidates(db, org_id)
    if not candidates:
        return AssistantAnswer(
            "recommended_controls",
            "There are no candidate investments to recommend right now — every control is already active, or no assets exist to assess.",
            {},
        )
    best = max(candidates, key=lambda c: c.estimated_risk_reduction)
    answer = (
        f"Based on current data, '{best.name}' offers the highest individual risk reduction "
        f"(${best.estimated_risk_reduction:,.0f} off total Expected Annual Loss if deployed alone) "
        f"for an annual cost of ${best.annual_cost:,.0f}. For an exact recommendation under your "
        f"specific budget, run the full Investment Optimizer."
    )
    return AssistantAnswer("recommended_controls", answer, {
        "control_name": best.name, "annual_cost": best.annual_cost, "estimated_risk_reduction": best.estimated_risk_reduction,
    })


def _answer_compliance_gaps(db: Session, org_id: int) -> AssistantAnswer:
    frameworks = db.query(ComplianceFramework).order_by(ComplianceFramework.id).all()
    if not frameworks:
        return AssistantAnswer("compliance_gaps", "No compliance frameworks are configured.", {})

    analyses = [compliance_crud.compute_gap_analysis(db, org_id, f) for f in frameworks]
    worst = min(analyses, key=lambda a: a["compliance_score"])
    answer = (
        f"Your weakest compliance area is {worst['framework']['name']}, at "
        f"{worst['compliance_score']}% compliant, with {worst['non_compliant_count']} non-compliant, "
        f"{worst['partially_compliant_count']} partially-compliant, and {worst['not_assessed_count']} "
        f"not-yet-assessed requirements."
    )
    return AssistantAnswer("compliance_gaps", answer, {
        "framework_name": worst["framework"]["name"], "compliance_score": worst["compliance_score"],
        "non_compliant_count": worst["non_compliant_count"],
    })


def _answer_risk_trend() -> AssistantAnswer:
    return AssistantAnswer(
        "risk_trend",
        (
            "Risk trend tracking over time isn't available yet — the platform currently stores only "
            "the latest risk calculation per asset, not a history of past calculations. This is a "
            "known limitation to address in a future phase, not a number I can estimate."
        ),
        {},
    )
