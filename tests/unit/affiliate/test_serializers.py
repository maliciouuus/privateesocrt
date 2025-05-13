from django.test import TestCase
from decimal import Decimal
from apps.accounts.models import User
from apps.affiliate.models import (
    ReferralClick,
    Referral,
    Commission,
    CommissionRate,
    Transaction,
    WhiteLabel,
    Banner,
)
from apps.affiliate.serializers import (
    UserSerializer,
    ReferralClickSerializer,
    ReferralSerializer,
    CommissionSerializer,
    CommissionRateSerializer,
    TransactionSerializer,
    WhiteLabelSerializer,
    BannerSerializer,
    AmbassadorStatsSerializer,
    WhiteLabelStatsSerializer,
)


class SerializerTestCase(TestCase):
    def setUp(self):
        # Créer les utilisateurs de test
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@test.com",
            password="testpass123",
            user_type="ambassador",
        )
        self.escort = User.objects.create_user(
            username="escort",
            email="escort@test.com",
            password="testpass123",
            user_type="escort",
        )

        # Créer les objets de test
        self.referral = Referral.objects.create(
            referrer=self.ambassador, referred=self.escort, referral_code="TEST123"
        )

        self.commission = Commission.objects.create(
            user=self.ambassador,
            referral=self.referral,
            amount=Decimal("100.00"),
            status="pending",
        )

        self.commission_rate = CommissionRate.objects.create(
            ambassador=self.ambassador, target_type="escort", rate=Decimal("0.10")
        )

        self.transaction = Transaction.objects.create(
            escort=self.escort,
            amount=Decimal("1000.00"),
            status="completed",
            payment_method="crypto",
            payment_id="BTC123",
        )

        self.white_label = WhiteLabel.objects.create(
            ambassador=self.ambassador,
            name="Test Site",
            domain="test.com",
            primary_color="#FF0000",
            secondary_color="#00FF00",
            is_active=True,
        )

        self.banner = Banner.objects.create(
            white_label=self.white_label,
            title="Test Banner",
            link="https://test.com",
            is_active=True,
        )

    def test_user_serializer(self):
        """Test du sérialiseur d'utilisateur"""
        serializer = UserSerializer(self.ambassador)
        data = serializer.data

        self.assertEqual(data["username"], "ambassador")
        self.assertEqual(data["email"], "ambassador@test.com")
        self.assertTrue(data["is_ambassador"])
        self.assertFalse(data["is_escort"])

    def test_referral_click_serializer(self):
        """Test du sérialiseur de clic de parrainage"""
        click = ReferralClick.objects.create(
            user=self.ambassador,
            referral_code="TEST123",
            ip_address="127.0.0.1",
            user_agent="Test Browser",
        )

        serializer = ReferralClickSerializer(click)
        data = serializer.data

        self.assertEqual(data["referral_code"], "TEST123")
        self.assertEqual(data["ip_address"], "127.0.0.1")
        self.assertEqual(data["user_agent"], "Test Browser")
        self.assertIn("user", data)

    def test_referral_serializer(self):
        """Test du sérialiseur de parrainage"""
        serializer = ReferralSerializer(self.referral)
        data = serializer.data

        self.assertEqual(data["referral_code"], "TEST123")
        self.assertIn("referrer", data)
        self.assertIn("referred", data)

    def test_commission_serializer(self):
        """Test du sérialiseur de commission"""
        serializer = CommissionSerializer(self.commission)
        data = serializer.data

        self.assertEqual(data["amount"], "100.00")
        self.assertEqual(data["status"], "pending")
        self.assertIn("user", data)
        self.assertIn("referral", data)

    def test_commission_rate_serializer(self):
        """Test du sérialiseur de taux de commission"""
        serializer = CommissionRateSerializer(self.commission_rate)
        data = serializer.data

        self.assertEqual(data["target_type"], "escort")
        self.assertEqual(data["rate"], "0.10")
        self.assertIn("ambassador", data)

    def test_transaction_serializer(self):
        """Test du sérialiseur de transaction"""
        serializer = TransactionSerializer(self.transaction)
        data = serializer.data

        self.assertEqual(data["amount"], "1000.00")
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["payment_method"], "crypto")
        self.assertEqual(data["payment_id"], "BTC123")
        self.assertIn("escort", data)

    def test_white_label_serializer(self):
        """Test du sérialiseur de site white label"""
        serializer = WhiteLabelSerializer(self.white_label)
        data = serializer.data

        self.assertEqual(data["name"], "Test Site")
        self.assertEqual(data["domain"], "test.com")
        self.assertEqual(data["primary_color"], "#FF0000")
        self.assertEqual(data["secondary_color"], "#00FF00")
        self.assertTrue(data["is_active"])
        self.assertIn("ambassador", data)

    def test_banner_serializer(self):
        """Test du sérialiseur de bannière"""
        serializer = BannerSerializer(self.banner)
        data = serializer.data

        self.assertEqual(data["title"], "Test Banner")
        self.assertEqual(data["link"], "https://test.com")
        self.assertTrue(data["is_active"])
        self.assertIn("white_label", data)

    def test_ambassador_stats_serializer(self):
        """Test du sérialiseur de statistiques d'ambassadeur"""
        stats = {
            "total_referrals": 10,
            "total_commissions": Decimal("1000.00"),
            "pending_commissions": Decimal("500.00"),
            "total_payouts": Decimal("500.00"),
            "conversion_rate": 25.5,
        }

        serializer = AmbassadorStatsSerializer(stats)
        data = serializer.data

        self.assertEqual(data["total_referrals"], 10)
        self.assertEqual(data["total_commissions"], "1000.00")
        self.assertEqual(data["pending_commissions"], "500.00")
        self.assertEqual(data["total_payouts"], "500.00")
        self.assertEqual(data["conversion_rate"], 25.5)

    def test_white_label_stats_serializer(self):
        """Test du sérialiseur de statistiques de site white label"""
        stats = {
            "total_clicks": 100,
            "total_conversions": 25,
            "conversion_rate": 25.0,
            "total_commissions": Decimal("2500.00"),
        }

        serializer = WhiteLabelStatsSerializer(stats)
        data = serializer.data

        self.assertEqual(data["total_clicks"], 100)
        self.assertEqual(data["total_conversions"], 25)
        self.assertEqual(data["conversion_rate"], 25.0)
        self.assertEqual(data["total_commissions"], "2500.00")
