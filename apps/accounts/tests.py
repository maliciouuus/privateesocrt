from django.test import TestCase, Client
from django.urls import reverse
from .models import User, UserProfile
from django.core import mail

# Create your tests here.


class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.user_profile = UserProfile.objects.create(user=self.user, user_type="member")

    def test_login_view_get(self):
        """Test l'affichage de la page de connexion"""
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_login_view_post_success(self):
        """Test la connexion réussie"""
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "testuser", "password": "testpass123"},
        )
        self.assertEqual(response.status_code, 302)  # Redirection après connexion
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_view_post_failure(self):
        """Test l'échec de connexion"""
        response = self.client.post(
            reverse("accounts:login"), {"username": "testuser", "password": "wrongpass"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertContains(response, "Nom d'utilisateur ou mot de passe incorrect")

    def test_logout_view(self):
        """Test la déconnexion"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class ProfileTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )
        self.user_profile = UserProfile.objects.create(user=self.user, user_type="member")
        self.client.login(username="testuser", password="testpass123")

    def test_profile_view(self):
        """Test l'affichage du profil"""
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile.html")
        self.assertContains(response, "Test User")

    def test_edit_profile(self):
        """Test la modification du profil"""
        response = self.client.post(
            reverse("accounts:edit_profile"),
            {
                "first_name": "Updated",
                "last_name": "Name",
                "email": "updated@example.com",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.last_name, "Name")
        self.assertEqual(self.user.email, "updated@example.com")

    def test_change_password(self):
        """Test le changement de mot de passe"""
        response = self.client.post(
            reverse("accounts:change_password"),
            {
                "old_password": "testpass123",
                "new_password1": "newpass123",
                "new_password2": "newpass123",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.login(username="testuser", password="newpass123"))


class RegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_view_get(self):
        """Test l'affichage de la page d'inscription"""
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_register_view_post_success(self):
        """Test l'inscription réussie"""
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "newpass123",
                "password2": "newpass123",
                "first_name": "New",
                "last_name": "User",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_view_post_failure(self):
        """Test l'échec d'inscription"""
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "newpass123",
                "password2": "differentpass",
                "first_name": "New",
                "last_name": "User",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())
        self.assertContains(response, "Les mots de passe ne correspondent pas")


class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_password_reset_request(self):
        """Test la demande de réinitialisation de mot de passe"""
        response = self.client.post(
            reverse("accounts:password_reset"), {"email": "test@example.com"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["test@example.com"])

    def test_password_reset_invalid_email(self):
        """Test la demande de réinitialisation avec un email invalide"""
        response = self.client.post(
            reverse("accounts:password_reset"), {"email": "nonexistent@example.com"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
