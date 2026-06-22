# MyAwesomeCart 🛒

A production-grade e-commerce platform built with Django 5, featuring async task processing, 2FA security, real-time Telegram alerts, and automated CI/CD — deployed on DigitalOcean.

---

## 🔗 Links

- **Live Site:** `[add your DigitalOcean URL here]`
- **GitHub:** `https://github.com/kattanandakishore5-source/My-projects`

---

## ✨ Features

### 🛍️ Core E-commerce
- Product catalog with stock tracking, low-stock thresholds, and automatic status flags
- Shopping cart, coupon code system, and order management
- Automated product rating aggregation (`average_rating`, `review_count`) stored on the model — no recalculation on page load

### 💳 Payments
- **Razorpay** payment gateway integration
- Webhook-driven order state transitions via Django signals — no polling

### 🔐 Security
- **2-Factor Authentication** via `django-two-factor-auth` + `django-otp` with QR code enrollment
- **Brute-force protection** via `django-axes` (auto-lockout on repeated failed logins)
- Session hardening and production-safe settings

### ⚡ Async Processing (Celery + Redis)
- OTP dispatch and verification emails are offloaded to background workers — zero main-thread blocking
- Order confirmation and transactional emails via **Resend** (`django-anymail`)
- `django-celery-beat` schedules a daily inventory summary report automatically

### 🤖 Telegram Bot (`telegram_bot.py`)
- Owner-authenticated via decorator — unauthorized requests are rejected
- MD5 message deduplication against Redis cache (prevents duplicate alerts within 30s)
- 3-attempt retry logic with delay on Telegram API failures
- Test/CI mode bypass — skips actual HTTP requests during automated testing

**Commands:**
| Command | Description |
|---|---|
| `/check_stock` | Stock levels for all active products |
| `/low_stock` | Products below threshold with recommended restock quantity |
| `/out_of_stock` | Products with zero inventory |
| `/daily_summary` | Full daily inventory + sales report |

### 🖼️ Media & Static
- **Cloudinary** for media file storage and delivery
- **WhiteNoise** for static file serving in production

### 🚀 DevOps
- **Dockerized** with a custom `Dockerfile` and `.dockerignore`
- **GitHub Actions** CI/CD pipeline (`deploy.yml`) — auto-deploys to DigitalOcean on every push to `main`
- Environment config via `python-decouple` and `.env.example` for clean local setup

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.0, Django REST Framework |
| Database | PostgreSQL (`psycopg2-binary`) |
| Async | Celery 5.4, Redis, `django-celery-beat` |
| Auth | `django-two-factor-auth`, `django-otp`, `django-axes` |
| Payments | Razorpay |
| Email | Resend via `django-anymail` |
| Media | Cloudinary |
| Static | WhiteNoise |
| Notifications | Telegram Bot API |
| Deployment | Docker, GitHub Actions, DigitalOcean |

---

## ⚙️ Local Setup

### Prerequisites
- Python 3.10+
- PostgreSQL
- Redis
- Docker (optional)

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/kattanandakishore5-source/My-projects.git
cd My-projects

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Fill in your values in .env

# 5. Run migrations
python manage.py migrate

# 6. Create superuser
python manage.py createsuperuser

# 7. Start the development server
python manage.py runserver

# 8. Start Celery worker (separate terminal)
celery -A myawesomecart worker --loglevel=info

# 9. Start Celery beat scheduler (separate terminal)
celery -A myawesomecart beat --loglevel=info

# 10. (Optional) Start Telegram bot
python telegram_bot.py
```

### Docker

```bash
docker build -t myawesomecart .
docker run -p 8000:8000 --env-file .env myawesomecart
```

---

## 📁 Project Structure

```
My-projects/
├── accounts/          # User auth, 2FA, OTP, Celery tasks
├── shop/              # Products, orders, cart, Razorpay, signals
├── myawesomecart/     # Django settings, Celery config
├── scripts/           # Utility scripts
├── .github/workflows/ # GitHub Actions CI/CD
├── telegram_bot.py    # Telegram bot (standalone, reads Django ORM)
├── Dockerfile
├── Procfile
├── build.sh
└── requirements.txt
```

---

## 🔑 Environment Variables

See `.env.example` for all required variables. Key ones:

```
SECRET_KEY=
DEBUG=False
DATABASE_URL=
REDIS_URL=
CLOUDINARY_URL=
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RESEND_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

---

## 📄 License

MIT
