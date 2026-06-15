"""
Celery application configuration for MyAwesomeCart.

Sets up the Celery app instance, loads configuration from Django settings
(using the CELERY_ namespace), auto-discovers tasks from all installed apps,
and defines the Celery Beat periodic schedule.
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myawesomecart.settings')

app = Celery('myawesomecart')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# ─── Celery Beat Schedule ─────────────────────────────────────
app.conf.beat_schedule = {
    'check-low-stock-every-30-minutes': {
        'task': 'shop.tasks.check_low_stock',
        'schedule': crontab(minute='*/30'),
    },
    'clear-expired-sessions-weekly': {
        'task': 'accounts.tasks.clear_expired_sessions',
        'schedule': crontab(hour=3, minute=0, day_of_week='sunday'),
    },
    'daily-inventory-summary': {
        'task': 'shop.tasks.send_daily_inventory_summary',
        'schedule': crontab(hour=23, minute=30),
    },
}
