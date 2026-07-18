"""CineBook — Theaters API URLs"""

from django.urls import path
from . import views

app_name = "theaters"

urlpatterns = [
    path("", views.CityListView.as_view(), name="city_list"),
]
