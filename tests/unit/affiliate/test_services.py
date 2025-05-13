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
from apps.affiliate.services import SupabaseService


class SupabaseServiceTestCase(TestCase):
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

    @patch("apps.affiliate.services.supabase_service.create_client")
    def test_sync_commission(self, mock_create_client):
        """Test de la synchronisation d'une commission"""
        # Configurer le mock
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Configurer les retours du mock
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_execute = MagicMock()

        # Structure de retour pour simuler result.data
        mock_execute.data = []

        # Configurer la chaîne de méthodes
        mock_client.table.return_value.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = mock_execute

        # Configurer l'insertion
        MagicMock()
        mock_insert_execute = MagicMock()
        mock_insert_execute.data = {"id": 1}
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            mock_insert_execute
        )

        # Créer le service après avoir configuré le mock
        service = SupabaseService()

        # Tester la synchronisation
        result = service.sync_commission(self.commission)

        # Vérifier que le service a fait appel à la méthode table
        mock_client.table.assert_called()

        # Vérifier le résultat
        self.assertTrue(result)

    @patch("apps.affiliate.services.supabase_service.create_client")
    def test_sync_white_label(self, mock_create_client):
        """Test de la synchronisation d'un site white label"""
        # Configurer le mock
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Configurer les retours du mock
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_execute = MagicMock()

        # Structure de retour pour simuler result.data
        mock_execute.data = []

        # Configurer la chaîne de méthodes
        mock_client.table.return_value.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = mock_execute

        # Configurer l'insertion
        MagicMock()
        mock_insert_execute = MagicMock()
        mock_insert_execute.data = {"id": 1}
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            mock_insert_execute
        )

        # Créer le service après avoir configuré le mock
        service = SupabaseService()

        # Tester la synchronisation
        result = service.sync_white_label(self.white_label)

        # Vérifier que le service a fait appel à la méthode table
        mock_client.table.assert_called()

        # Vérifier le résultat
        self.assertTrue(result)

    @patch("apps.affiliate.services.supabase_service.create_client")
    def test_get_ambassador_stats(self, mock_create_client):
        """Test de la récupération des statistiques d'un ambassadeur"""
        # Configurer le mock
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Configurer les retours du mock
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_execute = MagicMock()

        # Structure de retour pour simuler result.data
        mock_execute.data = [
            {
                "total_referrals": 10,
                "total_commissions": "1000.00",
                "pending_commissions": "500.00",
                "total_payouts": "500.00",
                "conversion_rate": 25.5,
            }
        ]

        # Configurer la chaîne de méthodes
        mock_client.table.return_value.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = mock_execute

        # Créer le service après avoir configuré le mock
        service = SupabaseService()

        # Tester la récupération des statistiques
        stats = service.get_ambassador_stats(str(self.ambassador.id))

        # Vérifier les appels
        mock_client.table.assert_called()

        # Vérifier le résultat
        self.assertIsNotNone(stats)
        self.assertEqual(stats["total_referrals"], 10)
        self.assertEqual(stats["total_commissions"], "1000.00")
        self.assertEqual(stats["pending_commissions"], "500.00")
        self.assertEqual(stats["total_payouts"], "500.00")
        self.assertEqual(stats["conversion_rate"], 25.5)

    @patch("apps.affiliate.services.supabase_service.create_client")
    def test_get_white_label_stats(self, mock_create_client):
        """Test de la récupération des statistiques d'un site white label"""
        # Configurer le mock
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Configurer les retours du mock
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_execute = MagicMock()

        # Structure de retour pour simuler result.data
        mock_execute.data = [
            {
                "total_clicks": 100,
                "total_conversions": 25,
                "conversion_rate": 25.0,
                "total_commissions": "2500.00",
            }
        ]

        # Configurer la chaîne de méthodes
        mock_client.table.return_value.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = mock_execute

        # Créer le service après avoir configuré le mock
        service = SupabaseService()

        # Tester la récupération des statistiques
        stats = service.get_white_label_stats(str(self.white_label.id))

        # Vérifier les appels
        mock_client.table.assert_called()

        # Vérifier le résultat
        self.assertIsNotNone(stats)
        self.assertEqual(stats["total_clicks"], 100)
        self.assertEqual(stats["total_conversions"], 25)
        self.assertEqual(stats["conversion_rate"], 25.0)
        self.assertEqual(stats["total_commissions"], "2500.00")

    @patch("apps.affiliate.services.supabase_service.create_client")
    def test_error_handling(self, mock_create_client):
        """Test de la gestion des erreurs"""
        # Configurer le mock pour simuler une erreur
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Configurer la chaîne de méthodes pour lever une exception
        mock_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = (
            Exception("Test error")
        )

        # Créer le service après avoir configuré le mock
        service = SupabaseService()

        # Tester la synchronisation avec erreur
        result = service.get_ambassador_stats(str(self.ambassador.id))

        # Vérifier que la fonction retourne None en cas d'erreur
        self.assertIsNone(result)
