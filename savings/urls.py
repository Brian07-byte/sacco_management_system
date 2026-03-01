from django.urls import path
from . import views

app_name = "savings"

urlpatterns = [
    # Member
    path("my/", views.my_savings, name="my"),
    path("my/transactions/", views.my_transactions, name="my_transactions"),
    path("my/deposit/", views.member_deposit, name="member_deposit"),
    path("my/withdraw/", views.member_withdrawal, name="member_withdrawal"),

    # Staff
    path("accounts/", views.accounts_list, name="accounts_list"),
    path("deposit/", views.record_deposit, name="deposit"),
    path("withdraw/", views.record_withdrawal, name="withdraw"),
    path("daily/", views.daily_transactions, name="daily"),

    # Approvals
    path("pending/", views.pending_transactions, name="pending"),
    path("pending/<int:pk>/approve/", views.approve_transaction, name="approve"),
    path("pending/<int:pk>/reject/", views.reject_transaction, name="reject"),
    path('reports/', views.savings_report, name='report'),
    path('my-statement/', views.member_statement, name='statement'),
]