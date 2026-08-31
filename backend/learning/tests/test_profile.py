"""Aggiornamento email e cambio password dal profilo utente."""
from rest_framework.test import APITestCase
from learning.models import Token, User


class ProfileUpdateTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="owner@example.com", password="password123")
        cls.other = User.objects.create_user(email="other@example.com", password="password123")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.user).key}")

    def test_can_update_email(self):
        response = self.client.patch("/api/profilo/", {"email": "new-owner@example.com"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "new-owner@example.com")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new-owner@example.com")

    def test_cannot_update_email_to_one_already_in_use(self):
        response = self.client.patch("/api/profilo/", {"email": "other@example.com"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_anonymous_cannot_update_profile(self):
        self.client.credentials()
        response = self.client.patch("/api/profilo/", {"email": "hacker@example.com"}, format="json")
        self.assertEqual(response.status_code, 401)


class ChangePasswordTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="pw@example.com", password="password123")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.user).key}")

    def test_change_password_with_correct_current_password(self):
        response = self.client.post(
            "/api/auth/password/",
            {"password_attuale": "password123", "nuova_password": "nuovaPassword456"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("nuovaPassword456"))

    def test_old_token_is_revoked_after_password_change(self):
        old_token = Token.objects.get(user=self.user).key
        self.client.post(
            "/api/auth/password/",
            {"password_attuale": "password123", "nuova_password": "nuovaPassword456"},
            format="json",
        )
        self.assertFalse(Token.objects.filter(key=old_token).exists())

    def test_rejects_wrong_current_password(self):
        response = self.client.post(
            "/api/auth/password/",
            {"password_attuale": "wrong-password", "nuova_password": "nuovaPassword456"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("password123"))

    def test_rejects_short_new_password(self):
        response = self.client.post(
            "/api/auth/password/",
            {"password_attuale": "password123", "nuova_password": "short"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_anonymous_cannot_change_password(self):
        self.client.credentials()
        response = self.client.post(
            "/api/auth/password/",
            {"password_attuale": "password123", "nuova_password": "nuovaPassword456"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)
