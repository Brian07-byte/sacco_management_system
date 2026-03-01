from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import get_random_string

from django.db import models

from .models import Member
from .forms import (
    MemberCompleteProfileForm,
    MemberEditProfileForm,
    StaffRegisterMemberForm,
    StaffEditMemberForm,
)

User = get_user_model()


# ---------- Role helpers ----------
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


def generate_member_number():
    return f"PMJ-{get_random_string(6).upper()}"


# ---------- Member self-service ----------
@member_required
def my_profile(request):
    member = request.user.member_profile
    return render(request, "members/my_profile.html", {"member": member})


@member_required
def complete_profile(request):
    member = request.user.member_profile

    # If already completed, send them to profile
    if member.national_id:
        messages.info(request, "Your profile is already complete.")
        return redirect("members:my_profile")

    form = MemberCompleteProfileForm(request.POST or None, instance=member)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Profile completed successfully.")
            return redirect("core:dashboard")
        messages.error(request, "Please correct the errors below.")

    return render(request, "members/complete_profile.html", {"form": form})


@member_required
def edit_profile(request):
    member = request.user.member_profile
    form = MemberEditProfileForm(request.POST or None, instance=member)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("members:my_profile")
        messages.error(request, "Please correct the errors below.")

    return render(request, "members/edit_profile.html", {"form": form})


# ---------- Staff operations ----------
@staff_required
@transaction.atomic
def register_member(request):
    form = StaffRegisterMemberForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            # Create user (role MEMBER)
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password1"],
            )
            user.role = "MEMBER"
            user.first_name = form.cleaned_data.get("first_name", "")
            user.last_name = form.cleaned_data.get("last_name", "")
            user.phone_number = form.cleaned_data.get("phone_number", "")
            user.save()

            # Create member profile (we create explicitly to include national_id etc.)
            member_number = generate_member_number()
            while Member.objects.filter(member_number=member_number).exists():
                member_number = generate_member_number()

            Member.objects.create(
                user=user,
                member_number=member_number,

                national_id=form.cleaned_data["national_id"],
                kra_pin=form.cleaned_data.get("kra_pin", ""),
                date_of_birth=form.cleaned_data.get("date_of_birth"),
                gender=form.cleaned_data.get("gender", ""),

                address=form.cleaned_data.get("address", ""),
                town=form.cleaned_data.get("town", ""),
                county=form.cleaned_data.get("county", ""),

                next_of_kin_name=form.cleaned_data.get("next_of_kin_name", ""),
                next_of_kin_phone=form.cleaned_data.get("next_of_kin_phone", ""),
                next_of_kin_relationship=form.cleaned_data.get("next_of_kin_relationship", ""),
            )

            messages.success(request, f"Member registered successfully. Member No: {member_number}")
            return redirect("members:list")

        messages.error(request, "Registration failed. Please correct the errors below.")

    return render(request, "members/register_member.html", {"form": form})


@staff_required
def members_list(request):
    q = request.GET.get("q", "").strip()
    qs = Member.objects.select_related("user").order_by("-date_joined")

    if q:
        qs = qs.filter(
            models.Q(member_number__icontains=q) |
            models.Q(national_id__icontains=q) |
            models.Q(user__username__icontains=q) |
            models.Q(user__email__icontains=q) |
            models.Q(user__first_name__icontains=q) |
            models.Q(user__last_name__icontains=q)
        )

    return render(request, "members/members_list.html", {"members": qs, "q": q})


@staff_required
def member_detail(request, pk):
    member = get_object_or_404(Member.objects.select_related("user"), pk=pk)
    return render(request, "members/member_detail.html", {"member": member})


@staff_required
def edit_member(request, pk):
    member = get_object_or_404(Member, pk=pk)
    form = StaffEditMemberForm(request.POST or None, instance=member)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Member record updated successfully.")
            return redirect("members:detail", pk=member.pk)
        messages.error(request, "Please correct the errors below.")

    return render(request, "members/edit_member.html", {"form": form, "member": member})