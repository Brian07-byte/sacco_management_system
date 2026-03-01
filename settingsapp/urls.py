from django.urls import path
from . import views

app_name = "settingsapp"

urlpatterns = [
    # Public/member read-only
    path("", views.products_home, name="home"),
    path("savings-products/", views.savings_products, name="savings_products"),
    path("loan-products/", views.loan_products, name="loan_products"),
    path("fees/", views.fees_and_charges, name="fees"),

    # Manager controls
    path("manage/savings-products/new/", views.savings_product_create, name="savings_create"),
    path("manage/savings-products/<int:pk>/edit/", views.savings_product_edit, name="savings_edit"),
    path("manage/policy/", views.charge_policy_edit, name="policy_edit"),
]