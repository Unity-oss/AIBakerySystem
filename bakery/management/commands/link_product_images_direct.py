"""
Management command: link_product_images_direct

Links product images from product-specific KnowledgeBase folders.

Usage:
    python manage.py link_product_images_direct
"""

from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from bakery.models import Product


class Command(BaseCommand):
    help = "Link product images from product-specific KnowledgeBase folders"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Linking product images from dedicated folders…"))

        knowledge_base_path = Path(__file__).resolve().parent.parent.parent.parent / "KnowledgeBase"
        
        # Direct product-to-folder mappings
        product_folder_mappings = {
            "Burger Buns": "burgerBuns",
            "Cinnamon Rolls": "cinnamonRolls",
            "Country Loaf": "countryLoaf",
            "Muffins": "Muffins",
        }

        linked_count = 0

        for product_name, folder_name in product_folder_mappings.items():
            folder_path = knowledge_base_path / folder_name
            
            if not folder_path.exists():
                self.stdout.write(self.style.WARNING(f"⚠ Folder not found: {folder_path}"))
                continue

            # Get all images in the folder
            image_files = sorted([f for f in folder_path.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
            
            if not image_files:
                self.stdout.write(self.style.WARNING(f"⚠ No images found in {folder_path}"))
                continue

            # Find the product and link first image
            try:
                product = Product.objects.get(name=product_name)
                if product.image:
                    product.image.delete()
                
                image_file = image_files[0]
                with open(image_file, 'rb') as f:
                    product.image.save(
                        image_file.name,
                        ContentFile(f.read()),
                        save=True
                    )
                linked_count += 1
                self.stdout.write(f"  ✓ {product_name} ← {image_file.name}")
            except Product.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"  ✗ Product not found: {product_name}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error linking {product_name}: {e}"))

        self.stdout.write(
            self.style.SUCCESS(f"✓ Done. {linked_count} product images linked.")
        )
