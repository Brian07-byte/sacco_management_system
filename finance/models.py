from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


# ----------------------------------------
# 1️⃣ SACCO SYSTEM ACCOUNTS
# ----------------------------------------

class SaccoAccount(models.Model):
    """
    Represents SACCO's internal accounts.
    Example:
    - FEES_INCOME
    - LOAN_INTEREST_INCOME
    - MEMBERSHIP_FEES
    - PENALTIES
    """

    ACCOUNT_TYPES = (
        ("INCOME", "Income"),
        ("EXPENSE", "Expense"),
        ("ASSET", "Asset"),
        ("LIABILITY", "Liability"),
    )

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default="INCOME")

    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name} ({self.balance})"


# ----------------------------------------
# 2️⃣ SACCO LEDGER ENTRIES
# ----------------------------------------

class SaccoLedgerEntry(models.Model):
    """
    Every movement of SACCO money is recorded here.
    This is the audit trail for system funds.
    """

    ENTRY_TYPES = (
        ("DEBIT", "Debit"),
        ("CREDIT", "Credit"),
    )

    account = models.ForeignKey(
        SaccoAccount,
        on_delete=models.CASCADE,
        related_name="entries"
    )

    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    narration = models.CharField(max_length=255, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finance_entries"
    )

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.entry_type} {self.amount} - {self.account.code}"


# ----------------------------------------
# 3️⃣ CHARGE POLICY (SYSTEM SETTINGS)
# ----------------------------------------

class ChargePolicy(models.Model):
    """
    Defines SACCO system charges.
    Only one active row should exist.
    """

    withdrawal_fee_flat = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    withdrawal_fee_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Percentage fee on withdrawal amount"
    )

    membership_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    loan_processing_fee_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00")
    )

    is_active = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "SACCO Charge Policy"