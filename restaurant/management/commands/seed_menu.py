from django.core.management.base import BaseCommand

from restaurant.models import MenuItem

MENU_ITEMS = [
    dict(
        name="Bruschetta",
        description="Grilled bread rubbed with garlic, topped with tomato and basil.",
        category=MenuItem.Category.APPETIZER,
        price="7.50",
    ),
    dict(
        name="Caesar Salad",
        description="Romaine, parmesan, croutons, house Caesar dressing.",
        category=MenuItem.Category.APPETIZER,
        price="8.00",
    ),
    dict(
        name="Margherita Pizza",
        description="San Marzano tomato, mozzarella, fresh basil.",
        category=MenuItem.Category.MAIN,
        price="14.00",
    ),
    dict(
        name="Spaghetti Carbonara",
        description="Guanciale, egg, pecorino, black pepper.",
        category=MenuItem.Category.MAIN,
        price="16.50",
    ),
    dict(
        name="Tiramisu",
        description="Espresso-soaked ladyfingers, mascarpone cream, cocoa.",
        category=MenuItem.Category.DESSERT,
        price="6.50",
    ),
    dict(
        name="House Red Wine",
        description="Glass of the house Chianti.",
        category=MenuItem.Category.DRINK,
        price="9.00",
    ),
]


class Command(BaseCommand):
    help = "Seed the database with a small sample restaurant menu."

    def handle(self, *args, **options):
        created = 0
        for item in MENU_ITEMS:
            _, was_created = MenuItem.objects.get_or_create(
                name=item["name"], defaults=item
            )
            created += int(was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded menu: {created} new item(s), {len(MENU_ITEMS)} total defined."
            )
        )
