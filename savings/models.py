from decimal import Decimal
import random
import uuid
import base64

from django.db import models
from django.utils import timezone


class SavingsAccount(models.Model):
    member = models.OneToOneField(
        "members.Member",
        on_delete=models.CASCADE,
        related_name="savings_account"
    )

    # ✅ New Account Number Field
    account_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        blank=True
    )

    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    membership_fee_paid = models.BooleanField(default=False)
    membership_fee_paid_at = models.DateTimeField(null=True, blank=True)

    # -----------------------------
    # Generate PSL + 14 digit number
    # -----------------------------
    def _generate_account_number(self):
        PREFIX = "PSL"

        # Generate 14 random digits
        digits = "".join(random.choices("0123456789", k=14))
        return f"{PREFIX}{digits}"

    def save(self, *args, **kwargs):
        if not self.account_number:
            acc_no = self._generate_account_number()

            # Ensure uniqueness
            while SavingsAccount.objects.filter(account_number=acc_no).exists():
                acc_no = self._generate_account_number()

            self.account_number = acc_no

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.account_number} - {self.member.member_number} ({self.balance})"


class SavingsTransaction(models.Model):
    TXN_TYPES = (
        ("DEPOSIT", "Deposit"),
        ("WITHDRAWAL", "Withdrawal"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("POSTED", "Posted"),
        ("REJECTED", "Rejected"),
    )

    CHANNEL_CHOICES = (
        ("MEMBER", "Member"),
        ("STAFF", "Staff"),
    )

    account = models.ForeignKey(SavingsAccount, on_delete=models.CASCADE, related_name="transactions")
    txn_type = models.CharField(max_length=20, choices=TXN_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # ✅ Fee charged to member (normally applies to withdrawals only)
    fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # ✅ Membership fee deducted from FIRST approved deposit (audit)
    membership_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="STAFF")
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="savings_txn_created"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="savings_txn_approved"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # ✅ Auto-generated unique reference (Mpesa-style)
    reference = models.CharField(max_length=30, unique=True, editable=False, blank=True)

    narration = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    # -----------------------------
    # Mpesa-style reference generator
    # -----------------------------
    def _generate_reference(self) -> str:
        """
        Generate a short, Mpesa-like, globally unique reference.

        Format: SAV-XXXXXXXXXX
        Where X is uppercase Base32 characters (A-Z, 2-7) - avoids ambiguous chars.
        Uses UUID4 for randomness (very low collision risk).
        """
        PREFIX = "PSL"
        REF_LEN = 10  # change to 12 if you want longer like SAV-XXXXXXXXXXXX

        # uuid4 => 128-bit random
        u = uuid.uuid4().bytes  # 16 bytes
        # base32 => A-Z and 2-7, then strip '=' padding
        token = base64.b32encode(u).decode("ascii").rstrip("=").upper()

        # Take first REF_LEN characters
        code = token[:REF_LEN]
        return f"{PREFIX}-{code}"

    def save(self, *args, **kwargs):
        """
        Ensures reference is generated once and is unique.

        Why we still loop:
        - reference has a UNIQUE constraint
        - extremely unlikely, but we guarantee no collision
        """
        if not self.reference:
            ref = self._generate_reference()
            while SavingsTransaction.objects.filter(reference=ref).exists():
                ref = self._generate_reference()
            self.reference = ref

        super().save(*args, **kwargs)

    @property
    def total_effect(self):
        """
        How much this transaction affects the member's balance when POSTED.
        Deposit => + (amount - membership_fee_amount)
        Withdrawal => - (amount + fee_amount)
        """
        if self.txn_type == "DEPOSIT":
            return (self.amount or Decimal("0.00")) - (self.membership_fee_amount or Decimal("0.00"))
        return (self.amount or Decimal("0.00")) + (self.fee_amount or Decimal("0.00"))

    def __str__(self):
        return f"{self.txn_type} {self.amount} - {self.account.member.member_number} ({self.status})"