"""CineBook — Accounts Frontend URLs"""

from django.urls import path
from . import frontend_views

urlpatterns = [
    path("login/", frontend_views.LoginPageView.as_view(), name="login_page"),
    path("register/", frontend_views.RegisterPageView.as_view(), name="register_page"),
    path("profile/", frontend_views.ProfilePageView.as_view(), name="profile_page"),
]
