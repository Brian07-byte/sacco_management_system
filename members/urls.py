from django.urls import path
from . import views

app_name = "members"

urlpatterns = [
    # Member self-service
    path("my-profile/", views.my_profile, name="my_profile"),
    path("complete-profile/", views.complete_profile, name="complete_profile"),
    path("edit-profile/", views.edit_profile, name="edit_profile"),

    # Staff operations
    path("register/", views.register_member, name="register"),
    path("list/", views.members_list, name="list"),
    path("<int:pk>/detail/", views.member_detail, name="detail"),
    path("<int:pk>/edit/", views.edit_member, name="edit"),
]