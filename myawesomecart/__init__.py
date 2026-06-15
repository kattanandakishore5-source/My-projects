"""
MyAwesomeCart project initialization.

Import the Celery app so it is always loaded when Django starts,
ensuring that shared_task decorators use this app instance.
"""

from .celery import app as celery_app

__all__ = ('celery_app',)
