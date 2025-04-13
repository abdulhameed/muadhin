from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import CustomUser, PasswordResetToken
from django.utils import timezone


class PasswordResetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email='testuser@example.com',
            password='oldpassword123'
        )

    def test_password_reset_flow(self):
        # Step 1: Request password reset
        response = self.client.post(
            reverse('reset-password'),  # Changed from 'password-reset'
            {'email': 'testuser@example.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Step 2: Verify token was created
        token = PasswordResetToken.objects.get(user=self.user)
        self.assertIsNotNone(token)
        self.assertFalse(token.is_used)
        self.assertFalse(token.is_expired)
        self.assertTrue(token.expires_at > timezone.now())

        # Step 3: Use token to reset password
        response = self.client.post(
            reverse('reset-password-confirm', args=[token.token]),
            {'new_password': 'newpassword123'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Step 4: Verify token is now marked as used
        token.refresh_from_db()
        self.assertTrue(token.is_used)

        # Step 5: Verify login works with new password
        login_successful = self.client.login(
            email='testuser@example.com',
            password='newpassword123'
        )
        self.assertTrue(login_successful)

    def test_expired_token(self):
        # Create an expired token
        expired_time = timezone.now() - timezone.timedelta(hours=25)
        token = PasswordResetToken.objects.create(
            user=self.user,
            token='expired-token',
            expires_at=expired_time,
            is_used=False,
            is_expired=False
        )

        # Try to use expired token
        response = self.client.post(
            reverse('reset-password-confirm', args=[token.token]),
            {'new_password': 'newpassword123'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('expired', response.data['error'].lower())
