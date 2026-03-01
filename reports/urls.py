from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    # member
    path("my/", views.my_reports_home, name="my_home"),
    path("my/savings/", views.my_savings_report, name="my_savings"),
    path("my/loans/", views.my_loans_report, name="my_loans"),

    # staff / manager
    path("staff/", views.staff_reports_home, name="staff_home"),
    path("staff/daily/", views.staff_daily_report, name="staff_daily"),
    path("staff/savings-summary/", views.staff_savings_summary, name="staff_savings_summary"),
    path("staff/loans-summary/", views.staff_loans_summary, name="staff_loans_summary"),

    # manager analytics
    path("manager/", views.manager_reports_home, name="manager_home"),
    path("manager/portfolio/", views.manager_loan_portfolio, name="manager_portfolio"),
]