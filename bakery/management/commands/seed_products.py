"""
Management command: seed_products

Populates the database with Tastyz Bakery's product catalog.
Safe to run multiple times (uses get_or_create).

Usage:
    python manage.py seed_products
"""

from django.core.management.base import BaseCommand

from bakery.models import Product


PRODUCTS = [
    # Cakes
    {"name": "Vanilla Sponge Cake", "category": "cake", "price_small": 65000, "price_large": 85000,
     "description": "Light and fluffy vanilla sponge cake, perfect for any occasion."},
    {"name": "Banana Cake", "category": "cake", "price_small": 60000, "price_large": 80000,
     "description": "Moist banana cake with a rich, fruity flavour."},
    {"name": "Chocolate Cake", "category": "cake", "price_small": 75000, "price_large": 95000,
     "description": "Rich, decadent chocolate cake — a customer favourite."},
    {"name": "Marble Cake", "category": "cake", "price_small": 70000, "price_large": 90000,
     "description": "Beautiful swirl of vanilla and chocolate in every slice."},
    {"name": "Fruity Cake", "category": "cake", "price_small": 85000, "price_large": 100000,
     "description": "Packed with dried fruits and a hint of spice."},
    {"name": "Lemon Cake", "category": "cake", "price_small": 55000, "price_large": 70000,
     "description": "Zesty lemon cake with a light, refreshing taste."},
    {"name": "Strawberry Cake", "category": "cake", "price_small": 70000, "price_large": 100000,
     "description": "Fresh strawberry layers with cream — a celebration treat."},
    {"name": "Red Velvet Cake", "category": "cake", "price_small": 90000, "price_large": 120000,
     "description": "Classic red velvet with velvety cream cheese frosting."},
    {"name": "Black Forest Cake", "category": "cake", "price_small": 100000, "price_large": 150000,
     "description": "Layers of chocolate, whipped cream and cherries."},
    {"name": "Carrot Cake", "category": "cake", "price_small": 70000, "price_large": 100000,
     "description": "Wholesome carrot cake with cream cheese icing."},
    # Cookies
    {"name": "Ginger Cookies", "category": "cookies", "price_small": 10000, "price_large": 35000,
     "description": "Crispy ginger snaps — great for gifting. Available in small, medium, big tin."},
    {"name": "Chocolate Cookies", "category": "cookies", "price_small": 15000, "price_large": 30000,
     "description": "Chunky chocolate cookies, freshly baked daily."},
    {"name": "Coconut Cookies", "category": "cookies", "price_small": 10000, "price_large": 30000,
     "description": "Lightly toasted coconut cookies with a tropical flavour."},
    {"name": "Butter Cookies", "category": "cookies", "price_small": 10000, "price_large": 25000,
     "description": "Classic buttery melt-in-your-mouth cookies."},
    {"name": "Black & White Cookies", "category": "cookies", "price_small": 10000, "price_large": 25000,
     "description": "Half chocolate, half vanilla glazed cookies."},
    # Fresh Pastries
    {"name": "Country Loaf", "category": "pastries", "price_small": 5000, "price_large": 10000,
     "description": "Rustic artisan loaf baked fresh every morning."},
    {"name": "Burger Buns", "category": "pastries", "price_small": 1000, "price_large": 2000,
     "description": "Soft sesame burger buns, sold individually."},
    {"name": "Donuts", "category": "pastries", "price_small": 2000, "price_large": 3000,
     "description": "Freshly fried ring donuts with sugar or chocolate glaze."},
    {"name": "Chocolate Brownies", "category": "pastries", "price_small": 20000, "price_large": 35000,
     "description": "Fudgy, rich chocolate brownies baked to perfection."},
    {"name": "Bread", "category": "pastries", "price_small": 3000, "price_large": 5000,
     "description": "Soft white sandwich bread, baked fresh daily."},
    {"name": "Muffins", "category": "pastries", "price_small": 2000, "price_large": 3000,
     "description": "Fluffy muffins in assorted flavours."},
    {"name": "Pizza", "category": "pastries", "price_small": 35000, "price_large": 40000,
     "description": "Hand-stretched bakery pizza with fresh toppings."},
    {"name": "Cupcakes", "category": "pastries", "price_small": 20000, "price_large": 30000,
     "description": "Beautifully frosted cupcakes — perfect for parties."},
    {"name": "Cinnamon Rolls", "category": "pastries", "price_small": 2000, "price_large": 5000,
     "description": "Warm, gooey cinnamon rolls with icing drizzle."},
]


class Command(BaseCommand):
    help = "Seed the database with Tastyz Bakery products"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding Tastyz Bakery products…"))
        created_count = 0
        for p in PRODUCTS:
            obj, created = Product.objects.get_or_create(
                name=p["name"],
                defaults={
                    "category": p["category"],
                    "price_small": p["price_small"],
                    "price_large": p.get("price_large"),
                    "description": p.get("description", ""),
                    "is_available": True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"  + {obj.name}")

        self.stdout.write(
            self.style.SUCCESS(f"✓ Done. {created_count} new products added ({len(PRODUCTS)} total).")
        )
