from typing import Dict, List

from pydantic import BaseModel, ConfigDict


class FeatureContributionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature: str
    value: float
    contribution: float


class AssetPredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: int
    asset_name: str
    predicted_probability: float
    contributions: List[FeatureContributionRead]


class ModelInfoRead(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    model_type: str
    is_synthetic_data: bool
    training_samples: int
    test_accuracy: float
    test_roc_auc: float
    coefficients: Dict[str, float]
    caveat: str


class MLPredictionsResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_info: ModelInfoRead
    predictions: List[AssetPredictionRead]
