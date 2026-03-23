"""
Management command: link_home_cake_images

Links cake images from special folders (wedding, valentines, graduation) 
to featured products for home page display.

Usage:
    python manage.py link_home_cake_images
"""

from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from bakery.models import Product


class Command(BaseCommand):
    help = "Link special cake images from themed folders to featured cake products"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Linking home page cake images…"))

        knowledge_base_path = Path(__file__).resolve().parent.parent.parent.parent / "KnowledgeBase"
        
        # Get featured cakes (first 6 available cakes)
        featured_cakes = list(Product.objects.filter(category="cake", is_available=True)[:6])
        
        if not featured_cakes:
            self.stdout.write(self.style.ERROR("No cakes found!"))
            return

        # Special cake image folders
        special_folders = [
            ("wedding-cakes", "wedding-cakes"),
            ("valentines&love-cakes", "val-love-cakes"),
            ("graduation=cakes", "graduaion-cakes"),
        ]

        linked_count = 0
        cake_idx = 0

        for folder_name, prefix in special_folders:
            folder_path = knowledge_base_path / folder_name
            
            if not folder_path.exists():
                self.stdout.write(f"⚠ Folder not found: {folder_path}")
                continue

            # Get all images
            image_files = sorted([f for f in folder_path.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
            
            if not image_files:
                continue

            # Assign images to featured cakes
            for image_file in image_files:
                if cake_idx < len(featured_cakes):
                    product = featured_cakes[cake_idx]
                    try:
                        # Delete old image if exists
                        if product.image:
                            product.image.delete()
                        
                        # Save new image
                        with open(image_file, 'rb') as f:
                            product.image.save(
                                image_file.name,
                                ContentFile(f.read()),
                                save=True
                            )
                        linked_count += 1
                        self.stdout.write(f"  ✓ {product.name} ← {image_file.name}")
                        cake_idx += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"  ✗ Error linking {product.name}: {e}")
                        )

        self.stdout.write(
            self.style.SUCCESS(f"✓ Done. {linked_count} home page cake images linked.")
        )
