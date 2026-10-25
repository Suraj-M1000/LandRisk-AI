import numpy as np


# Exact names are used after removing the preprocessing prefix.
# Sector and state features are handled separately by prefix.
FEATURE_GROUPS = {
    "schedule_slippage": "Schedule and progress",
    "time_elapsed_pct": "Schedule and progress",
    "months_elapsed": "Schedule and progress",
    "planned_duration_months": "Schedule and progress",
    "physical_progress_pct": "Schedule and progress",

    "spending_progress_gap": "Spending",
    "expenditure_pct": "Spending",

    "land_gap": "Land acquisition",
    "land_acquisition_pct": "Land acquisition",
    "land_acquisition_required": "Land acquisition",

    "contractor_experience_years": "Contractor readiness",

    "project_cost_cr": "Project size",
}

ACTIONABLE_GROUPS = {
    "Schedule and progress",
    "Spending",
    "Land acquisition",
    "Contractor readiness",
}

SUGGESTIONS = {
    "Schedule and progress": (
        "Review upcoming milestones, identify overdue activities, "
        "and agree on a realistic recovery schedule."
    ),
    "Spending": (
        "Compare expenditure with verified physical progress and "
        "investigate material gaps before changing the budget."
    ),
    "Land acquisition": (
        "Verify outstanding parcels, approval status, and documented "
        "acquisition blockers with the responsible team."
    ),
    "Contractor readiness": (
        "Review contractor capacity, staffing, equipment availability, "
        "and delivery commitments before deciding on corrective action."
    ),
}


def _get_group(feature_name):
    """Map one transformed feature to exactly one group."""

    # Example: remainder__months_elapsed -> months_elapsed
    name = feature_name.split("__", 1)[-1]

    if name.startswith("sector_") or name.startswith("state_"):
        return "Sector and state context"

    if name in FEATURE_GROUPS:
        return FEATURE_GROUPS[name]

    raise ValueError(
        f"Unmapped explanation feature: {feature_name!r}. "
        "Update FEATURE_GROUPS before using this model."
    )


def explain_prediction(model_pipeline, X):
    """
    Explain one prediction using logistic-regression contributions.

    Influence shares describe relative model contribution, not
    probability changes or causal effects.

    Corrective suggestions are provided only for higher-risk drivers.
    Lower-risk drivers are presented without corrective suggestions.
    """

    if len(X) != 1:
        raise ValueError(
            "Explainability currently supports one project at a time."
        )

    # Access the fitted pipeline components.
    feature_engineer = model_pipeline.named_steps[
        "landriskfeatureengineer"
    ]
    preprocessing_pipeline = model_pipeline.named_steps["pipeline"]

    preprocessor = preprocessing_pipeline.named_steps[
        "columntransformer"
    ]
    classifier = model_pipeline.named_steps["logisticregression"]

    # Apply the same transformations used during prediction.
    engineered = feature_engineer.transform(X)
    transformed = preprocessor.transform(engineered)

    if hasattr(transformed, "toarray"):
        transformed = transformed.toarray()
    else:
        transformed = np.asarray(transformed)

    transformed_row = transformed[0]
    feature_names = list(preprocessor.get_feature_names_out())
    coefficients = classifier.coef_[0]
    intercept = float(classifier.intercept_[0])

    # Ensure each transformed feature has one coefficient.
    if not (
        len(feature_names)
        == len(coefficients)
        == len(transformed_row)
    ):
        raise ValueError(
            "Transformed features, names, and coefficients do not match."
        )

    # Reject duplicate names instead of silently double-counting.
    if len(feature_names) != len(set(feature_names)):
        raise ValueError("Duplicate transformed feature names found.")

    contributions = coefficients * transformed_row

    # Every transformed feature is assigned to exactly one group.
    assignments = {}

    for name in feature_names:
        if name in assignments:
            raise ValueError(
                f"Feature assigned more than once: {name!r}"
            )

        assignments[name] = _get_group(name)

    if len(assignments) != len(feature_names):
        raise ValueError(
            "Not every feature was assigned exactly once."
        )

    # Sum feature contributions within each group.
    group_totals = {}

    for name, contribution in zip(feature_names, contributions):
        group = assignments[name]

        group_totals[group] = (
            group_totals.get(group, 0.0) + float(contribution)
        )

    # Verify the grouped logit and probability against the model.
    reconstructed_logit = intercept + sum(group_totals.values())

    reconstructed_probability = float(
        1.0 / (1.0 + np.exp(-reconstructed_logit))
    )

    actual_probability = float(
        model_pipeline.predict_proba(X)[0, 1]
    )

    verified = bool(
        np.isclose(
            reconstructed_probability,
            actual_probability,
            atol=1e-8,
            rtol=1e-8,
        )
    )

    if not verified:
        raise ValueError(
            "Explanation verification failed: reconstructed probability "
            "does not match model prediction."
        )

    # Relative influence shares use absolute group contributions.
    # They sum to 100% across all nonzero groups before driver filtering.
    denominator = sum(
        abs(value) for value in group_totals.values()
    )

    drivers = []

    for group, contribution in group_totals.items():
        if group not in ACTIONABLE_GROUPS or contribution == 0:
            continue

        direction = (
            "higher_risk"
            if contribution > 0
            else "lower_risk"
        )

        share = (
            100.0 * abs(contribution) / denominator
            if denominator > 0
            else 0.0
        )

        # Base information is included for both directions.
        driver = {
            "group": group,
            "direction": direction,
            "influence_share_pct": round(share, 1),
        }

        # FIX: corrective suggestions are only for higher-risk drivers.
        if direction == "higher_risk":
            driver["suggestion"] = SUGGESTIONS[group]

        drivers.append(driver)

    drivers_up = sorted(
        [
            driver for driver in drivers
            if driver["direction"] == "higher_risk"
        ],
        key=lambda driver: driver["influence_share_pct"],
        reverse=True,
    )[:3]

    drivers_down = sorted(
        [
            driver for driver in drivers
            if driver["direction"] == "lower_risk"
        ],
        key=lambda driver: driver["influence_share_pct"],
        reverse=True,
    )[:3]

    return {
        "verified": verified,
        "drivers_up": drivers_up,
        "drivers_down": drivers_down,
    }