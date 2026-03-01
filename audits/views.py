from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import AuditLog


def is_member(user):
    return user.is_authenticated and getattr(user, "role", None) == "MEMBER"


def is_staff_user(user):
    return user.is_authenticated and getattr(user, "role", None) in ("CLERK", "MANAGER")


def is_manager(user):
    return user.is_authenticated and (getattr(user, "role", None) == "MANAGER" or user.is_superuser)


def staff_readonly_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not (is_staff_user(request.user) or is_manager(request.user)):
            messages.error(request, "You are not authorized to access audits.")
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped


@login_required
def my_security_activity(request):
    """
    Member sees ONLY login/logout events for their own account.
    Now supports optional search + pagination.
    """
    qs = AuditLog.objects.filter(
        actor=request.user,
        module__in=["SECURITY", "SYSTEM"],
        action__in=["LOGIN", "LOGOUT"]
    ).order_by("-created_at")

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(reference__icontains=q) |
            Q(message__icontains=q)
        )

    paginator = Paginator(qs, 50)  # 50 per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "audits/member/my_security.html", {
        "logs": page_obj,   # template can iterate as usual
        "page_obj": page_obj,
        "q": q,
    })


@staff_readonly_required
def audit_home(request):
    """
    Staff/Manager audit dashboard summary:
    - totals: today/7 days/30 days/all
    - module breakdown today + 30 days
    - action breakdown today + 30 days
    - top actors (today + 30 days)
    - latest logs
    """
    today = timezone.localdate()
    now = timezone.now()

    last_7_days = today - timezone.timedelta(days=7)
    last_30_days = today - timezone.timedelta(days=30)

    base = AuditLog.objects.select_related("actor", "member", "member__user")

    total_all = base.count()
    total_today = base.filter(created_at__date=today).count()
    total_7d = base.filter(created_at__date__gte=last_7_days).count()
    total_30d = base.filter(created_at__date__gte=last_30_days).count()

    # Module + action breakdowns
    module_counts_today = (
        base.filter(created_at__date=today)
        .values("module")
        .annotate(total=Count("id"))
        .order_by("-total", "module")
    )

    module_counts_30d = (
        base.filter(created_at__date__gte=last_30_days)
        .values("module")
        .annotate(total=Count("id"))
        .order_by("-total", "module")
    )

    action_counts_today = (
        base.filter(created_at__date=today)
        .values("action")
        .annotate(total=Count("id"))
        .order_by("-total", "action")
    )

    action_counts_30d = (
        base.filter(created_at__date__gte=last_30_days)
        .values("action")
        .annotate(total=Count("id"))
        .order_by("-total", "action")
    )

    # Top actors (who is doing actions)
    top_actors_today = (
        base.filter(created_at__date=today, actor__isnull=False)
        .values("actor__username", "actor__role")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    top_actors_30d = (
        base.filter(created_at__date__gte=last_30_days, actor__isnull=False)
        .values("actor__username", "actor__role")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    latest_logs = base.order_by("-created_at")[:20]

    return render(request, "audits/staff/home.html", {
        "today": today,
        "now": now,

        "total_all": total_all,
        "total_today": total_today,
        "total_7d": total_7d,
        "total_30d": total_30d,

        "module_counts_today": module_counts_today,
        "module_counts_30d": module_counts_30d,

        "action_counts_today": action_counts_today,
        "action_counts_30d": action_counts_30d,

        "top_actors_today": top_actors_today,
        "top_actors_30d": top_actors_30d,

        "latest_logs": latest_logs,

        # For filters / dropdowns
        "MODULES": AuditLog.MODULE_CHOICES,
        "ACTIONS": AuditLog.ACTION_CHOICES,
    })


@staff_readonly_required
def audit_logs(request):
    """
    Staff/Manager: filterable audit log list.
    Updated to fetch comprehensively with:
    - module, action, query
    - actor username
    - member number
    - date range
    - pagination
    """
    qs = AuditLog.objects.select_related("actor", "member", "member__user").all()

    module = request.GET.get("module", "").strip()
    action = request.GET.get("action", "").strip()
    q = request.GET.get("q", "").strip()

    actor = request.GET.get("actor", "").strip()     # NEW
    member_no = request.GET.get("member", "").strip()  # NEW

    start = request.GET.get("start", "").strip()
    end = request.GET.get("end", "").strip()

    if module:
        qs = qs.filter(module=module)
    if action:
        qs = qs.filter(action=action)

    if actor:
        qs = qs.filter(actor__username__icontains=actor)

    if member_no:
        qs = qs.filter(member__member_number__icontains=member_no)

    if q:
        qs = qs.filter(
            Q(reference__icontains=q)
            | Q(message__icontains=q)
            | Q(actor__username__icontains=q)
            | Q(actor__email__icontains=q)
            | Q(member__member_number__icontains=q)
            | Q(member__national_id__icontains=q)
            | Q(ip_address__icontains=q)      # if you have this field
            | Q(user_agent__icontains=q)      # if you have this field
        )

    # optional date filters (YYYY-MM-DD)
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)

    qs = qs.order_by("-created_at")

    paginator = Paginator(qs, 100)  # 100 per page for staff
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "audits/staff/logs.html", {
        "logs": page_obj,        # iterate as usual
        "page_obj": page_obj,    # for pagination controls

        "module": module,
        "action": action,
        "q": q,
        "actor": actor,
        "member": member_no,
        "start": start,
        "end": end,

        "MODULES": AuditLog.MODULE_CHOICES,
        "ACTIONS": AuditLog.ACTION_CHOICES,

        # Helpful counts for UI badges
        "total_filtered": qs.count(),
    })