from django.urls import path

from .views import MenuItemListView, RestaurantDetailsView

urlpatterns = [
    path("menu/", MenuItemListView.as_view(), name="menu-list"),
    path("restaurant/", RestaurantDetailsView.as_view(), name="restaurant-details"),
]
