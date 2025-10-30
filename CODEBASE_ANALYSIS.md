# Muadhin Codebase Structure Analysis

## Project Overview
Muadhin is a Django-based service that sends daily Salah (Islamic prayer) time notifications to registered Muslim users via multiple channels (email, SMS, WhatsApp, and voice calls).

**Tech Stack:**
- Django 4.2.6 with Django REST Framework
- Celery for async task processing and scheduling
- PostgreSQL (production) / SQLite (development)
- Redis for Celery broker
- Twilio & Africa's Talking for communication
- JWT authentication (rest_framework_simplejwt)
- Docker for containerization

---

## 1. Main Django Apps

### A. **Users App** (`/Users/mac/Projects/muadhin/users/`)
Handles user authentication, profiles, and prayer preferences.

**Key Models:**
- `CustomUser` - Extended Django User with timezone, location, prayer preferences
  - Fields: sex, address, city, country, timezone, phone_number, whatsapp_number, twitter_handle
  - Properties: next_midnight, current_plan, has_feature(), can_send_notification()
  - Methods for country code mapping and provider selection

- `UserPreferences` - Notification preferences per user
  - Daily prayer summary settings (email/WhatsApp)
  - Pre-adhan notification settings (email/SMS/WhatsApp) 
  - Adhan call method (email/SMS/call/text)
  - Validates preferences against subscription plan

- `PrayerMethod` - Prayer time calculation method (16 different methods supported)
- `PrayerOffset` - Custom prayer time offsets per user
- `AuthToken` - Legacy token storage
- `Location` - User's latitude, longitude, timezone

**Key Services:**
- `LocationService` - Fetches countries and cities from REST Countries API & GeoNames API
  - Supports popular countries, Muslim-majority filtering, search
  - Has fallback data for major countries

**Views/APIs:**
- Large `api_views.py` (1501 lines) with many endpoints for user registration, profile management, preferences

**Tests:** Minimal - only placeholder file

---

### B. **SalatTracker App** (`/Users/mac/Projects/muadhin/SalatTracker/`)
Core functionality for fetching prayer times and scheduling notifications.

**Key Models:**
- `DailyPrayer` - One record per user per day
  - Fields: user, prayer_date, weekday_name, is_email_notified, is_sms_notified
  - Prevents duplicates with unique_together constraint

- `PrayerTime` - Individual prayer times (Fajr, Dhuhr, Asr, Maghrib, Isha, etc.)
  - Fields: daily_prayer, prayer_name, prayer_time, notification status flags
  - Has get_prayer_time() method

**Key Functionality:**
- Celery tasks for scheduling prayer time notifications
- `sync_utils.py` & `sync_views.py` - Syncs prayer times with external APIs
- `trigger_utils.py` & `trigger_views.py` - Handles notification triggers
- Large `tasks.py` file (40KB) with Celery tasks:
  - `schedule_midnight_checks()` - Main scheduling task
  - User preference/method fallback creation with defensive coding
  - Complex notification logic with provider fallbacks

**Tests:** Empty placeholder

---

### C. **Subscriptions App** (`/Users/mac/Projects/muadhin/subscriptions/`)
Handles subscription plans, billing, and feature access control.

**Key Models:**
- `SubscriptionPlan` - Pricing plans with feature flags
  - Fields: name, plan_type (basic/plus/premium), country, currency, price
  - Feature flags for notifications: email, SMS, WhatsApp, audio calls, text calls
  - max_notifications_per_day, priority_support, custom_adhan_sounds
  - Class methods: get_plans_for_country(), get_best_plan_for_country()
  - Properties: features_list, localized_price_display

- `UserSubscription` - User's current subscription
  - Fields: user, plan, status (active/cancelled/expired/trial/suspended)
  - Dates: start_date, end_date, trial_end_date
  - Stripe integration fields
  - Usage tracking: notifications_sent_today, last_usage_reset
  - Methods: is_active, is_trial, days_remaining, can_use_feature(), increment_usage()

- `SubscriptionHistory` - Audit trail of plan changes
- `NotificationUsage` - Tracks sent notifications per user
- `NotificationLog` (in communications) - Global communication attempts

**Key Services:**
- `SubscriptionService` - Business logic for subscriptions
  - get_user_plan() - Gets user's current/default plan
  - can_user_access_feature() - Feature access checks
  - upgrade_user_plan() - Plan upgrades with history
  - start_trial() - Trial management
  - validate_notification_preference() - Maps notification types to plan features

- `WhatsAppService` - WhatsApp-specific logic

**Tests:** Basic test file with 58 lines - covers:
- Default basic plan assignment
- Feature access validation
- Plan upgrades
- Trial functionality

---

### D. **Communications App** (`/Users/mac/Projects/muadhin/communications/`)
Multi-provider communication system with automatic provider selection and fallback.

**Key Models:**
- `ProviderConfiguration` - Database-stored provider config
  - name, provider_type (sms/call/whatsapp/combined)
  - configuration JSON, supported_countries, priority, cost_per_message

- `CommunicationLog` - Detailed communication attempt logging
  - user, communication_type, provider_name, recipient
  - success, error_message, cost, response_time_ms
  - country_code, prayer_name, notification_type context
  - Database indexes for efficient querying

- `ProviderStatus` - Health metrics per provider per country
  - total_attempts, successful_attempts, failed_attempts
  - average_response_time_ms, average_cost
  - consecutive_failures, is_healthy status
  - Success rate calculation, health status logic

**Provider Implementations:**
- `base.py` - Abstract provider classes
  - `BaseProvider` - ABC for all providers
  - `SMSProvider` - Abstract SMS class with async/sync wrappers
  - `CallProvider` - Abstract voice call class
  - `WhatsAppProvider` - Abstract WhatsApp class
  - `CommunicationResult` - Standard result dataclass
  - Phone number formatting (Nigeria, India, default)

- `twilio_provider.py` - Twilio SMS and voice calls
- `africas_talking_provider.py` - Africa's Talking SMS and voice (15KB)
- `nigeria_provider.py` - Nigeria-specific SMS provider
- `india_provider.py` - India-specific SMS provider

**Key Services:**
- `NotificationService` - Main notification orchestration
  - send_sms() - With provider selection and fallback
  - make_call() - Voice calls with audio URL
  - make_text_call() - Text-to-speech calls
  - send_whatsapp() - WhatsApp with SMS fallback
  - _log_usage() - Records notification attempts
  - get_provider_status() - Health status reporting

- `ProviderRegistry` - Provider discovery and selection
  - get_providers_for_country() - Country-specific providers
  - get_best_provider_for_cost() - Cost optimization

**Views:**
- Large `views.py` (12KB) with callback handlers for Twilio, Africa's Talking
- Webhook handling for delivery confirmations

**Tests:** Empty placeholder

---

## 2. Key Architecture Patterns

### Multi-Provider Pattern
- Providers are pluggable through inheritance
- Automatic provider selection based on:
  - User's country code
  - Provider availability for that country
  - Cost optimization
- Fallback mechanisms (e.g., SMS if WhatsApp fails)
- Health tracking per provider per country

### Subscription-Gated Features
- All communication methods are gated by subscription plan
- Plans differ by country with localized pricing
- Feature validation at serializer level (UserPreferencesSerializer)
- Usage tracking with daily reset

### Celery Task Patterns
- Defensive coding with auto-creation of missing related objects
- Mock fallback objects to prevent crashes
- Timezone-aware scheduling
- Integration with Django Celery Beat

### Service Layer Architecture
- Business logic extracted to services
- SubscriptionService, NotificationService, LocationService, ProviderRegistry
- Keeps views and serializers focused on API/HTTP concerns

---

## 3. Existing Test Coverage

**Current State:** Minimal testing
- **SalatTracker/tests.py** - Empty
- **Users/tests.py** - Empty
- **Communications/tests.py** - Empty
- **Subscriptions/tests.py** - 58 lines covering basic scenarios
  - 1 test class with 4 test methods
  - Tests basic plan assignment, feature access, upgrades, trials

**Standalone Integration Tests:** (root directory)
- test_at_direct_sms.py - Direct Africa's Talking SMS testing
- test_at_voice_call.py - Voice call testing
- test_at_no_senderid.py - Testing without sender ID
- test_at_basic_auth.py - Basic auth testing
- test_at_credentials.py - Credential validation
- test_at_sandbox_endpoint.py - Sandbox endpoint testing
- test_at_voice_simple.py - Simple voice testing
- debug_at_api.py - Debug utility

These are manual/integration tests, not unit tests.

---

## 4. Code Quality Issues Identified

### High Priority Issues:

1. **Defensive Coding Anti-Pattern** (SalatTracker/tasks.py)
   - Creates mock objects when related objects don't exist
   - Masks real data integrity issues
   - Should fail loudly or handle in migrations

2. **Business Logic in Serializers** (users/serializers.py line 162-163)
   - Comment: "BUG: perform_update and perform_destroy don't belong in serializer"
   - perform_* methods should be in ViewSet
   - Mixes concerns

3. **Missing Input Validation**
   - Phone number formatting has country-specific logic in base provider
   - No comprehensive phone number validation across the app
   - International format inconsistencies

4. **Async/Sync Wrapper Pattern** (communications/providers/base.py)
   - Creates new event loop per call in sync wrappers
   - Could cause issues with nested event loops
   - Not optimal for production

5. **No Rate Limiting**
   - No protection against notification spam
   - Relies on daily limits in subscriptions
   - No API endpoint rate limiting visible

6. **Hard-Coded Timezone Logic**
   - CustomUser.save() calculates midnight_utc
   - Repeated calculations in next_midnight property
   - Timezone validation fallback hides errors

---

## 5. Areas Requiring Unit Test Coverage

### Critical Business Logic (High Priority)

**A. Subscriptions Module**
```
Priority: CRITICAL
Coverage Gaps:
  - SubscriptionService.get_user_plan() edge cases
    - User with expired subscription
    - User with no subscription
    - Trial vs active differentiation
  
  - UserSubscription.is_active property
    - Trial expiry checks
    - End date comparisons
    - Timezone handling in dates
  
  - UserSubscription usage tracking
    - Daily reset logic (_reset_daily_usage_if_needed)
    - Usage increment with daily limits
    - Cross-day boundary behavior
  
  - Feature access validation
    - can_use_feature() method
    - Daily limit enforcement
    - Feature flag combinations
  
  - Plan upgrades and downgrades
    - History creation
    - End date calculations for different billing cycles
    - Multiple upgrade scenarios
  
  - Trial management
    - Trial start with different durations
    - Trial expiry detection
    - Transition to paid plan
```

**B. User Model & Preferences**
```
Priority: CRITICAL
Coverage Gaps:
  - CustomUser timezone handling
    - Timezone validation and fallback
    - next_midnight calculation accuracy
    - Daylight saving time edge cases
  
  - User country code mapping
    - get_country_code() for all supported countries
    - Fallback to 'GLOBAL'
    - Case sensitivity handling
  
  - UserPreferences validation
    - Subscription-gated preference updates
    - Invalid preference combinations
    - Cross-field validation logic (clean() method)
  
  - PrayerMethod
    - method_name property for all 16 methods
    - Invalid method number handling
    - User binding validation
  
  - PrayerOffset
    - Offset calculations with boundary values
    - Negative offsets
    - Prayer time calculations with offsets
```

**C. Communications/Notifications**
```
Priority: CRITICAL
Coverage Gaps:
  - NotificationService provider selection
    - Country-based provider selection
    - Provider availability fallback
    - Cost optimization ordering
  
  - SMS sending flow
    - Phone number validation
    - Provider-specific formatting (Nigeria, India)
    - Provider failure with fallback
    - Usage logging on success/failure
  
  - Voice calls
    - Audio URL validation
    - Country-specific call handling
    - Text-to-speech conversion
  
  - WhatsApp notifications
    - WhatsApp number vs phone number logic
    - SMS fallback when WhatsApp fails
    - Number formatting for WhatsApp
  
  - Provider health tracking
    - ProviderStatus.update_metrics() logic
    - Success rate calculations
    - Health status determination
    - Consecutive failure tracking
  
  - CommunicationLog
    - Complete logging of all attempts
    - PII handling (recipient hashing)
    - Index efficiency
```

**D. Prayer Times & Scheduling**
```
Priority: HIGH
Coverage Gaps:
  - DailyPrayer model
    - Duplicate prevention (unique_together)
    - Notification status tracking
    - User deletion cascade
  
  - PrayerTime model
    - Prayer name validation (Fajr, Dhuhr, etc.)
    - Prayer time calculations
    - Notification status flags
    - get_prayer_time() method accuracy
  
  - Prayer time syncing
    - sync_utils.py prayer API integration
    - Data transformation accuracy
    - Error handling for API failures
  
  - Notification triggering
    - trigger_utils.py notification logic
    - Pre-adhan offset handling
    - User preference respect
    - Provider selection during triggers
```

**E. Location Service**
```
Priority: MEDIUM
Coverage Gaps:
  - REST Countries API integration
    - Country data parsing
    - Field extraction accuracy
    - Error handling and fallback to pycountry
  
  - GeoNames API integration
    - City fetching and parsing
    - Search functionality
    - Fallback cities for major countries
  
  - Caching logic
    - Cache key generation
    - Cache timeout handling
    - Stale data management
  
  - Filtering
    - Popular countries filter
    - Muslim-majority countries filter
    - Search across fields
```

### API Endpoints (High Priority)

**Users App** (1501 lines in api_views.py)
```
Coverage Gaps:
  - Registration and authentication
    - User creation with validation
    - Password strength
    - Duplicate user handling
  
  - User profile updates
    - Field validation
    - Phone number format changes
    - Timezone validation
    - Country changes
  
  - Subscription endpoints
    - Current plan retrieval
    - Plan upgrade requests
    - Trial start
  
  - Preference management
    - Getting user preferences
    - Updating with plan validation
    - Invalid combinations rejection
```

**SalatTracker App** (597 lines in api_views.py)
```
Coverage Gaps:
  - Prayer time endpoints
    - Fetching prayer times
    - User's prayer times for date range
  
  - Notification endpoints
    - Manual notification trigger
    - Notification history
    - Statistics/usage
```

**Subscriptions App** (259 lines in api_views.py)
```
Coverage Gaps:
  - Plan listing
    - Country-specific plans
    - Plan details with features
  
  - Subscription management
    - Upgrade endpoints
    - Trial endpoints
    - Subscription status
```

**Communications App**
```
Coverage Gaps:
  - Callback handlers
    - Twilio webhooks
    - Africa's Talking webhooks
    - Delivery confirmation processing
  
  - Status endpoints
    - Provider status per country
    - User communication logs
    - Statistics
```

### Error Handling & Edge Cases (Medium Priority)

```
Coverage Gaps:
  - Network failures
    - Provider connection timeouts
    - Partial responses
    - Retry logic
  
  - Data validation
    - Invalid phone numbers
    - Invalid timezones
    - Invalid country codes
    - Invalid prayer times
  
  - Concurrency
    - Duplicate notification sending
    - Race conditions in usage tracking
    - Simultaneous subscription updates
  
  - Time-based logic
    - Midnight boundary crossing
    - DST transitions
    - Timezone edge cases
    - Past date handling
```

---

## 6. Testing Strategy Recommendations

### Test Organization
```
tests/
  unit/
    test_subscriptions_service.py
    test_notification_service.py
    test_user_models.py
    test_prayer_time_models.py
    test_location_service.py
    test_provider_registry.py
    test_communication_providers.py
  
  integration/
    test_user_registration_flow.py
    test_subscription_upgrade_flow.py
    test_notification_full_flow.py
    test_prayer_sync_flow.py
  
  api/
    test_user_endpoints.py
    test_subscription_endpoints.py
    test_prayer_endpoints.py
    test_communication_endpoints.py
  
  celery/
    test_scheduled_tasks.py
    test_notification_tasks.py
```

### Testing Tools
- pytest with pytest-django
- pytest-asyncio (for async provider tests)
- responses or pytest-mock (for HTTP mocking)
- factory-boy (for test data)
- freezegun (for time-based tests)
- django-celery-beat testing utilities

### Coverage Goals
- Subscriptions module: 90%+
- Communications service: 85%+
- User models: 85%+
- Prayer models: 80%+
- API views: 70%+ (focus on business logic)

---

## 7. Key Dependencies & Technology Stack

**Core:**
- Django 4.2.6
- Django REST Framework
- djangorestframework-simplejwt (JWT auth)
- drf-yasg (Swagger/OpenAPI)

**Async/Celery:**
- celery
- django-celery-beat
- redis

**Communication:**
- twilio
- requests

**Database:**
- django-crispy-forms
- dj-database-url

**External APIs:**
- REST Countries
- GeoNames
- Twilio
- Africa's Talking

**Utilities:**
- phonenumbers
- pycountry
- pytz
- python-dotenv

---

## 8. Summary Table

| Component | Lines | Tests | Coverage | Priority |
|-----------|-------|-------|----------|----------|
| Subscriptions Service | 123 | 4 | 5% | CRITICAL |
| Subscriptions Models | ~200 | 4 | 10% | CRITICAL |
| Communications Service | 303 | 0 | 0% | CRITICAL |
| User Models | 339 | 0 | 0% | CRITICAL |
| Location Service | 252 | 0 | 0% | MEDIUM |
| Prayer Models | 40 | 0 | 0% | HIGH |
| API Views (all) | 2357 | 0 | 0% | HIGH |
| Celery Tasks | 40KB+ | 0 | 0% | HIGH |

**Total Application Code:** ~93 Python files (excluding venv)
**Tested Code:** ~5%
**Critical Gap:** 95% of codebase untested

