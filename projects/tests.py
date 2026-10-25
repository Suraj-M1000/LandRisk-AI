
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from projects.models import Project
from predictions.models import Prediction
from projects.forms import ProjectForm
from django.core.exceptions import ValidationError


class ProjectPredictionFailureTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="prediction_test_user",
            password="test-password-123",
        )

        sector_field = Project._meta.get_field("sector")
        state_field = Project._meta.get_field("state")

        self.project = Project.objects.create(
            owner=self.user,
            name="Prediction Failure Test Project",
            sector=sector_field.choices[0][0],
            state=state_field.choices[0][0],
            project_cost_cr=100,
            planned_duration_months=24,
            months_elapsed=6,
            physical_progress_pct=25,
            expenditure_pct=30,
            contractor_experience_years=5,
            land_acquisition_required=False,
            land_acquisition_pct=0,
        )

        self.client.force_login(self.user)

    @patch(
        "projects.views.predict_risk",
        side_effect=RuntimeError("Simulated model failure"),
    )
    def test_inference_failure_does_not_create_prediction(
        self, mocked_predict_risk
    ):
        initial_count = Prediction.objects.filter(
            project=self.project
        ).count()

        with self.assertLogs("projects.views", level="ERROR") as logs:
            response = self.client.post(
                reverse("project_predict", args=[self.project.pk])
            )

        self.assertRedirects(
            response,
            reverse("project_detail", args=[self.project.pk]),
        )

        mocked_predict_risk.assert_called_once()

        final_count = Prediction.objects.filter(
            project=self.project
        ).count()
        self.assertEqual(final_count, initial_count)

        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                "could not be generated" in str(message).lower()
                for message in messages_list
            )
        )

        self.assertTrue(
            any(
                "Simulated model failure" in entry
                for entry in logs.output
            )
        )

    def test_user_cannot_predict_another_users_project(self):
        User = get_user_model()
        other_user = User.objects.create_user(
            username="another_project_owner",
            password="test-password-456",
        )

        other_project = Project.objects.create(
            owner=other_user,
            name="Private Project",
            sector=self.project.sector,
            state=self.project.state,
            project_cost_cr=200,
            planned_duration_months=36,
            months_elapsed=10,
            physical_progress_pct=20,
            expenditure_pct=35,
            contractor_experience_years=8,
            land_acquisition_required=False,
            land_acquisition_pct=0,
        )

        with patch("projects.views.predict_risk") as mocked_predict:
            response = self.client.post(
                reverse("project_predict", args=[other_project.pk])
            )

        self.assertEqual(response.status_code, 404)
        mocked_predict.assert_not_called()

        self.assertFalse(
            Prediction.objects.filter(project=other_project).exists()
        )

    @patch(
        "projects.views.predict_risk",
        return_value={
            "probability": 0.25,
            "risk_score": 25,
            "is_high_risk": False,
            "threshold": 0.5,
            "model_version": "test-model",
            "warnings": [],
            "explanation": {},
        },
    )
    def test_successful_prediction_stores_input_snapshot(
        self, mocked_predict_risk
    ):
        response = self.client.post(
            reverse("project_predict", args=[self.project.pk])
        )

        self.assertRedirects(
            response,
            reverse("project_detail", args=[self.project.pk]),
        )

        prediction = Prediction.objects.get(project=self.project)
        model_inputs = mocked_predict_risk.call_args.args[0]

        self.assertEqual(prediction.input_snapshot, model_inputs)
        self.assertEqual(
            prediction.input_snapshot["project_cost_cr"], 100
        )
        self.assertEqual(
            prediction.input_snapshot["physical_progress_pct"], 25
        )

        self.assertEqual(prediction.risk_score, 25)
        self.assertEqual(prediction.probability, 0.25)
        self.assertEqual(prediction.model_version, "test-model")

    @patch(
        "projects.views.predict_risk",
        return_value={
            "probability": 0.25,
            "risk_score": 25,
            "is_high_risk": False,
            "threshold": 0.5,
            "model_version": "test-model",
            "warnings": [],
            "explanation": {},
        },
    )
    @patch(
        "projects.views.Prediction.objects.create",
        side_effect=RuntimeError("Simulated database save failure"),
    )
    def test_save_failure_does_not_create_prediction(
        self, mocked_create, mocked_predict_risk
    ):
        initial_count = Prediction.objects.filter(
            project=self.project
        ).count()

        with self.assertLogs("projects.views", level="ERROR"):
            response = self.client.post(
                reverse("project_predict", args=[self.project.pk])
            )

        self.assertRedirects(
            response,
            reverse("project_detail", args=[self.project.pk]),
        )

        mocked_predict_risk.assert_called_once()
        mocked_create.assert_called_once()

        final_count = Prediction.objects.filter(
            project=self.project
        ).count()
        self.assertEqual(final_count, initial_count)

        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                "could not be saved" in str(message).lower()
                for message in messages_list
            )
        )


    def test_user_cannot_view_another_users_project(self):
        User = get_user_model()
        other_user = User.objects.create_user(
            username="view_owner",
            password="test-password-123",
        )
        other_project = Project.objects.create(
            owner=other_user,
            name="Private View Project",
            sector=self.project.sector,
            state=self.project.state,
            project_cost_cr=200,
            planned_duration_months=36,
            months_elapsed=10,
            physical_progress_pct=20,
            expenditure_pct=35,
            contractor_experience_years=8,
            land_acquisition_required=False,
            land_acquisition_pct=0,
        )

        response = self.client.get(
            reverse("project_detail", args=[other_project.pk])
        )

        self.assertEqual(response.status_code, 404)


    def test_user_cannot_update_another_users_project(self):
        User = get_user_model()
        other_user = User.objects.create_user(
            username="update_owner",
            password="test-password-123",
        )
        other_project = Project.objects.create(
            owner=other_user,
            name="Private Update Project",
            sector=self.project.sector,
            state=self.project.state,
            project_cost_cr=200,
            planned_duration_months=36,
            months_elapsed=10,
            physical_progress_pct=20,
            expenditure_pct=35,
            contractor_experience_years=8,
            land_acquisition_required=False,
            land_acquisition_pct=0,
        )

        response = self.client.get(
            reverse("project_update", args=[other_project.pk])
        )

        self.assertEqual(response.status_code, 404)
        other_project.refresh_from_db()
        self.assertEqual(other_project.name, "Private Update Project")


    def test_user_cannot_delete_another_users_project(self):
        User = get_user_model()
        other_user = User.objects.create_user(
            username="delete_owner",
            password="test-password-123",
        )
        other_project = Project.objects.create(
            owner=other_user,
            name="Private Delete Project",
            sector=self.project.sector,
            state=self.project.state,
            project_cost_cr=200,
            planned_duration_months=36,
            months_elapsed=10,
            physical_progress_pct=20,
            expenditure_pct=35,
            contractor_experience_years=8,
            land_acquisition_required=False,
            land_acquisition_pct=0,
        )

        response = self.client.post(
            reverse("project_delete", args=[other_project.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            Project.objects.filter(pk=other_project.pk).exists()
        )


    def test_project_list_shows_only_current_users_projects(self):
        User = get_user_model()
        other_user = User.objects.create_user(
            username="list_owner",
            password="test-password-123",
        )
        Project.objects.create(
            owner=other_user,
            name="Another Users Secret Project",
            sector=self.project.sector,
            state=self.project.state,
            project_cost_cr=200,
            planned_duration_months=36,
            months_elapsed=10,
            physical_progress_pct=20,
            expenditure_pct=35,
            contractor_experience_years=8,
            land_acquisition_required=False,
            land_acquisition_pct=0,
        )

        response = self.client.get(reverse("project_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.name)
        self.assertNotContains(response, "Another Users Secret Project")



    def test_created_project_belongs_to_logged_in_user(self):
        response = self.client.post(
            reverse("project_create"),
            {
                "name": "New Ownership Test Project",
                "sector": self.project.sector,
                "state": self.project.state,
                "project_cost_cr": 150,
                "planned_duration_months": 30,
                "months_elapsed": 5,
                "physical_progress_pct": 20,
                "expenditure_pct": 25,
                "contractor_experience_years": 6,
                "land_acquisition_required": False,
                "land_acquisition_pct": 0,
            },
        )

        self.assertEqual(response.status_code, 302)

        created_project = Project.objects.get(
            name="New Ownership Test Project"
        )

        self.assertEqual(created_project.owner, self.user)
        self.assertRedirects(
            response,
            reverse("project_detail", args=[created_project.pk]),
        )


class ProjectFormValidationTests(TestCase):
    def setUp(self):
        sector = Project._meta.get_field("sector").choices[0][0]
        state = Project._meta.get_field("state").choices[0][0]

        self.valid_data = {
            "name": "Validation Test Project",
            "sector": sector,
            "state": state,
            "project_cost_cr": 150,
            "planned_duration_months": 30,
            "months_elapsed": 5,
            "physical_progress_pct": 20,
            "expenditure_pct": 25,
            "contractor_experience_years": 6,
            "land_acquisition_required": False,
            "land_acquisition_pct": 0,
        }

    def test_form_accepts_valid_project_data(self):
        form = ProjectForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejects_land_percentage_when_acquisition_not_required(self):
        data = self.valid_data.copy()
        data["land_acquisition_pct"] = 25

        form = ProjectForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("land_acquisition_pct", form.errors)

    def test_form_accepts_zero_land_percentage_when_not_required(self):
        form = ProjectForm(data=self.valid_data)

        self.assertTrue(form.is_valid(), form.errors)


    def test_form_rejects_physical_progress_above_100(self):
        data = self.valid_data.copy()
        data["physical_progress_pct"] = 120

        form = ProjectForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("physical_progress_pct", form.errors)


    def test_form_rejects_negative_project_cost(self):
        data = self.valid_data.copy()
        data["project_cost_cr"] = -10

        form = ProjectForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("project_cost_cr", form.errors)


    def test_form_rejects_zero_planned_duration(self):
        data = self.valid_data.copy()
        data["planned_duration_months"] = 0

        form = ProjectForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn("planned_duration_months", form.errors)



class ProjectModelValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="model_validation_user",
            password="test-password-123",
        )

        self.project = Project(
            owner=self.user,
            name="Model Validation Project",
            sector=Project._meta.get_field("sector").choices[0][0],
            state=Project._meta.get_field("state").choices[0][0],
            project_cost_cr=100,
            planned_duration_months=24,
            months_elapsed=12,
            physical_progress_pct=50,
            expenditure_pct=55,
            contractor_experience_years=5,
            land_acquisition_required=True,
            land_acquisition_pct=40,
        )

    def test_rejects_physical_progress_above_100(self):
        self.project.physical_progress_pct = 120

        with self.assertRaises(ValidationError):
            self.project.full_clean()

    def test_rejects_negative_project_cost(self):
        self.project.project_cost_cr = -10

        with self.assertRaises(ValidationError):
            self.project.full_clean()

    def test_rejects_zero_planned_duration(self):
        self.project.planned_duration_months = 0

        with self.assertRaises(ValidationError):
            self.project.full_clean()

    def test_rejects_land_percentage_when_acquisition_not_required(self):
        self.project.land_acquisition_required = False
        self.project.land_acquisition_pct = 30

        with self.assertRaises(ValidationError) as error:
            self.project.full_clean()

        self.assertIn(
            "land_acquisition_pct",
            error.exception.message_dict,
        )

    def test_allows_zero_land_percentage_when_not_required(self):
        self.project.land_acquisition_required = False
        self.project.land_acquisition_pct = 0

        self.project.full_clean()
