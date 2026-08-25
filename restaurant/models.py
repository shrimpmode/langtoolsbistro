from django.db import models


class MenuItem(models.Model):
    class Category(models.TextChoices):
        APPETIZER = "appetizer", "Appetizer"
        MAIN = "main", "Main"
        DESSERT = "dessert", "Dessert"
        DRINK = "drink", "Drink"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Reservation(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    customer_name = models.CharField(max_length=200)
    party_size = models.PositiveIntegerField()
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.CONFIRMED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer_name} ({self.party_size}) on {self.date} {self.time}"
