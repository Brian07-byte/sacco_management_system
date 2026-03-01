from django.urls import path
from . import views

app_name = "audits"

urlpatterns = [
    # Member
    path("my-security/", views.my_security_activity, name="my_security"),

    # Staff/Manager
    path("", views.audit_home, name="home"),
    path("logs/", views.audit_logs, name="logs"),
]