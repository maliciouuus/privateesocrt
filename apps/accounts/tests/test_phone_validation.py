from django.test import SimpleTestCase
import re


class PhoneValidationTestCase(SimpleTestCase):
    """Tests pour la validation des numéros de téléphone."""
    
    def test_french_phone_validation(self):
        """Tests pour la validation des numéros de téléphone français."""
        # Regex plus permissive pour les numéros français
        french_phone_regex = r"^(?:(?:\+|00)33|0)\s*[1-9](?:[\s.]*\d{2}){4}$"
        
        # Liste des numéros valides à tester
        valid_phones = [
            "+33612345678",
            "+33 6 12 34 56 78",
            "0612345678",
            "06 12 34 56 78",
            "06.12.34.56.78",
            "0033612345678",
        ]
        
        for phone in valid_phones:
            self.assertTrue(re.match(french_phone_regex, phone), f"Le numéro valide '{phone}' a été rejeté")
        
        # Numéros invalides
        invalid_phones = [
            "612345678",       # Manque le 0 ou +33
            "+336123456789",   # Trop long
            "+3361234567",     # Trop court
            "+33 06 12 34 56 78", # Double préfixe
            "00336",           # Trop court
            "text",            # Pas un numéro
            "+33012345678",    # 0 après l'indicatif
        ]
        
        for phone in invalid_phones:
            self.assertFalse(re.match(french_phone_regex, phone), f"Le numéro invalide '{phone}' a été accepté")
    
    def test_international_phone_validation(self):
        """Tests pour la validation des numéros de téléphone internationaux (format E164)."""
        # Regex pour les numéros au format international E164
        e164_regex = r"^\+[1-9]\d{1,14}$"
        
        # Numéros valides
        valid_phones = [
            "+33612345678",   # France
            "+12125551234",   # USA
            "+447911123456",  # UK
            "+491234567890",  # Allemagne
            "+8618612345678", # Chine
        ]
        
        for phone in valid_phones:
            self.assertTrue(re.match(e164_regex, phone), f"Le numéro valide '{phone}' a été rejeté")
        
        # Numéros invalides
        invalid_phones = [
            "33612345678",    # Manque le +
            "+0123456789",    # Ne doit pas commencer par +0
            "+",              # Trop court
            "+123456789012345678", # Trop long (max 15 chiffres après le +)
            "text",           # Pas un numéro
        ]
        
        for phone in invalid_phones:
            self.assertFalse(re.match(e164_regex, phone), f"Le numéro invalide '{phone}' a été accepté") 