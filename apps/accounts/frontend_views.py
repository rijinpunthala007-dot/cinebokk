"""
CineBook — Accounts Frontend Views
=====================================
Simple template views — auth enforcement is done client-side via JWT.
"""

from django.views.generic import TemplateView


class LoginPageView(TemplateView):
    template_name = "accounts/login.html"


class RegisterPageView(TemplateView):
    template_name = "accounts/register.html"


class ProfilePageView(TemplateView):
    template_name = "accounts/profile.html"
