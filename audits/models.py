from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """
    Generic audit trail for compliance and investigations.
    Use module + action + ref fields to link back to real transactions.
    """
    MODULE_CHOICES = (
        ("ACCOUNTS", "Accounts"),
        ("MEMBERS", "Members"),
        ("SAVINGS", "Savings"),
        ("LOANS", "Loans"),
        ("FINANCE", "Finance"),
        ("REPORTS", "Reports"),
        ("SETTINGS", "Settings"),
        ("SYSTEM", "System"),
        ("SECURITY", "Security"),
    )

    ACTION_CHOICES = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("APPROVE", "Approve"),
        ("REJECT", "Reject"),
        ("POST", "Post"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("VIEW", "View"),
        ("EXPORT", "Export"),
    )

    module = models.CharField(max_length=30, choices=MODULE_CHOICES)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)

    # Who did the action
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions"
    )

    # Optional: member affected by the action
    member = models.ForeignKey(
        "members.Member",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs"
    )

    # Human readable summary
    message = models.CharField(max_length=255)

    # Reference: e.g. SavingsTransaction.reference, LoanRepayment.reference, Member.member_number
    reference = models.CharField(max_length=100, blank=True)

    # Optional metadata (lightweight)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["module", "action"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["reference"]),
        ]

    def __str__(self):
        return f"{self.created_at} {self.module}:{self.action} {self.reference}"