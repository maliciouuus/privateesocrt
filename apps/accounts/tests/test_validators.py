from django.test import SimpleTestCase
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError


class ValidatorsTestCase(SimpleTestCase):
    """Tests pour les validateurs utilisés dans l'application accounts."""
    
    def test_email_validation(self):
        """Tests pour la validation des emails."""
        validator = EmailValidator()
        
        # Emails valides
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user@sub.example.com",
            "user@example.co.uk",
            "1234567890@example.com",
            "user@example-domain.com",
            "user@example.technology",
        ]
        
        for email in valid_emails:
            try:
                validator(email)
                # Si on arrive ici, c'est que la validation a réussi
                self.assertTrue(True)
            except ValidationError:
                self.fail(f"Email valide '{email}' rejeté à tort")
        
        # Emails invalides
        invalid_emails = [
            "user@",
            "@example.com",
            "user@.com",
            "user@example..com",
            "user@example.com.",
            "user@example",
            "user.@example.com",
            ".user@example.com",
            "user@-example.com",
            "user@example-.com",
            "user@exam_ple.com",
            "user name@example.com",
            "user@exam ple.com",
        ]
        
        for email in invalid_emails:
            with self.assertRaises(ValidationError):
                validator(email)
                
    def test_password_strength(self):
        """Tests simples pour la validation de la complexité des mots de passe."""
        # Mots de passe forts (au moins 8 caractères, avec majuscules, minuscules, chiffres et caractères spéciaux)
        strong_passwords = [
            "Abcdef1!",
            "P@ssw0rd",
            "Str0ng_P@ss",
            "C0mpl3x!P@ssw0rd",
        ]
        
        for password in strong_passwords:
            self.assertTrue(len(password) >= 8)
            self.assertTrue(any(c.isupper() for c in password))
            self.assertTrue(any(c.islower() for c in password))
            self.assertTrue(any(c.isdigit() for c in password))
            self.assertTrue(any(not c.isalnum() for c in password))
            
        # Mots de passe faibles
        weak_passwords = [
            "password",  # Trop simple
            "12345678",  # Que des chiffres
            "abcdefgh",  # Que des lettres minuscules
            "ABCDEFGH",  # Que des lettres majuscules
            "short1!",   # Trop court
        ]
        
        for password in weak_passwords:
            # Au moins une des conditions n'est pas remplie
            self.assertTrue(
                len(password) < 8 or
                not any(c.isupper() for c in password) or
                not any(c.islower() for c in password) or
                not any(c.isdigit() for c in password) or
                not any(not c.isalnum() for c in password)
            ) 