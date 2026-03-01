from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "module", "action", "actor", "member", "reference", "message")
    list_filter = ("module", "action", "created_at")
    search_fields = ("reference", "message", "actor__username", "member__member_number")
    date_hierarchy = "created_at"