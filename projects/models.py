from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

# Create your models here.


class Project(models.Model):
    # Basic project information -- choose = ('the value Django stores in the database', "the human-readable label shown to the user.")
    STATE_TYPE_CHOOSE = [
        ("Maha","Maharashtra"),
        ("Guj", "Gujarat"),
        ("Kar", "Karnataka"),
        ("Raj","Rajasthan"),
        ("TN","Tamil Nadu"),
        ("UP", "Uttar Pradesh"),
        ("MP", "Madhya Pradesh"),
        ("Odi","Odisha"),
        ("Tel","Telangana"),
        ("WB","West Bengal"),
        ("Del", "Delhi"),
        ("Ke","Kerala"),
    ]

    SECTOR_CHOOSE = [
        ("RH", "Roads & Highways"),
        ("Rail", "Railways"),
        ("Wat", "Water"),
        ("En", "Energy"),
        ("HC", "Healthcare"),
        ("UD", "Urban Development"),
    ]

    name = models.CharField(max_length=200)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    sector = models.CharField(max_length=100, choices=SECTOR_CHOOSE)
    state = models.CharField(max_length=100, choices=STATE_TYPE_CHOOSE)

    # Project cost and schedule
    project_cost_cr = models.FloatField(
    validators=[MinValueValidator(0)]
    )

    planned_duration_months = models.PositiveIntegerField(
    validators=[MinValueValidator(1)]
    )
    months_elapsed = models.PositiveIntegerField(
    validators = [MinValueValidator(0)]
    )

    # Progress and expenditure
    physical_progress_pct = models.FloatField(
        validators=[
        MinValueValidator(0),
        MaxValueValidator(100),
    ]
    )
    expenditure_pct = models.FloatField(
        validators=[
        MinValueValidator(0),
        MaxValueValidator(100),
    ]
    )

    # Contractor year of working and land acquisition
    contractor_experience_years = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(60),
        ]
    )
    land_acquisition_required = models.BooleanField()
    land_acquisition_pct = models.FloatField(
        validators=[
        MinValueValidator(0),
        MaxValueValidator(100),
    ]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if (not self.land_acquisition_required and self.land_acquisition_pct != 0):
            raise ValidationError({
            "land_acquisition_pct": (
                "Land acquisition progress must be 0% "
                "when land acquisition is not required."
            )
        })
