"""
Management command: link_product_images

Links product images from the KnowledgeBase folder to Product model.
Maps images by product category and name patterns.

Usage:
    python manage.py link_product_images
"""

import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from bakery.models import Product


class Command(BaseCommand):
    help = "Link product images from KnowledgeBase folder to Product model"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Linking product images…"))

        # Define image folder mappings
        knowledge_base_path = Path(__file__).resolve().parent.parent.parent.parent / "KnowledgeBase"
        
        # Mapping of folder names to product search terms
        image_mappings = {
            "cookies": ["Ginger", "Coconut", "Cookie"],
            "cupcakes": ["Cupcake"],
            "brownies": ["Brownie"],
            "donuts": ["Donut"],
            "pizza": ["Pizza"],
            "bread": ["Country Loaf", "Burger Buns", "Muffins", "Cinnamon Rolls", "Bread"],
            "daddies": ["Cinnamon Rolls"],
            "Birthday-cakes": ["Cake"],
            "wedding-cakes": ["Cake"],
            "valentines&love-cakes": ["Cake"],
            "graduation=cakes": ["Cake"],
        }

        linked_count = 0

        for folder_name, product_keywords in image_mappings.items():
            folder_path = knowledge_base_path / folder_name
            
            if not folder_path.exists():
                self.stdout.write(f"⚠ Folder not found: {folder_path}")
                continue

            # Get all images in the folder
            image_files = sorted([f for f in folder_path.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
            
            if not image_files:
                continue

            # Global index for image distribution
            image_idx = 0

            # Find products matching this category
            for keyword in product_keywords:
                products = Product.objects.filter(name__icontains=keyword, image="")
                
                if products.exists():
                    # Assign different images to different products
                    for product in products:
                        if image_idx < len(image_files):
                            image_file = image_files[image_idx]
                            try:
                                with open(image_file, 'rb') as f:
                                    product.image.save(
                                        image_file.name,
                                        ContentFile(f.read()),
                                        save=True
                                    )
                                linked_count += 1
                                self.stdout.write(f"  ✓ {product.name} ← {image_file.name}")
                                image_idx += 1
                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(f"  ✗ Error linking {product.name}: {e}")
                                )

        self.stdout.write(
            self.style.SUCCESS(f"✓ Done. {linked_count} product images linked.")
        )
