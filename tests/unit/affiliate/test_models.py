import uuid
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from apps.affiliate.models import (
    ReferralClick,
    Referral,
    Commission,
    CommissionRate,
    Transaction,
    Payout,
    WhiteLabel,
    Banner,
    AffiliateProfile,
    AffiliateLevel,
    Badge,
    MarketingMaterial,
    PaymentMethod,
)

User = get_user_model()


class ReferralClickModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
        )
        self.referral_click = ReferralClick.objects.create(
            user=self.user,
            referral_code="TEST123",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0 Test Browser",
        )

    def test_referral_click_creation(self):
        self.assertEqual(self.referral_click.user, self.user)
        self.assertEqual(self.referral_click.referral_code, "TEST123")
        self.assertEqual(self.referral_click.ip_address, "127.0.0.1")
        self.assertEqual(self.referral_click.user_agent, "Mozilla/5.0 Test Browser")
        self.assertIsNotNone(self.referral_click.clicked_at)
        self.assertIn(f"Click from {self.user.username}", str(self.referral_click))


class ReferralModelTest(TestCase):
    def setUp(self):
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@example.com",
            password="password123",
            user_type="ambassador",
        )
        self.escort = User.objects.create_user(
            username="escort",
            email="escort@example.com",
            password="password123",
            user_type="escort",
        )

    def test_referral_creation(self):
        referral = Referral.objects.create(
            referrer=self.ambassador, referred=self.escort, referral_code="TEST123"
        )
        self.assertEqual(referral.referrer, self.ambassador)
        self.assertEqual(referral.referred, self.escort)
        self.assertEqual(referral.referral_code, "TEST123")
        self.assertIsNotNone(referral.created_at)
        self.assertEqual(
            str(referral), f"{self.ambassador.username} referred {self.escort.username}"
        )

    @patch("apps.affiliate.models.TelegramService")
    def test_save_method_telegram_notification(self, mock_telegram_service):
        mock_instance = MagicMock()
        mock_telegram_service.return_value = mock_instance
        Referral.objects.create(
            referrer=self.ambassador, referred=self.escort, referral_code="TEST123"
        )
        mock_instance.notify_new_referral.assert_called_once_with(self.ambassador, self.escort)


class CommissionModelTest(TestCase):
    def setUp(self):
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@example.com",
            password="password123",
            user_type="ambassador",
        )
        self.escort = User.objects.create_user(
            username="escort",
            email="escort@example.com",
            password="password123",
            user_type="escort",
        )
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.com", password="password123", is_staff=True
        )
        self.referral = Referral.objects.create(
            referrer=self.ambassador, referred=self.escort, referral_code="TEST123"
        )

    def test_commission_creation(self):
        """Test la création d'une commission"""
        commission = Commission.objects.create(
            user=self.ambassador,
            referral=self.referral,
            amount=Decimal("100.00"),
            gross_amount=Decimal("1000.00"),
            rate_applied=Decimal("10.00"),
            status="pending",
        )
        self.assertEqual(commission.user, self.ambassador)
        self.assertEqual(commission.referral, self.referral)
        self.assertEqual(commission.amount, Decimal("100.00"))
        self.assertEqual(commission.gross_amount, Decimal("1000.00"))
        self.assertEqual(commission.rate_applied, Decimal("10.00"))
        self.assertEqual(commission.status, "pending")
        self.assertIsNotNone(commission.created_at)

    def test_mark_as_approved(self):
        """Test la méthode mark_as_approved"""
        commission = Commission.objects.create(
            user=self.ambassador,
            referral=self.referral,
            amount=Decimal("100.00"),
            gross_amount=Decimal("1000.00"),
            status="pending",
        )

        commission.mark_as_approved(admin_user=self.admin)

        self.assertEqual(commission.status, "approved")
        self.assertIsNotNone(commission.approved_at)
        self.assertEqual(commission.updated_by, self.admin)

    def test_mark_as_rejected(self):
        """Test la méthode mark_as_rejected"""
        commission = Commission.objects.create(
            user=self.ambassador,
            referral=self.referral,
            amount=Decimal("100.00"),
            gross_amount=Decimal("1000.00"),
            status="pending",
        )

        commission.mark_as_rejected(admin_user=self.admin, reason="Test rejection")

        self.assertEqual(commission.status, "rejected")
        self.assertEqual(commission.rejection_reason, "Test rejection")
        self.assertEqual(commission.updated_by, self.admin)

    def test_mark_as_paid(self):
        """Test la méthode mark_as_paid"""
        commission = Commission.objects.create(
            user=self.ambassador,
            referral=self.referral,
            amount=Decimal("100.00"),
            gross_amount=Decimal("1000.00"),
            status="approved",
        )

        payout = Payout.objects.create(
            ambassador=self.ambassador,
            amount=Decimal("100.00"),
            payment_method="btc",
            wallet_address="test_wallet",
            status="completed",
        )

        commission.mark_as_paid(admin_user=self.admin, payout=payout)

        self.assertEqual(commission.status, "paid")
        self.assertIsNotNone(commission.paid_at)
        self.assertEqual(commission.updated_by, self.admin)

    def test_calculate_commission_amount(self):
        """Test la méthode de calcul du montant de commission"""
        # Test pour un utilisateur 'escort'
        amount = Commission.calculate_commission_amount(
            gross_amount=Decimal("1000.00"), user_type="escort", referrer=self.ambassador
        )
        self.assertEqual(amount, Decimal("300.00"))  # Taux par défaut de 30%

        # Test pour un utilisateur 'ambassador'
        amount = Commission.calculate_commission_amount(
            gross_amount=Decimal("1000.00"), user_type="ambassador", referrer=self.ambassador
        )
        self.assertEqual(amount, Decimal("100.00"))  # Taux par défaut de 10%

        # Test avec un taux personnalisé
        CommissionRate.objects.create(
            ambassador=self.ambassador, target_type="escort", rate=Decimal("40.00")
        )

        amount = Commission.calculate_commission_amount(
            gross_amount=Decimal("1000.00"), user_type="escort", referrer=self.ambassador
        )
        self.assertEqual(amount, Decimal("400.00"))  # Taux personnalisé de 40%


class CommissionRateModelTest(TestCase):
    def setUp(self):
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@example.com",
            password="password123",
            user_type="ambassador",
        )

    def test_commission_rate_creation(self):
        """Test la création d'un taux de commission"""
        rate = CommissionRate.objects.create(
            ambassador=self.ambassador, target_type="escort", rate=Decimal("35.00")
        )
        self.assertEqual(rate.ambassador, self.ambassador)
        self.assertEqual(rate.target_type, "escort")
        self.assertEqual(rate.rate, Decimal("35.00"))
        self.assertIsNotNone(rate.created_at)
        self.assertIn(self.ambassador.username, str(rate))
        self.assertIn("35.00%", str(rate))
        self.assertIn("escort", str(rate))


class TransactionModelTest(TestCase):
    def setUp(self):
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@example.com",
            password="password123",
            user_type="ambassador",
        )
        self.escort = User.objects.create_user(
            username="escort",
            email="escort@example.com",
            password="password123",
            user_type="escort",
        )
        self.referral = Referral.objects.create(
            referrer=self.ambassador, referred=self.escort, referral_code="TEST123"
        )

    def test_transaction_creation(self):
        """Test la création d'une transaction"""
        transaction = Transaction.objects.create(
            escort=self.escort,
            amount=Decimal("1000.00"),
            status="completed",
            payment_method="crypto",
            payment_id=str(uuid.uuid4()),
        )
        self.assertEqual(transaction.escort, self.escort)
        self.assertEqual(transaction.amount, Decimal("1000.00"))
        self.assertEqual(transaction.status, "completed")
        self.assertEqual(transaction.payment_method, "crypto")
        self.assertIsNotNone(transaction.payment_id)
        self.assertIsNotNone(transaction.created_at)
        self.assertIn(str(transaction.amount), str(transaction))

    @patch("apps.affiliate.models.Commission.objects.create")
    def test_create_commissions(self, mock_create_commission):
        """Test la création de commissions à partir d'une transaction"""
        # Configure le mock pour retourner un objet Commission
        mock_commission = MagicMock()
        mock_create_commission.return_value = mock_commission

        # Créer une transaction pour l'escort parrainé
        Transaction.objects.create(
            escort=self.escort,
            amount=Decimal("1000.00"),
            status="completed",
            payment_method="crypto",
            payment_id=str(uuid.uuid4()),
        )

        # Vérifier que la méthode create a été appelée pour créer une commission
        mock_create_commission.assert_called_once()
        # Vérifier les arguments passés à la méthode create
        args, kwargs = mock_create_commission.call_args
        self.assertEqual(kwargs["user"], self.ambassador)
        self.assertEqual(kwargs["referral"], self.referral)
        self.assertEqual(kwargs["gross_amount"], Decimal("1000.00"))


class PayoutModelTest(TestCase):
    def setUp(self):
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@example.com",
            password="password123",
            user_type="ambassador",
        )
        self.escort = User.objects.create_user(
            username="escort",
            email="escort@example.com",
            password="password123",
            user_type="escort",
        )
        self.referral = Referral.objects.create(
            referrer=self.ambassador, referred=self.escort, referral_code="TEST123"
        )
        self.commission = Commission.objects.create(
            user=self.ambassador,
            referral=self.referral,
            amount=Decimal("100.00"),
            gross_amount=Decimal("1000.00"),
            status="approved",
        )

    def test_payout_creation(self):
        """Test la création d'un paiement"""
        payout = Payout.objects.create(
            ambassador=self.ambassador,
            amount=Decimal("100.00"),
            payment_method="btc",
            wallet_address="test_wallet",
            status="pending",
        )
        self.assertEqual(payout.ambassador, self.ambassador)
        self.assertEqual(payout.amount, Decimal("100.00"))
        self.assertEqual(payout.payment_method, "btc")
        self.assertEqual(payout.wallet_address, "test_wallet")
        self.assertEqual(payout.status, "pending")
        self.assertIsNotNone(payout.created_at)
        self.assertIn(str(payout.amount), str(payout))
        self.assertIn(self.ambassador.username, str(payout))

    def test_create_from_commissions(self):
        """Test la création d'un paiement à partir de commissions"""
        commissions = Commission.objects.filter(id=self.commission.id)

        payout = Payout.create_from_commissions(
            ambassador=self.ambassador, commissions=commissions, payment_method="btc"
        )

        self.assertEqual(payout.ambassador, self.ambassador)
        self.assertEqual(payout.amount, Decimal("100.00"))
        self.assertEqual(payout.payment_method, "btc")
        self.assertEqual(payout.status, "pending")
        self.assertEqual(payout.commissions.count(), 1)
        self.assertEqual(payout.commissions.first(), self.commission)

    def test_mark_as_completed(self):
        """Test la méthode mark_as_completed"""
        payout = Payout.objects.create(
            ambassador=self.ambassador,
            amount=Decimal("100.00"),
            payment_method="btc",
            wallet_address="test_wallet",
            status="processing",
        )
        payout.commissions.add(self.commission)

        transaction_id = "tx_12345"
        payout.mark_as_completed(transaction_id)

        self.assertEqual(payout.status, "completed")
        self.assertEqual(payout.transaction_id, transaction_id)
        self.assertIsNotNone(payout.completed_at)

    def test_mark_as_failed(self):
        """Test la méthode mark_as_failed"""
        payout = Payout.objects.create(
            ambassador=self.ambassador,
            amount=Decimal("100.00"),
            payment_method="btc",
            wallet_address="test_wallet",
            status="processing",
        )

        payout.mark_as_failed()

        self.assertEqual(payout.status, "failed")

    def test_get_payment_method_icon(self):
        """Test la méthode get_payment_method_icon"""
        payout = Payout.objects.create(
            ambassador=self.ambassador,
            amount=Decimal("100.00"),
            payment_method="btc",
            wallet_address="test_wallet",
            status="pending",
        )

        icon = payout.get_payment_method_icon()
        self.assertEqual(icon, "fa-brands fa-bitcoin")

        payout.payment_method = "eth"
        payout.save()
        icon = payout.get_payment_method_icon()
        self.assertEqual(icon, "fa-brands fa-ethereum")

        payout.payment_method = "usdt"
        payout.save()
        icon = payout.get_payment_method_icon()
        self.assertEqual(icon, "fa-solid fa-dollar-sign")

    def test_get_status_class(self):
        """Test la méthode get_status_class"""
        payout = Payout.objects.create(
            ambassador=self.ambassador,
            amount=Decimal("100.00"),
            payment_method="btc",
            wallet_address="test_wallet",
            status="pending",
        )

        status_class = payout.get_status_class()
        self.assertEqual(status_class, "text-warning")

        payout.status = "processing"
        payout.save()
        status_class = payout.get_status_class()
        self.assertEqual(status_class, "text-info")

        payout.status = "completed"
        payout.save()
        status_class = payout.get_status_class()
        self.assertEqual(status_class, "text-success")

        payout.status = "failed"
        payout.save()
        status_class = payout.get_status_class()
        self.assertEqual(status_class, "text-danger")


class WhiteLabelModelTest(TestCase):
    def setUp(self):
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@example.com",
            password="password123",
            user_type="ambassador",
        )

    def test_white_label_creation(self):
        """Test la création d'un site white label"""
        white_label = WhiteLabel.objects.create(
            ambassador=self.ambassador,
            name="Test Site",
            domain="test.com",
            primary_color="#FF0000",
            secondary_color="#00FF00",
            is_active=True,
        )
        self.assertEqual(white_label.ambassador, self.ambassador)
        self.assertEqual(white_label.name, "Test Site")
        self.assertEqual(white_label.domain, "test.com")
        self.assertEqual(white_label.primary_color, "#FF0000")
        self.assertEqual(white_label.secondary_color, "#00FF00")
        self.assertTrue(white_label.is_active)
        self.assertFalse(white_label.dns_verified)
        self.assertIsNotNone(white_label.created_at)
        self.assertEqual(str(white_label), f"{white_label.name} ({white_label.domain})")

    def test_generate_dns_verification(self):
        """Test la génération du code de vérification DNS"""
        white_label = WhiteLabel.objects.create(
            ambassador=self.ambassador,
            name="Test Site",
            domain="test.com",
            custom_domain="custom.test.com",
            is_active=True,
        )
        # Vérifier que le code DNS est généré lors de la création
        self.assertIsNotNone(white_label.dns_verification_code)
        self.assertTrue(len(white_label.dns_verification_code) > 0)

    @patch("apps.affiliate.models.dns.resolver.resolve")
    def test_verify_dns(self, mock_resolve):
        """Test la vérification DNS"""
        # Configurer le mock pour simuler une réponse DNS réussie
        mock_txt_record = MagicMock()
        mock_txt_record.strings = [b"privateescort-verify=123456"]
        mock_resolve.return_value = [mock_txt_record]

        white_label = WhiteLabel.objects.create(
            ambassador=self.ambassador,
            name="Test Site",
            domain="test.com",
            custom_domain="custom.test.com",
            dns_verification_code="123456",
            is_active=True,
        )

        # Vérifier que la méthode vérifie correctement le DNS
        result = white_label.verify_dns()

        self.assertTrue(result)
        self.assertTrue(white_label.dns_verified)
        mock_resolve.assert_called_with("custom.test.com", "TXT")

    def test_get_dns_instructions(self):
        """Test l'obtention des instructions DNS"""
        white_label = WhiteLabel.objects.create(
            ambassador=self.ambassador,
            name="Test Site",
            domain="test.com",
            custom_domain="custom.test.com",
            dns_verification_code="123456",
            is_active=True,
        )

        instructions = white_label.get_dns_instructions()

        self.assertIn("privateescort-verify=123456", instructions)
        self.assertIn("custom.test.com", instructions)

    def test_get_absolute_url(self):
        """Test l'obtention de l'URL absolue"""
        white_label = WhiteLabel.objects.create(
            ambassador=self.ambassador, name="Test Site", domain="test.com", is_active=True
        )

        url = white_label.get_absolute_url()

        self.assertEqual(url, f"https://{white_label.domain}")


class BannerModelTest(TestCase):
    def setUp(self):
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@example.com",
            password="password123",
            user_type="ambassador",
        )
        self.white_label = WhiteLabel.objects.create(
            ambassador=self.ambassador, name="Test Site", domain="test.com", is_active=True
        )

    def test_banner_creation(self):
        """Test la création d'une bannière"""
        banner = Banner.objects.create(
            white_label=self.white_label,
            title="Test Banner",
            type="personal",
            link="https://example.com",
            is_active=True,
        )
        self.assertEqual(banner.white_label, self.white_label)
        self.assertEqual(banner.title, "Test Banner")
        self.assertEqual(banner.type, "personal")
        self.assertEqual(banner.link, "https://example.com")
        self.assertTrue(banner.is_active)
        self.assertEqual(banner.views_count, 0)
        self.assertEqual(banner.clicks_count, 0)
        self.assertIsNotNone(banner.created_at)
        self.assertEqual(str(banner), f"{banner.title} - {banner.white_label.name}")

    def test_track_view_click(self):
        """Test les méthodes track_view et track_click"""
        banner = Banner.objects.create(
            white_label=self.white_label, title="Test Banner", type="personal", is_active=True
        )

        # Test track_view
        initial_views = banner.views_count
        banner.track_view()
        banner.refresh_from_db()
        self.assertEqual(banner.views_count, initial_views + 1)

        # Test track_click
        initial_clicks = banner.clicks_count
        banner.track_click()
        banner.refresh_from_db()
        self.assertEqual(banner.clicks_count, initial_clicks + 1)

        # Test click_through_rate
        banner.views_count = 100
        banner.clicks_count = 25
        banner.save()
        self.assertEqual(banner.click_through_rate, 25.0)  # 25 / 100 * 100

    def test_clean_method_too_many_personal_banners(self):
        """Test la validation du nombre de bannières personnelles"""
        # Créer 3 bannières personnelles (maximum autorisé)
        for i in range(3):
            Banner.objects.create(
                white_label=self.white_label,
                title=f"Test Banner {i}",
                type="personal",
                is_active=True,
            )

        # Tenter de créer une 4e bannière personnelle (doit échouer)
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            banner = Banner(
                white_label=self.white_label, title="Test Banner 4", type="personal", is_active=True
            )
            banner.clean()  # Doit lever une ValidationError


class AffiliateLevelTest(TestCase):
    def setUp(self):
        # Créer des niveaux d'affiliation
        self.bronze = AffiliateLevel.objects.create(
            name="bronze",
            min_earnings=Decimal("0.00"),
            min_referrals=0,
            min_conversion_rate=Decimal("0.00"),
            commission_bonus=Decimal("0.00"),
        )
        self.silver = AffiliateLevel.objects.create(
            name="silver",
            min_earnings=Decimal("1000.00"),
            min_referrals=5,
            min_conversion_rate=Decimal("10.00"),
            commission_bonus=Decimal("5.00"),
        )
        self.gold = AffiliateLevel.objects.create(
            name="gold",
            min_earnings=Decimal("5000.00"),
            min_referrals=25,
            min_conversion_rate=Decimal("20.00"),
            commission_bonus=Decimal("10.00"),
        )

    def test_affiliate_level_creation(self):
        """Test la création d'un niveau d'affiliation"""
        level = self.silver
        self.assertEqual(level.name, "silver")
        self.assertEqual(level.min_earnings, Decimal("1000.00"))
        self.assertEqual(level.min_referrals, 5)
        self.assertEqual(level.min_conversion_rate, Decimal("10.00"))
        self.assertEqual(level.commission_bonus, Decimal("5.00"))
        self.assertIsNotNone(level.created_at)
        self.assertIn("Argent", str(level))

    def test_get_next_level(self):
        """Test la méthode get_next_level"""
        # Bronze devrait avoir Silver comme niveau suivant
        next_level = self.bronze.get_next_level()
        self.assertEqual(next_level, self.silver)

        # Silver devrait avoir Gold comme niveau suivant
        next_level = self.silver.get_next_level()
        self.assertEqual(next_level, self.gold)

        # Gold devrait retourner None comme niveau suivant (c'est le plus haut)
        next_level = self.gold.get_next_level()
        self.assertIsNone(next_level)

    def test_get_previous_level(self):
        """Test la méthode get_previous_level"""
        # Gold devrait avoir Silver comme niveau précédent
        prev_level = self.gold.get_previous_level()
        self.assertEqual(prev_level, self.silver)

        # Silver devrait avoir Bronze comme niveau précédent
        prev_level = self.silver.get_previous_level()
        self.assertEqual(prev_level, self.bronze)

        # Bronze devrait retourner None comme niveau précédent (c'est le plus bas)
        prev_level = self.bronze.get_previous_level()
        self.assertIsNone(prev_level)

    def test_calculate_progress(self):
        """Test le calcul de la progression vers le niveau suivant"""
        profile = MagicMock()
        profile.total_earnings = Decimal("500.00")
        profile.total_referrals = 2
        profile.conversion_rate = Decimal("5.00")

        # Calculer la progression de Bronze vers Silver
        progress = self.bronze.calculate_progress(profile)

        # Vérifier les résultats
        self.assertEqual(progress["earnings"]["current"], Decimal("500.00"))
        self.assertEqual(progress["earnings"]["target"], Decimal("1000.00"))
        self.assertEqual(progress["earnings"]["percentage"], 50)

        self.assertEqual(progress["referrals"]["current"], 2)
        self.assertEqual(progress["referrals"]["target"], 5)
        self.assertEqual(progress["referrals"]["percentage"], 40)

        self.assertEqual(progress["conversion"]["current"], Decimal("5.00"))
        self.assertEqual(progress["conversion"]["target"], Decimal("10.00"))
        self.assertEqual(progress["conversion"]["percentage"], 50)

        # La progression globale est la moyenne des trois pourcentages : (50 + 40 + 50) / 3 = 46.67
        self.assertAlmostEqual(progress["overall"], 46.67, places=2)


class AffiliateProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        self.bronze = AffiliateLevel.objects.create(
            name="bronze",
            min_earnings=Decimal("0.00"),
            min_referrals=0,
            min_conversion_rate=Decimal("0.00"),
            commission_bonus=Decimal("0.00"),
        )
        self.silver = AffiliateLevel.objects.create(
            name="silver",
            min_earnings=Decimal("1000.00"),
            min_referrals=5,
            min_conversion_rate=Decimal("10.00"),
            commission_bonus=Decimal("5.00"),
        )
        self.profile = AffiliateProfile.objects.get(user=self.user)
        self.profile.level = self.bronze
        self.profile.save()

    def test_affiliate_profile_creation(self):
        """Test la création automatique du profil d'affiliation"""
        self.assertIsNotNone(self.profile)
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.level, self.bronze)
        self.assertEqual(self.profile.points, 0)
        self.assertEqual(self.profile.total_earnings, Decimal("0.00"))
        self.assertEqual(self.profile.total_referrals, 0)
        self.assertEqual(self.profile.conversion_rate, Decimal("0.00"))
        self.assertIsNotNone(self.profile.created_at)
        self.assertIn(self.user.username, str(self.profile))

    def test_update_level(self):
        """Test la mise à jour du niveau d'affiliation"""
        # Mettre à jour les statistiques pour atteindre le niveau Silver
        self.profile.total_earnings = Decimal("1500.00")
        self.profile.total_referrals = 10
        self.profile.conversion_rate = Decimal("15.00")
        self.profile.save()

        # Appeler la méthode qui met à jour le niveau
        self.profile.update_level()

        # Vérifier que le niveau a été mis à jour à Silver
        self.assertEqual(self.profile.level, self.silver)

    def test_get_level_progress(self):
        """Test l'obtention de la progression vers le niveau suivant"""
        # Configurer le profil pour être à mi-chemin vers Silver
        self.profile.total_earnings = Decimal("500.00")
        self.profile.total_referrals = 2
        self.profile.conversion_rate = Decimal("5.00")
        self.profile.save()

        # Obtenir la progression
        progress = self.profile.get_level_progress()

        # Vérifier les résultats
        self.assertEqual(progress["next_level"], self.silver)
        self.assertEqual(progress["earnings"]["current"], Decimal("500.00"))
        self.assertEqual(progress["earnings"]["target"], Decimal("1000.00"))
        self.assertEqual(progress["earnings"]["percentage"], 50)
        self.assertAlmostEqual(progress["overall"], 46.67, places=2)


class BadgeModelTest(TestCase):
    def setUp(self):
        self.badge = Badge.objects.create(
            name="Super Référent",
            description="Obtenu en parrainant 10 personnes",
            category="referral",
            icon="fa-users",
            points_value=50,
            requirements={"min_referrals": 10},
        )

    def test_badge_creation(self):
        """Test la création d'un badge"""
        self.assertEqual(self.badge.name, "Super Référent")
        self.assertEqual(self.badge.description, "Obtenu en parrainant 10 personnes")
        self.assertEqual(self.badge.category, "referral")
        self.assertEqual(self.badge.icon, "fa-users")
        self.assertEqual(self.badge.points_value, 50)
        self.assertEqual(self.badge.requirements, {"min_referrals": 10})
        self.assertIsNotNone(self.badge.created_at)
        self.assertEqual(str(self.badge), "Super Référent")


class MarketingMaterialTest(TestCase):
    def setUp(self):
        self.material = MarketingMaterial.objects.create(
            title="Guide de l'Affiliation",
            description="Un guide complet pour les ambassadeurs",
            file_type="pdf",
        )

    def test_marketing_material_creation(self):
        """Test la création d'un matériel marketing"""
        self.assertEqual(self.material.title, "Guide de l'Affiliation")
        self.assertEqual(self.material.description, "Un guide complet pour les ambassadeurs")
        self.assertEqual(self.material.file_type, "pdf")
        self.assertTrue(self.material.is_active)
        self.assertEqual(self.material.download_count, 0)
        self.assertIsNotNone(self.material.created_at)
        self.assertEqual(str(self.material), "Guide de l'Affiliation")


class PaymentMethodTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password123"
        )
        self.payment_method = PaymentMethod.objects.create(
            user=self.user,
            payment_type="crypto",
            account_name="Bitcoin Wallet",
            account_details={"wallet_address": "bc1q..."},
            is_default=True,
        )

    def test_payment_method_creation(self):
        """Test la création d'une méthode de paiement"""
        self.assertEqual(self.payment_method.user, self.user)
        self.assertEqual(self.payment_method.payment_type, "crypto")
        self.assertEqual(self.payment_method.account_name, "Bitcoin Wallet")
        self.assertEqual(self.payment_method.account_details, {"wallet_address": "bc1q..."})
        self.assertTrue(self.payment_method.is_default)
        self.assertTrue(self.payment_method.is_active)
        self.assertIsNotNone(self.payment_method.created_at)
        self.assertIn("Bitcoin Wallet", str(self.payment_method))
        self.assertIn("crypto", str(self.payment_method))
