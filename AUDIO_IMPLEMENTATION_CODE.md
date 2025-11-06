# Audio Storage Implementation - Code Snippets Ready to Use

## File 1: muadhin/settings.py

Add after line 205 (after CACHES configuration):

```python
# ============================================================================
# Audio Files Configuration
# ============================================================================

# Adhan audio file URL - can be relative or absolute
ADHAN_AUDIO_URL = os.getenv(
    'ADHAN_AUDIO_URL',
    '/static/audio/adhan/adhan_standard.mp3'  # Relative path for development
)

# For production with full domain:
# ADHAN_AUDIO_URL = os.getenv(
#     'ADHAN_AUDIO_URL',
#     f"https://{os.getenv('DOMAIN', 'localhost:8000')}/static/audio/adhan/adhan_standard.mp3"
# )

# Optional: Multiple audio configurations for different prayers
ADHAN_AUDIO_URLS = {
    'fajr': os.getenv('ADHAN_AUDIO_FAJR', f"{os.getenv('ADHAN_AUDIO_URL', '/static/audio/adhan/adhan_standard.mp3')}"),
    'dhuhr': os.getenv('ADHAN_AUDIO_DHUHR', f"{os.getenv('ADHAN_AUDIO_URL', '/static/audio/adhan/adhan_standard.mp3')}"),
    'asr': os.getenv('ADHAN_AUDIO_ASR', f"{os.getenv('ADHAN_AUDIO_URL', '/static/audio/adhan/adhan_standard.mp3')}"),
    'maghrib': os.getenv('ADHAN_AUDIO_MAGHRIB', f"{os.getenv('ADHAN_AUDIO_URL', '/static/audio/adhan/adhan_standard.mp3')}"),
    'isha': os.getenv('ADHAN_AUDIO_ISHA', f"{os.getenv('ADHAN_AUDIO_URL', '/static/audio/adhan/adhan_standard.mp3')}"),
}
```

---

## File 2: SalatTracker/tasks.py

### Change 1: Update Imports (Line 1-20)
Add this import at the top of the file (after line 20):

```python
from django.conf import settings
```

### Change 2: Update Celery Task (Line ~791)
Replace:
```python
adhan_audio_url = 'https://media.sd.ma/assabile/adhan_3435370/0bf83c80b583.mp3'
```

With:
```python
# Use configured audio URL from settings
adhan_audio_url = settings.ADHAN_AUDIO_URL

# Optional: Use prayer-specific audio if configured
# prayer_name = daily_prayer.prayer_name or 'fajr'
# adhan_audio_url = settings.ADHAN_AUDIO_URLS.get(
#     prayer_name.lower(), 
#     settings.ADHAN_AUDIO_URL
# )
```

### Change 3: Helper Function (Optional, add after line 877)
Add this function for centralized audio URL management:

```python
def get_adhan_audio_url(prayer_name=None):
    """
    Get configured adhan audio URL for a specific prayer.
    
    Args:
        prayer_name: Prayer name (fajr, dhuhr, etc). If None, uses default.
        
    Returns:
        URL string to audio file
    """
    if prayer_name and hasattr(settings, 'ADHAN_AUDIO_URLS'):
        return settings.ADHAN_AUDIO_URLS.get(
            prayer_name.lower(),
            settings.ADHAN_AUDIO_URL
        )
    return settings.ADHAN_AUDIO_URL
```

Then use in tasks:
```python
adhan_audio_url = get_adhan_audio_url(prayer_name)
```

---

## File 3: nginx/conf.d/default.conf

Add this location block after the static files section (insert after line 25):

```nginx
# Audio files (MP3, WAV, OGG)
location /static/audio/ {
    alias /app/staticfiles/audio/;
    
    # Cache for a long time - these files change infrequently
    expires 1y;
    add_header Cache-Control "public, immutable, max-age=31536000";
    
    # MIME types for audio formats
    types {
        audio/mpeg mp3;
        audio/wav wav;
        audio/ogg ogg;
        audio/webm webm;
        audio/aac aac;
    }
    default_type audio/mpeg;
    
    # Compression for text metadata
    gzip on;
    gzip_types application/json;
    
    # Allow range requests for partial downloads
    add_header Accept-Ranges bytes;
}
```

---

## File 4: Create Directory & Sample Metadata

Create file: `staticfiles/audio/adhan/README.md`

```markdown
# Adhan Audio Files

## Files
- `adhan_standard.mp3` - Standard Adhan recitation

## Metadata

### adhan_standard.mp3
- **Duration**: ~2 minutes
- **Format**: MP3, 128kbps
- **Size**: ~2.5 MB
- **Language**: Arabic
- **Reciter**: [Your Reciter]
- **Added**: 2024-10-28

## Usage

These files are served via the application's voice calling APIs:
- Africa's Talking: `https://domain.com/static/audio/adhan/adhan_standard.mp3`
- Twilio: Same URL

## Adding New Audio

1. Place MP3 file in this directory
2. Update `muadhin/settings.py` with new filename
3. Run `python manage.py collectstatic`
4. Restart services
```

---

## File 5: Docker Volume Configuration (Optional)

To persist audio files separately, update `docker-compose.yml` or `docker-compose.prod.yml`:

### For Development (docker-compose.yml)

Add volume for audio files (after line 44):

```yaml
services:
  web:
    # ... existing config ...
    volumes:
      - .:/app
      - static_volume:/app/staticfiles
      - ./staticfiles/audio:/app/staticfiles/audio  # Add this line
```

### For Production (docker-compose.prod.yml)

```yaml
services:
  web:
    # ... existing config ...
    volumes:
      - ./staticfiles/audio:/app/staticfiles/audio
      - /data/audio:/app/audio  # Persistent audio storage
```

---

## File 6: Environment Configuration

Add to `.env` (development):
```bash
ADHAN_AUDIO_URL=/static/audio/adhan/adhan_standard.mp3
```

Add to `.env.prod` (production):
```bash
ADHAN_AUDIO_URL=https://yourdomain.com/static/audio/adhan/adhan_standard.mp3
DOMAIN=yourdomain.com
```

---

## File 7: Nginx Service Configuration (Optional)

If using separate audio server, add upstream in `nginx/nginx.conf`:

```nginx
# Optional: If serving audio from different server
upstream audio_server {
    server audio:8080;
    keepalive 32;
}
```

---

## Complete Migration Script

Create: `migrate_audio.sh`

```bash
#!/bin/bash

# Migrate adhan audio from external URL to local storage

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Creating audio directory structure..."
mkdir -p "$PROJECT_DIR/staticfiles/audio/adhan"

echo "Collecting static files..."
python "$PROJECT_DIR/manage.py" collectstatic --noinput

echo "Verifying audio file exists..."
if [ ! -f "$PROJECT_DIR/staticfiles/audio/adhan/adhan_standard.mp3" ]; then
    echo "ERROR: adhan_standard.mp3 not found in staticfiles/audio/adhan/"
    echo "Please add your audio file to:"
    echo "  $PROJECT_DIR/staticfiles/audio/adhan/adhan_standard.mp3"
    exit 1
fi

echo "Checking file size..."
SIZE=$(du -sh "$PROJECT_DIR/staticfiles/audio/adhan/adhan_standard.mp3" | cut -f1)
echo "Audio file size: $SIZE"

echo "Testing audio URL..."
curl -I http://localhost:8000/static/audio/adhan/adhan_standard.mp3 || echo "Note: Server not running, skipping HTTP test"

echo "Audio migration complete!"
echo ""
echo "Next steps:"
echo "1. Run: docker-compose restart web nginx celery celery-beat"
echo "2. Test: curl -I http://localhost:8000/static/audio/adhan/adhan_standard.mp3"
```

Usage:
```bash
chmod +x migrate_audio.sh
./migrate_audio.sh
```

---

## Testing Implementation

Create: `test_audio_delivery.py`

```python
#!/usr/bin/env python
"""Test audio file delivery and voice call integration"""

import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'muadhin.settings')
django.setup()

from django.conf import settings
from django.test import Client

def test_audio_file_accessible():
    """Test if audio file is accessible via HTTP"""
    client = Client()
    response = client.get('/static/audio/adhan/adhan_standard.mp3')
    
    print(f"Audio file status: {response.status_code}")
    assert response.status_code == 200, "Audio file not accessible"
    print(f"Content-Type: {response.get('Content-Type')}")
    assert 'audio' in response.get('Content-Type', '').lower(), "Wrong MIME type"
    print("✓ Audio file is accessible with correct MIME type")

def test_audio_settings():
    """Test audio settings configuration"""
    audio_url = settings.ADHAN_AUDIO_URL
    print(f"Configured ADHAN_AUDIO_URL: {audio_url}")
    assert audio_url, "ADHAN_AUDIO_URL not configured"
    print("✓ ADHAN_AUDIO_URL configured")
    
    if hasattr(settings, 'ADHAN_AUDIO_URLS'):
        print(f"Prayer-specific URLs: {settings.ADHAN_AUDIO_URLS}")

def test_voice_callback():
    """Test voice callback endpoint"""
    client = Client()
    response = client.get(
        '/api/communications/callbacks/africastalking/voice/',
        {
            'sessionId': 'test_session',
            'phoneNumber': '+254700000000',
            'callType': 'adhan_audio',
            'audioUrl': settings.ADHAN_AUDIO_URL
        }
    )
    
    print(f"Voice callback status: {response.status_code}")
    assert response.status_code == 200, "Voice callback failed"
    print(f"Response type: {response.get('Content-Type')}")
    assert 'xml' in response.get('Content-Type', '').lower(), "Not XML response"
    
    content = response.content.decode()
    assert '<Play' in content, "Audio not in callback response"
    print("✓ Voice callback returns XML with audio tag")
    print(f"Callback response (first 200 chars):\n{content[:200]}...")

if __name__ == '__main__':
    print("Testing Audio Delivery Implementation")
    print("=" * 50)
    print()
    
    try:
        test_audio_settings()
        print()
        test_audio_file_accessible()
        print()
        test_voice_callback()
        print()
        print("=" * 50)
        print("✓ All audio tests passed!")
    except AssertionError as e:
        print(f"✗ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        exit(1)
```

Run with:
```bash
python test_audio_delivery.py
```

---

## Summary of Changes

### Files to Create:
1. `staticfiles/audio/adhan/adhan_standard.mp3` - Your audio file
2. `staticfiles/audio/adhan/README.md` - Metadata

### Files to Modify:
1. `muadhin/settings.py` - Add ADHAN_AUDIO_URL configuration
2. `SalatTracker/tasks.py` - Replace hardcoded URL with settings variable
3. `nginx/conf.d/default.conf` - Add audio location block

### Optional Files:
1. `.env` / `.env.prod` - Add ADHAN_AUDIO_URL environment variable
2. `docker-compose.yml` - Add volume mount for audio persistence
3. `migrate_audio.sh` - Migration automation script
4. `test_audio_delivery.py` - Test implementation

### Lines of Code to Change:
- `muadhin/settings.py`: ~10 lines
- `SalatTracker/tasks.py`: ~2 lines (+ optional helper function)
- `nginx/conf.d/default.conf`: ~20 lines

**Total: ~32 lines across 3 files**

