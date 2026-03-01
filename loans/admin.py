from django.contrib import admin
from .models import LoanProduct, LoanApplication, Loan, LoanRepayment


@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "interest_rate_percent",
        "min_term_months",
        "max_term_months",
        "processing_fee_flat",
        "processing_fee_percent",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "product",
        "requested_amount",
        "term_months",
        "status",
        "submitted_at",
        "verified_by",
        "approved_by",
    )
    list_filter = ("status", "product")
    search_fields = ("member__member_number", "member__national_id", "member__user__username", "product__name")
    ordering = ("-submitted_at",)


class LoanRepaymentInline(admin.TabularInline):
    model = LoanRepayment
    extra = 0
    fields = ("created_at", "amount", "status", "channel", "reference")
    readonly_fields = ("reference", "created_at")
    ordering = ("-created_at",)


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        "member",
        "product",
        "principal",
        "interest_total",
        "fees_total",
        "total_payable",
        "balance",
        "status",
        "disbursement_status",
        "created_at",
    )
    list_filter = ("status", "disbursement_status", "product")
    search_fields = ("member__member_number", "member__national_id", "member__user__username", "product__name")
    readonly_fields = ("created_at",)
    inlines = [LoanRepaymentInline]
    ordering = ("-created_at",)


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = (
        "loan",
        "amount",
        "principal_component",
        "interest_component",
        "penalty_component",
        "status",
        "channel",
        "reference",
        "created_at",
    )
    list_filter = ("status", "channel")
    search_fields = ("reference", "loan__member__member_number", "loan__member__user__username")
    readonly_fields = ("reference", "created_at")
    ordering = ("-created_at",)