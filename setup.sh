#!/usr/bin/env bash
# ============================================================
# Tastyz Bakery AI System — Setup Script
# Run this once after cloning to get the project running.
# ============================================================

set -e

echo ""
echo "=============================================="
echo "  🍰  Tastyz Bakery AI System — Setup"
echo "=============================================="
echo ""

# 1. Check .env
if [ ! -f ".env" ]; then
  echo "⚠️  .env file not found. Copying from .env.example..."
  cp .env.example .env
  echo "✅  .env created. Please fill in your API keys before running the app."
  echo "    Edit .env and add at minimum: SECRET_KEY and OPENAI_API_KEY"
  echo ""
fi

# 2. Install dependencies
echo "📦  Installing Python dependencies..."
pip install -r requirements.txt
echo ""

# 3. Run migrations
echo "🗄️  Running database migrations..."
python manage.py migrate
echo ""

# 4. Seed products
echo "🌱  Seeding product catalog..."
python manage.py seed_products
echo ""

# 5. Build knowledge base (requires OPENAI_API_KEY in .env)
echo "🧠  Building RAG knowledge base (requires OPENAI_API_KEY)..."
python manage.py build_knowledge_base || echo "⚠️  Skipped (add OPENAI_API_KEY to .env and run: python manage.py build_knowledge_base)"
echo ""

# 6. Create superuser prompt
echo "👤  Would you like to create a Django admin superuser? (y/n)"
read -r CREATE_SUPER
if [ "$CREATE_SUPER" = "y" ]; then
  python manage.py createsuperuser
fi

echo ""
echo "=============================================="
echo "  ✅  Setup complete!"
echo ""
echo "  Start the server:   python manage.py runserver"
echo "  Admin panel:        http://127.0.0.1:8000/admin/"
echo ""
echo "  (Optional) Start Celery workers for background agents:"
echo "  celery -A tastyz_project worker -l info"
echo "  celery -A tastyz_project beat -l info"
echo "=============================================="
