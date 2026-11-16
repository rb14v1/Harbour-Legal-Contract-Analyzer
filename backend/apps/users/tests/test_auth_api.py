from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class AuthApiTests(APITestCase):
    def test_register_creates_user(self):
        url = reverse("auth-register")
        response = self.client.post(url, {
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "full_name": "New User",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_login_returns_access_and_refresh_tokens(self):
        User.objects.create_user(email="login@example.com", password="StrongPass123!")
        url = reverse("auth-login")
        response = self.client.post(url, {"email": "login@example.com", "password": "StrongPass123!"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "login@example.com")

    def test_login_with_wrong_password_fails(self):
        User.objects.create_user(email="login2@example.com", password="StrongPass123!")
        url = reverse("auth-login")
        response = self.client.post(url, {"email": "login2@example.com", "password": "wrong"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_issues_new_access_token(self):
        User.objects.create_user(email="refresh@example.com", password="StrongPass123!")
        login_response = self.client.post(reverse("auth-login"), {
            "email": "refresh@example.com", "password": "StrongPass123!",
        })
        refresh_token = login_response.data["refresh"]
        response = self.client.post(reverse("auth-refresh"), {"refresh": refresh_token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        User.objects.create_user(email="me@example.com", password="StrongPass123!")
        login_response = self.client.post(reverse("auth-login"), {
            "email": "me@example.com", "password": "StrongPass123!",
        })
        access = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "me@example.com")
