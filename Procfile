release: python manage.py migrate && python manage.py collectstatic --noinput
web: gunicorn tastyz_project.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --worker-class sync --timeout 120
worker: celery -A tastyz_project worker -l info
beat: celery -A tastyz_project beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
