from django.test import TestCase
from decimal import Decimal
from unittest.mock import patch, MagicMock
from apps.accounts.models import User
from apps.affiliate.models import (
    Referral,
    Commission,
    Transaction,
    WhiteLabel,
)
from apps.affiliate.services.supabase_service import SupabaseService


class SupabaseServiceTestCase(TestCase):
    def setUp(self):
        # Créer les utilisateurs de test
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@test.com",
            password="testpass123",
            is_ambassador=True,
        )
        self.escort = User.objects.create_user(
            username="escort",
            email="escort@test.com",
            password="testpass123",
            is_escort=True,
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

        # Initialiser le service Supabase
        self.service = SupabaseService()

    @patch("supabase.Client")
    def test_sync_commission(self, mock_client):
        """Test de la synchronisation d'une commission"""
        # Configurer le mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.table.return_value.upsert.return_value = {"data": {"id": 1}}

        # Tester la synchronisation
        result = self.service.sync_commission(self.commission)

        # Vérifier les appels
        mock_instance.table.assert_called_with("commissions")
        mock_instance.table.return_value.upsert.assert_called_once()

        # Vérifier le résultat
        self.assertTrue(result)

    @patch("supabase.Client")
    def test_sync_transaction(self, mock_client):
        """Test de la synchronisation d'une transaction"""
        # Configurer le mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.table.return_value.upsert.return_value = {"data": {"id": 1}}

        # Tester la synchronisation
        result = self.service.sync_transaction(self.transaction)

        # Vérifier les appels
        mock_instance.table.assert_called_with("transactions")
        mock_instance.table.return_value.upsert.assert_called_once()

        # Vérifier le résultat
        self.assertTrue(result)

    @patch("supabase.Client")
    def test_sync_white_label(self, mock_client):
        """Test de la synchronisation d'un site white label"""
        # Configurer le mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.table.return_value.upsert.return_value = {"data": {"id": 1}}

        # Tester la synchronisation
        result = self.service.sync_white_label(self.white_label)

        # Vérifier les appels
        mock_instance.table.assert_called_with("white_labels")
        mock_instance.table.return_value.upsert.assert_called_once()

        # Vérifier le résultat
        self.assertTrue(result)

    @patch("supabase.Client")
    def test_get_ambassador_stats(self, mock_client):
        """Test de la récupération des statistiques d'un ambassadeur"""
        # Configurer le mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = {
            "data": {
                "total_referrals": 10,
                "total_commissions": "1000.00",
                "pending_commissions": "500.00",
                "total_payouts": "500.00",
                "conversion_rate": 25.5,
            }
        }

        # Tester la récupération des statistiques
        stats = self.service.get_ambassador_stats(str(self.ambassador.id))

        # Vérifier les appels
        mock_instance.table.assert_called_with("ambassador_stats")
        mock_instance.table.return_value.select.assert_called_once()

        # Vérifier le résultat
        self.assertIsNotNone(stats)
        self.assertEqual(stats["total_referrals"], 10)
        self.assertEqual(stats["total_commissions"], "1000.00")
        self.assertEqual(stats["pending_commissions"], "500.00")
        self.assertEqual(stats["total_payouts"], "500.00")
        self.assertEqual(stats["conversion_rate"], 25.5)

    @patch("supabase.Client")
    def test_get_white_label_stats(self, mock_client):
        """Test de la récupération des statistiques d'un site white label"""
        # Configurer le mock
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.table.return_value.select.return_value.eq.return_value.execute.return_value = {
            "data": {
                "total_clicks": 100,
                "total_conversions": 25,
                "conversion_rate": 25.0,
                "total_commissions": "2500.00",
            }
        }

        # Tester la récupération des statistiques
        stats = self.service.get_white_label_stats(str(self.white_label.id))

        # Vérifier les appels
        mock_instance.table.assert_called_with("white_label_stats")
        mock_instance.table.return_value.select.assert_called_once()

        # Vérifier le résultat
        self.assertIsNotNone(stats)
        self.assertEqual(stats["total_clicks"], 100)
        self.assertEqual(stats["total_conversions"], 25)
        self.assertEqual(stats["conversion_rate"], 25.0)
        self.assertEqual(stats["total_commissions"], "2500.00")

    @patch("supabase.Client")
    def test_error_handling(self, mock_client):
        """Test de la gestion des erreurs"""
        # Configurer le mock pour simuler une erreur
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.table.return_value.upsert.side_effect = Exception("Test error")

        # Tester la synchronisation avec erreur
        result = self.service.sync_commission(self.commission)

        # Vérifier que la fonction retourne False en cas d'erreur
        self.assertFalse(result)
