"""CineBook — Dashboard API URLs"""

from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("summary/", views.DashboardSummaryView.as_view(), name="summary"),
    path("shows/", views.TodayShowsView.as_view(), name="today_shows"),
    path("revenue/", views.RevenueView.as_view(), name="revenue"),
]
