from rest_framework import serializers

from .models import MenuItem, Reservation


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ["id", "name", "description", "category", "price", "is_available"]


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = [
            "id",
            "customer_name",
            "party_size",
            "date",
            "time",
            "status",
            "created_at",
        ]
