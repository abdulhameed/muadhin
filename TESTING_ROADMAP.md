# Muadhin Testing Roadmap

## Current State
- **Total Python Files**: 93 (excluding venv)
- **Test Coverage**: ~5%
- **Untested Code**: 95%
- **Only Test File with Content**: subscriptions/tests.py (58 lines, 4 tests)

---

## Phase 1: Foundation (Week 1-2)

### Setup Testing Infrastructure

#### 1.1 Install Testing Dependencies
```bash
pip install pytest pytest-django pytest-asyncio pytest-mock freezegun factory-boy responses coverage
```

#### 1.2 Create Test Configuration (conftest.py)
```python
# /Users/mac/Projects/muadhin/tests/conftest.py
import os
import django
from django.conf import settings

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'muadhin.settings')
django.setup()

import pytest
from django.contrib.auth import get_user_model
from subscriptions.models import SubscriptionPlan, UserSubscription
from factory import django as factory_django

User = get_user_model()

@pytest.fixture
def user_factory():
    """Factory for creating test users"""
    class UserFactory(factory_django.DjangoModelFactory):
        class Meta:
            model = User
        
        username = factory.Sequence(lambda n: f'user{n}')
        email = factory.Sequence(lambda n: f'user{n}@test.com')
        password = 'testpass123'
    
    return UserFactory

@pytest.fixture
def admin_user():
    """Create admin user"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='admin123'
    )

@pytest.fixture
def basic_plan():
    """Create basic subscription plan"""
    return SubscriptionPlan.objects.create(
        name='Basic',
        plan_type='basic',
        country='GLOBAL',
        currency='USD',
        price=0.00,
        billing_cycle='monthly',
        daily_prayer_summary_email=True,
        pre_adhan_email=True,
    )

@pytest.fixture
def premium_plan():
    """Create premium subscription plan"""
    return SubscriptionPlan.objects.create(
        name='Premium',
        plan_type='premium',
        country='GLOBAL',
        currency='USD',
        price=9.99,
        billing_cycle='monthly',
        daily_prayer_summary_email=True,
        daily_prayer_summary_whatsapp=True,
        pre_adhan_email=True,
        pre_adhan_sms=True,
        pre_adhan_whatsapp=True,
        adhan_call_audio=True,
        max_notifications_per_day=50,
    )
```

#### 1.3 Setup pytest.ini
```ini
[pytest]
DJANGO_DB_NAME = :memory:
DJANGO_SETTINGS_MODULE = muadhin.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --cov=. --cov-report=html --cov-report=term-missing
testpaths = tests
```

#### 1.4 Create Test Directory Structure
```bash
mkdir -p /Users/mac/Projects/muadhin/tests/{unit,integration,api,celery,fixtures}
touch /Users/mac/Projects/muadhin/tests/__init__.py
touch /Users/mac/Projects/muadhin/tests/conftest.py
touch /Users/mac/Projects/muadhin/tests/unit/__init__.py
touch /Users/mac/Projects/muadhin/tests/integration/__init__.py
touch /Users/mac/Projects/muadhin/tests/api/__init__.py
touch /Users/mac/Projects/muadhin/tests/celery/__init__.py
```

---

## Phase 2: Critical Business Logic (Week 2-4)

### 2.1 Subscriptions Module Tests
**File**: `/Users/mac/Projects/muadhin/tests/unit/test_subscriptions_service.py`

**Tests to Write** (40-50 tests):
```python
# SubscriptionService tests
- test_get_user_plan_returns_basic_for_no_subscription
- test_get_user_plan_returns_active_subscription_plan
- test_get_user_plan_returns_basic_for_expired_subscription
- test_can_user_access_feature_with_basic_plan
- test_can_user_access_feature_with_premium_plan
- test_can_user_access_feature_inactive_subscription
- test_upgrade_user_plan_creates_history
- test_upgrade_user_plan_sets_correct_end_date_monthly
- test_upgrade_user_plan_sets_correct_end_date_yearly
- test_upgrade_user_plan_sets_end_date_none_for_lifetime
- test_start_trial_creates_trial_subscription
- test_start_trial_with_custom_duration
- test_start_trial_fails_if_already_on_trial
- test_validate_notification_preference_valid_method
- test_validate_notification_preference_invalid_method
- test_validate_notification_preference_checks_plan_features

# UserSubscription model tests
- test_subscription_is_active_for_active_status
- test_subscription_is_active_false_for_cancelled
- test_subscription_is_active_false_for_expired
- test_subscription_is_trial_returns_true_for_trial_status
- test_subscription_is_trial_false_if_expired
- test_days_remaining_calculation
- test_days_remaining_returns_none_for_lifetime
- test_days_remaining_zero_for_expired
- test_can_use_feature_checks_daily_limit
- test_can_use_feature_respects_plan_flags
- test_increment_usage_increments_counter
- test_reset_daily_usage_at_day_boundary
- test_reset_daily_usage_preserves_count_same_day
- test_start_trial_sets_trial_status
- test_activate_subscription_sets_active_status
- test_cancel_subscription_sets_cancelled_status

# SubscriptionPlan model tests
- test_plan_features_list_for_basic
- test_plan_features_list_for_premium
- test_get_plans_for_country_returns_country_and_global
- test_get_best_plan_prefers_country_specific
- test_get_best_plan_falls_back_to_global
- test_localized_price_display_ngn
- test_localized_price_display_usd
- test_localized_price_display_gbp
```

**Estimated Coverage**: 90%

### 2.2 User Model & Preferences Tests
**File**: `/Users/mac/Projects/muadhin/tests/unit/test_user_models.py`

**Tests to Write** (35-45 tests):
```python
# CustomUser timezone tests
- test_customuser_save_validates_timezone
- test_customuser_save_fallback_invalid_timezone
- test_customuser_next_midnight_calculation
- test_customuser_next_midnight_daylight_saving
- test_customuser_get_country_code_for_supported_countries
- test_customuser_get_country_code_fallback_to_global
- test_customuser_get_country_code_case_insensitive
- test_customuser_preferred_currency_by_country
- test_customuser_is_nigeria_user
- test_customuser_get_available_plans
- test_customuser_can_send_notification_active_subscription
- test_customuser_can_send_notification_no_subscription
- test_customuser_can_send_notification_daily_limit
- test_customuser_record_notification_sent

# UserPreferences validation tests
- test_user_preferences_daily_summary_email_validation
- test_user_preferences_pre_adhan_validation
- test_user_preferences_adhan_call_validation
- test_user_preferences_invalid_combination_raises_validation_error
- test_user_preferences_clean_method_with_invalid_plan
- test_user_preferences_utc_time_for_1159_calculation
- test_user_preferences_save_timezone_calculation

# PrayerMethod tests
- test_prayer_method_name_property_for_all_methods
- test_prayer_method_invalid_method_number
- test_prayer_method_user_binding
- test_prayer_method_string_representation

# PrayerOffset tests
- test_prayer_offset_creation
- test_prayer_offset_positive_offsets
- test_prayer_offset_negative_offsets
- test_prayer_offset_zero_offsets
- test_prayer_offset_large_offsets

# Location model tests
- test_location_user_binding
- test_location_decimal_fields

# CustomUserManager tests
- test_manager_get_users_needing_scheduling
- test_manager_bulk_update_scheduled_time
```

**Estimated Coverage**: 85%

### 2.3 Communications Service Tests
**File**: `/Users/mac/Projects/muadhin/tests/unit/test_notification_service.py`

**Tests to Write** (50-60 tests):
```python
# SMS sending tests
- test_send_sms_with_valid_phone_number
- test_send_sms_with_no_phone_number
- test_send_sms_selects_best_provider_for_country
- test_send_sms_tries_fallback_provider_on_failure
- test_send_sms_logs_usage_on_success
- test_send_sms_logs_usage_on_failure
- test_send_sms_with_preferred_provider
- test_send_sms_preferred_provider_fallback_to_list

# Voice call tests
- test_make_call_with_valid_phone_and_audio_url
- test_make_call_with_no_phone_number
- test_make_call_selects_best_provider
- test_make_call_tries_fallback_on_failure
- test_make_call_logs_usage

# Text call tests
- test_make_text_call_with_valid_phone
- test_make_text_call_fallback_to_sms
- test_make_text_call_logs_usage

# WhatsApp tests
- test_send_whatsapp_with_whatsapp_number
- test_send_whatsapp_fallback_to_phone_number
- test_send_whatsapp_fallback_to_sms_provider_unavailable
- test_send_whatsapp_logs_usage
- test_send_whatsapp_with_no_number

# Provider registry tests
- test_get_providers_for_country_ng
- test_get_providers_for_country_us
- test_get_providers_for_country_fallback
- test_get_best_provider_for_cost

# CommunicationResult tests
- test_communication_result_success_case
- test_communication_result_failure_case
- test_communication_result_to_dict

# ProviderStatus tests
- test_provider_status_success_rate_calculation
- test_provider_status_update_metrics_success
- test_provider_status_update_metrics_failure
- test_provider_status_health_determination_good
- test_provider_status_health_determination_poor
- test_provider_status_consecutive_failures_tracking
```

**Estimated Coverage**: 85%

### 2.4 Prayer Models Tests
**File**: `/Users/mac/Projects/muadhin/tests/unit/test_prayer_models.py`

**Tests to Write** (20-30 tests):
```python
# DailyPrayer tests
- test_daily_prayer_creation
- test_daily_prayer_unique_together_constraint
- test_daily_prayer_duplicate_raises_error
- test_daily_prayer_user_deletion_cascade
- test_daily_prayer_string_representation
- test_daily_prayer_notification_flags

# PrayerTime tests
- test_prayer_time_creation
- test_prayer_time_unique_together_constraint
- test_prayer_time_for_each_prayer_name
- test_prayer_time_get_prayer_time_method
- test_prayer_time_notification_flags
- test_prayer_time_created_at_timestamp
- test_prayer_time_updated_at_timestamp
- test_prayer_time_string_representation
```

**Estimated Coverage**: 80%

---

## Phase 3: Service Layer & Integration (Week 4-6)

### 3.1 Location Service Tests
**File**: `/Users/mac/Projects/muadhin/tests/unit/test_location_service.py`

**Tests to Write** (30-40 tests):
```python
# Country API integration (mocked)
- test_get_all_countries_from_rest_api
- test_get_all_countries_fallback_to_pycountry
- test_get_all_countries_caching
- test_get_all_countries_filter_popular
- test_get_all_countries_filter_muslim_majority
- test_get_all_countries_search_by_name
- test_get_all_countries_search_by_code

# City API integration (mocked)
- test_get_cities_for_country_from_geonames
- test_get_cities_for_country_caching
- test_get_cities_for_country_search
- test_get_cities_fallback_for_major_countries
- test_get_cities_fallback_fields_present

# REST Countries parsing
- test_rest_countries_field_extraction
- test_rest_countries_calling_code_extraction
- test_rest_countries_timezone_parsing

# GeoNames parsing
- test_geonames_city_parsing
- test_geonames_coordinates_parsing
- test_geonames_timezone_extraction

# Error handling
- test_rest_countries_api_timeout
- test_geonames_api_error
- test_invalid_country_code
```

**Estimated Coverage**: 80%

### 3.2 Provider Implementation Tests
**File**: `/Users/mac/Projects/muadhin/tests/unit/test_communication_providers.py`

**Tests to Write** (40-50 tests):
```python
# Base provider tests
- test_provider_phone_number_formatting_nigeria
- test_provider_phone_number_formatting_india
- test_provider_phone_number_formatting_default
- test_provider_config_validation

# Twilio provider tests (mocked)
- test_twilio_sms_success
- test_twilio_sms_failure
- test_twilio_call_success
- test_twilio_call_failure
- test_twilio_supported_countries

# Africa's Talking provider tests (mocked)
- test_at_sms_success
- test_at_sms_with_sender_id
- test_at_sms_failure
- test_at_call_success
- test_at_call_failure
- test_at_supported_countries

# Nigeria provider tests (mocked)
- test_nigeria_sms_success
- test_nigeria_sms_termii_api

# India provider tests (mocked)
- test_india_sms_success
- test_india_sms_textlocal_api

# Cost calculations
- test_cost_per_message_by_country
- test_cost_per_message_combined

# Async/Sync wrapper tests
- test_sync_wrapper_runs_async_code
- test_multiple_sync_wrapper_calls
- test_event_loop_handling
```

**Estimated Coverage**: 75%

### 3.3 Prayer Sync & Trigger Tests
**File**: `/Users/mac/Projects/muadhin/tests/integration/test_prayer_sync_flow.py`

**Tests to Write** (20-30 tests):
```python
# Prayer API sync tests (mocked)
- test_sync_prayer_times_from_api
- test_sync_creates_daily_prayer_record
- test_sync_creates_prayer_time_records
- test_sync_handles_api_failure
- test_sync_updates_existing_prayer_times
- test_sync_with_multiple_users

# Prayer notification trigger tests
- test_trigger_notification_before_prayer
- test_trigger_respects_user_preferences
- test_trigger_uses_correct_provider
- test_trigger_records_notification_sent
- test_trigger_skips_already_notified
- test_trigger_pre_adhan_offset_calculation

# Timezone handling
- test_prayer_sync_respects_user_timezone
- test_prayer_time_matching_user_timezone
- test_daylight_saving_transition_handling
```

**Estimated Coverage**: 75%

---

## Phase 4: API Endpoints (Week 6-8)

### 4.1 User API Tests
**File**: `/Users/mac/Projects/muadhin/tests/api/test_user_endpoints.py`

**Tests to Write** (40-50 tests):
```python
# Authentication endpoints
- test_user_registration_success
- test_user_registration_duplicate_username
- test_user_registration_invalid_email
- test_user_login_success
- test_user_login_invalid_credentials
- test_token_refresh

# Profile endpoints
- test_get_user_profile
- test_update_user_profile
- test_update_timezone_validation
- test_update_country_changes_currency
- test_update_phone_number_validation

# Preferences endpoints
- test_get_user_preferences
- test_update_preferences_valid
- test_update_preferences_invalid_for_plan
- test_update_preferences_feature_validation
- test_get_available_notification_methods

# Prayer method endpoints
- test_get_prayer_methods
- test_update_prayer_method
- test_prayer_method_validation

# Prayer offset endpoints
- test_get_prayer_offsets
- test_update_prayer_offsets
- test_offset_boundary_values

# Location endpoints
- test_get_countries
- test_filter_popular_countries
- test_filter_muslim_majority_countries
- test_search_countries
- test_get_cities_for_country
- test_search_cities
```

**Estimated Coverage**: 70%

### 4.2 Subscription API Tests
**File**: `/Users/mac/Projects/muadhin/tests/api/test_subscription_endpoints.py`

**Tests to Write** (30-40 tests):
```python
# Plan listing
- test_list_plans_for_country
- test_get_plan_details
- test_plan_features_in_response
- test_plan_pricing_in_user_currency

# Subscription management
- test_get_current_subscription
- test_upgrade_to_plan
- test_upgrade_creates_history
- test_upgrade_recalculates_end_date
- test_downgrade_to_plan

# Trial management
- test_start_trial
- test_trial_appears_in_current_subscription
- test_trial_upgrade_to_paid
- test_cannot_start_trial_if_active

# Usage tracking
- test_get_usage_statistics
- test_notifications_sent_today_counter
- test_daily_reset_at_midnight
```

**Estimated Coverage**: 75%

### 4.3 Prayer API Tests
**File**: `/Users/mac/Projects/muadhin/tests/api/test_prayer_endpoints.py`

**Tests to Write** (25-35 tests):
```python
# Prayer time endpoints
- test_get_today_prayer_times
- test_get_prayer_times_for_date
- test_get_prayer_times_date_range
- test_prayer_times_respects_user_timezone
- test_prayer_times_include_offsets

# Notification endpoints
- test_trigger_manual_notification
- test_manual_notification_respects_preferences
- test_notification_history_for_user
- test_notification_stats_by_type
- test_notification_stats_by_prayer

# Prayer preferences
- test_get_notification_preferences
- test_notification_log_entries
```

**Estimated Coverage**: 70%

### 4.4 Communications API Tests
**File**: `/Users/mac/Projects/muadhin/tests/api/test_communication_endpoints.py`

**Tests to Write** (20-30 tests):
```python
# Webhook handlers
- test_twilio_sms_callback_updates_status
- test_twilio_call_callback_logs_result
- test_africa_talking_callback_updates_status
- test_callback_validation

# Status endpoints
- test_get_provider_status_by_country
- test_get_all_provider_status
- test_communication_log_for_user
- test_communication_stats_by_type
- test_communication_stats_by_provider

# Error handling
- test_invalid_callback_signature
- test_missing_required_callback_fields
```

**Estimated Coverage**: 65%

---

## Phase 5: Celery Tasks (Week 8-9)

### 5.1 Celery Task Tests
**File**: `/Users/mac/Projects/muadhin/tests/celery/test_scheduled_tasks.py`

**Tests to Write** (25-35 tests):
```python
# Midnight checks
- test_schedule_midnight_checks_finds_users
- test_schedule_midnight_checks_creates_daily_prayers
- test_schedule_midnight_checks_skips_recent_users

# Notification scheduling
- test_schedule_prayer_notifications
- test_notification_task_respects_timezone
- test_notification_task_respects_preferences
- test_notification_task_handles_missing_preferences
- test_notification_task_handles_missing_prayer_method

# Error handling
- test_task_handles_api_failure_gracefully
- test_task_handles_database_error
- test_task_handles_provider_failure
- test_task_retry_logic

# Celery Beat integration
- test_celery_beat_task_scheduled
- test_task_runs_at_expected_times
```

**Estimated Coverage**: 70%

---

## Phase 6: Edge Cases & Error Handling (Week 9-10)

### 6.1 Error Handling Tests
**File**: `/Users/mac/Projects/muadhin/tests/test_error_handling.py`

**Tests to Write** (30-40 tests):
```python
# Input validation
- test_invalid_phone_number_formats
- test_invalid_timezone_string
- test_invalid_country_code
- test_invalid_email_format
- test_password_validation_strength

# Boundary conditions
- test_timezone_dst_transition
- test_midnight_boundary_crossing
- test_end_of_month_notification
- test_leap_year_handling

# Concurrency
- test_duplicate_notification_prevention
- test_race_condition_subscription_update
- test_usage_counter_race_condition
- test_daily_reset_concurrent_users

# API error responses
- test_404_not_found
- test_401_unauthorized
- test_403_forbidden
- test_400_bad_request
- test_429_rate_limited
- test_500_server_error

# Network failures
- test_provider_timeout
- test_provider_partial_response
- test_provider_invalid_json
- test_api_connection_error
- test_database_connection_error
```

**Estimated Coverage**: 60%

---

## Execution Plan

### Week 1-2: Foundation & Subscriptions (60 tests)
- Setup testing infrastructure
- Write subscription tests
- Achieve 85% coverage in subscriptions

### Week 2-4: User & Communications (120 tests)
- User model & preferences tests
- Communications service tests
- Prayer models tests
- Achieve 80%+ coverage in these modules

### Week 4-6: Services & Integration (80 tests)
- Location service tests
- Provider implementation tests
- Prayer sync & trigger tests

### Week 6-8: API Endpoints (110 tests)
- User API tests
- Subscription API tests
- Prayer API tests
- Communications API tests

### Week 8-9: Celery Tasks (30 tests)
- Scheduled task tests
- Beat scheduler tests
- Task execution tests

### Week 9-10: Edge Cases (70 tests)
- Error handling
- Boundary conditions
- Concurrency issues
- API error responses

### Total Tests: 470-550
### Expected Coverage: 75-80%

---

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_subscriptions_service.py

# Run with coverage report
pytest --cov=. --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run only API tests
pytest tests/api/

# Run with verbose output
pytest -v

# Run specific test
pytest tests/unit/test_subscriptions_service.py::test_get_user_plan_returns_basic_for_no_subscription

# Run with markers
pytest -m "not slow"
```

---

## Quick Reference: Testing Best Practices

### Use Fixtures
```python
@pytest.fixture
def user_with_premium(user_factory, premium_plan):
    user = user_factory()
    UserSubscription.objects.create(user=user, plan=premium_plan, status='active')
    return user
```

### Mock External APIs
```python
@pytest.mark.django_db
def test_send_sms_success(mocker):
    mocker.patch('communications.providers.twilio_provider.Client.messages.create')
    result = NotificationService.send_sms(user, "test")
    assert result.success
```

### Use freezegun for Time Tests
```python
@freeze_time("2024-01-15 12:30:00")
def test_daily_reset_logic():
    # Test time-dependent logic
    pass
```

### Test Database Isolation
```python
@pytest.mark.django_db
def test_user_creation():
    user = User.objects.create_user(username='test')
    assert user.id is not None
```

---

## Coverage Tracking

Track coverage with:
```bash
pytest --cov=. --cov-report=term-missing --cov-report=html
```

View HTML report: `htmlcov/index.html`

Set coverage thresholds in `setup.cfg`:
```ini
[coverage:run]
branch = True
source = .
omit = venv/*, */migrations/*, */test*.py

[coverage:report]
precision = 2
show_missing = True
skip_covered = False

[coverage:html]
directory = htmlcov
```

---

## Continuous Integration Setup (Optional)

Add to `.github/workflows/tests.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:13
        options: --health-cmd pg_isready --health-interval 10s
      redis:
        image: redis:6
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.10
      - run: pip install -r requirements.txt pytest pytest-django pytest-cov
      - run: pytest --cov
      - uses: codecov/codecov-action@v2
```

