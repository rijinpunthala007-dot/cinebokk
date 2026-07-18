"""CineBook — Bookings API URLs"""

from django.urls import path
from . import views

app_name = "bookings"

urlpatterns = [
    path("lock-seats/", views.LockSeatsView.as_view(), name="lock_seats"),
    path("confirm/", views.ConfirmBookingView.as_view(), name="confirm_booking"),
    path("my-bookings/", views.MyBookingsView.as_view(), name="my_bookings"),
    path("my-bookings/<uuid:booking_ref>/", views.BookingDetailView.as_view(), name="booking_detail"),
    path("cancel/<uuid:booking_ref>/", views.CancelBookingView.as_view(), name="cancel_booking"),
]
