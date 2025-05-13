from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
import uuid
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

User = get_user_model()


class UserModelTest(TestCase):
    """Tests pour le modèle User."""
    
    def setUp(self):
        """Préparer les données de test."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User",
            user_type="escort"
        )
    
    def test_user_creation(self):
        """Tester la création d'un utilisateur."""
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.email, "test@example.com")
        self.assertTrue(self.user.check_password("testpassword123"))
        self.assertEqual(self.user.first_name, "Test")
        self.assertEqual(self.user.last_name, "User")
        self.assertEqual(self.user.user_type, "escort")
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
    
    def test_user_str_method(self):
        """Tester la méthode __str__ du modèle User."""
        self.assertEqual(str(self.user), "testuser")
    
    def test_user_get_full_name(self):
        """Tester la méthode get_full_name."""
        self.assertEqual(self.user.get_full_name(), "Test User")
    
    def test_user_get_short_name(self):
        """Tester la méthode get_short_name."""
        self.assertEqual(self.user.get_short_name(), "Test")


class UserProfileTest(TestCase):
    """Tests pour le modèle UserProfile."""
    
    def setUp(self):
        """Préparer les données de test."""
        self.user = User.objects.create_user(
            username="profiletest",
            email="profile@example.com",
            password="testpassword123",
            user_type="escort"
        )
        
        self.profile = UserProfile.objects.create(
            user=self.user,
            bio="Test bio",
            phone_number="+33612345678",
            address="123 Test St",
            city="Test City",
            postal_code="12345",
            country="Test Country",
            language="fr",
            email_notifications=True,
            sms_notifications=False
        )
    
    def test_profile_creation(self):
        """Tester la création d'un profil utilisateur."""
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.bio, "Test bio")
        self.assertEqual(self.profile.phone_number, "+33612345678")
        self.assertEqual(self.profile.address, "123 Test St")
        self.assertEqual(self.profile.city, "Test City")
        self.assertEqual(self.profile.postal_code, "12345")
        self.assertEqual(self.profile.country, "Test Country")
        self.assertEqual(self.profile.language, "fr")
        self.assertTrue(self.profile.email_notifications)
        self.assertFalse(self.profile.sms_notifications)
    
    def test_profile_str_method(self):
        """Tester la méthode __str__ du modèle UserProfile."""
        self.assertEqual(str(self.profile), "Profile de profiletest")

    def test_user_profile_relationship(self):
        """Test la relation entre l'utilisateur et son profil"""
        self.assertEqual(self.user.account_profile, self.profile) 