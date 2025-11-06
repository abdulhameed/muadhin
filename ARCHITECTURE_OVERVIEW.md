# Muadhin Architecture Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  Mobile App / Web App / Third-party Integrations                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (DRF)                             │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │ Users API    │ Subscriptions │ Prayer Times │ Communications│
│  │ (1501 lines) │ API (259)    │ API (597)    │ API (webhooks)│
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Service     │ │ Serializers │ │ Permissions │
│ Layer       │ │ & Schema    │ │ & Auth      │
└─────────────┘ └─────────────┘ └─────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                          │
│  ┌────────────────────┐  ┌────────────────────┐                │
│  │ SubscriptionService│  │ NotificationService│                │
│  │ - Plan validation  │  │ - Provider select  │                │
│  │ - Feature gating   │  │ - SMS/Call/Email   │                │
│  │ - Usage tracking   │  │ - Fallback logic   │                │
│  └────────────────────┘  └────────────────────┘                │
│  ┌────────────────────┐  ┌────────────────────┐                │
│  │ LocationService    │  │ ProviderRegistry   │                │
│  │ - Country data     │  │ - Provider lookup  │                │
│  │ - City matching    │  │ - Cost optimization│                │
│  │ - Caching         │  │ - Health tracking   │                │
│  └────────────────────┘  └────────────────────┘                │
│                                                                  │
│  ┌────────────────────┐  ┌────────────────────┐                │
│  │ Prayer Sync Utils  │  │ Prayer Trigger     │                │
│  │ - API integration  │  │ - Notification     │                │
│  │ - Data parsing     │  │ - Schedule mgmt    │                │
│  │ - Error handling   │  │ - Preference check │                │
│  └────────────────────┘  └────────────────────┘                │
└─────────────────────┬──────────────────────────────────────────┘
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
┌─────────────┐ ┌──────────────┐ ┌──────────────┐
│ Models      │ │ Celery Tasks │ │ Providers    │
│ (ORM)       │ │ (Async)      │ │ (Pluggable)  │
└─────────────┘ └──────────────┘ └──────────────┘
       │              │              │
       ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                 │
│  ┌──────────────┬──────────────┬──────────────────────────┐    │
│  │ PostgreSQL   │ Redis        │ External APIs            │    │
│  │ (Production) │ (Celery)     │ - Twilio, Africa's Talk  │    │
│  │              │              │ - Prayer Times API       │    │
│  │              │              │ - REST Countries API     │    │
│  │              │              │ - GeoNames API           │    │
│  └──────────────┴──────────────┴──────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Model Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CustomUser                               │
│  (Extended Django User)                                          │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ username, email, password, first_name, last_name           ││
│  │ sex, address, city, country, timezone, phone_number        ││
│  │ whatsapp_number, twitter_handle, midnight_utc             ││
│  │ last_scheduled_time                                        ││
│  └────────────────────────────────────────────────────────────┘│
└────┬────────────────────────────────────────────────────────────┘
     │
     ├─1:1──┐ ┌─────────────────────────────────────┐
     │      └─┤ UserPreferences                    │
     │        │ - daily_prayer_summary_enabled     │
     │        │ - notification_before_prayer       │
     │        │ - adhan_call_method                │
     │        └─────────────────────────────────────┘
     │
     ├─1:1──┐ ┌──────────────────────────────┐
     │      └─┤ PrayerMethod                 │
     │        │ - sn (method number 1-16)    │
     │        │ - name (method name)         │
     │        └──────────────────────────────┘
     │
     ├─1:1──┐ ┌──────────────────────────────┐
     │      └─┤ PrayerOffset                 │
     │        │ - imsak, fajr, sunrise, ...  │
     │        │ - dhuhr, asr, maghrib, isha  │
     │        │ - midnight, sunset           │
     │        └──────────────────────────────┘
     │
     ├─1:1──┐ ┌──────────────────────────────┐
     │      └─┤ Location                     │
     │        │ - latitude, longitude        │
     │        │ - timezone                   │
     │        └──────────────────────────────┘
     │
     ├─1:1──┐ ┌──────────────────────────────┐
     │      └─┤ UserSubscription             │
     │        │ - plan (FK)                  │
     │        │ - status                     │
     │        │ - start/end/trial_end_date   │
     │        │ - notifications_sent_today   │
     │        └──────────────────────────────┘
     │        │
     │        ├─FK──────────────────────────────┐
     │        │   ┌─────────────────────────────┤
     │        │   └─▶ SubscriptionPlan         │
     │        │      - plan_type               │
     │        │      - country, currency       │
     │        │      - price, billing_cycle    │
     │        │      - feature flags           │
     │        │      - max_notifications_day   │
     │        └─────────────────────────────────┘
     │
     ├─1:N──┐ ┌──────────────────────────────┐
     │      └─┤ DailyPrayer                  │
     │        │ - prayer_date                │
     │        │ - weekday_name               │
     │        │ - is_email_notified          │
     │        │ - is_sms_notified            │
     │        └──┬───────────────────────────┘
     │           │
     │           ├─1:N─┐ ┌──────────────────┐
     │           │     └─┤ PrayerTime       │
     │           │       │ - prayer_name    │
     │           │       │ - prayer_time    │
     │           │       │ - notification   │
     │           │       │   status flags   │
     │           │       └──────────────────┘
     │           │
     │           └─FK────────────────────┐
     │                                   │
     │                                   ▼
     │                        (unique_together)
     │
     ├─1:N──┐ ┌──────────────────────────────┐
     │      └─┤ NotificationUsage            │
     │        │ - notification_type          │
     │        │ - date_sent                  │
     │        │ - prayer_name                │
     │        │ - success, error_message     │
     │        └──────────────────────────────┘
     │
     └─1:N──┐ ┌──────────────────────────────┐
            └─┤ CommunicationLog             │
              │ - communication_type         │
              │ - provider_name, recipient   │
              │ - message_id, cost           │
              │ - success, error_message     │
              │ - response_time_ms           │
              │ - country_code, prayer_name  │
              └──────────────────────────────┘
```

---

## Notification Flow Diagram

```
                    SCHEDULED EVENT (Celery Beat)
                            │
                            ▼
                  ┌──────────────────────┐
                  │ schedule_midnight_    │
                  │ checks() [Celery]     │
                  └──────────┬────────────┘
                             │
                             ▼
                  ┌──────────────────────────────────┐
                  │ Find users needing scheduling:    │
                  │ - last_scheduled_time < cutoff    │
                  │ - Check user timezone             │
                  └──────────┬─────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────────────────┐
                  │ Create DailyPrayer records        │
                  │ for each user for today           │
                  └──────────┬─────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────────────────┐
                  │ Sync Prayer Times from API:       │
                  │ - Fetch from prayer API           │
                  │ - Apply user's prayer method      │
                  │ - Apply user's prayer offsets     │
                  │ - Create PrayerTime records       │
                  └──────────┬─────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────────────────┐
                  │ Schedule notification tasks       │
                  │ for each prayer time              │
                  └──────────┬─────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
   PRE-ADHAN (15min    ADHAN AT TIME       DAILY SUMMARY
   before prayer)      (Prayer time)       (11:59 AM)
        │                    │                   │
        ▼                    ▼                   ▼
   ┌────────────┐     ┌─────────────┐    ┌──────────────┐
   │ Get user   │     │ Get user    │    │ Get all      │
   │ preferences│     │ preferences │    │ prayer times │
   │            │     │             │    │ for today    │
   └─────┬──────┘     └──────┬──────┘    └──────┬───────┘
         │                   │                   │
         ▼                   ▼                   ▼
   ┌────────────────────────────────────────────────────┐
   │        Check subscription/feature access           │
   │   SubscriptionService.can_user_access_feature()    │
   │   - Check plan features                            │
   │   - Check daily notification limit                 │
   │   - Check subscription status                      │
   └──────────────┬─────────────────────────────────────┘
                  │
                  ▼
   ┌─────────────────────────────────────────────────┐
   │   NotificationService method selection:          │
   │   - Check user preference (email/sms/call/etc)  │
   │   - Select provider for user's country          │
   │   - Prepare message/audio                       │
   └──────────────┬────────────────────────────────────┘
                  │
      ┌───────────┼────────────┐
      ▼           ▼            ▼
    EMAIL       SMS/CALL     WHATSAPP
      │           │            │
      ▼           ▼            ▼
   Django    NotificationService    NotificationService
   Email     Provider Selection:    Provider Selection:
   Backend   1. Try preferred       1. Try preferred
             2. Cost-optimized      2. Cost-optimized
             3. Fallback SMS        3. Fallback SMS
             │                      │
             ▼                      ▼
        ┌─────────────────────────────────┐
        │   ProviderRegistry lookup:       │
        │   - Get providers for country    │
        │   - Filter by capability        │
        │   - Sort by cost                │
        └──────────┬──────────────────────┘
                   │
       ┌───────────┴────────────┬──────────┐
       ▼                        ▼          ▼
   TwilioProvider        Africa's      Nigeria
   - SMS send            Talking        Provider
   - Voice call          - SMS          - SMS
   - WhatsApp            - Voice        only
       │                    │          │
       ▼                    ▼          ▼
   External API Calls (Mocked in Tests)
       │
       ▼
   ┌──────────────────────────────┐
   │ CommunicationResult:          │
   │ - success (bool)              │
   │ - message_id                  │
   │ - error_message               │
   │ - cost                        │
   │ - delivery_status             │
   └──────────┬───────────────────┘
              │
              ▼
   ┌──────────────────────────────┐
   │ Log Communication:            │
   │ - CommunicationLog record     │
   │ - ProviderStatus update       │
   │ - NotificationUsage record    │
   │ - Update DailyPrayer flag     │
   └──────────────────────────────┘
```

---

## Subscription & Feature Gating Flow

```
                    USER REGISTRATION
                           │
                           ▼
              ┌────────────────────────┐
              │ Create CustomUser      │
              │ (extends Django User)  │
              └──────────┬─────────────┘
                         │
                         ▼
              ┌────────────────────────┐
              │ Create UserPreferences │
              │ (defaults to email)    │
              └──────────┬─────────────┘
                         │
                         ▼
              ┌────────────────────────┐
              │ Auto-assign Basic Plan │
              │ (Free)                 │
              └──────────┬─────────────┘
                         │
                         ▼
              ┌────────────────────────────────────┐
              │ Default Basic Features:            │
              │ - Daily prayer summary (email)     │
              │ - Pre-adhan notification (email)   │
              │ - Max 10 notifications/day         │
              └──────────┬─────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    ▼                    ▼                    ▼
USER TRIES TO      USER UPGRADES         USER DOWNGRADES
USE FEATURE        TO PREMIUM            PLAN
│                  │                     │
▼                  ▼                     ▼
Check           ┌──────────────────┐  Update
Subscription    │ SubscriptionSrvce│  subscription
Status          │ .upgrade_user_   │  status
│               │ plan()           │  │
▼               │                  │  ▼
SubscriptionSrvce │ 1. Create      │  ┌──────────────┐
.can_user_       │    SubscrHist   │  │ Recalculate  │
access_feature() │                 │  │ feature      │
│                │ 2. Update       │  │ access       │
├─Check plan     │    plan & end   │  │              │
│ features       │    date          │  └──────────────┘
│                │                 │
├─Check daily    │ 3. Update status│
│ limit          │    to 'active'  │
│                │                 │
└─Return bool    └────────┬────────┘
                          │
                          ▼
                 ┌──────────────────────┐
                 │ Premium Features:     │
                 │ - Email + WhatsApp    │
                 │ - SMS Pre-adhan       │
                 │ - Audio adhan calls   │
                 │ - Max 50 notifications│
                 │ - Priority support    │
                 └──────────────────────┘

FEATURE VALIDATION HIERARCHY:
1. Is subscription active?
   ├─ NO: Check basic plan features only
   └─ YES: Check next level

2. Is subscription in trial period?
   ├─ NO: Check plan end date
   └─ YES: Check trial end date

3. Is subscription expired?
   ├─ YES: Revert to basic plan
   └─ NO: Use active subscription plan

4. Check daily usage limit
   ├─ EXCEEDED: Return False
   └─ WITHIN LIMIT: Check feature flag

5. Feature flag check
   ├─ ENABLED: Return True
   └─ DISABLED: Return False
```

---

## Multi-Provider Selection Strategy

```
NOTIFICATION SERVICE REQUEST
│
├─ Determine user's country (from country field)
│
├─ Notification type (SMS/Call/WhatsApp)
│
└─ User's preferred provider (if any)
         │
         ▼
   ┌──────────────────────────────┐
   │ ProviderRegistry.get_         │
   │ providers_for_country()       │
   │ Filter by:                    │
   │ - Capability (SMS/Call)       │
   │ - Country support             │
   │ - Is configured               │
   │ - Is healthy (low failures)   │
   └──────────┬───────────────────┘
              │
              ▼
   ┌────────────────────────────────────┐
   │ Sort providers by:                 │
   │ 1. Cost (lower first)              │
   │ 2. Success rate (higher first)     │
   │ 3. Response time (lower first)     │
   └──────────┬─────────────────────────┘
              │
              ▼
   ┌────────────────────────────────────┐
   │ Provider List (Priority Order):     │
   │ [Nigeria SMS, Twilio, Africa's Talk]│
   └──────────┬─────────────────────────┘
              │
    ┌─────────┴──────────┐
    │                    │
    ▼                    ▼
PREFERRED          TRY EACH PROVIDER
PROVIDER (if        IN ORDER
specified)          │
│                   ├─ Send via Provider 1
│                   │  ├─ Success? Return
└─┐ Success?        │  └─ Failure? Try next
  │ │               │
  │ └─NO: Fallback  ├─ Send via Provider 2
  │                 │  ├─ Success? Return
  └─YES: Return     │  └─ Failure? Try next
                    │
                    ├─ Send via Provider 3
                    │  ├─ Success? Return
                    │  └─ Failure? Log error
                    │
                    ▼
        All providers failed
        │
        ├─ Log failure to CommunicationLog
        ├─ Update ProviderStatus
        ├─ Return error result
        └─ NO FALLBACK (except SMS↔WhatsApp)

FALLBACK SCENARIOS:
- WhatsApp fails → Try SMS
- Text-to-speech fails → Try SMS
- SMS fails → NO fallback (hard stop)
- Call fails → NO fallback (hard stop)
```

---

## Key Design Patterns

### 1. Service Layer Pattern
```python
# Business logic isolated in services
SubscriptionService.upgrade_user_plan(user, new_plan)
NotificationService.send_sms(user, message)
LocationService.get_cities_for_country(country_code)
ProviderRegistry.get_providers_for_country(country_code)
```

### 2. Provider Strategy Pattern
```python
BaseProvider (Abstract)
  ├─ SMSProvider (Abstract)
  │  ├─ TwilioProvider
  │  ├─ AfricasTalkingProvider
  │  ├─ NigeriaProvider
  │  └─ IndiaProvider
  ├─ CallProvider (Abstract)
  └─ WhatsAppProvider (Abstract)
```

### 3. Subscription Gating Pattern
```python
# Feature access controlled via subscriptions
if user.has_feature('daily_prayer_summary_whatsapp'):
    # Allow WhatsApp
else:
    # Fall back to email
```

### 4. Celery Task Pattern
```python
@shared_task
def schedule_midnight_checks():
    # Find users needing scheduling
    # Create daily prayer records
    # Schedule notification tasks
```

---

## Database Schema (Key Tables)

```
USERS
├── users_customuser (extends auth_user)
│   ├── user_ptr_id (PK, FK to auth_user)
│   ├── sex, address, city, country
│   ├── timezone, phone_number, whatsapp_number
│   └── midnight_utc, last_scheduled_time
│
└── users_userpreferences (1:1)
    ├── id (PK)
    ├── user_id (FK, UNIQUE)
    ├── daily_prayer_summary_enabled
    ├── daily_prayer_summary_message_method
    ├── notification_before_prayer_enabled
    ├── notification_before_prayer (method)
    ├── notification_time_before_prayer (minutes)
    ├── adhan_call_enabled
    ├── adhan_call_method
    └── utc_time_for_1159

PRAYER TRACKING
├── salattracker_dailyprayer
│   ├── id (PK)
│   ├── user_id (FK)
│   ├── prayer_date
│   ├── weekday_name
│   ├── is_email_notified
│   ├── is_sms_notified
│   └── UNIQUE(user_id, prayer_date)
│
└── salattracker_prayertime
    ├── id (PK)
    ├── daily_prayer_id (FK)
    ├── prayer_name
    ├── prayer_time
    ├── is_sms_notified
    ├── is_phonecall_notified
    ├── created_at, updated_at
    └── UNIQUE(daily_prayer_id, prayer_name)

SUBSCRIPTIONS
├── subscriptions_subscriptionplan
│   ├── id (PK)
│   ├── name, plan_type (basic/plus/premium)
│   ├── country, currency, price
│   ├── billing_cycle (monthly/yearly/lifetime)
│   ├── Feature flags (daily_prayer_summary_email, etc)
│   ├── max_notifications_per_day
│   ├── priority_support, custom_adhan_sounds
│   └── UNIQUE(plan_type, country, billing_cycle)
│
├── subscriptions_usersubscription
│   ├── id (PK)
│   ├── user_id (FK, UNIQUE)
│   ├── plan_id (FK)
│   ├── status (active/cancelled/expired/trial/suspended)
│   ├── start_date, end_date, trial_end_date
│   ├── Stripe fields (subscription_id, customer_id)
│   ├── notifications_sent_today, last_usage_reset
│   └── created_at, updated_at
│
└── subscriptions_subscriptionhistory
    ├── id (PK)
    ├── user_id (FK)
    ├── from_plan_id (FK, nullable)
    ├── to_plan_id (FK)
    ├── change_date
    ├── reason
    └── amount_paid

COMMUNICATIONS
├── communications_communicationlog
│   ├── id (PK)
│   ├── user_id (FK)
│   ├── communication_type (sms/call/whatsapp/email)
│   ├── provider_name
│   ├── recipient (hashed)
│   ├── message_id, success
│   ├── error_message, cost
│   ├── prayer_name, notification_type
│   ├── response_time_ms, country_code
│   ├── raw_response (JSON)
│   ├── created_at
│   └── INDEXES: (user_id, created_at), (communication_type, created_at)
│
└── communications_providerstatus
    ├── id (PK)
    ├── provider_name, country_code
    ├── total_attempts, successful_attempts, failed_attempts
    ├── average_response_time_ms, average_cost
    ├── is_healthy, consecutive_failures
    ├── last_success_at, last_failure_at
    ├── created_at, last_updated
    └── UNIQUE(provider_name, country_code)
```

