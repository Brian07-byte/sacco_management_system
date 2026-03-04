from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.shortcuts import render
from django.utils import timezone

from members.models import Member
from savings.models import SavingsAccount, SavingsTransaction
from settingsapp.models import ChargePolicy

from audits.models import AuditLog
from loans.models import Loan, LoanRepayment
from finance.models import SaccoAccount  # you created this in finance app


def _role(user):
    if getattr(user, "is_superuser", False):
        return "MANAGER"
    return getattr(user, "role", "")


def _money(v):
    return v if v is not None else Decimal("0.00")


def landing(request):
    # You already have landing. Keep your existing landing if you want.
    return render(request, "core/landing.html")


@login_required
def dashboard(request):
    user = request.user
    role = _role(user)
    today = timezone.localdate()

    context = {
        "role": role,
        "today": today,
    }

    # =========================
    # MEMBER DASHBOARD
    # =========================
    if role == "MEMBER":
        member = getattr(user, "member_profile", None)

        # safety: if member profile missing
        if not member:
            context.update({
                "member": None,
                "member_issue": "Member profile missing. Contact support.",
            })
            return render(request, "core/dashboard.html", context)

        # savings
        savings_account, _ = SavingsAccount.objects.get_or_create(member=member)
        savings_balance = savings_account.balance

        posted_txns = SavingsTransaction.objects.filter(
            account=savings_account,
            status="POSTED",
        )
        pending_txns = SavingsTransaction.objects.filter(
            account=savings_account,
            status="PENDING",
        ).order_by("-created_at")

        total_deposits = _money(posted_txns.filter(txn_type="DEPOSIT").aggregate(t=Sum("amount"))["t"])
        total_withdrawals = _money(posted_txns.filter(txn_type="WITHDRAWAL").aggregate(t=Sum("amount"))["t"])
        
        # Comprehensive fee calculation for member (Savings fees + Membership fees if applicable)
        total_fees = _money(posted_txns.aggregate(
            t=Sum("fee_amount") + Sum("membership_fee_amount")
        )["t"])

        recent_txns = SavingsTransaction.objects.filter(
            account=savings_account
        ).order_by("-created_at")[:8]

        # loans
        active_loans = Loan.objects.filter(member=member, status="ACTIVE").order_by("-created_at")
        loan_balance_total = _money(active_loans.aggregate(t=Sum("balance"))["t"])
        active_loans_count = active_loans.count()

        last_repayment = LoanRepayment.objects.filter(
            loan__member=member,
            status="POSTED"
        ).order_by("-created_at").first()

        # member security audits
        my_security = AuditLog.objects.filter(
            actor=user,
            module__in=["SECURITY", "SYSTEM"],
            action__in=["LOGIN", "LOGOUT"]
        ).order_by("-created_at")[:5]

        context.update({
            "member": member,
            "member_number": member.member_number,
            "member_status": getattr(member, "status", "ACTIVE"),
            "savings_account": savings_account,
            "savings_balance": savings_balance,
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "total_fees": total_fees,
            "pending_count": pending_txns.count(),
            "pending_txns": pending_txns[:6],
            "recent_txns": recent_txns,
            "active_loans_count": active_loans_count,
            "loan_balance_total": loan_balance_total,
            "active_loans": active_loans[:5],
            "last_repayment": last_repayment,
            "my_security": my_security,
        })
        return render(request, "core/dashboard.html", context)

    # =========================
    # STAFF (CLERK / MANAGER) DASHBOARD
    # =========================
    
    # 1. Savings Activity Today
    todays_savings = SavingsTransaction.objects.filter(
        status="POSTED",
        created_at__date=today
    )
    today_deposit_vol = _money(todays_savings.filter(txn_type="DEPOSIT").aggregate(t=Sum("amount"))["t"])
    today_withdraw_vol = _money(todays_savings.filter(txn_type="WITHDRAWAL").aggregate(t=Sum("amount"))["t"])
    
    # 2. Loan Repayments Today
    repayments_today = LoanRepayment.objects.filter(status="POSTED", created_at__date=today)
    today_repayments = _money(repayments_today.aggregate(t=Sum("amount"))["t"])

    # 3. Accurate Fees Calculation (Savings Fees + Membership Fees Collected)
    savings_fees = _money(todays_savings.aggregate(t=Sum("fee_amount"))["t"])
    membership_fees = _money(todays_savings.aggregate(t=Sum("membership_fee_amount"))["t"])
    # Add loan processing fees if they are tracked in today's loan objects
    today_total_fees = savings_fees + membership_fees

    # 4. Accurate Net Flow
    # Inflow = Deposits + Repayments + Fees
    # Outflow = Withdrawals
    today_net = (today_deposit_vol + today_repayments + today_total_fees - today_withdraw_vol).quantize(Decimal("0.01"))

    # Pending queues (Savings)
    pending_savings = SavingsTransaction.objects.select_related(
        "account", "account__member", "account__member__user"
    ).filter(status="PENDING").order_by("created_at")
    pending_savings_count = pending_savings.count()

    # Member stats
    total_members = Member.objects.count()
    active_members = Member.objects.filter(status="ACTIVE").count() if hasattr(Member, "status") else Member.objects.filter(is_active=True).count()

    # Loan stats
    active_loans_qs = Loan.objects.filter(status="ACTIVE")
    active_loans_count = active_loans_qs.count()
    loan_book_balance = _money(active_loans_qs.aggregate(t=Sum("balance"))["t"])

    # Recent operational activity
    recent_staff_txns = SavingsTransaction.objects.select_related(
        "account", "account__member"
    ).filter(status="POSTED").order_by("-created_at")[:10]

    context.update({
        "total_members": total_members,
        "active_members": active_members,
        "today_in": today_deposit_vol,
        "today_out": today_withdraw_vol,
        "today_net": today_net,
        "today_fees": today_total_fees,
        "today_repayments": today_repayments,
        "pending_savings_count": pending_savings_count,
        "pending_savings": pending_savings[:8],
        "active_loans_count": active_loans_count,
        "loan_book_balance": loan_book_balance,
        "recent_staff_txns": recent_staff_txns,
    })

    # =========================
    # MANAGER EXTRA (FINANCE + AUDIT)
    # =========================
    if role == "MANAGER":
        policy = ChargePolicy.objects.first()

        def _acct(code, name):
            acc, _ = SaccoAccount.objects.get_or_create(code=code, defaults={"name": name})
            return acc

        fees_income_acc = _acct("FEES_INCOME", "Fees Income")
        membership_fees_acc = _acct("MEMBERSHIP_FEES", "Membership Fees")
        loan_fees_acc = _acct("LOAN_FEES", "Loan Fees")
        loan_interest_acc = _acct("LOAN_INTEREST", "Loan Interest")

        # Audit summary today
        audit_today = AuditLog.objects.filter(created_at__date=today)
        audit_today_count = audit_today.count()
        approvals_today = audit_today.filter(action="APPROVE").count()

        context.update({
            "policy": policy,
            "fees_income_balance": _money(getattr(fees_income_acc, "balance", Decimal("0.00"))),
            "membership_fees_balance": _money(getattr(membership_fees_acc, "balance", Decimal("0.00"))),
            "loan_fees_balance": _money(getattr(loan_fees_acc, "balance", Decimal("0.00"))),
            "loan_interest_balance": _money(getattr(loan_interest_acc, "balance", Decimal("0.00"))),
            "audit_today_count": audit_today_count,
            "approvals_today": approvals_today,
            "recent_audits": AuditLog.objects.select_related("actor", "member").order_by("-created_at")[:10],
        })

    return render(request, "core/dashboard.html", context)