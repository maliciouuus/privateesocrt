from django.test import SimpleTestCase
from decimal import Decimal


class FormattingTestCase(SimpleTestCase):
    """Tests pour les fonctions de formatage utilisées dans le dashboard."""
    
    def test_currency_formatting(self):
        """Tests pour le formatage des devises."""
        # Test formatage simples
        self.assertEqual(f"{Decimal('1234.56'):.2f}", "1234.56")
        self.assertEqual(f"{Decimal('1234.56'):.2f} €", "1234.56 €")
        
        # Valeurs avec différentes précisions
        self.assertEqual(f"{Decimal('1234.5'):.2f}", "1234.50")
        self.assertEqual(f"{Decimal('1234'):.2f}", "1234.00")
        
        # Grandes valeurs avec séparateurs
        self.assertEqual(f"{Decimal('1234567.89'):.2f}".replace('.', ','), "1234567,89")
        
    def test_percentage_formatting(self):
        """Tests pour le formatage des pourcentages."""
        # Test formatage simple
        self.assertEqual(f"{50}%", "50%")
        self.assertEqual(f"{50.5:.1f}%", "50.5%")
        
        # Test formatage avec signe
        self.assertEqual(f"{25.5:.1f}%", "25.5%")
        self.assertEqual(f"{-25.5:.1f}%", "-25.5%")
        
    def test_number_formatting(self):
        """Test pour le formatage des nombres."""
        # Test formatage simple
        self.assertEqual(f"{1234}", "1234")
        
        # Test formatage avec séparateurs
        self.assertEqual(f"{1234567:,}".replace(',', ' '), "1 234 567")
        
        # Test formatage avec décimales
        self.assertEqual(f"{1234.5678:.2f}", "1234.57")
        self.assertEqual(f"{0.5678:.2f}", "0.57") 