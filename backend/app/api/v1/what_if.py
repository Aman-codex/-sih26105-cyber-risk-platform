from typing import Union

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.what_if import BudgetWhatIfResponse, WhatIfRequest, WhatIfResponse
from app.services import what_if_simulator

router = APIRouter(prefix="/what-if", tags=["what-if"])

WRITE_ROLES = (UserRole.ADMIN, UserRole.CISO, UserRole.RISK_ANALYST)


@router.post("/simulate", response_model=Union[WhatIfResponse, BudgetWhatIfResponse], dependencies=[Depends(require_roles(*WRITE_ROLES))])
def simulate(payload: WhatIfRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Simulates one hypothetical change and returns a before/after
    comparison. Nothing is persisted — this is purely exploratory, safe to
    run as many times as you like. Every number is computed by the same
    Risk Engine (Phase 3) and Investment Optimizer (Phase 5) used
    everywhere else, so a what-if result is always consistent with what
    you'd see if you actually made the change for real.

    Required fields depend on scenario_type:
      - add_control: control_id (+ optional asset_ids, defaults to all assets)
      - remove_control: control_id
      - fix_vulnerability: vulnerability_id
      - improve_control_effectiveness: control_id, new_effectiveness
      - increase_budget: new_budget (+ optional old_budget, defaults to org's current budget)
    """
    org_id = current_user.organization_id
    try:
        if payload.scenario_type == "add_control":
            if payload.control_id is None:
                raise ValueError("control_id is required for add_control")
            return what_if_simulator.simulate_add_control(db, org_id, payload.control_id, payload.asset_ids)

        if payload.scenario_type == "remove_control":
            if payload.control_id is None:
                raise ValueError("control_id is required for remove_control")
            return what_if_simulator.simulate_remove_control(db, org_id, payload.control_id)

        if payload.scenario_type == "fix_vulnerability":
            if payload.vulnerability_id is None:
                raise ValueError("vulnerability_id is required for fix_vulnerability")
            return what_if_simulator.simulate_fix_vulnerability(db, org_id, payload.vulnerability_id)

        if payload.scenario_type == "improve_control_effectiveness":
            if payload.control_id is None or payload.new_effectiveness is None:
                raise ValueError("control_id and new_effectiveness are required for improve_control_effectiveness")
            return what_if_simulator.simulate_control_effectiveness_change(db, org_id, payload.control_id, payload.new_effectiveness)

        if payload.scenario_type == "increase_budget":
            if payload.new_budget is None:
                raise ValueError("new_budget is required for increase_budget")
            return what_if_simulator.simulate_budget_change(db, org_id, payload.new_budget, payload.old_budget)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown scenario_type")
