from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, UserProfile
from .models import ReferralClick, Referral, Commission
from decimal import Decimal
import datetime


class AffiliateTests(TestCase):
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
        # Créer un utilisateur parrainé
        self.referred_user = User.objects.create_user(
            username="referred", email="referred@example.com", password="testpass123"
        )
        self.referred_profile = UserProfile.objects.create(
            user=self.referred_user, user_type="member"
        )

    def test_affiliate_dashboard(self):
        """Test l'accès au tableau de bord d'affiliation"""
        self.client.login(username="ambassador", password="testpass123")
        response = self.client.get(reverse("affiliate:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "affiliate/dashboard.html")

    def test_referral_link_generation(self):
        """Test la génération de lien de parrainage"""
        self.client.login(username="ambassador", password="testpass123")
        response = self.client.get(reverse("affiliate:referral_links"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "affiliate/referral_links.html")
        self.assertContains(response, "TEST123")

    def test_referral_click_tracking(self):
        """Test le suivi des clics sur les liens de parrainage"""
        response = self.client.get(
            reverse("affiliate:track_click", args=["TEST123"]),
            HTTP_REFERER="https://example.com",
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ReferralClick.objects.filter(
                referral_code="TEST123", source="https://example.com"
            ).exists()
        )

    def test_referral_registration(self):
        """Test l'enregistrement d'un parrainage"""
        # Simuler un clic
        click = ReferralClick.objects.create(
            referral_code="TEST123",
            source="https://example.com",
            ip_address="127.0.0.1",
        )
        # Créer le parrainage
        referral = Referral.objects.create(
            referrer=self.ambassador, referred_user=self.referred_user, click=click
        )
        self.assertEqual(referral.referrer, self.ambassador)
        self.assertEqual(referral.referred_user, self.referred_user)


class CommissionTests(TestCase):
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
        # Créer quelques commissions
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

    def test_commission_list(self):
        """Test l'affichage de la liste des commissions"""
        self.client.login(username="ambassador", password="testpass123")
        response = self.client.get(reverse("affiliate:commission_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "affiliate/commission_list.html")
        self.assertContains(response, "100.00")
        self.assertContains(response, "50.00")

    def test_commission_stats(self):
        """Test les statistiques des commissions"""
        self.client.login(username="ambassador", password="testpass123")
        response = self.client.get(reverse("affiliate:commission_stats"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "affiliate/commission_stats.html")
        # Vérifier que les montants sont corrects
        self.assertContains(response, "150.00")  # Total des commissions

    def test_commission_withdrawal(self):
        """Test la demande de retrait de commission"""
        self.client.login(username="ambassador", password="testpass123")
        response = self.client.post(
            reverse("affiliate:withdraw_commission"),
            {"amount": "100.00", "payment_method": "bank_transfer"},
        )
        self.assertEqual(response.status_code, 302)
        # Vérifier que la commission est marquée comme en attente de paiement
        self.commission1.refresh_from_db()
        self.assertEqual(self.commission1.status, "pending_payment")


class MarketingMaterialTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@example.com",
            password="testpass123",
        )
        self.ambassador_profile = UserProfile.objects.create(
            user=self.ambassador, user_type="ambassador"
        )

    def test_marketing_materials_list(self):
        """Test l'affichage des matériels marketing"""
        self.client.login(username="ambassador", password="testpass123")
        response = self.client.get(reverse("affiliate:marketing_materials"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "affiliate/marketing_materials.html")

    def test_marketing_material_download(self):
        """Test le téléchargement d'un matériel marketing"""
        self.client.login(username="ambassador", password="testpass123")
        # Créer un matériel marketing de test
        from .models import MarketingMaterial

        material = MarketingMaterial.objects.create(
            title="Test Material",
            description="Test Description",
            file_type="image",
            is_active=True,
        )
        response = self.client.get(reverse("affiliate:download_material", args=[material.id]))
        self.assertEqual(response.status_code, 200)
        # Vérifier que le compteur de téléchargements a été incrémenté
        material.refresh_from_db()
        self.assertEqual(material.download_count, 1)
