from decimal import Decimal
from django.db import models
from django.utils import timezone


class SavingsProduct(models.Model):
    """
    Readable by members, editable by manager.
    """
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    minimum_monthly_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    allow_withdrawals = models.BooleanField(default=True)

    # If you want per-product savings interest later
    interest_rate_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ChargePolicy(models.Model):
    """
    One-row configuration: system-wide charges/fees.
    Manager edits, others read-only.
    """
    # Membership fee (deduct once on first approved deposit)
    membership_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # Savings withdrawal fees
    withdrawal_fee_flat = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    withdrawal_fee_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    # Optional: savings deposit charges
    deposit_fee_flat = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    deposit_fee_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return "System Charge Policy"

    class Meta:
        verbose_name_plural = "Charge Policy"