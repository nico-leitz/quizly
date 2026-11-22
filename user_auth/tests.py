"""Automated API endpoint tests for user_auth."""

from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


@override_settings(AUTH_COOKIE_SECURE=False)
class UserAuthTests(APITestCase):
    """Test suite for all user_auth authentication endpoints."""

    def setUp(self):
        """Create a default test user and resolve auth URLs."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123!",
        )
        self.register_url = reverse("register")
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")
        self.refresh_url = reverse("token_refresh")

    def login_test_user(self):
        """Log in the default test user via the login endpoint."""
        payload = {"username": "testuser", "password": "TestPassword123!"}
        return self.client.post(self.login_url, payload, format="json")

    def test_register_success(self):
        """Registering with valid data returns 201 and creates a user."""
        payload = {
            "username": "newuser",
            "email": "New@Example.com",
            "password": "StrongPassword123!",
            "confirmed_password": "StrongPassword123!",
        }
        res = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["detail"], "User created successfully!")
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_password_mismatch(self):
        """Mismatched passwords return 400 Bad Request."""
        payload = {
            "username": "mismatchuser",
            "email": "mismatch@example.com",
            "password": "Password123!",
            "confirmed_password": "OtherPassword123!",
        }
        res = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        """Duplicate email (case-insensitive) returns 400 Bad Request."""
        payload = {
            "username": "otheruser",
            "email": "TEST@EXAMPLE.COM",
            "password": "Password123!",
            "confirmed_password": "Password123!",
        }
        res = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success_sets_cookies(self):
        """Valid credentials return 200, user info, and JWT cookies."""
        res = self.login_test_user()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["detail"], "Login successfully!")
        self.assertEqual(res.data["user"]["username"], "testuser")
        self.assertIn("access_token", res.cookies)
        self.assertIn("refresh_token", res.cookies)

    def test_login_invalid_credentials(self):
        """Wrong password returns 401 Unauthorized."""
        payload = {"username": "testuser", "password": "wrongpassword"}
        res = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_password(self):
        """Missing credentials fields return 401 Unauthorized."""
        payload = {"username": "testuser"}
        res = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_success(self):
        """Valid refresh cookie returns 200 and a new access cookie."""
        self.login_test_user()
        res = self.client.post(self.refresh_url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["detail"], "Token refreshed")
        self.assertIn("access_token", res.cookies)

    def test_token_refresh_missing_cookie(self):
        """Missing refresh cookie returns 401 Unauthorized."""
        res = self.client.post(self.refresh_url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_invalid_cookie(self):
        """Invalid refresh cookie returns 401 Unauthorized."""
        self.client.cookies["refresh_token"] = "invalid-token"
        res = self.client.post(self.refresh_url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_success_and_blacklist(self):
        """Logout returns 200, clears cookies, and blacklists refresh."""
        login_res = self.login_test_user()
        old_refresh = login_res.cookies["refresh_token"].value
        res = self.client.post(self.logout_url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.cookies["access_token"].value, "")
        self.client.cookies["refresh_token"] = old_refresh
        retry = self.client.post(self.refresh_url, {}, format="json")
        self.assertEqual(retry.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_refresh_cookie(self):
        """Logout succeeds even if the refresh cookie is missing."""
        self.login_test_user()
        del self.client.cookies["refresh_token"]
        res = self.client.post(self.logout_url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_logout_with_invalid_refresh_cookie(self):
        """Logout ignores a corrupted refresh cookie without failing."""
        self.login_test_user()
        self.client.cookies["refresh_token"] = "corrupted-token"
        res = self.client.post(self.logout_url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_logout_unauthenticated(self):
        """Logout without authentication returns 401 Unauthorized."""
        res = self.client.post(self.logout_url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)