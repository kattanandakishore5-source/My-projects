import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_async_email(self, subject, message, recipient_list, from_email=None):
    if from_email is None:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'webmaster@localhost')

    try:
        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
        )
        logger.info("Email sent successfully to %s: '%s'", recipient_list, subject)
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", recipient_list, exc)
        raise self.retry(exc=exc)


@shared_task
def clear_expired_sessions():
    from django.core.management import call_command
    call_command('clearsessions')
    logger.info("Expired sessions cleared successfully.")
