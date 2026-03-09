"""
Celery configuration for LedgerPro.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("ledgerpro")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# =============================================================================
# Periodic Tasks
# =============================================================================
app.conf.beat_schedule = {
    "update-exchange-rates-daily": {
        "task": "apps.ledger.tasks.update_exchange_rates",
        "schedule": crontab(hour=6, minute=0),
        "options": {"expires": 3600},
    },
    "check-overdue-invoices": {
        "task": "apps.invoicing.tasks.check_overdue_invoices",
        "schedule": crontab(hour=8, minute=0),
        "options": {"expires": 3600},
    },
    "generate-recurring-invoices": {
        "task": "apps.invoicing.tasks.generate_recurring_invoices",
        "schedule": crontab(hour=1, minute=0),
        "options": {"expires": 3600},
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
