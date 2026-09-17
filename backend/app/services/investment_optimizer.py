"""
Investment Optimization (module 9), using Google OR-Tools.

Two steps:
1. For every not-yet-deployed security control, estimate how much it would
   reduce total organizational Expected Annual Loss if deployed at 100%
   coverage across every asset — reusing the exact same Risk Engine from
   Phase 3 (calculate_asset_risk with extra_mitigation), so the estimate
   is consistent with everything else in the platform, not a separate
   ad-hoc formula.
2. Given a fixed budget, solve the classic 0/1 knapsack problem — pick the
   subset of candidates whose combined cost fits the budget while
   maximizing total risk reduction — with Google OR-Tools' CP-SAT solver.
"""
from dataclasses import dataclass
from typing import List

from ortools.sat.python import cp_model
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.security_control import SecurityControl
from app.services.risk_engine import calculate_asset_risk, get_or_create_config


@dataclass
class InvestmentCandidate:
    control_id: int
    name: str
    control_type: str
    annual_cost: float
    effectiveness_score: float  # raw effectiveness (0-1), needed to recombine multiple selected candidates correctly
    estimated_risk_reduction: float  # reduction in total org EAL if deployed alone (a prioritization signal — see note below)


@dataclass
class OptimizationResult:
    budget: float
    baseline_total_eal: float
    selected: List[InvestmentCandidate]
    total_investment: float
    total_risk_reduction: float
    remaining_risk: float  # baseline EAL minus achieved reduction
    rosi_percent: float  # Return on Security Investment: (reduction - cost) / cost * 100


def _total_eal(db: Session, assets: List[Asset], config, extra_mitigation_by_asset: dict) -> float:
    total = 0.0
    for asset in assets:
        result = calculate_asset_risk(db, asset, config, extra_mitigation=extra_mitigation_by_asset.get(asset.id, 0.0))
        total += result.expected_annual_loss
    return total


def estimate_investment_candidates(db: Session, org_id: int) -> List[InvestmentCandidate]:
    """
    Every inactive (not-yet-deployed) control is a candidate. Its
    estimated_risk_reduction is: (org's current total EAL) minus (total
    EAL if this control alone were deployed at 100% coverage on every
    asset). This is deliberately simple — no interaction effects between
    two candidates deployed together are modeled — appropriate for an
    explainable prototype; real deployments would want marginal analysis
    or a more detailed simulation.
    """
    config = get_or_create_config(db, org_id)
    assets = db.query(Asset).filter(Asset.organization_id == org_id).all()
    if not assets:
        return []

    baseline_eal = _total_eal(db, assets, config, {})

    candidates = []
    inactive_controls = (
        db.query(SecurityControl)
        .filter(SecurityControl.organization_id == org_id, SecurityControl.is_active.is_(False))
        .all()
    )
    for control in inactive_controls:
        extra = {asset.id: control.effectiveness_score for asset in assets}
        with_investment_eal = _total_eal(db, assets, config, extra)
        reduction = max(0.0, round(baseline_eal - with_investment_eal, 2))
        candidates.append(InvestmentCandidate(
            control_id=control.id, name=control.name, control_type=control.control_type.value,
            annual_cost=control.annual_cost, effectiveness_score=control.effectiveness_score,
            estimated_risk_reduction=reduction,
        ))
    return candidates


def optimize_budget_allocation(
    db: Session, org_id: int, candidates: List[InvestmentCandidate], budget: float, baseline_total_eal: float
) -> OptimizationResult:
    """
    0/1 knapsack: choose a subset of candidates maximizing total risk
    reduction without exceeding the budget. Solved exactly with Google
    OR-Tools CP-SAT (not a greedy heuristic).

    IMPORTANT: each candidate's estimated_risk_reduction is computed
    *alone* (useful for comparing/prioritizing individual controls), but
    deploying several controls together does NOT simply add up their solo
    reductions — they can overlap (e.g. two controls that would each
    individually fill the same risk-mitigation headroom on an asset don't
    combine to more than 100% of that headroom). CP-SAT uses the solo
    reductions as its selection heuristic (a reasonable proxy for value),
    but the totals actually reported below are computed by re-running the
    Risk Engine ONCE MORE against the exact combined effect of the final
    selected set — so the numbers you see are always internally
    consistent (total reduction can never exceed the baseline).
    """
    from app.models.asset import Asset
    from app.services.risk_engine import get_or_create_config

    if not candidates or budget <= 0:
        return OptimizationResult(
            budget=budget, baseline_total_eal=baseline_total_eal, selected=[],
            total_investment=0.0, total_risk_reduction=0.0, remaining_risk=baseline_total_eal, rosi_percent=0.0,
        )

    model = cp_model.CpModel()
    # Scale to integer cents/paise-equivalent units since CP-SAT works over integers.
    scale = 100
    costs = [int(round(c.annual_cost * scale)) for c in candidates]
    budget_scaled = int(round(budget * scale))
    # Risk reduction scaled to integer "cents of dollars" for the objective too.
    reductions = [int(round(c.estimated_risk_reduction * scale)) for c in candidates]

    chosen = [model.NewBoolVar(f"choose_{i}") for i in range(len(candidates))]
    model.Add(sum(costs[i] * chosen[i] for i in range(len(candidates))) <= budget_scaled)
    model.Maximize(sum(reductions[i] * chosen[i] for i in range(len(candidates))))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.Solve(model)

    selected: List[InvestmentCandidate] = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        selected = [candidates[i] for i in range(len(candidates)) if solver.Value(chosen[i]) == 1]

    total_investment = round(sum(c.annual_cost for c in selected), 2)

    # Recompute the TRUE combined effect of deploying every selected
    # control together, rather than summing their solo reductions.
    if selected:
        config = get_or_create_config(db, org_id)
        assets = db.query(Asset).filter(Asset.organization_id == org_id).all()
        combined_extra_mitigation = sum(c.effectiveness_score for c in selected)
        combined_eal = _total_eal(db, assets, config, {a.id: combined_extra_mitigation for a in assets})
        total_risk_reduction = max(0.0, round(baseline_total_eal - combined_eal, 2))
    else:
        total_risk_reduction = 0.0

    remaining_risk = round(baseline_total_eal - total_risk_reduction, 2)
    rosi_percent = round(
        ((total_risk_reduction - total_investment) / total_investment * 100) if total_investment > 0 else 0.0, 1
    )

    return OptimizationResult(
        budget=budget, baseline_total_eal=baseline_total_eal, selected=selected,
        total_investment=total_investment, total_risk_reduction=total_risk_reduction,
        remaining_risk=remaining_risk, rosi_percent=rosi_percent,
    )
