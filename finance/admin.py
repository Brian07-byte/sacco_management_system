from django.contrib import admin
from .models import SaccoAccount, SaccoLedgerEntry, ChargePolicy


@admin.register(SaccoAccount)
class SaccoAccountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "account_type", "balance", "is_active")
    search_fields = ("code", "name")
    list_filter = ("account_type", "is_active")


@admin.register(SaccoLedgerEntry)
class SaccoLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("account", "entry_type", "amount", "created_by", "created_at")
    list_filter = ("entry_type", "account")
    search_fields = ("account__code", "narration")
    ordering = ("-created_at",)


@admin.register(ChargePolicy)
class ChargePolicyAdmin(admin.ModelAdmin):
    list_display = (
        "withdrawal_fee_flat",
        "withdrawal_fee_percent",
        "membership_fee",
        "loan_processing_fee_percent",
        "is_active",
    )