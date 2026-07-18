"""CineBook — Movies Frontend Views (stub)"""
from django.views.generic import TemplateView

class HomeView(TemplateView):
    template_name = "movies/home.html"

class MovieDetailView(TemplateView):
    template_name = "movies/movie_detail.html"

class ShowtimesView(TemplateView):
    template_name = "shows/showtimes.html"
