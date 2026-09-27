from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .info import restaurant_details, restaurant_now

from .models import MenuItem
from .serializers import MenuItemSerializer


class MenuItemListView(generics.ListAPIView):
    queryset = MenuItem.objects.filter(is_available=True).order_by("category", "name")
    serializer_class = MenuItemSerializer


class RestaurantDetailsView(APIView):
    """Name, address, opening hours and whether it's open right now."""

    def get(self, request):
        return Response(restaurant_details(restaurant_now()))
