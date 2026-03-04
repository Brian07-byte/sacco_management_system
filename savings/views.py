from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from finance.models import *
from .models import SavingsAccount, SavingsTransaction
from .forms import (
    StaffDepositForm,
    StaffWithdrawalForm,
    MemberDepositForm,
    MemberWithdrawalForm,
)


def is_member(user):
    return user.is_authenticated and getattr(user, "role", None) == "MEMBER"


def is_staff_user(user):
    return user.is_authenticated and getattr(user, "role", None) in ("CLERK", "MANAGER")


def staff_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_staff_user(request.user):
            messages.error(request, "You are not authorized to access that page.")
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped


def member_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_member(request.user):
            messages.error(request, "This page is only available to members.")
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped


# ---------------- MEMBER PAGES ----------------
@member_required
def my_savings(request):
    member = request.user.member_profile
    account, _ = SavingsAccount.objects.get_or_create(member=member)

    posted = account.transactions.filter(status="POSTED")

    total_deposits = posted.filter(txn_type="DEPOSIT").aggregate(
        total=models.Sum("amount")
    )["total"] or Decimal("0.00")

    total_withdrawals = posted.filter(txn_type="WITHDRAWAL").aggregate(
        total=models.Sum("amount")
    )["total"] or Decimal("0.00")

    total_fees = posted.filter(txn_type="WITHDRAWAL").aggregate(
        total=models.Sum("fee_amount")
    )["total"] or Decimal("0.00")

    pending_count = account.transactions.filter(status="PENDING").count()

    last_transaction = account.transactions.order_by("-created_at").first()

    return render(request, "savings/my_savings.html", {
        "account": account,
        "total_deposits": total_deposits,
        "total_withdrawals": total_withdrawals,
        "total_fees": total_fees,
        "pending_count": pending_count,
        "last_transaction": last_transaction,
    })


@member_required
def my_transactions(request):
    member = request.user.member_profile
    account, _ = SavingsAccount.objects.get_or_create(member=member)

    txns = account.transactions.order_by("-created_at")[:200]
    return render(request, "savings/my_transactions.html", {"account": account, "txns": txns})


@member_required
def member_deposit(request):
    member = request.user.member_profile
    account, _ = SavingsAccount.objects.get_or_create(member=member)

    form = MemberDepositForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            narration = form.cleaned_data.get("narration", "")

            SavingsTransaction.objects.create(
                account=account,
                txn_type="DEPOSIT",
                amount=amount,
                narration=narration,
                channel="MEMBER",
                status="PENDING",
                created_by=request.user,
                created_at=timezone.now(),
            )

            messages.success(request, "Deposit submitted successfully. Await staff approval.")
            return redirect("savings:my")

        messages.error(request, "Please correct the errors below.")

    return render(request, "savings/member_deposit.html", {"form": form, "account": account})


@member_required
def member_withdrawal(request):
    member = request.user.member_profile
    account, _ = SavingsAccount.objects.get_or_create(member=member)

    form = MemberWithdrawalForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            narration = form.cleaned_data.get("narration", "")

            if account.balance < amount:
                messages.error(request, "Insufficient balance for that withdrawal request.")
                return render(request, "savings/member_withdrawal.html", {"form": form, "account": account})

            SavingsTransaction.objects.create(
                account=account,
                txn_type="WITHDRAWAL",
                amount=amount,
                narration=narration,
                channel="MEMBER",
                status="PENDING",
                created_by=request.user,
                created_at=timezone.now(),
            )

            messages.success(request, "Withdrawal request submitted. Await staff approval.")
            return redirect("savings:my")

        messages.error(request, "Please correct the errors below.")

    return render(request, "savings/member_withdrawal.html", {"form": form, "account": account})


# ---------------- STAFF PAGES ----------------
from django.db.models import Sum
from django.contrib.admin.views.decorators import staff_member_required # or your custom staff_required
from django.shortcuts import render
from .models import SavingsAccount

@staff_required
def accounts_list(request):
    accounts = SavingsAccount.objects.select_related("member", "member__user").order_by("-created_at")

    total_savings = SavingsAccount.objects.aggregate(
        total=models.Sum("balance")
    )["total"] or Decimal("0.00")

    today = timezone.localdate()

    # Fees collected today
    fees_account = SaccoAccount.objects.filter(code="FEES_INCOME").first()
    if fees_account:
        fees_today = SaccoLedgerEntry.objects.filter(
            account=fees_account,
            entry_type="CREDIT",
            created_at__date=today
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
    else:
        fees_today = Decimal("0.00")

    pending_count = SavingsTransaction.objects.filter(status="PENDING").count()

    # Fees paid per member (sum of posted withdrawal fee_amount)
    fee_rows = SavingsTransaction.objects.filter(
        status="POSTED",
        txn_type="WITHDRAWAL"
    ).values("account__member_id").annotate(total=models.Sum("fee_amount"))

    member_fee_map = {row["account__member_id"]: row["total"] for row in fee_rows}

    return render(request, "savings/accounts_list.html", {
        "accounts": accounts,
        "total_savings": total_savings,
        "fees_today": fees_today,
        "pending_count": pending_count,
        "member_fee_map": member_fee_map,
    })

@staff_required
@transaction.atomic
def record_deposit(request):
    form = StaffDepositForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            member = form.cleaned_data["member"]
            amount = form.cleaned_data["amount"]
            narration = form.cleaned_data.get("narration", "")

            account, _ = SavingsAccount.objects.select_for_update().get_or_create(member=member)

            SavingsTransaction.objects.create(
                account=account,
                txn_type="DEPOSIT",
                amount=amount,
                narration=narration,
                channel="STAFF",
                status="POSTED",
                created_by=request.user,
                approved_by=request.user,
                approved_at=timezone.now(),
                created_at=timezone.now(),
            )

            account.balance = (account.balance or Decimal("0.00")) + amount
            account.save(update_fields=["balance"])

            messages.success(request, f"Deposit recorded for {member.member_number}: +{amount}")
            return redirect("savings:accounts_list")

        messages.error(request, "Please correct the errors below.")

    return render(request, "savings/record_deposit.html", {"form": form})


@staff_required
@transaction.atomic
def record_withdrawal(request):
    form = StaffWithdrawalForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            member = form.cleaned_data["member"]
            amount = form.cleaned_data["amount"]
            narration = form.cleaned_data.get("narration", "")

            account, _ = SavingsAccount.objects.select_for_update().get_or_create(member=member)

            policy = ChargePolicy.objects.first()
            if not policy:
                messages.error(request, "Charge policy is not configured. Please contact manager.")
                return render(request, "savings/record_withdrawal.html", {"form": form})

            fee = (policy.withdrawal_fee_flat or Decimal("0.00"))
            percent_fee = (policy.withdrawal_fee_percent or Decimal("0.00")) / Decimal("100.00")
            fee = fee + (amount * percent_fee)

            total_deduction = amount + fee

            if account.balance < total_deduction:
                messages.error(request, "Insufficient balance after withdrawal fee.")
                return render(request, "savings/record_withdrawal.html", {"form": form})

            # Create posted transaction (withdrawal amount) and store fee
            txn = SavingsTransaction.objects.create(
                account=account,
                txn_type="WITHDRAWAL",
                amount=amount,
                fee_amount=fee,
                narration=narration,
                channel="STAFF",
                status="POSTED",
                created_by=request.user,
                approved_by=request.user,
                approved_at=timezone.now(),
                created_at=timezone.now(),
            )

            # Deduct total (withdrawal + fee)
            account.balance = (account.balance or Decimal("0.00")) - total_deduction
            account.save(update_fields=["balance"])

            # Credit SACCO fees income
            fees_account, _ = SaccoAccount.objects.select_for_update().get_or_create(
                code="FEES_INCOME",
                defaults={"name": "Fees Income"}
            )
            fees_account.balance = (fees_account.balance or Decimal("0.00")) + fee
            fees_account.save(update_fields=["balance"])

            SaccoLedgerEntry.objects.create(
                account=fees_account,
                entry_type="CREDIT",
                amount=fee,
                narration=f"Withdrawal fee for {member.member_number} (Txn {txn.reference})",
                created_by=request.user
            )

            messages.success(
                request,
                f"Withdrawal recorded for {member.member_number}: -{amount} (Fee: {fee})"
            )
            return redirect("savings:accounts_list")

        messages.error(request, "Please correct the errors below.")

    return render(request, "savings/record_withdrawal.html", {"form": form})


def daily_transactions(request):
    # Use localdate to match the Kenyan timezone configuration
    today = timezone.localdate()

    # Optimized Query: Select related to reduce DB hits
    # We check for 'POSTED' or 'SUCCESSFUL' to be safe
    txns = SavingsTransaction.objects.select_related(
        "account", "account__member", "account__member__user"
    ).filter(
        created_at__date=today
    ).filter(
        Q(status="POSTED") | Q(status="SUCCESSFUL")
    ).order_by("-created_at")

    # Aggregations
    total_in = txns.filter(txn_type="DEPOSIT").aggregate(
        total=Sum("amount"))["total"] or Decimal("0.00")
    total_out = txns.filter(txn_type="WITHDRAWAL").aggregate(
        total=Sum("amount"))["total"] or Decimal("0.00")
    net_flow = total_in - total_out

    # Total liquidity in the system
    closing_balance = SavingsAccount.objects.aggregate(
        total=Sum("balance"))["total"] or Decimal("0.00")

    # System Revenue (Fees) Logic
    # We search case-insensitively for the account code
    fees_account = SaccoAccount.objects.filter(code__iexact="FEES_INCOME").first()
    
    if fees_account:
        fees_today = SaccoLedgerEntry.objects.filter(
            account=fees_account,
            entry_type="CREDIT",
            created_at__date=today
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    else:
        # Fallback: Sum fee fields from the transactions themselves if ledger is empty
        fees_today = txns.aggregate(
            total=Sum(models.F("fee_amount") + models.F("membership_fee_amount"))
        )["total"] or Decimal("0.00")

    context = {
        "today": today,
        "txns": txns,
        "total_in": total_in,
        "total_out": total_out,
        "net_flow": net_flow,
        "closing_balance": closing_balance,
        "fees_today": fees_today,
    }
    return render(request, "savings/daily_transactions.html", context)

# ---------------- STAFF APPROVAL QUEUE ----------------
@staff_required
def pending_transactions(request):
    txns = SavingsTransaction.objects.select_related(
        "account", "account__member", "account__member__user"
    ).filter(status="PENDING").order_by("created_at")

    pending_deposits = txns.filter(txn_type="DEPOSIT").aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
    pending_withdrawals = txns.filter(txn_type="WITHDRAWAL").aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

    return render(request, "savings/pending_transactions.html", {
        "txns": txns,
        "pending_deposits": pending_deposits,
        "pending_withdrawals": pending_withdrawals,
        
    })


@staff_required
@transaction.atomic
def approve_transaction(request, pk):
    txn = get_object_or_404(SavingsTransaction.objects.select_for_update(), pk=pk)

    if txn.status != "PENDING":
        messages.info(request, "This transaction has already been reviewed.")
        return redirect("savings:pending")

    account = SavingsAccount.objects.select_for_update().get(pk=txn.account_id)

    # ✅ Get active policy
    policy = ChargePolicy.objects.filter(is_active=True).first()
    if not policy:
        messages.error(request, "Charge policy is not configured. Please contact manager.")
        return redirect("savings:pending")

    # Defaults
    withdrawal_fee = Decimal("0.00")
    membership_fee = (policy.membership_fee or Decimal("0.00"))

    # ----------------------------
    # ✅ WITHDRAWAL APPROVAL
    # ----------------------------
    if txn.txn_type == "WITHDRAWAL":
        flat_fee = (policy.withdrawal_fee_flat or Decimal("0.00"))
        percent_fee = (policy.withdrawal_fee_percent or Decimal("0.00")) / Decimal("100.00")

        withdrawal_fee = flat_fee + (txn.amount * percent_fee)
        withdrawal_fee = withdrawal_fee.quantize(Decimal("0.01"))

        total_deduction = (txn.amount or Decimal("0.00")) + withdrawal_fee

        if (account.balance or Decimal("0.00")) < total_deduction:
            messages.error(request, "Cannot approve withdrawal: insufficient balance after withdrawal fee.")
            return redirect("savings:pending")

        # Deduct withdrawal + fee from member savings
        account.balance = (account.balance or Decimal("0.00")) - total_deduction
        account.save(update_fields=["balance"])

        # Save fee on transaction
        txn.fee_amount = withdrawal_fee
        txn.membership_fee_amount = Decimal("0.00")

        # Credit SACCO fees income
        fees_account, _ = SaccoAccount.objects.select_for_update().get_or_create(
            code="FEES_INCOME",
            defaults={"name": "Withdrawal Fees Income", "account_type": "INCOME"}
        )
        fees_account.balance = (fees_account.balance or Decimal("0.00")) + withdrawal_fee
        fees_account.save(update_fields=["balance"])

        SaccoLedgerEntry.objects.create(
            account=fees_account,
            entry_type="CREDIT",
            amount=withdrawal_fee,
            narration=f"Withdrawal fee for {account.member.member_number} (Txn {txn.reference})",
            created_by=request.user,
            created_at=timezone.now(),
        )

    # ----------------------------
    # ✅ DEPOSIT APPROVAL
    # ----------------------------
    else:
        deposit_amount = txn.amount or Decimal("0.00")
        applied_membership_fee = Decimal("0.00")

        # Apply membership fee ONCE (first approved deposit)
        if (not account.membership_fee_paid) and membership_fee > 0:
            if membership_fee > deposit_amount:
                messages.error(
                    request,
                    f"Cannot approve deposit: membership fee (KES {membership_fee}) exceeds deposit amount."
                )
                return redirect("savings:pending")

            applied_membership_fee = membership_fee

            # Credit SACCO membership fees income
            membership_account, _ = SaccoAccount.objects.select_for_update().get_or_create(
                code="MEMBERSHIP_FEES",
                defaults={"name": "Membership Fees Income", "account_type": "INCOME"}
            )
            membership_account.balance = (membership_account.balance or Decimal("0.00")) + applied_membership_fee
            membership_account.save(update_fields=["balance"])

            SaccoLedgerEntry.objects.create(
                account=membership_account,
                entry_type="CREDIT",
                amount=applied_membership_fee,
                narration=f"Membership fee deducted from deposit for {account.member.member_number} (Txn {txn.reference})",
                created_by=request.user,
                created_at=timezone.now(),
            )

            # Mark membership fee as paid on the savings account
            account.membership_fee_paid = True
            account.membership_fee_paid_at = timezone.now()

        # Credit member savings with net deposit
        net_credit = deposit_amount - applied_membership_fee
        account.balance = (account.balance or Decimal("0.00")) + net_credit

        account.save(update_fields=["balance", "membership_fee_paid", "membership_fee_paid_at"])

        # Save on transaction for audit
        txn.fee_amount = Decimal("0.00")
        txn.membership_fee_amount = applied_membership_fee

    # ----------------------------
    # ✅ Mark transaction posted
    # ----------------------------
    txn.status = "POSTED"
    txn.approved_by = request.user
    txn.approved_at = timezone.now()
    txn.save(update_fields=[
        "status",
        "approved_by",
        "approved_at",
        "fee_amount",
        "membership_fee_amount",
    ])

    messages.success(request, "Transaction approved and posted successfully.")
    return redirect("savings:pending")
@staff_required
def reject_transaction(request, pk):
    txn = get_object_or_404(SavingsTransaction, pk=pk)

    if txn.status != "PENDING":
        messages.info(request, "This transaction has already been reviewed.")
        return redirect("savings:pending")

    txn.status = "REJECTED"
    txn.approved_by = request.user
    txn.approved_at = timezone.now()
    txn.save(update_fields=["status", "approved_by", "approved_at"])

    messages.success(request, "Transaction rejected.")
    return redirect("savings:pending")


## Report
import csv
from django.http import HttpResponse
from django.db.models import Sum, Q
from decimal import Decimal

@staff_required
def savings_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    member_id = request.GET.get('member')
    export_csv = request.GET.get('export') == 'true'

    txns = SavingsTransaction.objects.select_related(
        "account__member__user"
    ).filter(status="POSTED").order_by("-created_at")

    # Filter Logic
    if start_date:
        txns = txns.filter(created_at__date__gte=start_date)
    if end_date:
        txns = txns.filter(created_at__date__lte=end_date)
    if member_id:
        txns = txns.filter(account__member__member_number__icontains=member_id)

    # 1. Handle CSV Export
    if export_csv:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="savings_report_{timezone.now().date()}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Member', 'Type', 'Reference', 'Amount', 'Fees', 'Staff'])
        for t in txns:
            fees = (t.fee_amount or 0) + (t.membership_fee_amount or 0)
            writer.writerow([
                t.created_at.strftime('%Y-%m-%d %H:%M'), 
                t.account.member.member_number, 
                t.txn_type, 
                t.reference, 
                t.amount, 
                fees, 
                t.created_by.username
            ])
        return response

    # 2. Aggregation Logic
    summary = txns.aggregate(
        total_deposits=Sum('amount', filter=Q(txn_type='DEPOSIT')),
        total_withdrawals=Sum('amount', filter=Q(txn_type='WITHDRAWAL')),
        withdrawal_fees=Sum('fee_amount'),
        joining_fees=Sum('membership_fee_amount'),
    )

    # 3. Clean and Calculate (Prevents template errors)
    for key in summary:
        summary[key] = summary[key] or Decimal("0.00")
    
    summary['total_fees'] = summary['withdrawal_fees'] + summary['joining_fees']
    summary['net_movement'] = summary['total_deposits'] - summary['total_withdrawals']
    
    # Pre-determine UI colors
    summary['net_color'] = "#15803d" if summary['net_movement'] >= 0 else "#b91c1c"

    return render(request, "savings/savings_report.html", {
        "txns": txns,
        "summary": summary,
        "start_date": start_date,
        "end_date": end_date,
        "member_query": member_id,
    })


@member_required
def member_statement(request):
    member = request.user.member_profile
    account = get_object_or_404(SavingsAccount, member=member)
    
    # Get filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Base Query
    txns = SavingsTransaction.objects.filter(
        account=account, 
        status="POSTED"
    ).order_by("created_at") # Order by oldest first for running balance calculation

    if start_date:
        txns = txns.filter(created_at__date__gte=start_date)
    if end_date:
        txns = txns.filter(created_at__date__lte=end_date)

    # Calculate Running Balance
    statement_data = []
    current_balance = Decimal("0.00")
    
    # Optional: If filtering by date, you might need an "Opening Balance"
    # For simplicity here, we assume the full history:
    for t in txns:
        if t.txn_type == "DEPOSIT":
            # Net deposit is amount minus membership fee
            net_change = t.amount - (t.membership_fee_amount or 0)
            current_balance += net_change
        else:
            # Net withdrawal is amount plus fee deducted from balance
            net_change = t.amount + (t.fee_amount or 0)
            current_balance -= net_change
        
        statement_data.append({
            'obj': t,
            'running_balance': current_balance
        })

    # Reverse for display (Newest at top)
    statement_data.reverse()

    return render(request, "savings/member_statement.html", {
        "account": account,
        "statement": statement_data,
        "start_date": start_date,
        "end_date": end_date,
    })