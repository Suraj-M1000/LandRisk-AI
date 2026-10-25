from django.contrib import admin
from .models import Project

# Register your models here.



class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "sector" , 'state','project_cost_cr','created_at']  # Which field should admin can see navigating through the admin panel
    search_fields = ["name", 'sector', 'state']  # Field that user can use to search a particular entry.
    list_filter = ['state', 'sector', 'land_acquisition_required']  # Field which we can use for filtering.



admin.site.register(Project, ProjectAdmin)