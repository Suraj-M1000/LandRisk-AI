
from django import forms
from .models import Project


class ProjectForm(forms.ModelForm):     # ProjectForm works as an form builder
    class Meta:                        # Meta (inner class) as its configuration instructions/settings related to this Form.
        model = Project
        fields = [
            "name",
            "sector",
            "state",
            "project_cost_cr",
            "planned_duration_months",
            "months_elapsed",
            "physical_progress_pct",
            "expenditure_pct",
            "contractor_experience_years",
            "land_acquisition_required",
            "land_acquisition_pct",
        ]

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "sector": forms.Select(attrs={"class": "form-control"}),
            "state": forms.Select(attrs={"class": "form-control"}),
            "project_cost_cr": forms.NumberInput(attrs={"class": "form-control"}),
            "planned_duration_months": forms.NumberInput(attrs={"class": "form-control"}),
            "months_elapsed": forms.NumberInput(attrs={"class": "form-control"}),
            "physical_progress_pct": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
            "expenditure_pct": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
            "contractor_experience_years": forms.NumberInput(attrs={"class": "form-control"}),
            "land_acquisition_required": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "land_acquisition_pct": forms.NumberInput(attrs={"class": "form-control", "step": "0.1"}),
        }


    def clean(self):
        cleaned_data = super().clean()

        required = cleaned_data.get("land_acquisition_required")
        percentage = cleaned_data.get("land_acquisition_pct")

        if required is False and percentage is not None and percentage != 0:
            self.add_error(
                "land_acquisition_pct",
                "Land acquisition progress Should be 0"
            )

        return cleaned_data
