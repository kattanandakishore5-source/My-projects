web: python manage.py migrate --noinput && gunicorn --bind 0.0.0.0:${PORT:-8080} myawesomecart.wsgi:application
