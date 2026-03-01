from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ChargePolicyForm
from .models import ChargePolicy, SaccoAccount, SaccoLedgerEntry


def is_manager(user):
    return user.is_authenticated and getattr(user, "role", None) == "MANAGER"


def manager_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_manager(request.user) and not request.user.is_superuser:
            messages.error(request, "You are not authorized to access Finance.")
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped


def get_or_create_account(code: str, name: str, account_type: str = "INCOME"):
    acct, _ = SaccoAccount.objects.get_or_create(
        code=code,
        defaults={"name": name, "account_type": account_type}
    )
    return acct


def sum_today_for_account(account: SaccoAccount):
    today = timezone.localdate()
    total = SaccoLedgerEntry.objects.filter(
        account=account,
        entry_type="CREDIT",
        created_at__date=today
    ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
    return total


@manager_required
def dashboard(request):
    """
    Finance dashboard:
    - Total SACCO balances by account
    - Today's income by account
    - Total income today (all income accounts)
    """
    today = timezone.localdate()

    # Ensure common accounts exist (ALL fees)
    fees_income = get_or_create_account("FEES_INCOME", "Withdrawal Fees Income", "INCOME")
    membership_fees = get_or_create_account("MEMBERSHIP_FEES", "Membership Fees Income", "INCOME")
    loan_interest = get_or_create_account("LOAN_INTEREST", "Loan Interest Income", "INCOME")
    loan_fees = get_or_create_account("LOAN_FEES", "Loan Processing Fees", "INCOME")

    # Today totals
    fees_today = sum_today_for_account(fees_income)
    membership_today = sum_today_for_account(membership_fees)
    loan_interest_today = sum_today_for_account(loan_interest)
    loan_fees_today = sum_today_for_account(loan_fees)

    total_income_today = fees_today + membership_today + loan_interest_today + loan_fees_today

    # Overall balances (system money)
    total_system_balance = SaccoAccount.objects.filter(is_active=True).aggregate(
        total=models.Sum("balance")
    )["total"] or Decimal("0.00")

    # Latest ledger entries
    latest_entries = SaccoLedgerEntry.objects.select_related("account", "created_by").order_by("-created_at")[:15]

    return render(request, "finance/dashboard.html", {
        "today": today,
        "total_system_balance": total_system_balance,
        "total_income_today": total_income_today,

        "fees_income": fees_income,
        "membership_fees": membership_fees,
        "loan_interest": loan_interest,
        "loan_fees": loan_fees,

        "fees_today": fees_today,
        "membership_today": membership_today,
        "loan_interest_today": loan_interest_today,
        "loan_fees_today": loan_fees_today,

        "latest_entries": latest_entries,
    })


@manager_required
def accounts_list(request):
    accounts = SaccoAccount.objects.order_by("account_type", "code")
    total_balance = SaccoAccount.objects.aggregate(total=models.Sum("balance"))["total"] or Decimal("0.00")
    return render(request, "finance/accounts_list.html", {
        "accounts": accounts,
        "total_balance": total_balance,
    })


@manager_required
def ledger(request):
    """
    Ledger list with optional filters:
    - account=ID
    - date=YYYY-MM-DD
    """
    qs = SaccoLedgerEntry.objects.select_related("account", "created_by").order_by("-created_at")

    account_id = request.GET.get("account")
    date_str = request.GET.get("date")

    selected_account = None
    selected_date = None

    if account_id:
        selected_account = get_object_or_404(SaccoAccount, pk=account_id)
        qs = qs.filter(account=selected_account)

    if date_str:
        try:
            selected_date = timezone.datetime.fromisoformat(date_str).date()
            qs = qs.filter(created_at__date=selected_date)
        except ValueError:
            messages.error(request, "Invalid date format. Use YYYY-MM-DD.")

    total_credit = qs.filter(entry_type="CREDIT").aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
    total_debit = qs.filter(entry_type="DEBIT").aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

    accounts = SaccoAccount.objects.order_by("code")

    return render(request, "finance/ledger.html", {
        "entries": qs[:300],
        "accounts": accounts,
        "selected_account": selected_account,
        "selected_date": selected_date,
        "total_credit": total_credit,
        "total_debit": total_debit,
    })


@manager_required
def fees_report(request):
    """
    Fees report = income breakdown (today or by date range)
    GET:
      - start=YYYY-MM-DD
      - end=YYYY-MM-DD
    """
    start = request.GET.get("start")
    end = request.GET.get("end")

    qs = SaccoLedgerEntry.objects.select_related("account").filter(entry_type="CREDIT").order_by("-created_at")

    start_date = None
    end_date = None

    if start:
        try:
            start_date = timezone.datetime.fromisoformat(start).date()
            qs = qs.filter(created_at__date__gte=start_date)
        except ValueError:
            messages.error(request, "Invalid start date (use YYYY-MM-DD).")

    if end:
        try:
            end_date = timezone.datetime.fromisoformat(end).date()
            qs = qs.filter(created_at__date__lte=end_date)
        except ValueError:
            messages.error(request, "Invalid end date (use YYYY-MM-DD).")

    # Ensure accounts exist
    fees_income = get_or_create_account("FEES_INCOME", "Withdrawal Fees Income", "INCOME")
    membership_fees = get_or_create_account("MEMBERSHIP_FEES", "Membership Fees Income", "INCOME")
    loan_interest = get_or_create_account("LOAN_INTEREST", "Loan Interest Income", "INCOME")
    loan_fees = get_or_create_account("LOAN_FEES", "Loan Processing Fees", "INCOME")

    def sum_for(acct):
        return qs.filter(account=acct).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

    total_withdrawal_fees = sum_for(fees_income)
    total_membership_fees = sum_for(membership_fees)
    total_loan_interest = sum_for(loan_interest)
    total_loan_fees = sum_for(loan_fees)

    grand_total = total_withdrawal_fees + total_membership_fees + total_loan_interest + total_loan_fees

    return render(request, "finance/fees_report.html", {
        "start": start_date,
        "end": end_date,
        "total_withdrawal_fees": total_withdrawal_fees,
        "total_membership_fees": total_membership_fees,
        "total_loan_interest": total_loan_interest,
        "total_loan_fees": total_loan_fees,
        "grand_total": grand_total,
        "rows": qs[:300],
    })


@manager_required
def charge_policy(request):
    policy = ChargePolicy.objects.first()

    if request.method == "POST":
        form = ChargePolicyForm(request.POST, instance=policy)
        if form.is_valid():
            policy = form.save()
            messages.success(request, "Charge policy updated successfully.")
            return redirect("finance:policy")
        messages.error(request, "Please correct the errors below.")
    else:
        form = ChargePolicyForm(instance=policy)

    return render(request, "finance/policy.html", {
        "policy": policy,
        "form": form,
    })