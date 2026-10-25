
import unittest

from ml.inference import (
    predict_risk,
    get_input_schema,
    load_artifact,
    InputValidationError,
)


class TestLandRiskInference(unittest.TestCase):

    def setUp(self):
        # A valid example project reused by individual tests.
        self.project = {
            "sector": "Energy",
            "state": "Maharashtra",
            "project_cost_cr": 877.50,
            "planned_duration_months": 40,
            "months_elapsed": 38,
            "physical_progress_pct": 83.10,
            "expenditure_pct": 75.70,
            "contractor_experience_years": 16,
            "land_acquisition_required": 0,
            "land_acquisition_pct": 100.00,
        }

    def test_artifact_loads(self):
        artifact = load_artifact()

        self.assertIn("model", artifact)
        self.assertIn("threshold", artifact)
        self.assertIn("model_version", artifact)

    def test_input_schema_loads(self):
        schema = get_input_schema()

        self.assertIsInstance(schema, dict)
        self.assertGreater(len(schema), 0)

    def test_valid_project_returns_prediction(self):
        result = predict_risk(self.project)

        expected_keys = {
            "probability",
            "risk_score",
            "is_high_risk",
            "threshold",
            "model_version",
            "warnings",
            "inputs",
            "explanation",
        }

        self.assertTrue(expected_keys.issubset(result.keys()))

    def test_probability_is_in_valid_range(self):
        result = predict_risk(self.project)

        self.assertGreaterEqual(result["probability"], 0.0)
        self.assertLessEqual(result["probability"], 1.0)

    def test_risk_score_is_between_zero_and_hundred(self):
        result = predict_risk(self.project)

        self.assertGreaterEqual(result["risk_score"], 0)
        self.assertLessEqual(result["risk_score"], 100)

    def test_threshold_controls_classification(self):
        result = predict_risk(self.project)

        expected_classification = (
            result["probability"] >= result["threshold"]
        )

        self.assertEqual(
            result["is_high_risk"],
            expected_classification,
        )

    def test_explanation_is_verified(self):
        result = predict_risk(self.project)
        explanation = result["explanation"]

        self.assertTrue(explanation["verified"])
        self.assertIn("drivers_up", explanation)
        self.assertIn("drivers_down", explanation)

    def test_unknown_input_is_rejected(self):
        invalid_project = self.project.copy()
        invalid_project["made_up_feature"] = 123

        with self.assertRaises(InputValidationError):
            predict_risk(invalid_project)

    def test_invalid_progress_is_rejected(self):
        invalid_project = self.project.copy()
        invalid_project["physical_progress_pct"] = 150

        with self.assertRaises(InputValidationError):
            predict_risk(invalid_project)

    def test_invalid_schedule_is_rejected(self):
        invalid_project = self.project.copy()
        invalid_project["months_elapsed"] = 45

        with self.assertRaises(InputValidationError):
            predict_risk(invalid_project)

    def test_invalid_land_combination_is_rejected(self):
        invalid_project = self.project.copy()
        invalid_project["land_acquisition_required"] = 0
        invalid_project["land_acquisition_pct"] = 70

        with self.assertRaises(InputValidationError):
            predict_risk(invalid_project)

    def test_suggestions_only_appear_on_higher_risk_drivers(self):
        result = predict_risk(self.project)
        explanation = result["explanation"]

        for driver in explanation["drivers_up"]:
            self.assertEqual(driver["direction"], "higher_risk")
            self.assertIn("suggestion", driver)

        for driver in explanation["drivers_down"]:
            self.assertEqual(driver["direction"], "lower_risk")
            self.assertNotIn("suggestion", driver)

if __name__ == "__main__":
    unittest.main()
