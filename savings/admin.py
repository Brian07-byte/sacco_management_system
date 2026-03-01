from django.contrib import admin
from .models import SavingsAccount, SavingsTransaction


@admin.register(SavingsAccount)
class SavingsAccountAdmin(admin.ModelAdmin):
    list_display = ("member", "balance", "created_at")
    search_fields = ("member__member_number", "member__national_id", "member__user__username")
    ordering = ("-created_at",)


@admin.register(SavingsTransaction)
class SavingsTransactionAdmin(admin.ModelAdmin):
    list_display = ("account", "txn_type", "amount", "status", "channel", "created_by", "approved_by", "created_at")
    list_filter = ("txn_type", "status", "channel", "created_at")
    search_fields = ("account__member__member_number", "reference", "created_by__username")
    ordering = ("-created_at",)