"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
        path("", include(("core.urls", "core"), namespace="core")),
    path("accounts/", include(("accounts.urls", "accounts"), namespace="accounts")),
    path("members/", include(("members.urls", "members"), namespace="members")),
    path("savings/", include(("savings.urls", "savings"), namespace="savings")),
    path("finance/", include(("finance.urls", "finance"), namespace="finance")),
    path("loans/", include(("loans.urls", "loans"), namespace="loans")),
    path("reports/", include(("reports.urls", "reports"), namespace="reports")),
    path("settings/", include(("settingsapp.urls", "settingsapp"), namespace="settingsapp")),
    path("audits/", include(("audits.urls", "audits"), namespace="audits")),
]
