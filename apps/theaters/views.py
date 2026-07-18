"""CineBook — Theaters API Views"""

from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from .models import City
from .serializers import CitySerializer


class CityListView(ListAPIView):
    """
    GET /api/v1/cities/
    List all active cities for the city selector.
    """

    serializer_class = CitySerializer
    permission_classes = [AllowAny]
    pagination_class = None     # Return all cities without pagination
    queryset = City.objects.filter(is_active=True).order_by("name")
