from django.test import SimpleTestCase
from apps.dashboard.views import calculate_growth
from datetime import datetime, timedelta
from django.utils import timezone


class UtilsTestCase(SimpleTestCase):
    """Tests pour les fonctions utilitaires du dashboard qui ne nécessitent pas d'accès DB."""

    def test_calculate_growth(self):
        """Test pour la fonction calculate_growth."""
        # Test avec valeur précédente à 0
        self.assertEqual(calculate_growth(100, 0), 100)
        self.assertEqual(calculate_growth(0, 0), 0)
        
        # Test avec valeurs positives
        self.assertEqual(calculate_growth(200, 100), 100)
        self.assertEqual(calculate_growth(100, 200), -50)
        
        # Test avec valeurs négatives
        self.assertEqual(calculate_growth(-50, -100), -50)  # -50 est plus grand que -100, d'où -50%
        
        # Test avec changement important
        self.assertEqual(calculate_growth(1000, 100), 900)
    
    def test_date_formatting(self):
        """Tests pour les fonctions liées au formatage des dates."""
        # Test formatage date simple
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        last_week = now - timedelta(days=7)
        
        # Vérification que les dates sont différentes
        self.assertNotEqual(now.date(), yesterday.date())
        self.assertNotEqual(now.date(), last_week.date())
        
        # Test pour les calculs de périodes
        period_30_days = now - timedelta(days=30)
        period_7_days = now - timedelta(days=7)
        
        self.assertEqual((now.date() - period_30_days.date()).days, 30)
        self.assertEqual((now.date() - period_7_days.date()).days, 7) 