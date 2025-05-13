from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
import uuid
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

User = get_user_model()


class UserModelTest(TestCase):
    """Tests pour le modèle User."""
    
    @classmethod
    def setUpTestData(cls):
        """Préparer les données de test une seule fois pour toute la classe."""
        cls.user_data = {
            'username': "testuser",
            'email': "test@example.com",
            'password': "testpassword123",
            'first_name': "Test",
            'last_name': "User",
        }
        cls.escort_user = User.objects.create_user(**cls.user_data, user_type=User.UserType.ESCORT)
        cls.ambassador_user = User.objects.create_user(
            username="ambassadoruser", 
            email="ambassador@example.com", 
            password="testpassword123", 
            user_type=User.UserType.AMBASSADOR
        )
        cls.member_user = User.objects.create_user(
            username="memberuser", 
            email="member@example.com", 
            password="testpassword123", 
            user_type=User.UserType.MEMBER
        )

    def test_user_creation(self):
        """Tester la création d'un utilisateur."""
        self.assertEqual(self.escort_user.username, "testuser")
        self.assertEqual(self.escort_user.email, "test@example.com")
        self.assertTrue(self.escort_user.check_password("testpassword123"))
        self.assertEqual(self.escort_user.first_name, "Test")
        self.assertEqual(self.escort_user.last_name, "User")
        self.assertEqual(self.escort_user.user_type, User.UserType.ESCORT)
        self.assertTrue(self.escort_user.is_active)
        self.assertFalse(self.escort_user.is_staff)
        self.assertFalse(self.escort_user.is_superuser)
        self.assertIsNotNone(self.escort_user.referral_code)
        self.assertTrue(len(self.escort_user.referral_code) > 0)

    def test_user_str_method(self):
        """Tester la méthode __str__ du modèle User."""
        self.assertEqual(str(self.escort_user), "testuser")
    
    def test_user_get_full_name(self):
        """Tester la méthode get_full_name."""
        self.assertEqual(self.escort_user.get_full_name(), "Test User")
    
    def test_user_get_short_name(self):
        """Tester la méthode get_short_name."""
        self.assertEqual(self.escort_user.get_short_name(), "Test")

    def test_create_superuser(self):
        """Tester la création d'un superutilisateur."""
        admin_user = User.objects.create_superuser(
            username='adminuser', 
            email='admin@example.com', 
            password='adminpassword123'
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)
        self.assertEqual(admin_user.user_type, User.UserType.ADMIN)

    def test_user_type_properties(self):
        """Tester les propriétés booléennes liées au user_type."""
        self.assertTrue(self.escort_user.is_escort)
        self.assertFalse(self.escort_user.is_ambassador)
        self.assertFalse(self.escort_user.is_admin)

        self.assertTrue(self.ambassador_user.is_ambassador)
        self.assertFalse(self.ambassador_user.is_escort)
        self.assertFalse(self.ambassador_user.is_admin)
        
        self.assertFalse(self.member_user.is_escort)
        self.assertFalse(self.member_user.is_ambassador)
        self.assertFalse(self.member_user.is_admin)

    def test_referral_code_uniqueness(self):
        """Tester que les codes de parrainage sont uniques."""
        user1 = User.objects.create_user(username='user1referral', email='user1referral@example.com', password='password')
        user2 = User.objects.create_user(username='user2referral', email='user2referral@example.com', password='password')
        self.assertNotEqual(user1.referral_code, user2.referral_code)
        self.assertIsNotNone(user1.referral_code)
        self.assertTrue(len(user1.referral_code) >= 6) 


class UserProfileTest(TestCase):
    """Tests pour le modèle UserProfile."""
    
    @classmethod
    def setUpTestData(cls):
        """Préparer les données de test."""
        cls.user = User.objects.create_user(
            username="profiletest",
            email="profile@example.com",
            password="testpassword123",
            user_type=User.UserType.ESCORT
        )
        
        # Le UserProfile est normalement créé par un signal.
        # Pour ce test, on s'assure qu'il existe et on le met à jour.
        cls.profile, created = UserProfile.objects.get_or_create(user=cls.user)

        cls.profile.bio="Test bio"
        cls.profile.phone_number="+33612345678"
        cls.profile.address="123 Test St"
        cls.profile.city="Test City"
        cls.profile.postal_code="12345"
        cls.profile.country="Test Country"
        cls.profile.language="fr"
        cls.profile.email_notifications=True
        cls.profile.sms_notifications=False
        cls.profile.save()

    def test_profile_creation_and_fields(self):
        """Tester la création et les champs d'un profil utilisateur."""
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.bio, "Test bio")
        self.assertEqual(profile.phone_number, "+33612345678")
        self.assertEqual(profile.address, "123 Test St")
        self.assertEqual(profile.city, "Test City")
        self.assertEqual(profile.postal_code, "12345")
        self.assertEqual(profile.country, "Test Country")
        self.assertEqual(profile.language, "fr")
        self.assertTrue(profile.email_notifications)
        self.assertFalse(profile.sms_notifications)
    
    def test_profile_str_method(self):
        """Tester la méthode __str__ du modèle UserProfile."""
        self.assertEqual(str(self.profile), f"Profile de {self.user.username}")

    def test_user_profile_relationship(self):
        """Test la relation entre l'utilisateur et son profil"""
        self.assertEqual(self.user.account_profile, self.profile)
        # Selon votre logique, le profil affilié pourrait aussi être testé ici
        # self.assertIsNotNone(self.user.affiliate_profile)

    def test_profile_default_values_on_user_creation(self):
        """Tester les valeurs par défaut du profil lors de la création de l'utilisateur."""
        new_user = User.objects.create_user(username="newdefaultuser", email="newdefault@example.com", password="newpassword")
        # UserProfile est créé par un signal lors de la création de User
        try:
            new_profile = UserProfile.objects.get(user=new_user)
            # Vérifiez ici les valeurs par défaut attendues pour un nouveau profil
            # Par exemple, si la langue par défaut est 'en':
            self.assertEqual(new_profile.language, UserProfile.LanguageChoices.ENGLISH)
            self.assertFalse(new_profile.email_notifications) # Si False est le défaut
            self.assertEqual(new_profile.bio, "") # Si bio vide est le défaut
        except UserProfile.DoesNotExist:
            self.fail("UserProfile not created automatically for new_user via signal") 