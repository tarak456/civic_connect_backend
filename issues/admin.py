from django.contrib import admin
from .models import Issue, Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "status", "citizen", "department", "created_at")
    list_filter = ("status", "category", "department")
    search_fields = ("title", "description")