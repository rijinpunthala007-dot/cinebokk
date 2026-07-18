"""CineBook — Bookings Frontend URLs"""

from django.urls import path
from . import frontend_views

urlpatterns = [
    path("seat-map/<int:show_id>/", frontend_views.SeatMapView.as_view(), name="seat_map"),
    path("checkout/", frontend_views.CheckoutView.as_view(), name="checkout"),
    path("confirmation/<uuid:booking_ref>/", frontend_views.ConfirmationView.as_view(), name="confirmation"),
    path("my-bookings/", frontend_views.MyBookingsView.as_view(), name="my_bookings"),
]
