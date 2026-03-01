from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string


class LoanProduct(models.Model):
    """
    Manager-configured loan types (rules, interest, fees).
    """
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    # Interest model (we start with flat total interest for whole loan)
    interest_rate_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    # Repayment term rules (months)
    min_term_months = models.PositiveIntegerField(default=1)
    max_term_months = models.PositiveIntegerField(default=36)

    # Eligibility rules (optional, can enforce later in views)
    min_savings_required = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    max_multiplier_of_savings = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("3.00"),
        help_text="Max loan = savings * this multiplier"
    )

    # Processing fee (system income)
    processing_fee_flat = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    processing_fee_percent = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0.00"),
        help_text="Percentage of principal"
    )

    # Penalty settings (optional)
    late_fee_flat = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    late_fee_percent = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0.00"),
        help_text="Percentage of overdue amount"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class LoanApplication(models.Model):
    """
    Member submits an application. Staff verifies. Manager approves/rejects.
    After approval, system creates a Loan account.
    """
    STATUS = (
        ("DRAFT", "Draft"),
        ("PENDING", "Pending"),
        ("VERIFIED", "Verified"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    )

    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="loan_applications")
    product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT, related_name="applications")

    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    term_months = models.PositiveIntegerField(default=12)

    purpose = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")

    submitted_at = models.DateTimeField(default=timezone.now)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="verified_loan_apps"
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="approved_loan_apps"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    decision_reason = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.member.member_number} - {self.product.name} - {self.requested_amount} ({self.status})"


class Loan(models.Model):
    """
    Active loan account created after application is approved.
    Tracks principal, interest, fees, balances, and disbursement status.
    """
    STATUS = (
        ("ACTIVE", "Active"),
        ("CLEARED", "Cleared"),
        ("DEFAULTED", "Defaulted"),
        ("CANCELLED", "Cancelled"),
    )

    DISBURSEMENT_STATUS = (
        ("PENDING", "Pending"),
        ("AUTHORIZED", "Authorized"),
        ("DISBURSED", "Disbursed"),
    )

    member = models.ForeignKey("members.Member", on_delete=models.CASCADE, related_name="loans")
    product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT, related_name="loans")
    application = models.OneToOneField(LoanApplication, on_delete=models.SET_NULL, null=True, blank=True, related_name="loan")

    principal = models.DecimalField(max_digits=12, decimal_places=2)
    term_months = models.PositiveIntegerField(default=12)
    interest_rate_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    # Computed totals (flat interest model)
    interest_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    fees_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))  # processing fees etc.
    penalties_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    total_payable = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    status = models.CharField(max_length=20, choices=STATUS, default="ACTIVE")

    disbursement_status = models.CharField(max_length=20, choices=DISBURSEMENT_STATUS, default="PENDING")
    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="authorized_loans"
    )
    authorized_at = models.DateTimeField(null=True, blank=True)

    disbursed_at = models.DateTimeField(null=True, blank=True)
    disbursement_reference = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def compute_interest_total(self) -> Decimal:
        """
        Flat interest model:
        total interest = principal * (interest_rate% / 100) * (term_months / 12)
        """
        rate = (self.interest_rate_percent or Decimal("0.00")) / Decimal("100.00")
        years = Decimal(str(self.term_months)) / Decimal("12.00")
        return (self.principal * rate * years).quantize(Decimal("0.01"))

    def recompute_totals(self, save: bool = True):
        """
        Recompute interest_total, total_payable, balance (if first set).
        """
        self.interest_total = self.compute_interest_total()
        self.total_payable = (self.principal + self.interest_total + (self.fees_total or Decimal("0.00")) + (self.penalties_total or Decimal("0.00"))).quantize(Decimal("0.01"))

        # If balance is 0 or not set meaningfully, initialize it to total_payable
        if self.balance is None or self.balance == Decimal("0.00"):
            self.balance = self.total_payable

        if save:
            self.save(update_fields=["interest_total", "total_payable", "balance"])

    def __str__(self):
        return f"Loan {self.member.member_number} - {self.principal} ({self.status})"


class LoanRepayment(models.Model):
    """
    Repayment records. We store component breakdown for proper finance posting later.
    """
    STATUS = (
        ("PENDING", "Pending"),
        ("POSTED", "Posted"),
        ("REJECTED", "Rejected"),
    )

    CHANNEL = (
        ("MEMBER", "Member"),
        ("STAFF", "Staff"),
    )

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="repayments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Component breakdown (set during posting)
    principal_component = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    interest_component = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    penalty_component = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    channel = models.CharField(max_length=20, choices=CHANNEL, default="STAFF")
    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="loan_repayments_created"
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="loan_repayments_posted"
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    # Auto reference
    reference = models.CharField(max_length=30, unique=True, editable=False, blank=True)

    narration = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def _generate_reference(self) -> str:
        # Example: LRP-20260226-AB12CD
        today = timezone.localdate().strftime("%Y%m%d")
        return f"LRP-{today}-{get_random_string(6).upper()}"

    def save(self, *args, **kwargs):
        if not self.reference:
            ref = self._generate_reference()
            while LoanRepayment.objects.filter(reference=ref).exists():
                ref = self._generate_reference()
            self.reference = ref
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Repayment {self.amount} - {self.loan.member.member_number} ({self.status})"


