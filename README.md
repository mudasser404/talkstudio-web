# Voice Cloning Platform

A complete voice cloning web application built with Django, featuring user management, credit system, payment processing, and AI-powered voice generation.

## 📁 Project Structure

```
copy/
├── manage.py                  # Django management script
├── requirements.txt           # Python dependencies
├── db.sqlite3                 # SQLite database
├── .env                       # Environment variables
│
├── voice_cloning/             # Main Django project settings
│   ├── settings.py            # Django settings
│   ├── urls.py                # Main URL routing
│   ├── wsgi.py                # WSGI config
│   └── startup_patches.py     # Startup initialization
│
├── accounts/                  # User management app
│   ├── models.py              # User, CreditTransaction, PlatformSettings
│   ├── views.py               # Auth, Admin APIs, Dashboard
│   ├── admin.py               # Django admin config
│   └── urls.py                # Account URLs
│
├── voices/                    # Voice management app
│   ├── models.py              # VoiceLibrary, ClonedVoice, GeneratedAudio
│   ├── views.py               # Voice CRUD, Generation history
│   ├── progress_tracker.py    # Real-time generation tracking
│   └── urls.py                # Voice URLs
│
├── tts_engine/                # TTS/Voice Generation app
│   ├── views.py               # Generation endpoints
│   ├── tts_api_service.py     # External TTS API integration
│   └── urls.py                # TTS URLs
│
├── payments/                  # Payment processing app
│   ├── models.py              # Payment, Subscription, CreditPackage
│   ├── views.py               # Stripe, PayPal integration
│   ├── gateways.py            # Payment gateway classes
│   └── urls.py                # Payment URLs
│
├── support/                   # Support ticket system
│   ├── models.py              # SupportTicket, TicketResponse
│   └── views.py               # Support endpoints
│
├── homepage/                  # Landing page management
│   ├── models.py              # Carousel, Features, Testimonials
│   └── views.py               # Homepage content APIs
│
├── templates/                 # HTML templates
│   ├── base.html              # Base template
│   ├── clone.html             # Voice cloning page
│   ├── dashboard.html         # User dashboard
│   ├── admin_dashboard.html   # Admin panel
│   ├── pricing.html           # Pricing page
│   └── ...
│
├── static/                    # Static files (CSS, JS, images)
├── staticfiles/               # Collected static files
├── media/                     # User uploads (voices, audio)
├── locale/                    # Translation files
└── logs/                      # Application logs
```

## 🖥️ System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.10+ | 3.10 |
| RAM | 2GB | 4GB+ |
| Disk | 1GB | 5GB+ |

**Note:** This Django app does NOT require a GPU. Voice generation is handled by an external TTS API server.

## 🚀 Quick Start

### Step 1: Setup Virtual Environment

```bash
cd copy

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment

Create `.env` file:

```bash
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite by default)
# DATABASE_URL=postgres://user:pass@localhost:5432/voicecloning

# TTS API Configuration (External F5-TTS Server)
TTS_API_URL=http://localhost:8001/generate
TTS_API_KEY=
TTS_API_TIMEOUT=300

# Payment Gateways
STRIPE_PUBLIC_KEY=pk_test_xxx
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

PAYPAL_CLIENT_ID=xxx
PAYPAL_CLIENT_SECRET=xxx
PAYPAL_MODE=sandbox

# Email (Optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=app-password
```

### Step 4: Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Step 5: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### Step 6: Run Server

```bash
python manage.py runserver 0.0.0.0:8000
```

Access the application at: http://localhost:8000

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/accounts/register/` | Register new user |
| POST | `/api/accounts/login/` | Login |
| POST | `/api/accounts/logout/` | Logout |
| GET | `/api/accounts/profile/` | Get user profile |

### Voice Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tts/generate/` | Generate speech |
| GET | `/api/tts/api/progress/<task_id>/` | Check generation progress |
| GET | `/api/tts/api/model-info/` | Get TTS model info |

### Voices

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/voices/library/` | List default voices |
| GET | `/api/voices/cloned/` | List user's cloned voices |
| POST | `/api/voices/cloned/` | Clone new voice |
| GET | `/api/voices/generated/` | List generated audio |

### Payments

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/payments/stripe/create-intent/` | Create Stripe payment |
| POST | `/api/payments/stripe/confirm/` | Confirm Stripe payment |
| POST | `/api/payments/paypal/create-order/` | Create PayPal order |
| GET | `/api/payments/paypal/capture/` | Capture PayPal payment |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/accounts/admin/stats/` | Dashboard statistics |
| GET | `/api/accounts/admin/users/` | List users |
| GET | `/api/accounts/admin/payments/` | List payments |
| GET | `/api/accounts/admin/platform-settings/` | Get settings |

## 🔗 TTS API Integration

This application uses an external TTS API for voice generation. Configure the TTS server in `.env`:

```bash
# For Local F5-TTS Server
TTS_API_URL=http://your-gpu-server:8001/generate

# For RunPod Serverless
TTS_API_URL=https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync
TTS_API_KEY=your-runpod-api-key
```

### Architecture

```
┌─────────────────────────────┐         ┌─────────────────────────────┐
│                             │         │                             │
│   Voice Cloning Platform    │  HTTP   │   F5-TTS API Server         │
│   (This Django App)         │ ──────► │   (Separate GPU Server)     │
│   Port: 8000                │         │   Port: 8001                │
│                             │         │                             │
│   Features:                 │         │   Features:                 │
│   - User Management         │         │   - F5-TTS Model            │
│   - Credits System          │         │   - Voice Cloning           │
│   - Payment Processing      │         │   - Audio Processing        │
│   - Admin Dashboard         │         │                             │
│   - Voice Library           │         │                             │
│                             │         │                             │
└─────────────────────────────┘         └─────────────────────────────┘
```

## 💳 Payment Integration

### Stripe

1. Get API keys from [Stripe Dashboard](https://dashboard.stripe.com/)
2. Add to `.env`:
   ```bash
   STRIPE_PUBLIC_KEY=pk_test_xxx
   STRIPE_SECRET_KEY=sk_test_xxx
   ```

### PayPal

1. Get credentials from [PayPal Developer](https://developer.paypal.com/)
2. Add to `.env`:
   ```bash
   PAYPAL_CLIENT_ID=xxx
   PAYPAL_CLIENT_SECRET=xxx
   PAYPAL_MODE=sandbox  # or 'live' for production
   ```

## 👤 User Roles

| Role | Access |
|------|--------|
| **User** | Dashboard, Voice Cloning, Purchase Credits |
| **Admin** | Full access + Admin Dashboard |
| **Superuser** | Django Admin + All features |

## 📊 Credit System

- New users get **1000 free credits**
- Credits are deducted per character generated
- Default: **1 credit = 1 character**
- Configurable in Admin Dashboard → Platform Settings

## 🔧 Admin Dashboard

Access: `/admin-dashboard/` (requires admin login)

Features:
- User Management (CRUD)
- Payment Transactions (with API response viewer)
- Voice Cloning Status
- Platform Settings
- Activity Logs
- Revenue Charts

## 📁 Media Files

User uploads are stored in `/media/`:

```
media/
├── cloned_voices/      # User cloned voice samples
├── generated_audio/    # Generated speech files
├── library_voices/     # Default voice library
├── voice_images/       # Voice profile images
└── references/         # Temporary reference audio
```

## 🌐 Deployment

### Production Checklist

1. Set `DEBUG=False` in `.env`
2. Configure proper `SECRET_KEY`
3. Setup PostgreSQL database
4. Configure HTTPS/SSL
5. Setup static file serving (Nginx/WhiteNoise)
6. Configure email settings
7. Setup TTS API server

### Docker Deployment

```dockerfile
# Example Dockerfile for Django app
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "voice_cloning.wsgi:application", "-b", "0.0.0.0:8000"]
```

## 🔒 Security Notes

- Never commit `.env` file
- Use strong `SECRET_KEY` in production
- Enable HTTPS in production
- Regularly update dependencies
- Use environment variables for sensitive data

## 📝 License

This project is proprietary software.

## 🔗 Related Projects

- **F5-TTS API Server**: Located in `../f5tts_api_server/`
  - Separate GPU server for voice generation
  - Can be deployed on RunPod, local GPU server, or cloud
