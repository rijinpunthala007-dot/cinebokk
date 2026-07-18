"""
CineBook — Bookings Frontend Views
=====================================
Simple template views — auth enforcement is done client-side via JWT.
The JS on each page redirects to /accounts/login/ if no token is found.
"""

from django.views.generic import TemplateView


class SeatMapView(TemplateView):
    template_name = "bookings/seat_map.html"


class CheckoutView(TemplateView):
    template_name = "bookings/checkout.html"


class ConfirmationView(TemplateView):
    template_name = "bookings/confirmation.html"


class MyBookingsView(TemplateView):
    template_name = "bookings/my_bookings.html"
