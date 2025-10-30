# Quick Start: Adding Adhan Audio Files to Muadhin

## TL;DR - 5 Minute Setup

### 1. Create Directory
```bash
mkdir -p staticfiles/audio/adhan
```

### 2. Add Your MP3 File
```bash
cp /path/to/your/adhan.mp3 staticfiles/audio/adhan/adhan_standard.mp3
```

### 3. Update Django Settings
Add to `muadhin/settings.py` (after line 205):
```python
# Audio configuration
ADHAN_AUDIO_URL = os.getenv('ADHAN_AUDIO_URL', '/static/audio/adhan/adhan_standard.mp3')
```

### 4. Update Celery Task
In `SalatTracker/tasks.py` (line 791), replace:
```python
adhan_audio_url = 'https://media.sd.ma/assabile/adhan_3435370/0bf83c80b583.mp3'
```

With:
```python
from django.conf import settings
adhan_audio_url = settings.ADHAN_AUDIO_URL
```

### 5. Update Nginx
Add this location block to `nginx/conf.d/default.conf` (after line 25, before `/media/` section):
```nginx
# Audio files
location /static/audio/ {
    alias /app/staticfiles/audio/;
    expires 1y;
    add_header Cache-Control "public, immutable";
    types {
        audio/mpeg mp3;
        audio/wav wav;
        audio/ogg ogg;
    }
    default_type audio/mpeg;
}
```

### 6. Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 7. Restart Services
```bash
docker-compose restart web nginx celery celery-beat
```

---

## Verify It Works

### Test 1: Check File is Accessible
```bash
curl -I http://localhost:8000/static/audio/adhan/adhan_standard.mp3
# Should return: HTTP/1.1 200 OK
```

### 2. Check Django Setting
```bash
python manage.py shell
>>> from django.conf import settings
>>> print(settings.ADHAN_AUDIO_URL)
/static/audio/adhan/adhan_standard.mp3
```

### 3. Test Voice Callback
```bash
curl "http://localhost:8000/api/communications/callbacks/africastalking/voice/?callType=adhan_audio&audioUrl=/static/audio/adhan/adhan_standard.mp3"
# Should return XML with <Play> tag
```

---

## File Structure After Setup
```
muadhin/
├── staticfiles/
│   ├── audio/
│   │   └── adhan/
│   │       └── adhan_standard.mp3  ← Your file here
│   ├── admin/
│   └── ...
├── SalatTracker/
│   ├── tasks.py               ← Updated
├── muadhin/
│   └── settings.py            ← Updated
├── nginx/
│   └── conf.d/
│       └── default.conf       ← Updated
└── AUDIO_STORAGE_ARCHITECTURE.md
```

---

## Important Notes

- MP3 should be 1-3 MB (typical adhan files)
- File must be publicly accessible via URL
- In production, Nginx serves from `/app/staticfiles/`
- Relative URL (`/static/...`) auto-converts to full URL by providers
- For full URL, set env var: `ADHAN_AUDIO_URL=https://yourserver.com/static/audio/adhan/adhan_standard.mp3`

---

## Troubleshooting

### File Not Found (404)
```bash
# Check if file exists
ls -la staticfiles/audio/adhan/

# Rebuild static files
python manage.py collectstatic --noinput

# Check Nginx is serving it
curl -I http://localhost:8000/static/audio/adhan/adhan_standard.mp3
```

### Wrong MIME Type
- Add to Nginx `types { audio/mpeg mp3; }`
- Check: `curl -I http://localhost:8000/static/audio/adhan/adhan_standard.mp3 | grep Content-Type`

### Audio Not Playing in Calls
- Verify URL is accessible: `curl -I https://yourserver.com/static/audio/...`
- Check provider logs: `docker-compose logs -f celery`
- Verify callback endpoint: `curl "http://localhost:8000/api/communications/callbacks/africastalking/voice/..."`

---

## Environment Variables for Production

Add to `.env.prod`:
```bash
ADHAN_AUDIO_URL=https://your-domain.com/static/audio/adhan/adhan_standard.mp3
DOMAIN=your-domain.com
```

---

## Multiple Audio Files (Optional)

### Directory Structure
```
staticfiles/audio/
├── adhan/
│   ├── adhan_standard.mp3
│   ├── adhan_melodic.mp3
│   ├── adhan_female.mp3
│   └── README.md
└── manifest.json
```

### Usage in Code
```python
from django.conf import settings

# Use different audio for different prayers
ADHAN_URLS = {
    'fajr': f"{settings.STATIC_URL}audio/adhan/adhan_standard.mp3",
    'dhuhr': f"{settings.STATIC_URL}audio/adhan/adhan_standard.mp3",
    'asr': f"{settings.STATIC_URL}audio/adhan/adhan_standard.mp3",
    # ... etc
}

# Use in tasks
adhan_audio_url = ADHAN_URLS.get(prayer_name, ADHAN_URLS['fajr'])
```

---

## Next Steps for Production

1. Use CDN for geographic distribution (CloudFlare, AWS CloudFront)
2. Store audio in cloud (S3, Google Cloud Storage)
3. Create admin interface to upload new audio files
4. A/B test different audio versions
5. Track analytics: which audio is used, user engagement

---

## Files You Need to Modify

1. `staticfiles/audio/adhan/` - CREATE & ADD MP3
2. `muadhin/settings.py` - ADD ADHAN_AUDIO_URL
3. `SalatTracker/tasks.py` - UPDATE hardcoded URL
4. `nginx/conf.d/default.conf` - ADD audio location block

Total lines to change: ~20 lines across 3 files
