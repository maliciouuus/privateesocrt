from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
import uuid

from apps.accounts.models import User
from apps.affiliate.models import ReferralClick, Referral, Commission, MarketingMaterial
from django.core.files.uploadedfile import SimpleUploadedFile


class ReferralClickTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            referral_code="TEST123"
        )
        
        self.click = ReferralClick.objects.create(
            referral_code="TEST123",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
            source="https://example.com"
        )
    
    def test_referral_click_creation(self):
        """Test la création d'un clic de parrainage"""
        self.assertEqual(self.click.referral_code, "TEST123")
        self.assertEqual(self.click.ip_address, "127.0.0.1")
        self.assertEqual(self.click.user_agent, "Mozilla/5.0")
        self.assertEqual(self.click.source, "https://example.com")
        
        # Vérifier que la date de création est correcte
        self.assertIsNotNone(self.click.clicked_at)
        self.assertTrue((timezone.now() - self.click.clicked_at).total_seconds() < 60)


class ReferralTest(TestCase):
    def setUp(self):
        # Créer un référent (ambassadeur)
        self.referrer = User.objects.create_user(
            username="referrer",
            email="referrer@example.com",
            password="password123",
            referral_code="REF123",
            user_type="ambassador"
        )
        
        # Créer un utilisateur référé
        self.referred = User.objects.create_user(
            username="referred",
            email="referred@example.com",
            password="password123",
            user_type="escort"
        )
        
        # Créer un clic de parrainage
        self.click = ReferralClick.objects.create(
            referral_code="REF123",
            ip_address="127.0.0.1"
        )
        
        # Créer un parrainage
        self.referral = Referral.objects.create(
            referrer=self.referrer,
            referred=self.referred,
            total_earnings=Decimal("0.00")
        )
    
    def test_referral_creation(self):
        """Test la création d'un parrainage"""
        self.assertEqual(self.referral.referrer, self.referrer)
        self.assertEqual(self.referral.referred, self.referred)
        self.assertEqual(self.referral.total_earnings, Decimal("0.00"))
        
        # Vérifier que la date de création est correcte
        self.assertIsNotNone(self.referral.created_at)
        self.assertTrue((timezone.now() - self.referral.created_at).total_seconds() < 60)


class CommissionTest(TestCase):
    def setUp(self):
        # Créer un référent (ambassadeur)
        self.referrer = User.objects.create_user(
            username="referrer",
            email="referrer@example.com",
            password="password123",
            referral_code="REF123",
            user_type="ambassador"
        )
        
        # Créer un utilisateur référé
        self.referred = User.objects.create_user(
            username="referred",
            email="referred@example.com",
            password="password123",
            user_type="escort"
        )
        
        # Créer un parrainage
        self.referral = Referral.objects.create(
            referrer=self.referrer,
            referred=self.referred,
            total_earnings=Decimal("0.00")
        )
        
        # Créer une commission
        self.commission = Commission.objects.create(
            referral=self.referral,
            amount=Decimal("100.00"),
            commission_type="purchase",
            status="pending",
            description="Test commission",
            reference_id=str(uuid.uuid4())
        )
    
    def test_commission_creation(self):
        """Test la création d'une commission"""
        self.assertEqual(self.commission.referral, self.referral)
        self.assertEqual(self.commission.amount, Decimal("100.00"))
        self.assertEqual(self.commission.commission_type, "purchase")
        self.assertEqual(self.commission.status, "pending")
        self.assertEqual(self.commission.description, "Test commission")
        
        # Vérifier que la date de création est correcte
        self.assertIsNotNone(self.commission.created_at)
        self.assertTrue((timezone.now() - self.commission.created_at).total_seconds() < 60)
    
    def test_mark_as_paid(self):
        """Test le marquage d'une commission comme payée"""
        # Vérifier l'état initial
        self.assertEqual(self.commission.status, "pending")
        self.assertIsNone(self.commission.paid_at)
        
        # Marquer comme payée
        batch_id = "TEST-BATCH-123"
        success = self.commission.mark_as_paid(batch_id=batch_id)
        
        # Vérifier que l'opération a réussi
        self.assertTrue(success)
        
        # Vérifier le nouvel état
        self.assertEqual(self.commission.status, "paid")
        self.assertIsNotNone(self.commission.paid_at)
        self.assertEqual(self.commission.batch_id, batch_id)


class MarketingMaterialTest(TestCase):
    """Tests pour le modèle MarketingMaterial."""
    
    def setUp(self):
        """Préparer les données de test."""
        # Créer un fichier fictif pour le test
        self.test_file = SimpleUploadedFile(
            name="test_file.pdf",
            content=b"file_content",
            content_type="application/pdf"
        )
        
        self.marketing_material = MarketingMaterial.objects.create(
            title="Test Material",
            description="This is a test marketing material",
            file=self.test_file,
            file_type="pdf",
            is_active=True
        )
    
    def test_marketing_material_creation(self):
        """Tester la création d'un matériel marketing."""
        self.assertEqual(self.marketing_material.title, "Test Material")
        self.assertEqual(self.marketing_material.description, "This is a test marketing material")
        self.assertEqual(self.marketing_material.file_type, "pdf")
        self.assertTrue(self.marketing_material.is_active)
        self.assertEqual(self.marketing_material.download_count, 0)
    
    def test_marketing_material_str_method(self):
        """Tester la méthode __str__ du modèle MarketingMaterial."""
        self.assertEqual(str(self.marketing_material), "Test Material")
    
    def test_increment_download_count(self):
        """Tester l'incrémentation du compteur de téléchargements."""
        initial_count = self.marketing_material.download_count
        
        # Incrémenter manuellement le compteur
        self.marketing_material.download_count += 1
        self.marketing_material.save()
        
        # Récupérer le matériel depuis la base de données
        refreshed_material = MarketingMaterial.objects.get(id=self.marketing_material.id)
        
        # Vérifier que le compteur a été incrémenté
        self.assertEqual(refreshed_material.download_count, initial_count + 1)
