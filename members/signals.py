from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Member

def generate_member_number(prefix: str) -> str:
    """
    Generates PS001, PS002, ...
    Works well for SQLite/dev. For high-concurrency production,
    you can switch to a dedicated sequence model.
    """
    last = (
        Member.objects
        .filter(member_number__startswith=prefix)
        .order_by("-member_number")
        .first()
    )

    if not last:
        next_num = 1
    else:
        # Extract numeric tail from e.g. "PS001" -> 1
        tail = last.member_number.replace(prefix, "")
        next_num = int(tail) + 1 if tail.isdigit() else 1

    return f"{prefix}{next_num:03d}"  # PS001

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_member_profile(sender, instance, created, **kwargs):
    if not created:
        return

    # Only auto-create for MEMBER self-signup
    if getattr(instance, "role", None) != "MEMBER":
        return

    # National ID must come from signup view
    national_id = getattr(instance, "_signup_national_id", None)
    if not national_id:
        # If user was created from admin without national_id passed, skip
        return

    prefix = getattr(settings, "SACCO_ABBR", "PS")

    with transaction.atomic():
        # Generate a unique member number
        member_no = generate_member_number(prefix)

        # Create Member
        Member.objects.create(
            user=instance,
            member_number=member_no,
            national_id=national_id,
        )