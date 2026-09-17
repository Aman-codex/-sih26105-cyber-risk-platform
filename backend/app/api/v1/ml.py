from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ml import MLPredictionsResponse
from app.services.ml_predictor import predict_for_assets

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/predictions", response_model=MLPredictionsResponse)
def get_predictions(asset_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Interpretable ML incident-likelihood predictions (Logistic Regression)
    for one asset (?asset_id=) or every asset in the organization, with
    per-feature contributions explaining each prediction. See
    model_info.caveat — this model is trained on synthetic data
    bootstrapped from the Risk Engine's own logic, not on real historical
    incidents (which this prototype has none of). Read-only; available to
    every role, since it never changes anything.
    """
    asset_ids = [asset_id] if asset_id is not None else None
    predictions, info = predict_for_assets(db, current_user.organization_id, asset_ids)
    return MLPredictionsResponse.model_validate({"model_info": info, "predictions": predictions})
