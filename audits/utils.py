from typing import Optional
from django.utils import timezone
from .models import AuditLog


def get_client_ip(request) -> Optional[str]:
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_user_agent(request) -> str:
    if not request:
        return ""
    ua = request.META.get("HTTP_USER_AGENT", "")
    return ua[:255]


def log_event(
    *,
    module: str,
    action: str,
    message: str,
    actor=None,
    member=None,
    reference: str = "",
    request=None
) -> AuditLog:
    """
    Call this anywhere to log auditable actions.
    """
    return AuditLog.objects.create(
        module=module,
        action=action,
        message=message[:255],
        actor=actor,
        member=member,
        reference=reference[:100],
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        created_at=timezone.now(),
    )