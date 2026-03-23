"""
Management command: prepare_home_images

Copies cake images from special folders to media/home_images for home page display.

Usage:
    python manage.py prepare_home_images
"""

import shutil
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Copy special cake images to media folder for home page display"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Preparing home page images…"))

        knowledge_base_path = Path(__file__).resolve().parent.parent.parent.parent / "KnowledgeBase"
        home_images_path = Path(settings.MEDIA_ROOT) / "home_images"
        
        # Create home_images folder
        home_images_path.mkdir(parents=True, exist_ok=True)
        
        # Special cake image folders
        special_folders = [
            "wedding-cakes",
            "valentines&love-cakes",
            "graduation=cakes",
        ]

        copied_count = 0

        for folder_name in special_folders:
            folder_path = knowledge_base_path / folder_name
            
            if not folder_path.exists():
                self.stdout.write(f"⚠ Folder not found: {folder_path}")
                continue

            # Get all images
            image_files = sorted([f for f in folder_path.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
            
            if not image_files:
                continue

            # Copy images
            for image_file in image_files:
                try:
                    dest_path = home_images_path / image_file.name
                    shutil.copy2(image_file, dest_path)
                    copied_count += 1
                    self.stdout.write(f"  ✓ Copied {image_file.name}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ Error copying {image_file.name}: {e}"))

        self.stdout.write(
            self.style.SUCCESS(f"✓ Done. {copied_count} images prepared for home page.")
        )
