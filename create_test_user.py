#!/usr/bin/env python
"""Script to create test user for login testing"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'muadhin.settings')
django.setup()

from users.models import CustomUser

# Check if user already exists
if CustomUser.objects.filter(username='abdul').exists():
    print("User 'abdul' already exists. Updating password...")
    user = CustomUser.objects.get(username='abdul')
    user.set_password('SecurePassword123!')
    user.is_active = True
    user.save()
    print(f"✓ Password updated for user: {user.username}")
    print(f"✓ Email: {user.email}")
    print(f"✓ Is Active: {user.is_active}")
else:
    print("Creating new user 'abdul'...")
    user = CustomUser.objects.create_user(
        username='abdul',
        email='abdul@test.com',
        password='SecurePassword123!',
        is_active=True,
        city='Lagos',
        country='Nigeria',
        timezone='Africa/Lagos',
        phone_number='+2348012345678'
    )
    print(f"✓ User created successfully!")
    print(f"✓ Username: {user.username}")
    print(f"✓ Email: {user.email}")
    print(f"✓ Is Active: {user.is_active}")
    print(f"✓ City: {user.city}")
    print(f"✓ Country: {user.country}")
    print(f"✓ Timezone: {user.timezone}")

print("\n--- User Details ---")
print(f"ID: {user.id}")
print(f"Username: {user.username}")
print(f"Email: {user.email}")
print(f"Is Active: {user.is_active}")
print(f"Date Joined: {user.date_joined}")

print("\n✅ Test user is ready for login testing!")
print("\n--- Login Test Command ---")
print('curl -X POST https://api.almuadhin.com/api/login/ \\')
print('  -H "Content-Type: application/json" \\')
print("  -d '{\"username\": \"abdul\", \"password\": \"SecurePassword123!\"}'")
