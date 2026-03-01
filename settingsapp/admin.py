from django.contrib import admin
from .models import SavingsProduct, ChargePolicy


@admin.register(SavingsProduct)
class SavingsProductAdmin(admin.ModelAdmin):
    list_display = ("name", "minimum_monthly_contribution", "allow_withdrawals", "interest_rate_percent", "is_active")
    list_filter = ("is_active", "allow_withdrawals")
    search_fields = ("name",)


@admin.register(ChargePolicy)
class ChargePolicyAdmin(admin.ModelAdmin):
    list_display = (
        "membership_fee_amount",
        "withdrawal_fee_flat",
        "withdrawal_fee_percent",
        "deposit_fee_flat",
        "deposit_fee_percent",
        "updated_at",
    )

    def has_add_permission(self, request):
        # allow only one policy row
        if ChargePolicy.objects.exists():
            return False
        return True