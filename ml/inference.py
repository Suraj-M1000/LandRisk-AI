"""
ml/inference.py: the ONLY file the website talks to.

    from ml.inference import predict_risk, get_input_schema, InputValidationError

It knows nothing about Django. It loads the saved model once, checks the raw inputs against the schema
stored inside the artifact, and returns a prediction.
"""
import math
import warnings
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# The pickled model refers to ml.features.LandRiskFeatureEngineer. Importing the module here makes sure
# Python can find that class when the artifact is loaded.
# import ml.features
import ml.features
from ml.explain import explain_prediction


DEFAULT_ARTIFACT_PATH = Path(__file__).resolve().parent / "artifacts" / "landrisk_model.joblib"  # Model Path


class InputValidationError(ValueError):
    """Raised when the raw inputs are not acceptable. `errors` maps field name -> message."""

    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(f"{field}: {message}" for field, message in errors.items()))


# ----------------------------------------------------------------------------- loading
@lru_cache(maxsize=None)
def _load(path_str):
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(
            f"Model artifact not found at {path}. Train and save the model first (see the modelling notebook)."
        )
    artifact = joblib.load(path)
    _warn_if_versions_differ(artifact)
    return artifact


def load_artifact(path=None):
    """Load the saved model + metadata. Cached, so the file is read only once per process."""
    return _load(str(Path(path) if path else DEFAULT_ARTIFACT_PATH))


def _warn_if_versions_differ(artifact):
    import sklearn
    trained_with = artifact.get("library_versions", {}).get("scikit-learn")
    if trained_with and trained_with != sklearn.__version__:
        warnings.warn(
            f"Model was trained with scikit-learn {trained_with} but {sklearn.__version__} is installed. "
            "Predictions may differ or loading may fail; install the training version.",
            RuntimeWarning,
        )


def get_input_schema(path=None):
    """The schema the forms should use: field -> type, required, allowed values / range."""
    return load_artifact(path)["input_schema"]


# ----------------------------------------------------------------------------- validation
def _is_missing(value):
    return value is None or (isinstance(value, str) and value.strip() == "") or \
        (isinstance(value, float) and math.isnan(value))


def _to_number(value, field, kind):
    """Convert to float or int; raise ValueError with a readable message."""
    if isinstance(value, bool):                      # True/False are accepted for 0/1 fields
        value = int(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("must be a number")
    if not math.isfinite(number):
        raise ValueError("must be a finite number")
    if kind == "int":
        if number != int(number):
            raise ValueError("must be a whole number")
        return int(number)
    return number


def validate_input(raw, path=None):
    """
    Check and clean the raw inputs.
    Returns (clean, warnings): clean has every schema field (None for a missing optional one).
    Raises InputValidationError listing ALL problems at once.
    """
    schema = get_input_schema(path)
    errors, clean, notes = {}, {}, []

    unknown = sorted(set(raw) - set(schema))
    for field in unknown:
        errors[field] = "unexpected field"

    for field, rule in schema.items():
        value = raw.get(field)

        if _is_missing(value):
            if rule["required"]:
                errors[field] = "this field is required"
            clean[field] = None
            continue

        if rule["type"] == "category":
            value = str(value).strip()
            if value not in rule["allowed_values"]:
                errors[field] = f"must be one of: {', '.join(rule['allowed_values'])}"
                continue
            clean[field] = value
            continue

        try:
            number = _to_number(value, field, rule["type"])
        except ValueError as exc:
            errors[field] = str(exc)
            continue
        if "allowed_values" in rule and number not in rule["allowed_values"]:
            errors[field] = f"must be one of: {rule['allowed_values']}"
            continue
        if "min" in rule and number < rule["min"]:
            errors[field] = f"must be at least {rule['min']}"
            continue
        if "max" in rule and number > rule["max"]:
            errors[field] = f"must be at most {rule['max']}"
            continue
        clean[field] = number

        low, high = rule.get("training_range", (None, None))
        if low is not None and not (low <= number <= high):
            notes.append(f"{field}={number} is outside the range seen in training ({low:g} to {high:g}); "
                         "treat the result with extra caution.")

    # Rules that involve more than one field (only checked if the fields themselves were valid)
    elapsed, planned = clean.get("months_elapsed"), clean.get("planned_duration_months")
    if "months_elapsed" not in errors and "planned_duration_months" not in errors \
            and elapsed is not None and planned is not None and elapsed > planned:
        errors["months_elapsed"] = "must not be greater than planned_duration_months"

    land_required, land_pct = clean.get("land_acquisition_required"), clean.get("land_acquisition_pct")
    if "land_acquisition_pct" not in errors and land_required == 0 and land_pct is not None and land_pct != 100:
        errors["land_acquisition_pct"] = "must be 100 when land_acquisition_required is 0"

    if errors:
        raise InputValidationError(errors)
    return clean, notes


# ----------------------------------------------------------------------------- prediction
def _to_frame(clean, schema):
    """One-row DataFrame with the training column names and order; missing numbers become NaN."""
    row = {field: (np.nan if clean[field] is None else clean[field]) for field in schema}
    frame = pd.DataFrame([row], columns=list(schema))
    for field, rule in schema.items():
        if rule["type"] == "category":
            frame[field] = frame[field].astype(object)      # the pipeline selects text columns by dtype=object
        else:
            frame[field] = frame[field].astype(float)
    return frame


def predict_risk(raw, path=None):
    """raw inputs (a dict) -> prediction dict. Raises InputValidationError for bad input."""
    artifact = load_artifact(path)
    clean, notes = validate_input(raw, path)

    frame = _to_frame(clean, artifact["input_schema"])
    explanation = explain_prediction(artifact['model'], frame)
    probability = float(artifact["model"].predict_proba(frame)[0, 1])
    threshold = float(artifact["threshold"])

    return {
        "probability": probability,
        "risk_score": int(round(100 * probability)),     # model score from 0 to 100 (calibration not yet verified)
        "is_high_risk": probability >= threshold,
        "threshold": threshold,
        "model_version": artifact["model_version"],
        "warnings": notes,
        "inputs": clean,                # cleaned values, JSON-safe, ready to store
        "explanation": explanation,
    }
