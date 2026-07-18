"""CineBook — Shows API URLs"""

from django.urls import path
from . import views

app_name = "shows"

urlpatterns = [
    path("", views.ShowListView.as_view(), name="show_list"),
    path("<int:pk>/", views.ShowDetailView.as_view(), name="show_detail"),
    path("<int:pk>/seat-map/", views.ShowSeatMapView.as_view(), name="seat_map"),
]
