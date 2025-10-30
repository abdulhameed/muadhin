# Muadhin Audio Files Storage - Complete Documentation

This directory contains comprehensive documentation for implementing audio file storage for Adhan MP3 files in the Muadhin project.

## Documentation Files

### 1. **AUDIO_STORAGE_ARCHITECTURE.md** (17 KB, 528 lines)
**Purpose**: Comprehensive technical reference  
**Audience**: Architects, senior developers, decision makers

**Contains**:
- Project overview and technology stack
- Complete directory structure
- Voice call architecture and flow diagram
- Audio provider details (Africa's Talking, Twilio)
- Current vs. recommended storage approaches
- Docker and container configuration
- Three implementation phases (immediate, medium-term, long-term)
- Production deployment considerations
- 13 detailed sections with code examples

**Read this first if you want to**:
- Understand the entire architecture
- Learn about all available options
- Make informed decisions about implementation approach
- Set up production deployment

---

### 2. **AUDIO_STORAGE_QUICK_START.md** (5 KB, 201 lines)
**Purpose**: Quick implementation guide  
**Audience**: Developers who want to implement immediately

**Contains**:
- 7-step TL;DR setup (5 minutes)
- Verification testing with curl commands
- Complete file structure after setup
- Troubleshooting checklist
- Multiple audio files example
- Production environment variables
- Important notes and gotchas

**Read this when you want to**:
- Implement audio storage quickly
- Test if everything is working
- Set up multiple audio versions
- Configure environment variables

---

### 3. **AUDIO_IMPLEMENTATION_CODE.md** (10 KB, 386 lines)
**Purpose**: Ready-to-use code snippets  
**Audience**: Developers implementing the changes

**Contains**:
- Exact code for each file to modify
- Line numbers and file paths
- Optional configurations
- Docker volume setup
- Environment variable templates
- Migration automation script (bash)
- Testing utilities (Python)
- Summary of changes needed

**Use this when you need to**:
- Copy-paste code snippets
- Know exactly what lines to change
- Automate migration
- Test implementation

---

### 4. **AUDIO_FILES_README.md** (This file)
**Purpose**: Navigation and index  
**Audience**: Everyone

**Contains**:
- Documentation overview
- How to use each document
- Quick reference for files to create
- Summary of key findings
- Links to relevant project files

---

## Quick Reference

### Files You Need to Create
```
staticfiles/audio/adhan/
├── adhan_standard.mp3          ← Your MP3 file
└── README.md                   ← Metadata file
```

### Files You Need to Modify
1. **muadhin/settings.py** (+10 lines)
   - Add: `ADHAN_AUDIO_URL` configuration
   
2. **SalatTracker/tasks.py** (~2 lines)
   - Replace: Hardcoded URL with `settings.ADHAN_AUDIO_URL`
   
3. **nginx/conf.d/default.conf** (+20 lines)
   - Add: Audio location block with MIME types

**Total Changes**: ~32 lines of code across 3 files

---

## Key Project Files (Reference)

### Voice Call Implementation
- `/communications/providers/africas_talking_provider.py` - Africa's Talking API
- `/communications/providers/twilio_provider.py` - Twilio API
- `/communications/views.py` - Voice callback endpoint
- `/communications/services/notification_service.py` - Provider orchestration

### Audio Integration
- `/SalatTracker/tasks.py` (Line 791) - Hardcoded audio URL
- `/SalatTracker/tasks.py` (Line 810) - make_call_and_play_audio() task

### Configuration
- `/muadhin/settings.py` - Django settings (static file configuration)
- `/nginx/conf.d/default.conf` - Nginx routing and MIME types
- `/docker-compose.yml` - Development environment
- `/docker-compose.prod.yml` - Production environment

---

## Implementation Checklist

### Phase 1: Local Storage Setup (30 minutes)
- [ ] Read AUDIO_STORAGE_QUICK_START.md
- [ ] Create directory: `mkdir -p staticfiles/audio/adhan`
- [ ] Copy your MP3 file to `staticfiles/audio/adhan/adhan_standard.mp3`
- [ ] Add ADHAN_AUDIO_URL to muadhin/settings.py
- [ ] Update hardcoded URL in SalatTracker/tasks.py
- [ ] Update Nginx config
- [ ] Run `python manage.py collectstatic`
- [ ] Restart Docker services
- [ ] Test with curl command

### Phase 2: Verification (10 minutes)
- [ ] Test file accessibility: `curl -I http://localhost:8000/static/audio/...`
- [ ] Test Django settings: `python manage.py shell`
- [ ] Test voice callback: `curl "http://localhost:8000/api/communications/callbacks/..."`
- [ ] Check logs: `docker-compose logs -f celery`

### Phase 3: Production Setup (20 minutes)
- [ ] Update .env.prod with full domain URL
- [ ] Configure CDN if needed (optional)
- [ ] Set up monitoring/analytics (optional)
- [ ] Document audio files and versions

---

## Current Architecture

### Voice Call Flow
```
User Subscription
    ↓
Celery Task (send_adhan_call_notifications)
    ↓
NotificationService (selects provider)
    ↓
Provider (Africa's Talking or Twilio)
    ↓
Audio File URL ← Current: External URL
               ← Recommended: Internal /static/audio/...
    ↓
Calls Phone with Audio
```

### Current Problem
- Audio stored on external server: `https://media.sd.ma/...`
- Dependency on third-party service
- No version control
- Hard to test alternatives

### Recommended Solution
- Store in project: `/staticfiles/audio/adhan/`
- Served by Nginx
- Configured in Django settings
- Version controlled

---

## Environment Variables

### Development (.env)
```bash
ADHAN_AUDIO_URL=/static/audio/adhan/adhan_standard.mp3
```

### Production (.env.prod)
```bash
ADHAN_AUDIO_URL=https://yourdomain.com/static/audio/adhan/adhan_standard.mp3
DOMAIN=yourdomain.com
```

### Optional - Prayer-Specific Audio
```bash
ADHAN_AUDIO_FAJR=https://yourdomain.com/static/audio/adhan/fajr.mp3
ADHAN_AUDIO_DHUHR=https://yourdomain.com/static/audio/adhan/dhuhr.mp3
# etc.
```

---

## Testing

### Test 1: File Accessibility
```bash
curl -I http://localhost:8000/static/audio/adhan/adhan_standard.mp3
# Expected: 200 OK, Content-Type: audio/mpeg
```

### Test 2: Django Settings
```bash
python manage.py shell
>>> from django.conf import settings
>>> print(settings.ADHAN_AUDIO_URL)
```

### Test 3: Voice Callback
```bash
curl "http://localhost:8000/api/communications/callbacks/africastalking/voice/?callType=adhan_audio&audioUrl=/static/audio/adhan/adhan_standard.mp3"
# Expected: XML response with <Play url="..."/> tag
```

### Test 4: Integration Test
See `test_audio_delivery.py` in AUDIO_IMPLEMENTATION_CODE.md

---

## Troubleshooting

### File Not Found (404)
1. Check if file exists: `ls -la staticfiles/audio/adhan/`
2. Rebuild static files: `python manage.py collectstatic --noinput`
3. Check Nginx is serving: `curl -I http://localhost:8000/static/audio/...`

### Wrong MIME Type
1. Verify Nginx has audio MIME types defined
2. Check: `curl -I | grep Content-Type`
3. Ensure mp3 is mapped to audio/mpeg in Nginx

### Audio Not Playing in Calls
1. Verify URL is publicly accessible
2. Check provider logs: `docker-compose logs -f celery`
3. Test callback endpoint separately
4. Verify audio file is valid MP3

---

## Advanced Topics

### Multiple Audio Files
Create separate directory for each prayer or variation:
```
staticfiles/audio/
├── adhan/
│   ├── adhan_standard.mp3
│   ├── adhan_melodic.mp3
│   ├── adhan_female.mp3
│   └── README.md
└── manifest.json
```

### CDN Integration
For production with geographic distribution:
1. Upload to CloudFlare, AWS CloudFront, or Bunny CDN
2. Update ADHAN_AUDIO_URL to CDN URL
3. Monitor bandwidth and costs

### Admin Interface
Create Django admin interface to:
1. Upload new audio files
2. Select active version
3. Track usage analytics
4. A/B test different versions

---

## Document Navigation

**New to this project?**
→ Start with AUDIO_STORAGE_ARCHITECTURE.md

**Want to implement now?**
→ Follow AUDIO_STORAGE_QUICK_START.md

**Need exact code?**
→ Use AUDIO_IMPLEMENTATION_CODE.md

**Understanding architecture?**
→ See diagrams in AUDIO_STORAGE_ARCHITECTURE.md

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Typical MP3 Size | 1-3 MB |
| Typical Duration | 2-3 minutes |
| Implementation Time | ~30 minutes |
| Code Changes | ~32 lines |
| Files to Modify | 3 files |
| Complexity Level | Low |
| Risk Level | Low |
| Database Changes | None |
| Backward Compatible | Yes |

---

## Support & Questions

For questions about:
- **Architecture**: See AUDIO_STORAGE_ARCHITECTURE.md sections 2-6
- **Implementation**: See AUDIO_IMPLEMENTATION_CODE.md
- **Setup**: See AUDIO_STORAGE_QUICK_START.md
- **Troubleshooting**: See AUDIO_STORAGE_QUICK_START.md section "Troubleshooting"

---

## Version History

- **2024-10-28**: Initial documentation created
  - AUDIO_STORAGE_ARCHITECTURE.md
  - AUDIO_STORAGE_QUICK_START.md
  - AUDIO_IMPLEMENTATION_CODE.md
  - AUDIO_FILES_README.md

---

## See Also

- `/communications/` - Multi-provider notification system
- `/SalatTracker/` - Prayer time tracking and tasks
- `/nginx/` - Web server configuration
- `docker-compose.yml` - Container orchestration
- `muadhin/settings.py` - Django configuration

---

**Last Updated**: October 28, 2024  
**Status**: Ready for implementation  
**Confidence Level**: High - Fully analyzed and documented
