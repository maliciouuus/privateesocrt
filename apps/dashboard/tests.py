from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, UserProfile
from affiliate.models import ReferralClick, Referral, Commission
from decimal import Decimal
import datetime

# Create your tests here.


class DashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Créer un utilisateur
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.user_profile = UserProfile.objects.create(user=self.user, user_type="member")
        # Créer un ambassadeur
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@example.com",
            password="testpass123",
        )
        self.ambassador_profile = UserProfile.objects.create(
            user=self.ambassador, user_type="ambassador", referral_code="TEST123"
        )

    def test_dashboard_home(self):
        """Test l'accès à la page d'accueil du tableau de bord"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/home.html")

    def test_dashboard_stats(self):
        """Test l'accès aux statistiques"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("dashboard:stats"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/stats.html")

    def test_dashboard_settings(self):
        """Test l'accès aux paramètres"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("dashboard:settings"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/settings.html")


class NotificationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.user_profile = UserProfile.objects.create(user=self.user, user_type="member")

    def test_notifications_list(self):
        """Test l'affichage des notifications"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("dashboard:notifications"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/notifications.html")

    def test_mark_notification_read(self):
        """Test le marquage d'une notification comme lue"""
        self.client.login(username="testuser", password="testpass123")
        # Créer une notification de test
        from .models import Notification

        notification = Notification.objects.create(
            user=self.user,
            title="Test Notification",
            message="Test Message",
            is_read=False,
        )
        response = self.client.post(
            reverse("dashboard:mark_notification_read", args=[notification.id])
        )
        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)


class ReferralStatsTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Créer un ambassadeur
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@example.com",
            password="testpass123",
        )
        self.ambassador_profile = UserProfile.objects.create(
            user=self.ambassador, user_type="ambassador", referral_code="TEST123"
        )
        # Créer des clics et parrainages de test
        self.click = ReferralClick.objects.create(
            referral_code="TEST123",
            source="https://example.com",
            ip_address="127.0.0.1",
        )
        self.referred_user = User.objects.create_user(
            username="referred", email="referred@example.com", password="testpass123"
        )
        self.referral = Referral.objects.create(
            referrer=self.ambassador, referred_user=self.referred_user, click=self.click
        )

    def test_referral_stats(self):
        """Test les statistiques de parrainage"""
        self.client.login(username="ambassador", password="testpass123")
        response = self.client.get(reverse("dashboard:referral_stats"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/referral_stats.html")
        self.assertContains(response, "1")  # Nombre de parrainages

    def test_referral_list(self):
        """Test la liste des parrainages"""
        self.client.login(username="ambassador", password="testpass123")
        response = self.client.get(reverse("dashboard:referral_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/referral_list.html")
        self.assertContains(response, "referred")  # Nom d'utilisateur parrainé


class CommissionStatsTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Créer un ambassadeur
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@example.com",
            password="testpass123",
        )
        self.ambassador_profile = UserProfile.objects.create(
            user=self.ambassador, user_type="ambassador", referral_code="TEST123"
        )
        # Créer des commissions de test
        self.commission1 = Commission.objects.create(
            affiliate=self.ambassador,
            amount=Decimal("100.00"),
            status="pending",
            created_at=datetime.datetime.now(),
        )
        self.commission2 = Commission.objects.create(
            affiliate=self.ambassador,
            amount=Decimal("50.00"),
            status="paid",
            created_at=datetime.datetime.now(),
        )

    def test_commission_stats(self):
        """Test les statistiques de commission"""
        self.client.login(username="ambassador", password="testpass123")
        response = self.client.get(reverse("dashboard:commission_stats"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/commission_stats.html")
        self.assertContains(response, "150.00")  # Total des commissions

    def test_commission_list(self):
        """Test la liste des commissions"""
        self.client.login(username="ambassador", password="testpass123")
        response = self.client.get(reverse("dashboard:commission_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/commission_list.html")
        self.assertContains(response, "100.00")
        self.assertContains(response, "50.00")
