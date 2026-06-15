from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        # Optimized: Dynamically appends to existing default fields to prevent losing base validation logic
        fields = UserCreationForm.Meta.fields + ('email', 'phone_number', 'address')


class AsyncPasswordResetForm(PasswordResetForm):
    """
    Custom PasswordResetForm that sends password reset emails
    asynchronously via the Celery task queue instead of blocking
    the request thread with a synchronous SMTP call.
    """

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """Override to dispatch email via Celery instead of Django's send_mail."""
        from django.template.loader import render_to_string

        subject = render_to_string(subject_template_name, context)
        # Django subjects must not contain newlines
        subject = ''.join(subject.splitlines())
        body = render_to_string(email_template_name, context)

        from accounts.tasks import send_async_email
        send_async_email.delay(subject, body, [to_email], from_email)