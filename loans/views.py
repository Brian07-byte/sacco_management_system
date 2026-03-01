from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from finance.models import SaccoAccount, SaccoLedgerEntry
from savings.models import SavingsAccount, SavingsTransaction
from .forms import (
    DisbursementForm,
    MemberLoanApplicationForm,
    RepaymentRequestForm,
    StaffRepaymentForm,
)
from .models import Loan, LoanApplication, LoanProduct, LoanRepayment


# ---------------- Role helpers ----------------
def is_member(user):
    return user.is_authenticated and getattr(user, "role", None) == "MEMBER"


def is_staff_user(user):
    return user.is_authenticated and getattr(user, "role", None) in ("CLERK", "MANAGER")


def is_manager(user):
    return user.is_authenticated and (getattr(user, "role", None) == "MANAGER" or user.is_superuser)


def member_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_member(request.user):
            messages.error(request, "This page is only available to members.")
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped


def staff_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_staff_user(request.user):
            messages.error(request, "You are not authorized to access that page.")
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped


def manager_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_manager(request.user):
            messages.error(request, "Manager authorization required.")
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped


def compute_processing_fee(product: LoanProduct, principal: Decimal) -> Decimal:
    flat_fee = (product.processing_fee_flat or Decimal("0.00"))
    pct = (product.processing_fee_percent or Decimal("0.00")) / Decimal("100.00")
    fee = flat_fee + (principal * pct)
    return fee.quantize(Decimal("0.01"))


# ---------------- MEMBER ----------------
@member_required
def apply_loan(request):
    member = request.user.member_profile
    form = MemberLoanApplicationForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            app = form.save(commit=False)
            app.member = member
            app.status = "PENDING"
            app.submitted_at = timezone.now()
            app.save()
            messages.success(request, "Loan application submitted successfully.")
            return redirect("loans:my_applications")
        messages.error(request, "Please correct the errors below.")
    return render(request, "loans/member_apply.html", {"form": form})


@member_required
def my_applications(request):
    member = request.user.member_profile
    apps = LoanApplication.objects.select_related("product").filter(member=member).order_by("-submitted_at")
    return render(request, "loans/my_applications.html", {"apps": apps})


@member_required
def my_loans(request):
    member = request.user.member_profile
    loans = Loan.objects.select_related("product").filter(member=member).order_by("-created_at")
    return render(request, "loans/my_loans.html", {"loans": loans})


@member_required
def loan_detail(request, pk):
    member = request.user.member_profile
    loan = get_object_or_404(Loan.objects.select_related("product"), pk=pk, member=member)
    repayments = loan.repayments.order_by("-created_at")[:50]

    paid_interest = loan.repayments.filter(status="POSTED").aggregate(
        t=models.Sum("interest_component")
    )["t"] or Decimal("0.00")

    paid_principal = loan.repayments.filter(status="POSTED").aggregate(
        t=models.Sum("principal_component")
    )["t"] or Decimal("0.00")

    return render(request, "loans/loan_detail.html", {
        "loan": loan,
        "repayments": repayments,
        "paid_interest": paid_interest,
        "paid_principal": paid_principal,
    })


@member_required
def member_repay(request, pk):
    member = request.user.member_profile
    loan = get_object_or_404(Loan, pk=pk, member=member)

    if loan.status != "ACTIVE":
        messages.error(request, "This loan is not active.")
        return redirect("loans:loan_detail", pk=loan.pk)

    form = RepaymentRequestForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            rep = form.save(commit=False)
            rep.loan = loan
            rep.channel = "MEMBER"
            rep.status = "PENDING"  # FIXED: Must be ALL CAPS to match staff filter
            rep.created_by = request.user
            rep.save()
            messages.success(request, "Repayment submitted. Awaiting approval.")
            return redirect("loans:loan_detail", pk=loan.pk)
    
    return render(request, "loans/member_repay.html", {"loan": loan, "form": form})


# ---------------- STAFF: Applications ----------------
@staff_required
def applications_queue(request):
    qs = LoanApplication.objects.select_related("member", "member__user", "product").order_by("submitted_at")
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)
    return render(request, "loans/staff/applications_queue.html", {"apps": qs[:300], "status": status})


@staff_required
def application_detail(request, pk):
    app = get_object_or_404(LoanApplication.objects.select_related("member", "member__user", "product"), pk=pk)
    fee_estimate = compute_processing_fee(app.product, app.requested_amount)
    return render(request, "loans/staff/application_detail.html", {
        "app": app,
        "fee_estimate": fee_estimate,
    })


@staff_required
@transaction.atomic
def verify_application(request, pk):
    app = get_object_or_404(LoanApplication.objects.select_for_update(), pk=pk)
    if app.status not in ("PENDING",):
        messages.info(request, "This application cannot be verified in its current status.")
        return redirect("loans:application_detail", pk=app.pk)

    app.status = "VERIFIED"
    app.verified_by = request.user
    app.verified_at = timezone.now()
    app.save(update_fields=["status", "verified_by", "verified_at"])

    messages.success(request, "Application verified successfully.")
    return redirect("loans:application_detail", pk=app.pk)


# ---------------- MANAGER: Approve/Reject ----------------
@manager_required
@transaction.atomic
def approve_application(request, pk):
    app = get_object_or_404(LoanApplication.objects.select_for_update(), pk=pk)

    if app.status not in ("VERIFIED", "PENDING"):
        messages.info(request, "This application cannot be approved in its current status.")
        return redirect("loans:application_detail", pk=app.pk)

    if request.method == "POST":
        principal = app.requested_amount
        product = app.product
        fees_total = compute_processing_fee(product, principal)

        # Create loan account
        loan = Loan.objects.create(
            member=app.member,
            product=product,
            application=app,
            principal=principal,
            term_months=app.term_months,
            interest_rate_percent=product.interest_rate_percent,
            fees_total=fees_total,
            penalties_total=Decimal("0.00"),
            status="ACTIVE",
            disbursement_status="PENDING",
        )
        loan.recompute_totals(save=True)

        # Update application
        app.status = "APPROVED"
        app.approved_by = request.user
        app.approved_at = timezone.now()
        app.save(update_fields=["status", "approved_by", "approved_at"])

        messages.success(request, f"Loan approved for {app.member}. Ready for disbursement.")
        return redirect("loans:pending_disbursements")

    # Handle GET request (renders the detail page with a confirm flag)
    fee_estimate = compute_processing_fee(app.product, app.requested_amount)
    return render(request, "loans/staff/application_detail.html", {
        "app": app,
        "fee_estimate": fee_estimate,
        "show_approval_confirm": True
    })


@manager_required
@transaction.atomic
def reject_application(request, pk):
    app = get_object_or_404(LoanApplication.objects.select_for_update(), pk=pk)
    if app.status in ("APPROVED",):
        messages.error(request, "Cannot reject an approved application.")
        return redirect("loans:application_detail", pk=app.pk)

    if request.method == "POST":
        app.status = "REJECTED"
        app.approved_by = request.user
        app.approved_at = timezone.now()
        app.decision_reason = request.POST.get("reason", "")[:255]
        app.save(update_fields=["status", "approved_by", "approved_at", "decision_reason"])
        messages.success(request, "Application rejected.")
        return redirect("loans:applications_queue")
    
    return redirect("loans:application_detail", pk=app.pk)


# ---------------- DISBURSEMENTS ----------------
@staff_required
def pending_disbursements(request):
    loans = Loan.objects.select_related("member", "member__user", "product").filter(
        status="ACTIVE",
        disbursement_status__in=("PENDING", "AUTHORIZED")
    ).order_by("-created_at")
    return render(request, "loans/staff/pending_disbursements.html", {"loans": loans})


@manager_required
@transaction.atomic
def authorize_disbursement(request, pk):
    loan = get_object_or_404(Loan.objects.select_for_update(), pk=pk)
    if loan.disbursement_status != "PENDING":
        messages.info(request, "This loan is not pending authorization.")
        return redirect("loans:pending_disbursements")

    if (loan.fees_total or Decimal("0.00")) > 0:
        acct, _ = SaccoAccount.objects.select_for_update().get_or_create(
            code="LOAN_FEES",
            defaults={"name": "Loan Processing Fees", "account_type": "INCOME"}
        )
        acct.balance = (acct.balance or Decimal("0.00")) + loan.fees_total
        acct.save(update_fields=["balance"])

        SaccoLedgerEntry.objects.create(
            account=acct,
            entry_type="CREDIT",
            amount=loan.fees_total,
            narration=f"Loan processing fee - {loan.member.member_number} (Loan #{loan.id})",
            created_by=request.user,
        )

    loan.disbursement_status = "AUTHORIZED"
    loan.authorized_by = request.user
    loan.authorized_at = timezone.now()
    loan.save(update_fields=["disbursement_status", "authorized_by", "authorized_at"])

    messages.success(request, "Disbursement authorized.")
    return redirect("loans:pending_disbursements")


@manager_required
@transaction.atomic
def mark_disbursed(request, pk):
    # 1. Lock the loan record
    loan = get_object_or_404(Loan.objects.select_for_update(), pk=pk)
    
    if loan.disbursement_status != "AUTHORIZED":
        messages.error(request, "You must authorize disbursement first.")
        return redirect("loans:pending_disbursements")

    form = DisbursementForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            # --- A. UPDATE LOAN STATUS ---
            loan.disbursement_reference = form.cleaned_data["disbursement_reference"]
            loan.disbursement_status = "DISBURSED"
            loan.disbursed_at = timezone.now()
            loan.save(update_fields=["disbursement_reference", "disbursement_status", "disbursed_at"])

            # --- B. UPDATE MEMBER SAVINGS ---
            savings_account, _ = SavingsAccount.objects.select_for_update().get_or_create(
                member=loan.member
            )
            
            SavingsTransaction.objects.create(
                account=savings_account,
                txn_type="DEPOSIT",
                amount=loan.principal,
                narration=f"Loan Disbursement (Loan #{loan.id})",
                channel="SYSTEM",
                status="POSTED",
                created_by=request.user,
                approved_by=request.user,
                approved_at=timezone.now()
            )

            savings_account.balance = (savings_account.balance or Decimal("0.00")) + loan.principal
            savings_account.save(update_fields=["balance"])

            # --- C. SACCO LEDGER ENTRIES ---
            # 1. Update the 'Loan Portfolio' Account (Asset increases)
            portfolio_acct, _ = SaccoAccount.objects.select_for_update().get_or_create(
                code="LOAN_PORTFOLIO",
                defaults={"name": "Loan Portfolio", "account_type": "ASSET"}
            )
            portfolio_acct.balance = (portfolio_acct.balance or Decimal("0.00")) + loan.principal
            portfolio_acct.save(update_fields=["balance"])

            SaccoLedgerEntry.objects.create(
                account=portfolio_acct,
                entry_type="DEBIT",  # Asset increase is a Debit
                amount=loan.principal,
                narration=f"Loan disbursed to {loan.member.member_number} (Ref: {loan.disbursement_reference})",
                created_by=request.user
            )

            # 2. Update the 'Member Savings' Control Account (Liability increases)
            # This represents the total of all member savings accounts combined
            savings_control_acct, _ = SaccoAccount.objects.select_for_update().get_or_create(
                code="SAVINGS_CONTROL",
                defaults={"name": "Member Savings Control", "account_type": "LIABILITY"}
            )
            savings_control_acct.balance = (savings_control_acct.balance or Decimal("0.00")) + loan.principal
            savings_control_acct.save(update_fields=["balance"])

            SaccoLedgerEntry.objects.create(
                account=savings_control_acct,
                entry_type="CREDIT",  # Liability increase is a Credit
                amount=loan.principal,
                narration=f"Funds moved to savings for member {loan.member.member_number}",
                created_by=request.user
            )

            messages.success(request, f"Loan disbursed. Savings and Ledger updated.")
            return redirect("loans:pending_disbursements")
            
    return render(request, "loans/staff/mark_disbursed.html", {"loan": loan, "form": form})

# ---------------- REPAYMENTS ----------------
@staff_required
@transaction.atomic
def record_repayment(request, pk=None):
    pending_rep = None
    if pk:
        # 1. If PK is provided, we are approving a member's claim
        pending_rep = get_object_or_404(LoanRepayment, pk=pk, status="PENDING")
        loan = pending_rep.loan
        # Pre-fill the form with the member's submitted data
        initial_data = {
            'loan': pending_rep.loan,
            'amount': pending_rep.amount,
            'narration': f"Approved: {pending_rep.narration or ''}"
        }
    else:
        initial_data = {}

    if request.method == "POST":
        form = StaffRepaymentForm(request.POST)
        if form.is_valid():
            # Extract cleaned data
            loan = form.cleaned_data["loan"]
            amount = form.cleaned_data["amount"]
            
            # Lock the loan for update to prevent double-posting
            loan = Loan.objects.select_for_update().get(pk=loan.pk)

            # Calculation Logic (Principal vs Interest)
            # ... (Your existing calculation logic here) ...

            if pending_rep:
                # Update the existing member record
                rep = pending_rep
                rep.amount = amount 
                rep.status = "POSTED"
                rep.posted_by = request.user
                # ... update components ...
                rep.save()
            else:
                # Create a new manual record
                rep = LoanRepayment.objects.create(
                    loan=loan, amount=amount, status="POSTED",
                    channel="STAFF", posted_by=request.user, # etc
                )

            # Update Loan Balance
            loan.balance -= amount
            if loan.balance <= 0:
                loan.balance = 0
                loan.status = "CLEARED"
            loan.save()

            messages.success(request, "Payment posted successfully.")
            return redirect("loans:pending_repayments_list")
    else:
        form = StaffRepaymentForm(initial=initial_data)

    return render(request, "loans/staff/record_repayment.html", {
        "form": form, 
        "pending_rep": pending_rep # Pass this to the template!
    })

# --- STAFF SIDE LIST ---
@staff_required
def pending_repayments_list(request):
    # This filter now matches the "PENDING" set in the member view
    pending_reps = LoanRepayment.objects.filter(
        status="PENDING"
    ).select_related('loan', 'loan__member__user').order_by('-created_at')
    
    return render(request, "loans/staff/pending_repayments.html", {
        "pending_reps": pending_reps
    })


# ---------------- Monitoring ----------------
@staff_required
def active_loans(request):
    loans = Loan.objects.select_related("member", "member__user", "product").filter(status="ACTIVE").order_by("-created_at")
    return render(request, "loans/staff/active_loans.html", {"loans": loans})


@staff_required
def cleared_loans(request):
    loans = Loan.objects.select_related("member", "member__user", "product").filter(status="CLEARED").order_by("-created_at")
    return render(request, "loans/staff/cleared_loans.html", {"loans": loans})


@member_required
def repayment_history(request):
    member = request.user.member_profile
    # Get all repayments across all loans for this member
    repayments = LoanRepayment.objects.filter(
        loan__member=member
    ).select_related('loan', 'loan__product').order_by('-created_at')

    return render(request, "loans/repayment_history.html", {
        "repayments": repayments,
    })


@member_required
def loan_statement(request, pk):
    member = request.user.member_profile
    loan = get_object_or_404(Loan.objects.select_related('product'), pk=pk, member=member)
    
    # Get all POSTED repayments for the statement
    repayments = loan.repayments.filter(status="POSTED").order_by('posted_at')
    
    # Calculate Summary Stats
    total_paid = repayments.aggregate(t=models.Sum('amount'))['t'] or Decimal("0.00")
    
    # logic to create a running balance list
    statement_lines = []
    current_running_balance = loan.total_payable
    
    # We work backwards or forwards; usually, statements show 
    # initial debt then subtract payments.
    for rep in repayments:
        current_running_balance -= rep.amount
        statement_lines.append({
            'date': rep.posted_at or rep.created_at,
            'description': f"Repayment - Ref: {rep.reference}",
            'amount': rep.amount,
            'balance': current_running_balance
        })

    return render(request, "loans/loan_statement.html", {
        "loan": loan,
        "total_paid": total_paid,
        "statement_lines": statement_lines,
    })