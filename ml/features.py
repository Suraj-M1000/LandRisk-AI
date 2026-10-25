"""
Loads the saved LandRisk AI pipeline ONCE and predicts delay risk for one project.

Django will use it like this:
    from ml.inference import predict_risk
    result = predict_risk({"sector": "Railways", "state": "Gujarat", ...})
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class LandRiskFeatureEngineer(BaseEstimator, TransformerMixin):
    """Create project-status features used for delay-risk prediction."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        X = X.copy()

        duration = X["planned_duration_months"]

        # Avoid division by zero or invalid planned durations.
        if (duration <= 0).any():
            raise ValueError(
                "Planned duration must be greater than zero."
            )

        # Percentage of planned time already consumed.
        X["time_elapsed_pct"] = (
            X["months_elapsed"] / duration
        ) * 100

        # Negative values indicate progress behind the
        # simple time-proportional benchmark.
        X["schedule_slippage"] = (
            X["physical_progress_pct"]
            - X["time_elapsed_pct"]
        )

        # Positive values indicate expenditure ahead of
        # physical progress.
        X["spending_progress_gap"] = (
            X["expenditure_pct"]
            - X["physical_progress_pct"]
        )

        # Remaining acquisition percentage.
        X["land_gap"] = (
            100 - X["land_acquisition_pct"]
        )

        # Land acquisition is irrelevant when land is not required.
        no_land_required = (
            X["land_acquisition_required"] == 0
        )
        X.loc[no_land_required, "land_gap"] = 0

        return X

    def get_feature_names_out(self, input_features=None):
        if input_features is None:
            input_features = [
                    "sector",
                    "state",
                    "project_cost_cr",
                    "planned_duration_months",
                    "months_elapsed",
                    "physical_progress_pct",
                    "expenditure_pct",
                    "contractor_experience_years",
                    "land_acquisition_required",
                    "land_acquisition_pct"
                ]

        return np.asarray(
            list(input_features) + [
                    "time_elapsed_pct",
                    "schedule_slippage",
                    "spending_progress_gap",
                    "land_gap",
                ],
            dtype=object,
            )
