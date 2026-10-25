from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView , DeleteView, DetailView, TemplateView
from django.http import HttpResponse
from .models import Project
from .forms import ProjectForm
from django.urls import reverse_lazy, reverse
from django.views import View
from ml.inference import predict_risk
from predictions.models import Prediction
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Avg, OuterRef, Subquery
from predictions.models import Prediction
import logging
from django.db import transaction

# Create your views here.

logger = logging.getLogger(__name__)

def home(request):
    # return HttpResponse("Welcome to LandRisk AI!!")
    return render(request, "projects/home.html")

def about(request):
    return render(request, "projects/about.html")

def contact(request):
    return render(request, 'projects/contact.html')

def services(request):
    return render(request, "projects/services.html")


def roadmap(request):
    return render(request, "projects/roadmap.html")

#  Function Based Views
# def project_list(request):
#     projects = Project.objects.all().order_by("-created_at")
#     return render(request, "projects/projects_list.html", {"projects" : projects})


# Class Based Views
class ProjectListView(LoginRequiredMixin ,ListView):
    model = Project
    template_name = "projects/projects_list.html"
    context_object_name = 'projects'

    def get_queryset(self):
        return Project.objects.filter(owner= self.request.user)


# Function Based Views
# def project_detail(request, pk):
#     project = get_object_or_404(Project, id = pk)
#     return render(request, "projects/project_details.html", {"project" : project})


def get_project_monitoring_metrics(project):
    planned_months = project.planned_duration_months
    elapsed_months = project.months_elapsed

    # 1. Percentage of planned time that has elapsed.
    if planned_months > 0:
        schedule_utilization = (
            elapsed_months / planned_months
        ) * 100
    else:
        schedule_utilization = None

    # 2. Difference between expenditure and physical progress.
    progress_gap = (
        project.expenditure_pct - project.physical_progress_pct
    )

    # 3. Compare physical progress with elapsed schedule.
    # A 10-percentage-point tolerance avoids overreacting to small gaps.
    if schedule_utilization is None:
        schedule_status = "Schedule data unavailable"

    elif project.physical_progress_pct < schedule_utilization - 10:
        schedule_status = "Progress behind elapsed schedule"

    elif project.physical_progress_pct > schedule_utilization + 10:
        schedule_status = "Progress ahead of elapsed schedule"

    else:
        schedule_status = "Progress broadly aligned"

    return {
        "schedule_utilization": schedule_utilization,
        "progress_gap": progress_gap,
        "schedule_status": schedule_status,
    }


# Class Based Views
class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "projects/project_details.html"
    context_object_name = 'project'

    def get_queryset(self):
        return Project.objects.filter(owner= self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        predictions = self.object.predictions.order_by("-created_at")

        context["latest_prediction"] = predictions.first()
        context["prediction_history"] = predictions
        context.update(
            get_project_monitoring_metrics(self.object)
        )
        return context






# Function Based Views
# def project_create(request):
#     form = ProjectForm(request.POST or None)
#     if request.method == "POST" and form.is_valid():
#         project = form.save()
#         return redirect("project_detail", pk = project.pk)
#     return render(request, "projects/projects_form.html", {"form":form, "page_title": "Create Project",})



# Class Based Views
class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/projects_form.html"

    def get_success_url(self):
        return reverse_lazy("project_detail", kwargs= {"pk" : self.object.pk})

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(
            self.request,
            "Project created successfully!"
        )
        return super().form_valid(form)      # Everything is valid. Continue with the normal CreateView process





# Function Based Views
# def project_update(request, pk):
#     project = get_object_or_404(Project, id = pk)
#     form = ProjectForm(request.POST or None, instance=project)

#     if (request.method == "POST" and form.is_valid()):
#         project = form.save()
#         return redirect("project_detail", pk=project.pk)

#     return render(request, "projects/projects_form.html", {
#         "form": form,
#         "page_title": "Edit Project",
#     })



# Class Based Views
class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/projects_form.html"

    def get_success_url(self):
        return reverse_lazy("project_detail", kwargs= {"pk" : self.object.pk})

    def get_queryset(self):
        return Project.objects.filter(owner = self.request.user)  # Getting the all project that below to the current login user to update the data



# Function Based Views
# def project_delete(request, pk):
#     project = get_object_or_404(Project, id = pk)
#     if request.method == 'POST':
#         project.delete()
#         return redirect("project_list")
#     return render(request, "projects/project_confirm_delete.html", {"project": project})



# Class Based Views
class ProjectDeleteView(LoginRequiredMixin , DeleteView):
    model = Project
    template_name = "projects/project_confirm_delete.html"
    success_url = reverse_lazy("project_list")

    def get_queryset(self):
        return Project.objects.filter(    # Getting the all project that below to the current login user to delete the data
            owner=self.request.user
        )



class ProjectPredictView(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(
            Project,
            pk=pk,
            owner=request.user
        )

        # Prepare inputs in the format expected by the ML model.
        project_data = {
            "sector": project.get_sector_display(),
            "state": project.get_state_display(),
            "project_cost_cr": project.project_cost_cr,
            "planned_duration_months": project.planned_duration_months,
            "months_elapsed": project.months_elapsed,
            "physical_progress_pct": project.physical_progress_pct,
            "expenditure_pct": project.expenditure_pct,
            "contractor_experience_years": project.contractor_experience_years,
            "land_acquisition_required": int(
                project.land_acquisition_required
            ),
            "land_acquisition_pct": project.land_acquisition_pct,
        }

        # Step 1: Run the ML model.
        try:
            result = predict_risk(project_data)

        except Exception:
            logger.exception(
                "Risk prediction failed for project ID %s",
                project.pk
            )

            messages.error(
                request,
                "The risk assessment could not be generated. "
                "Please try again later or contact support if the problem persists."
            )

            return redirect("project_detail", pk=project.pk)

        # Step 2: Save the result only after inference succeeds.
        try:
            with transaction.atomic():
                Prediction.objects.create(
                    project=project,
                    probability=result["probability"],
                    risk_score=result["risk_score"],
                    is_high_risk=result["is_high_risk"],
                    threshold=result["threshold"],
                    model_version=str(result["model_version"]),
                    warnings=result.get("warnings", []),
                    explanation=result.get("explanation", {}),
                    input_snapshot=project_data,
                )

        except Exception:
            logger.exception(
                "Failed to save risk prediction for project ID %s",
                project.pk
            )

            messages.error(
                request,
                "The risk assessment was generated, but could not be saved. "
                "Your prediction history has not been updated."
            )

            return redirect("project_detail", pk=project.pk)

        # Step 3: Report success.
        messages.success(
            request,
            "Risk assessment completed and saved successfully."
        )

        return redirect("project_detail", pk=project.pk)




class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "projects/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Find the latest prediction belonging to each project.
        latest_predictions = Prediction.objects.filter(
            project=OuterRef("pk")
        ).order_by("-created_at", "-pk")

        # Restrict the dashboard to the logged-in user's projects.
        projects = Project.objects.filter(
            owner=self.request.user
        ).annotate(
            latest_risk_score=Subquery(
                latest_predictions.values("risk_score")[:1]
            ),
            latest_is_high_risk=Subquery(
                latest_predictions.values("is_high_risk")[:1]
            ),
        )

        # Existing dashboard statistics.
        context["total_projects"] = projects.count()

        context["total_predictions"] = Prediction.objects.filter(
            project__owner=self.request.user
        ).count()

        # Count projects using only their latest prediction.
        high_risk_count = projects.filter(
            latest_is_high_risk=True
        ).count()

        lower_risk_count = projects.filter(
            latest_is_high_risk=False
        ).count()

        not_assessed_count = projects.filter(
            latest_is_high_risk__isnull=True
        ).count()

        context["high_risk_projects"] = high_risk_count

        context["average_risk_score"] = projects.aggregate(
            average=Avg("latest_risk_score")
        )["average"]

        # Calculate average physical progress across the user's projects.
        context["average_physical_progress"] = Project.objects.filter(
            owner=self.request.user
        ).aggregate(
            average=Avg("physical_progress_pct")
        )["average"]

        # Calculate average expenditure across the user's projects.
        context["average_expenditure"] = Project.objects.filter(
            owner=self.request.user
        ).aggregate(
            average=Avg("expenditure_pct")
        )["average"]

        context["recent_projects"] = projects.order_by(
            "-created_at"
        )[:5]


        # Get the logged-in user's projects for monitoring calculations.
        user_projects = list(
            Project.objects.filter(owner=self.request.user)
        )

        # Calculate monitoring metrics for each project using our helper.
        monitoring_results = [
            get_project_monitoring_metrics(project)
            for project in user_projects
        ]

        # Average schedule utilization, excluding unavailable values.
        schedule_values = [
            result["schedule_utilization"]
            for result in monitoring_results
            if result["schedule_utilization"] is not None
        ]

        context["average_schedule_utilization"] = (
            sum(schedule_values) / len(schedule_values)
            if schedule_values else None
        )

        # Average expenditure-versus-physical-progress gap.
        gap_values = [
            result["progress_gap"]
            for result in monitoring_results
        ]

        context["average_progress_gap"] = (
            sum(gap_values) / len(gap_values)
            if gap_values else None
        )

        # Count each schedule status across the user's projects.
        status_counts = {
            "Progress behind elapsed schedule": 0,
            "Progress broadly aligned": 0,
            "Progress ahead of elapsed schedule": 0,
            "Schedule data unavailable": 0,
        }

        for result in monitoring_results:
            status_counts[result["schedule_status"]] += 1

        context["schedule_status_labels"] = list(status_counts.keys())
        context["schedule_status_data"] = list(status_counts.values())
        context["schedule_status_counts"] = status_counts


        # Data for the JavaScript chart.
        context["risk_chart_labels"] = [
            "High Risk",
            "Lower Risk",
            "Not Assessed",
        ]

        context["risk_chart_data"] = [
            high_risk_count,
            lower_risk_count,
            not_assessed_count,
        ]

        return context
