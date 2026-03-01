from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from loans.models import LoanProduct

from .forms import ChargePolicyForm, SavingsProductForm
from .models import ChargePolicy, SavingsProduct


def is_member(user):
    return user.is_authenticated and getattr(user, "role", None) == "MEMBER"


def is_staff_user(user):
    return user.is_authenticated and getattr(user, "role", None) in ("CLERK", "MANAGER")


def is_manager(user):
    return user.is_authenticated and (getattr(user, "role", None) == "MANAGER" or user.is_superuser)


def manager_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_manager(request.user):
            messages.error(request, "Manager access required.")
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped


@login_required
def products_home(request):
    return render(request, "settingsapp/home.html")


@login_required
def savings_products(request):
    products = SavingsProduct.objects.filter(is_active=True).order_by("name")
    return render(request, "settingsapp/savings_products.html", {"products": products})


@login_required
def loan_products(request):
    products = LoanProduct.objects.filter(is_active=True).order_by("name")
    return render(request, "settingsapp/loan_products.html", {"products": products})


@login_required
def fees_and_charges(request):
    policy = ChargePolicy.objects.first()
    return render(request, "settingsapp/fees.html", {"policy": policy})


# ---------------- Manager controls ----------------
@manager_required
def savings_product_create(request):
    form = SavingsProductForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Savings product created successfully.")
            return redirect("settingsapp:savings_products")
        messages.error(request, "Please correct the errors below.")
    return render(request, "settingsapp/manage/savings_form.html", {"form": form, "mode": "create"})


@manager_required
def savings_product_edit(request, pk):
    product = get_object_or_404(SavingsProduct, pk=pk)
    form = SavingsProductForm(request.POST or None, instance=product)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Savings product updated successfully.")
            return redirect("settingsapp:savings_products")
        messages.error(request, "Please correct the errors below.")
    return render(request, "settingsapp/manage/savings_form.html", {"form": form, "mode": "edit"})


@manager_required
def charge_policy_edit(request):
    policy = ChargePolicy.objects.first()
    if not policy:
        policy = ChargePolicy.objects.create()  # create default one-row

    form = ChargePolicyForm(request.POST or None, instance=policy)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Charge policy updated successfully.")
            return redirect("settingsapp:fees")
        messages.error(request, "Please correct the errors below.")
    return render(request, "settingsapp/manage/policy_form.html", {"form": form})