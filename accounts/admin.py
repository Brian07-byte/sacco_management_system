from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    list_display = ("username", "email", "role", "is_staff", "is_active", "date_joined")
    list_filter = ("role", "is_staff", "is_active")

    fieldsets = UserAdmin.fieldsets + (
        ("SACCO Role Info", {"fields": ("role", "phone_number")}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("SACCO Role Info", {"fields": ("role", "phone_number")}),
    )

    search_fields = ("username", "email", "phone_number")
    ordering = ("-date_joined",)