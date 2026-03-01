from django.urls import path
from . import views

app_name = "loans"

urlpatterns = [
    # -------- Member --------
    path("apply/", views.apply_loan, name="apply"),
    path("applications/", views.my_applications, name="my_applications"),
    path("my-loans/", views.my_loans, name="my_loans"),
    path("my-loans/<int:pk>/", views.loan_detail, name="loan_detail"),
    path("my-loans/<int:pk>/repay/", views.member_repay, name="member_repay"),

    # -------- Staff / Manager --------
    path("staff/applications/", views.applications_queue, name="applications_queue"),
    path("staff/applications/<int:pk>/", views.application_detail, name="application_detail"),
    path("staff/applications/<int:pk>/verify/", views.verify_application, name="verify_application"),

    # Manager-only decisions
    path("staff/applications/<int:pk>/approve/", views.approve_application, name="approve_application"),
    path("staff/applications/<int:pk>/reject/", views.reject_application, name="reject_application"),

    # Disbursement
    path("staff/disbursements/", views.pending_disbursements, name="pending_disbursements"),
    path("staff/loans/<int:pk>/authorize/", views.authorize_disbursement, name="authorize_disbursement"),
    path("staff/loans/<int:pk>/disburse/", views.mark_disbursed, name="mark_disbursed"),

    # Repayments
    path("staff/repayments/record/", views.record_repayment, name="record_repayment"),
    path('repay/record/', views.record_repayment, name='record_repayment'),
    path('repay/approve/<int:pk>/', views.record_repayment, name='approve_repayment'),
    path('repayments/pending/', views.pending_repayments_list, name='pending_repayments_list'),

    # Monitoring
    path("staff/active/", views.active_loans, name="active_loans"),
    path("staff/cleared/", views.cleared_loans, name="cleared_loans"),

    path('repayments/history/', views.repayment_history, name='repayment_history'),
    path('statement/<int:pk>/', views.loan_statement, name='loan_statement'),
]