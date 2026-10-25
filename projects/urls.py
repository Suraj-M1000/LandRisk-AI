from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name = "home"),
    path("about/", views.about, name = "about"),
    path("contact/", views.contact, name = "contact"),
    path("services/", views.services, name="services"),
    path("roadmap/", views.roadmap, name="roadmap"),
    path("projects/", views.ProjectListView.as_view(), name= "project_list"),
    path("projects/create/", views.ProjectCreateView.as_view(), name= "project_create"),
    path("projects/<int:pk>/detail/", views.ProjectDetailView.as_view(), name= "project_detail"),
    path("projects/<int:pk>/edit/", views.ProjectUpdateView.as_view(), name = "project_update"),
    path("projects/<int:pk>/delete/", views.ProjectDeleteView.as_view(), name = "project_delete"),
    path("projects/<int:pk>/predict", views.ProjectPredictView.as_view(), name = "project_predict"),
    path(
    "dashboard/",
    views.DashboardView.as_view(),
    name="dashboard",
),
]
