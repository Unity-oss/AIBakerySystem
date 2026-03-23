"""
Management command: build_knowledge_base

Embeds all knowledge base documents into ChromaDB.
Run once after setup, or whenever the knowledge base files are updated.

Usage:
    python manage.py build_knowledge_base
"""

import logging

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Build the Tastyz Bakery RAG knowledge base (embed docs into ChromaDB)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Building Tastyz Bakery knowledge base…"))

        if not settings.OPENAI_API_KEY:
            self.stderr.write(self.style.ERROR("OPENAI_API_KEY is not set in .env"))
            return

        try:
            from knowledge_base.loader import build_knowledge_base

            build_knowledge_base(
                persist_dir=settings.CHROMA_PERSIST_DIR,
                api_key=settings.OPENAI_API_KEY,
                embedding_model=settings.OPENAI_EMBEDDING_MODEL,
            )
            self.stdout.write(
                self.style.SUCCESS("✓ Knowledge base built successfully in: " + settings.CHROMA_PERSIST_DIR)
            )
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Failed to build knowledge base: {exc}"))
            raise
