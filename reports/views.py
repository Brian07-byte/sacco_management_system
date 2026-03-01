from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from savings.models import SavingsAccount, SavingsTransaction
from loans.models import Loan, LoanRepayment


# -------- Role helpers --------
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


# =========================
# MEMBER REPORTS
# =========================
@member_required
def my_reports_home(request):
    member = request.user.member_profile
    sav = getattr(member, "savings_account", None)
    savings_balance = sav.balance if sav else Decimal("0.00")

    active_loans = Loan.objects.filter(member=member, status="ACTIVE").count()
    total_loan_balance = Loan.objects.filter(member=member).aggregate(
        t=Sum("balance")
    )["t"] or Decimal("0.00")

    return render(request, "reports/member/home.html", {
        "savings_balance": savings_balance,
        "active_loans": active_loans,
        "total_loan_balance": total_loan_balance,
    })


@member_required
def my_savings_report(request):
    member = request.user.member_profile
    account, _ = SavingsAccount.objects.get_or_create(member=member)

    # 1. Get the base QuerySet (do NOT slice yet)
    base_txns = account.transactions.filter(status="POSTED")

    # 2. Perform aggregations on the full (un-sliced) data
    total_in = base_txns.filter(txn_type="DEPOSIT").aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    total_out = base_txns.filter(txn_type="WITHDRAWAL").aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

    # 3. Create the sliced version for the table display
    txns_to_display = base_txns.order_by("-created_at")[:200]

    return render(request, "reports/member/my_savings.html", {
        "account": account,
        "txns": txns_to_display,
        "total_in": total_in,
        "total_out": total_out,
    })

@member_required
def my_loans_report(request):
    member = request.user.member_profile
    loans = Loan.objects.select_related("product").filter(member=member).order_by("-created_at")

    total_principal = loans.aggregate(t=Sum("principal"))["t"] or Decimal("0.00")
    total_balance = loans.aggregate(t=Sum("balance"))["t"] or Decimal("0.00")

    return render(request, "reports/member/my_loans.html", {
        "loans": loans,
        "total_principal": total_principal,
        "total_balance": total_balance,
    })


# =========================
# STAFF REPORTS
# =========================
@staff_required
def staff_reports_home(request):
    total_savings = SavingsAccount.objects.aggregate(t=Sum("balance"))["t"] or Decimal("0.00")
    active_loans = Loan.objects.filter(status="ACTIVE").count()
    loan_balance = Loan.objects.filter(status="ACTIVE").aggregate(t=Sum("balance"))["t"] or Decimal("0.00")
    return render(request, "reports/staff/home.html", {
        "total_savings": total_savings,
        "active_loans": active_loans,
        "loan_balance": loan_balance,
    })


@staff_required
def staff_daily_report(request):
    today = timezone.localdate()

    savings_txns = SavingsTransaction.objects.filter(
        status="POSTED",
        created_at__date=today
    )

    savings_in = savings_txns.filter(txn_type="DEPOSIT").aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    savings_out = savings_txns.filter(txn_type="WITHDRAWAL").aggregate(t=Sum("amount"))["t"] or Decimal("0.00")
    savings_net = (savings_in - savings_out).quantize(Decimal("0.01"))

    repayments_today = LoanRepayment.objects.filter(status="POSTED", created_at__date=today)
    repayments_total = repayments_today.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

    return render(request, "reports/staff/daily.html", {
        "today": today,
        "savings_in": savings_in,
        "savings_out": savings_out,
        "savings_net": savings_net,
        "repayments_total": repayments_total,
        "savings_txns": savings_txns.order_by("-created_at")[:200],
        "repayments": repayments_today.order_by("-created_at")[:200],
    })


@staff_required
def staff_savings_summary(request):
    accounts = SavingsAccount.objects.select_related("member", "member__user").order_by("-balance")
    total_savings = accounts.aggregate(t=Sum("balance"))["t"] or Decimal("0.00")
    return render(request, "reports/staff/savings_summary.html", {
        "accounts": accounts[:300],
        "total_savings": total_savings,
    })


@staff_required
def staff_loans_summary(request):
    loans = Loan.objects.select_related("member", "member__user", "product").order_by("-created_at")
    active = loans.filter(status="ACTIVE")
    total_balance = active.aggregate(t=Sum("balance"))["t"] or Decimal("0.00")
    return render(request, "reports/staff/loans_summary.html", {
        "loans": loans[:300],
        "total_balance": total_balance,
        "active_count": active.count(),
    })


# =========================
# MANAGER REPORTS
# =========================
@manager_required
def manager_reports_home(request):
    total_savings = SavingsAccount.objects.aggregate(t=Sum("balance"))["t"] or Decimal("0.00")
    total_loan_balance = Loan.objects.filter(status="ACTIVE").aggregate(t=Sum("balance"))["t"] or Decimal("0.00")
    return render(request, "reports/manager/home.html", {
        "total_savings": total_savings,
        "total_loan_balance": total_loan_balance,
    })


@manager_required
def manager_loan_portfolio(request):
    active = Loan.objects.filter(status="ACTIVE")
    active_count = active.count()
    active_balance = active.aggregate(t=Sum("balance"))["t"] or Decimal("0.00")

    cleared = Loan.objects.filter(status="CLEARED").count()

    # simple portfolio quality placeholders (we can improve later)
    defaulted = Loan.objects.filter(status="DEFAULTED").count()

    return render(request, "reports/manager/portfolio.html", {
        "active_count": active_count,
        "active_balance": active_balance,
        "cleared_count": cleared,
        "defaulted_count": defaulted,
    })