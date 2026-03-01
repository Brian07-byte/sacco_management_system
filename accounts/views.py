from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import SignUpForm


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    form = SignUpForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.role = "MEMBER"

                    # ✅ pass data to signal via temporary attributes
                    user._signup_national_id = form.cleaned_data["national_id"]

                    user.save()  # ✅ signal uses _signup_national_id to create Member

                login(request, user)
                messages.success(request, "Account created successfully. Welcome to Pamoja SACCO!")
                return redirect("core:dashboard")

            except IntegrityError:
                form.add_error("national_id", "This National ID is already registered.")
                messages.error(request, "Signup failed. Please correct the errors below.")
        else:
            messages.error(request, "Signup failed. Please correct the errors below.")

    return render(request, "accounts/signup.html", {"form": form})

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect("core:dashboard")

        messages.error(request, "Invalid username or password.")

    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("core:landing")