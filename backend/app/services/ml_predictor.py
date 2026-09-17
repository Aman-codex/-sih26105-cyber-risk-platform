"""
Module 11: ML prediction and explainability.

HONEST LIMITATION, stated upfront: a real deployment would train this
model on actual historical incident data (did an incident happen on this
asset in a given year, yes/no). This prototype has no such history to
learn from — so, to still deliver a genuine, interpretable, trained
model rather than faking one, we bootstrap a synthetic training set using
the SAME feature relationships the Risk Engine (Phase 3) already encodes
(exploitability, severity, exposure, threat relevance, control
mitigation), with random noise added so the model isn't just memorizing
the formula. This is clearly surfaced to the user via `is_synthetic_data`
in every response — nobody should mistake this for a model trained on
real incidents.

Logistic Regression is used deliberately: its coefficients are directly
interpretable (each one says "this feature increases/decreases incident
odds by this much"), which matters more for an explainable prototype than
squeezing out marginal accuracy with a black-box model.
"""
import random
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.enums import BusinessCriticality
from app.services.risk_engine import _max_threat_relevance, _total_control_mitigation, _worst_open_vulnerability

FEATURE_NAMES = [
    "cvss_score", "exploitability_score", "internet_exposure",
    "threat_relevance", "control_mitigation", "criticality_score",
]

_EXPLOITABILITY_SCORE = {"theoretical": 0.1, "proof_of_concept": 0.4, "functional": 0.7, "actively_exploited": 1.0}
_CRITICALITY_SCORE = {
    BusinessCriticality.LOW: 0.25, BusinessCriticality.MEDIUM: 0.5,
    BusinessCriticality.HIGH: 0.75, BusinessCriticality.CRITICAL: 1.0,
}


@dataclass
class FeatureContribution:
    feature: str
    value: float
    contribution: float  # coefficient x value — this feature's push toward/away from "incident"


@dataclass
class AssetPrediction:
    asset_id: int
    asset_name: str
    predicted_probability: float
    contributions: List[FeatureContribution] = field(default_factory=list)


@dataclass
class ModelInfo:
    model_type: str
    is_synthetic_data: bool
    training_samples: int
    test_accuracy: float
    test_roc_auc: float
    coefficients: dict
    caveat: str


def _extract_features(db: Session, asset: Asset) -> List[float]:
    worst_vuln = _worst_open_vulnerability(asset)
    cvss = (worst_vuln.cvss_score / 10.0) if worst_vuln else 0.0
    exploit = _EXPLOITABILITY_SCORE.get(worst_vuln.exploitability.value, 0.0) if worst_vuln else 0.0
    exposure = 1.0 if asset.internet_exposure else 0.0
    relevance = _max_threat_relevance(db, asset.id)
    mitigation = _total_control_mitigation(db, asset.id, max_mitigation=1.0)  # uncapped here, purely a feature
    criticality = _CRITICALITY_SCORE.get(asset.business_criticality, 0.5)
    return [cvss, exploit, exposure, relevance, mitigation, criticality]


def _generate_synthetic_dataset(n_samples: int = 600, seed: int = 42):
    """
    Builds a synthetic (feature, label) dataset using the same directional
    relationships as the Risk Engine — higher CVSS/exploitability/exposure/
    threat relevance raise incident odds, higher control mitigation lowers
    them — plus random noise, so the model must learn a real (if
    simplified) pattern rather than trivially memorizing a formula.
    """
    rng = random.Random(seed)
    X, y = [], []
    for _ in range(n_samples):
        cvss = rng.random()
        exploit = rng.random()
        exposure = 1.0 if rng.random() < 0.5 else 0.0
        relevance = rng.random() * rng.random()  # skewed toward low relevance, like real data
        mitigation = rng.random()
        criticality = rng.choice([0.25, 0.5, 0.75, 1.0])

        latent = (
            0.35 * cvss + 0.30 * exploit + 0.15 * exposure + 0.15 * relevance
            - 0.35 * mitigation + 0.05 * criticality
        )
        latent += rng.gauss(0, 0.15)
        probability = 1 / (1 + np.exp(-6 * (latent - 0.25)))
        label = 1 if rng.random() < probability else 0

        X.append([cvss, exploit, exposure, relevance, mitigation, criticality])
        y.append(label)
    return np.array(X), np.array(y)


def train_and_evaluate() -> tuple:
    """Trains fresh each call — with ~600 samples and 6 features this is well under a second."""
    X, y = _generate_synthetic_dataset()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    accuracy = round(accuracy_score(y_test, y_pred), 3)
    try:
        auc = round(roc_auc_score(y_test, y_proba), 3)
    except ValueError:
        auc = 0.5

    info = ModelInfo(
        model_type="Logistic Regression",
        is_synthetic_data=True,
        training_samples=len(X_train),
        test_accuracy=accuracy,
        test_roc_auc=auc,
        coefficients={name: round(float(coef), 3) for name, coef in zip(FEATURE_NAMES, model.coef_[0])},
        caveat=(
            "This model is trained on synthetic data bootstrapped from the Risk Engine's own logic, "
            "since no historical incident data exists yet for this organization. It demonstrates the "
            "approach (interpretable model + feature-level explanations) rather than predicting from "
            "real observed incidents. Retrain on real incident history once available."
        ),
    )
    return model, info


def predict_for_assets(db: Session, org_id: int, asset_ids: Optional[List[int]] = None) -> tuple:
    model, info = train_and_evaluate()

    query = db.query(Asset).filter(Asset.organization_id == org_id)
    if asset_ids:
        query = query.filter(Asset.id.in_(asset_ids))
    assets = query.all()

    predictions = []
    for asset in assets:
        features = _extract_features(db, asset)
        probability = float(model.predict_proba([features])[0][1])
        contributions = [
            FeatureContribution(feature=name, value=round(val, 3), contribution=round(coef * val, 3))
            for name, val, coef in zip(FEATURE_NAMES, features, model.coef_[0])
        ]
        contributions.sort(key=lambda c: abs(c.contribution), reverse=True)
        predictions.append(AssetPrediction(
            asset_id=asset.id, asset_name=asset.name,
            predicted_probability=round(probability, 4), contributions=contributions,
        ))

    predictions.sort(key=lambda p: p.predicted_probability, reverse=True)
    return predictions, info
