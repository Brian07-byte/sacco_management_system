from django.conf import settings
from django.db import models
from django.utils import timezone


class Member(models.Model):
    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("SUSPENDED", "Suspended"),
        ("EXITED", "Exited"),
    )

    GENDER_CHOICES = (
        ("MALE", "Male"),
        ("FEMALE", "Female"),
        ("OTHER", "Other"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="member_profile"
    )

    # SACCO visible number
    member_number = models.CharField(max_length=30, unique=True)

    # Membership state
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    is_active = models.BooleanField(default=True)
    date_joined = models.DateField(auto_now_add=True)

    # KYC
    national_id = models.CharField(max_length=20, unique=True)
    kra_pin = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)

    # Contact / Address
    address = models.CharField(max_length=255, blank=True)
    town = models.CharField(max_length=120, blank=True)
    county = models.CharField(max_length=120, blank=True)
    # Change this line temporarily
    phone_number = models.CharField(
    max_length=15, 
    null=True,      # Add this
    blank=True,     # Add this
    unique=False,    # Change to False temporarily
    help_text="Primary mobile number"
)
    alternative_phone = models.CharField(max_length=15, blank=True)

    # Next of kin
    next_of_kin_name = models.CharField(max_length=120, blank=True)
    next_of_kin_phone = models.CharField(max_length=15, blank=True)
    next_of_kin_relationship = models.CharField(max_length=60, blank=True)

    # -------- FEES / BILLING (NEW) --------
    membership_fee_paid = models.BooleanField(default=False)
    membership_fee_paid_at = models.DateTimeField(null=True, blank=True)

    # If you later charge monthly account fee and allow it to accumulate:
    account_fee_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_account_fee_charged_on = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        name = self.user.get_full_name() or self.user.username
        return f"{self.member_number} - {name}"