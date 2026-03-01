from django.urls import path
from . import views

app_name = "finance"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("accounts/", views.accounts_list, name="accounts"),
    path("ledger/", views.ledger, name="ledger"),
    path("fees-report/", views.fees_report, name="fees_report"),
    path("policy/", views.charge_policy, name="policy"),
]