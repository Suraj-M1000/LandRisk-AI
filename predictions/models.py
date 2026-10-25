from django.db import models

# Create your models here.

class Prediction(models.Model):
    # Link this prediction to one project
    project = models.ForeignKey(
        "projects.Project",     # Here, the one-to-many relation get build where onw project can have multiple predictions
        on_delete=models.CASCADE,   # on_delete=models.CASCADE means deleting a project also deletes its associated predictions
        related_name="predictions",  # related_name="predictions" will let us retrieve a project's predictions with project.predictions.all() for crud operations
    )
     # Results returned by the ML model
    probability = models.FloatField()
    risk_score = models.PositiveSmallIntegerField()
    is_high_risk = models.BooleanField()
    threshold = models.FloatField()
    model_version = models.CharField(max_length=50)

    # Additional information returned by inference
    warnings = models.JSONField(default = list, blank=True)
    explanation = models.JSONField(default= dict, blank = True)

     # Preserve the inputs used for this prediction
    input_snapshot = models.JSONField()

    # Record when the prediction was created
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prediction for {self.project.name} - Score: {self.risk_score}"
