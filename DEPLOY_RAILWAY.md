# Railway Deployment Guide

This guide walks through deploying the Tastyz Bakery AI System to Railway.

## Prerequisites

- GitHub account with this repo pushed
- Railway account (free tier available at [railway.app](https://railway.app))
- All API keys ready (OpenAI, Google, Stripe, etc.)

## Quick Deploy (5 minutes)

### 1. Connect GitHub to Railway

1. Go to [railway.app](https://railway.app) → Dashboard
2. Click **New Project** → **Deploy from GitHub**
3. Select your repository
4. Railway auto-detects `Procfile` and `railway.json`

### 2. Add Services

Railway will show options to add:
- ✅ **PostgreSQL** — Click "Add"
- ✅ **Redis** — Click "Add"

The web service already connects to your GitHub repo.

### 3. Configure Environment Variables

In Railway Dashboard → **Variables**:

```
# Django
SECRET_KEY=generate-a-secure-key-here
DEBUG=False
ALLOWED_HOSTS=your-app-name.railway.app
CSRF_TRUSTED_ORIGINS=https://your-app-name.railway.app

# Database & Redis (auto-linked)
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# LLM APIs
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...

# Other APIs
STRIPE_API_KEY=sk_test_...
GOOGLE_CALENDAR_CLIENT_ID=...
```

See `.env.example` for all available variables.

### 4. Deploy

Railway auto-deploys when you:
- Push to GitHub
- Click **Deploy** in the dashboard

The `Procfile` handles:
- `release`: Runs migrations & collectstatic
- `web`: Starts Django with Gunicorn
- `worker`: Starts Celery tasks
- `beat`: Runs scheduled tasks

### 5. Verify

Once deployed:
- ✅ Visit `https://your-app.railway.app`
- ✅ Check logs: Dashboard → Deployments → Logs
- ✅ Admin panel: `/admin`
- ✅ Run migrations (if needed): Dashboard → Shell → `python manage.py migrate`

---

## Advanced Configuration

### Create Superuser

After first deploy, open Railway Shell and run:

```bash
python manage.py createsuperuser
```

### Seed Initial Data

```bash
python manage.py seed_products
python manage.py setup_google_calendar
```

### Database Backup

PostgreSQL backups are automatic with Railway. Access via:
- Dashboard → PostgreSQL service → Backups

### Monitor Celery Tasks

Open Railway Shell for the **worker** service:

```bash
celery -A tastyz_project inspect active
```

### View Real-time Logs

```bash
railway logs -f
```

---

## Environment Variables Reference

| Variable | Required | Example |
|----------|----------|---------|
| `SECRET_KEY` | Yes | `your-secure-random-string` |
| `DEBUG` | Yes | `False` |
| `OPENAI_API_KEY` | Yes | `sk-...` |
| `GEMINI_API_KEY` | No | `AIza...` |
| `ANTHROPIC_API_KEY` | No | `sk-ant-...` |
| `STRIPE_API_KEY` | No | `sk_test_...` |
| `GOOGLE_CALENDAR_CLIENT_ID` | No | `xxx.apps.googleusercontent.com` |
| `DATABASE_URL` | Auto | `postgresql://...` |
| `REDIS_URL` | Auto | `redis://...` |

---

## Troubleshooting

### 502 Bad Gateway

**Check logs:**
```bash
railway logs
```

**Common causes:**
- Missing environment variables
- Database migration failed
- Port binding issue

**Fix:**
```bash
# View detailed error
railway logs -f

# Re-run migrations
railway run python manage.py migrate
```

### Static Files Not Loading

**Fix:**
```bash
railway run python manage.py collectstatic --noinput
```

### Celery Tasks Not Running

**Verify Redis connection in logs:**
```bash
railway logs -f
```

**Restart worker:**
- Dashboard → worker service → Re-deploy

### ChromaDB Persistence

By default, ChromaDB stores in `/var/data/chroma_db` (ephemeral). To persist between deploys:

**Option 1: Add a Disk**
- Dashboard → Your web service → Storage → Add Disk
- Mount to: `/var/data`

**Option 2: Use Pinecone** (cloud vector DB)
- Set `PINECONE_API_KEY` in variables

---

## Rolling Back

If something breaks:

1. Dashboard → Deployments → Select previous version
2. Click **Redeploy**

---

## Local Development

To test locally before pushing:

```bash
# Create .env from .env.example
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start dev server
python manage.py runserver

# In another terminal, start Celery worker
celery -A tastyz_project worker -l info
```

---

## Support

- Railways docs: https://docs.railway.app
- Django deployment: https://docs.djangoproject.com/en/4.2/howto/deployment/
- Troubleshooting: Check Railway logs or open an issue on GitHub
