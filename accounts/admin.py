from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_verified", "is_staff")
    list_filter = ("role", "is_verified")
    fieldsets = UserAdmin.fieldsets + (
        ("Civic Connect", {"fields": ("role", "is_verified", "employee_id", "phone_number")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Civic Connect", {"fields": ("role", "is_verified", "employee_id", "phone_number")}),
    )


admin.site.register(User, CustomUserAdmin)