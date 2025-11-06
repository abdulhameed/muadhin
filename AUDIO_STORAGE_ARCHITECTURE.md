# Muadhin Project Architecture & Audio File Storage Analysis

## Project Overview
Muadhin is a Django-based Islamic prayer time notification service that sends daily salah (prayer) time notifications to Muslim users via multiple channels: email, SMS, WhatsApp, and voice calls. It uses:
- **Backend**: Django 4.2
- **Task Queue**: Celery with Redis broker
- **Database**: PostgreSQL (production) / SQLite (development)
- **Voice/SMS Providers**: Multi-provider system (Africa's Talking, Twilio, region-specific)
- **Web Server**: Nginx reverse proxy with Gunicorn
- **Containerization**: Docker & Docker Compose

---

## Current Architecture

### 1. Project Structure
```
/Users/mac/Projects/muadhin/
├── muadhin/                     # Django project settings
│   ├── settings.py             # Configuration (static, media, celery)
│   ├── urls.py                 # URL routing
│   ├── celery.py               # Celery configuration
│   └── wsgi.py                 # WSGI application
├── communications/             # Multi-provider notification system
│   ├── models.py              # CommunicationLog, ProviderStatus, ProviderConfiguration
│   ├── views.py               # API endpoints for notifications
│   ├── urls.py                # Communication routes
│   ├── providers/             # Provider implementations
│   │   ├── base.py            # Base provider classes
│   │   ├── africas_talking_provider.py    # Africa's Talking (voice + SMS)
│   │   ├── twilio_provider.py            # Twilio (SMS + voice)
│   │   ├── nigeria_provider.py           # Termii (Nigeria-specific)
│   │   └── india_provider.py             # TextLocal (India-specific)
│   └── services/              # Service layer
│       ├── notification_service.py       # Main notification orchestration
│       └── provider_registry.py          # Provider selection logic
├── SalatTracker/              # Prayer time tracking
│   ├── tasks.py              # Celery tasks for scheduled notifications
│   ├── models.py             # PrayerTime, DailyPrayer models
│   └── views.py              # Prayer API endpoints
├── users/                     # User management
│   ├── models.py            # CustomUser, UserPreferences, PrayerMethod
│   └── api_views.py         # User API endpoints
├── subscriptions/             # Subscription & billing
│   ├── models.py            # Subscription plans, NotificationUsage
│   └── services/            # Feature availability, pricing
├── staticfiles/              # Collected static files (CSS, JS, images)
│   ├── admin/
│   ├── rest_framework/
│   └── drf-yasg/
├── docker/                   # Docker configuration
├── nginx/                    # Nginx reverse proxy config
├── docker-compose.yml        # Development environment
├── docker-compose.prod.yml   # Production environment
├── Dockerfile                # Multi-stage Docker build
└── requirements.txt          # Python dependencies
```

---

## 2. Voice Call Architecture (Key for Adhan MP3)

### Audio Call Flow
```
User Subscription → Scheduled Task (Celery) → NotificationService → Provider Registry
                                                    ↓
                        Try Africa's Talking → Try Twilio → Fall back to SMS
                                    ↓
                        Provider makes call to user phone
                                    ↓
                        Calls callback endpoint to get XML/audio response
```

### Providers & Audio Support

#### **Africa's Talking Provider** (Primary for Africa)
- **File**: `/Users/mac/Projects/muadhin/communications/providers/africas_talking_provider.py`
- **Methods**:
  - `make_call()` - Plays audio file via URL
  - `make_text_call()` - Text-to-speech (TTS)
- **Audio Format**: Expects public URL to MP3 file
- **Voice Callback URL**: Configured in settings as `voice_callback_url`
- **XML Response Example**:
  ```xml
  <Response>
      <Play url="https://example.com/adhan.mp3"/>
      <Say voice="woman">Assalamu Alaikum. This is your Adhan call from Muadhin.</Say>
  </Response>
  ```

#### **Twilio Provider** (Universal Fallback)
- **File**: `/Users/mac/Projects/muadhin/communications/providers/twilio_provider.py`
- **Methods**:
  - `make_call()` - Plays audio via TwiML
  - `make_text_call()` - Text-to-speech
- **Audio Format**: MP3 URL
- **TwiML Example**:
  ```xml
  <Response><Play>https://example.com/adhan.mp3</Play></Response>
  ```

### Current Audio URL (Hardcoded)
**Location**: `/Users/mac/Projects/muadhin/SalatTracker/tasks.py` (Line 791)
```python
adhan_audio_url = 'https://media.sd.ma/assabile/adhan_3435370/0bf83c80b583.mp3'
```
- External URL to Sudanese media server
- **Issue**: Depends on third-party hosting, not versioned, could be unavailable

---

## 3. Static/Media File Configuration

### Current Configuration (Django Settings)
**File**: `/Users/mac/Projects/muadhin/muadhin/settings.py`

```python
# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(BASE_DIR, 'file_cache/'),
    }
}
```

**Missing**: No `MEDIA_ROOT` or `MEDIA_URL` configured (common pattern for user uploads)

### Nginx Configuration (File Serving)
**File**: `/Users/mac/Projects/muadhin/nginx/conf.d/default.conf`

```nginx
# Static files (existing)
location /static/ {
    alias /app/staticfiles/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Media files (exists but unused)
location /media/ {
    alias /app/media/;
    expires 1m;
    add_header Cache-Control "public";
}
```

---

## 4. Voice Call Integration Points

### Celery Task
**File**: `/Users/mac/Projects/muadhin/SalatTracker/tasks.py`

```python
@shared_task
def send_adhan_call_notifications(daily_prayer_id):
    # ... code ...
    adhan_audio_url = 'https://media.sd.ma/assabile/adhan_3435370/0bf83c80b583.mp3'
    make_call_and_play_audio.apply_async(
        (user.phone_number, adhan_audio_url, user.id), 
        countdown=60
    )

@shared_task
def make_call_and_play_audio(recipient_phone_number, audio_url, user_id):
    """Make adhan call using the new provider system"""
    user = User.objects.get(pk=user_id)
    result = NotificationService.make_call(user, audio_url, log_usage=True)
```

### Voice Callback Endpoint
**File**: `/Users/mac/Projects/muadhin/communications/views.py` (Lines 258-308)

```python
@csrf_exempt
@require_http_methods(["GET", "POST"])
def africas_talking_voice_callback(request):
    """
    Callback endpoint for Africa's Talking voice calls
    This serves the TTS/Audio XML response
    """
    call_type = request.GET.get('callType', 'adhan')
    
    if call_type == 'adhan_audio':
        audio_url = request.GET.get('audioUrl', 'default_url')
        xml_response = f'''<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="woman">Assalamu Alaikum. It is time for prayer.</Say>
            <Play url="{audio_url}"/>
            <Say voice="woman">May Allah accept your prayers.</Say>
        </Response>'''
    # ... more handlers ...
    return HttpResponse(xml_response, content_type='application/xml')
```

**URL Route**: `/api/communications/callbacks/africastalking/voice/`

---

## 5. Docker & Container Setup

### Volume Mounts (docker-compose.yml)
```yaml
web:
  volumes:
    - .:/app                           # Source code
    - static_volume:/app/staticfiles   # Static files
    
# Note: No separate media volume configured
```

### Dockerfile Stages
- **Base Stage**: Python 3.11-slim, system dependencies
- **Development**: Development server (runserver)
- **Production**: Gunicorn with 3 workers

### Static File Collection
- Runs in `docker-entrypoint.sh`
- Uses WhiteNoise middleware for compression & serving
- Files collected to `/app/staticfiles/`

---

## 6. How Audio Files Are Currently Served

### Current Flow
1. **External URL**: Audio stored on `media.sd.ma` (third-party server)
2. **Provider receives URL**: Twilio/Africa's Talking API receives URL
3. **Provider plays file**: Calls the URL when handling the call
4. **User receives audio**: Streamed directly to caller's phone

### Characteristics
- **Advantages**: No storage in our system, no bandwidth usage
- **Disadvantages**: 
  - Depends on external service availability
  - No version control
  - Difficult to A/B test different audio files
  - Security concern if URL is compromised
  - No analytics on audio playback

---

## 7. Best Practices for Storing Adhan MP3

### Option 1: Static Files (Recommended for Small Files)
**Best for**: Single adhan file, < 5MB, infrequent updates

**Implementation**:
```
staticfiles/
├── audio/
│   ├── adhan_standard.mp3      (1-3 MB typical)
│   ├── adhan_alternative.mp3
│   └── adhan_info.json         (metadata)
```

**Django Setup**:
```python
# In settings.py - static files already configured
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# In your code
ADHAN_AUDIO_URL = f"{settings.STATIC_URL}audio/adhan_standard.mp3"
```

**Nginx Serving**:
```nginx
location /static/audio/ {
    alias /app/staticfiles/audio/;
    expires 1y;
    add_header Cache-Control "public, immutable";
    types {
        audio/mpeg mp3;
    }
}
```

### Option 2: Media Files (Better for User Content)
**Best for**: Multiple adhan versions, user uploads, frequent updates

**Implementation**:
```python
# In settings.py
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Create directories
# media/
#   ├── adhan/
#   │   ├── adhan_fajr.mp3
#   │   ├── adhan_dhuhr.mp3
#   │   └── ...
#   └── uploads/  (user-generated)
```

**Nginx Serving**:
```nginx
location /media/ {
    alias /app/media/;
    expires 30d;
    add_header Cache-Control "public";
    types {
        audio/mpeg mp3;
    }
}
```

### Option 3: CDN/Cloud Storage (Production Scale)
**Best for**: Multi-region deployment, high availability, DDoS protection

**Implementation**:
```python
# AWS S3, Google Cloud Storage, or Cloudflare
ADHAN_AUDIO_URL = "https://cdn.muadhin.com/audio/adhan.mp3"
```

---

## 8. Recommended Implementation Strategy

### Phase 1: Local Storage (Immediate)
1. Create `/Users/mac/Projects/muadhin/staticfiles/audio/` directory
2. Store adhan MP3 files there
3. Update settings and Nginx config
4. Update hardcoded URL in `SalatTracker/tasks.py`
5. Collect static files: `python manage.py collectstatic`

### Phase 2: Database-Driven Configuration (Medium-term)
```python
# New model in SalatTracker or communications app
class AdhanAudio(models.Model):
    name = models.CharField(max_length=100)  # "Standard", "Melodic", etc.
    audio_file = models.FileField(upload_to='adhan/')
    language = models.CharField(max_length=10, default='ar')
    prayer_types = models.JSONField(default=list)  # Fajr, Dhuhr, etc.
    is_active = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def get_url(self):
        return f"{settings.MEDIA_URL}{self.audio_file}"
```

### Phase 3: Provider-Specific URLs (Long-term)
```python
# Store different URLs for different providers
class ProviderAudioConfig(models.Model):
    provider = models.CharField(max_length=50)  # 'twilio', 'africas_talking'
    adhan = models.ForeignKey(AdhanAudio, on_delete=models.CASCADE)
    url = models.URLField()  # Can be relative or CDN URL
    
    class Meta:
        unique_together = ['provider', 'adhan']
```

---

## 9. Critical Code Changes Needed

### 1. Update Hardcoded URL
**File**: `/Users/mac/Projects/muadhin/SalatTracker/tasks.py` (Line 791)

**Current**:
```python
adhan_audio_url = 'https://media.sd.ma/assabile/adhan_3435370/0bf83c80b583.mp3'
```

**Better** (with settings):
```python
from django.conf import settings
adhan_audio_url = getattr(settings, 'ADHAN_AUDIO_URL', 
    f'{settings.STATIC_URL}audio/adhan_standard.mp3')
```

### 2. Add Django Settings
**File**: `/Users/mac/Projects/muadhin/muadhin/settings.py`

```python
# Audio files
ADHAN_AUDIO_URL = os.getenv(
    'ADHAN_AUDIO_URL',
    '/static/audio/adhan_standard.mp3'  # relative path in production
)

# Or for full URL:
ADHAN_AUDIO_URL = os.getenv(
    'ADHAN_AUDIO_URL',
    f"https://{os.getenv('DOMAIN', 'localhost:8000')}/static/audio/adhan_standard.mp3"
)
```

### 3. Update Nginx Config
Add audio MIME type and caching to `/nginx/conf.d/default.conf`:

```nginx
location /static/audio/ {
    alias /app/staticfiles/audio/;
    expires 1y;
    add_header Cache-Control "public, immutable";
    
    # Audio MIME types
    types {
        audio/mpeg mp3;
        audio/wav wav;
        audio/ogg ogg;
    }
    default_type audio/mpeg;
}
```

---

## 10. Directory Structure for Audio Files

### Recommended Layout
```
/Users/mac/Projects/muadhin/
├── staticfiles/
│   ├── audio/              ← CREATE THIS
│   │   ├── adhan/
│   │   │   ├── adhan_standard.mp3      (primary Adhan)
│   │   │   ├── adhan_melodic.mp3       (alternative)
│   │   │   ├── adhan_fajr.mp3          (prayer-specific)
│   │   │   ├── adhan_dhuhr.mp3
│   │   │   └── README.md               (audio metadata)
│   │   └── audio_manifest.json         (version info)
│   ├── admin/
│   ├── rest_framework/
│   └── drf-yasg/
├── media/                  ← OR USE THIS FOR USER UPLOADS
│   ├── adhan/
│   │   └── default.mp3
│   └── uploads/
```

---

## 11. Testing Audio Delivery

### Test with Africa's Talking Callback
```bash
# Test the voice callback endpoint
curl -X GET "http://localhost:8000/api/communications/callbacks/africastalking/voice/" \
  -G \
  --data-urlencode "sessionId=test" \
  --data-urlencode "phoneNumber=+254700000000" \
  --data-urlencode "callType=adhan_audio" \
  --data-urlencode "audioUrl=/static/audio/adhan/adhan_standard.mp3"
```

### Test via Celery Task (Django Shell)
```python
from django.contrib.auth import get_user_model
from SalatTracker.tasks import make_call_and_play_audio

User = get_user_model()
user = User.objects.first()

# Synchronously test (for development)
result = make_call_and_play_audio.apply(
    args=(user.phone_number, 'https://yourserver.com/static/audio/adhan_standard.mp3', user.id)
)
```

---

## 12. Key Files & their Roles

| File | Purpose |
|------|---------|
| `muadhin/settings.py` | Django configuration (static, media, providers) |
| `communications/views.py` | Voice callback endpoint for audio delivery |
| `communications/providers/africas_talking_provider.py` | Africa's Talking voice implementation |
| `communications/providers/twilio_provider.py` | Twilio voice implementation |
| `communications/services/notification_service.py` | Orchestrates provider selection for calls |
| `SalatTracker/tasks.py` | Celery tasks that trigger audio calls |
| `nginx/conf.d/default.conf` | Nginx routing & MIME types for audio |
| `docker-compose.yml` | Volume mounts for static files |

---

## 13. Production Deployment Considerations

### Environment Variables (Add to .env / .env.prod)
```bash
# Audio configuration
ADHAN_AUDIO_URL=https://your-domain.com/static/audio/adhan_standard.mp3
DOMAIN=your-domain.com

# Provider callbacks
AFRICASTALKING_VOICE_CALLBACK_URL=https://your-domain.com/api/communications/callbacks/africastalking/voice/

# Storage
# If using S3 or Cloud Storage
AWS_STORAGE_BUCKET_NAME=muadhin-audio
AWS_S3_REGION_NAME=us-east-1
```

### Caching Headers
- Static audio files: `Cache-Control: public, immutable, max-age=31536000` (1 year)
- Dynamic callbacks: `Cache-Control: no-cache, no-store, must-revalidate`

### CDN Integration (Optional)
```python
# For CloudFlare, Bunny CDN, or AWS CloudFront
if ENVIRONMENT == 'production':
    ADHAN_AUDIO_URL = f"https://cdn.{DOMAIN}/audio/adhan_standard.mp3"
```

---

## Summary: Next Steps

1. **Create audio directory**: `mkdir -p staticfiles/audio/adhan/`
2. **Place MP3 file**: Add your adhan MP3 to `staticfiles/audio/adhan/`
3. **Update Django settings**: Add `ADHAN_AUDIO_URL` configuration
4. **Update Nginx**: Add audio MIME type handling
5. **Update Celery task**: Use settings variable instead of hardcoded URL
6. **Collect static files**: `python manage.py collectstatic`
7. **Test**: Use curl or Django shell to verify audio delivery
8. **Monitor**: Check access logs for audio downloads and provider call logs

