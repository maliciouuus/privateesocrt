from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages
from decimal import Decimal
import json
from datetime import timedelta
import uuid

from apps.accounts.models import User, UserProfile
from apps.affiliate.models import ReferralClick, Referral, Commission
from apps.dashboard.models import Notification


class AdminDashboardViewsTest(TestCase):
    def setUp(self):
        # Créer un administrateur
        self.admin_user = User.objects.create_user(
            username="adminuser", 
            email="admin@example.com", 
            password="password123",
            user_type="member",
            is_staff=True
        )
        
        # Créer un utilisateur standard
        self.user = User.objects.create_user(
            username="testuser", 
            email="testuser@example.com", 
            password="password123",
            user_type="member"
        )
        
        # Créer un ambassadeur
        self.ambassador = User.objects.create_user(
            username="ambassador", 
            email="ambassador@example.com", 
            password="password123",
            user_type="ambassador",
            user_category="ambassador",
            commission_rate=10.0
        )
        
        # Créer une escorte
        self.escort = User.objects.create_user(
            username="escort", 
            email="escort@example.com", 
            password="password123",
            user_type="escort",
            user_category="escort"
        )
        
        # Créer un parrainage
        self.referral = Referral.objects.create(
            referrer=self.ambassador,
            referred=self.escort,
            created_at=timezone.now()
        )
        
        # Créer des commissions
        self.commission = Commission.objects.create(
            referral=self.referral,
            amount=Decimal("100.00"),
            commission_type="purchase",
            status="pending",
            created_at=timezone.now()
        )
        
        self.client = Client()

    def test_manage_ambassadors(self):
        """Test la vue manage_ambassadors"""
        # Test pour un utilisateur standard (non-admin)
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("dashboard:manage_ambassadors"))
        self.assertEqual(response.status_code, 302)  # Doit rediriger
        
        # Test pour un administrateur
        self.client.login(username="adminuser", password="password123")
        response = self.client.get(reverse("dashboard:manage_ambassadors"))
        self.assertEqual(response.status_code, 200)
        
        # Test avec modification d'un taux de commission
        response = self.client.post(reverse("dashboard:manage_ambassadors"), {
            "user_id": self.ambassador.id,
            "commission_rate": "15.0"
        })
        self.assertEqual(response.status_code, 200)

    def test_bulk_update_ambassadors(self):
        """Test la vue bulk_update_ambassadors"""
        self.client.login(username="adminuser", password="password123")
        
        # Créer des données JSON pour la requête
        data = {
            "commission_rate": 12.0,
            "apply_to": "all"
        }
        
        response = self.client.post(
            reverse("dashboard:bulk_update_ambassadors"), 
            json.dumps(data), 
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 200)

    def test_manage_escorts(self):
        """Test la vue manage_escorts"""
        # Test pour un administrateur
        self.client.login(username="adminuser", password="password123")
        response = self.client.get(reverse("dashboard:manage_escorts"))
        self.assertEqual(response.status_code, 200)
        
        # Test avec modification d'un taux de commission
        response = self.client.post(reverse("dashboard:manage_escorts"), {
            "user_id": self.escort.id,
            "commission_rate": "20.0"
        })
        self.assertEqual(response.status_code, 200)

    def test_update_specific_rates(self):
        """Test la vue update_specific_rates"""
        self.client.login(username="adminuser", password="password123")
        
        response = self.client.post(reverse("dashboard:update_specific_rates"), {
            "user_id": self.ambassador.id,
            "escort_rate": "25.0",
            "ambassador_rate": "10.0"
        })
        
        self.assertEqual(response.status_code, 302)  # Redirection

    def test_admin_commissions(self):
        """Test la vue admin_commissions"""
        # Test pour un administrateur
        self.client.login(username="adminuser", password="password123")
        response = self.client.get(reverse("dashboard:admin_commissions"))
        self.assertEqual(response.status_code, 200)
        
        # Test avec filtrage par mois
        response = self.client.get(reverse("dashboard:admin_commissions"), {
            "month": "1",
            "year": "2023"
        })
        self.assertEqual(response.status_code, 200)
        
        # Test avec action de marquer une commission comme payée
        response = self.client.post(reverse("dashboard:admin_commissions"), {
            "action": "mark_single_paid",
            "commission_id": self.commission.id
        })
        self.assertEqual(response.status_code, 302)  # Redirection

    def test_mark_commission_paid(self):
        """Test la vue mark_commission_paid"""
        # Test pour un administrateur
        self.client.login(username="adminuser", password="password123")
        response = self.client.post(reverse("dashboard:mark_commission_paid", args=[self.commission.id]))
        self.assertEqual(response.status_code, 200)

    def test_user_profile(self):
        """Test la vue user_profile"""
        # Test pour un administrateur
        self.client.login(username="adminuser", password="password123")
        response = self.client.get(reverse("dashboard:user_profile", args=[self.ambassador.username]))
        self.assertEqual(response.status_code, 200)
        
        # Test avec un utilisateur inexistant
        response = self.client.get(reverse("dashboard:user_profile", args=["nonexistentuser"]))
        self.assertEqual(response.status_code, 302)  # Redirection

    def test_debug_affiliate_relations(self):
        """Test la vue debug_affiliate_relations"""
        self.client.login(username="adminuser", password="password123")
        
        # Test sans spécifier d'utilisateur
        response = self.client.get(reverse("dashboard:debug_affiliate_relations"))
        self.assertEqual(response.status_code, 200)
        
        # Test avec un utilisateur spécifique
        response = self.client.get(reverse("dashboard:debug_affiliate_relations", args=[self.ambassador.username]))
        self.assertEqual(response.status_code, 200)
        
        # Test avec un utilisateur inexistant
        response = self.client.get(reverse("dashboard:debug_affiliate_relations", args=["nonexistentuser"]))
        self.assertContains(response, "non trouvé")

    def test_fix_affiliation(self):
        """Test la vue fix_affiliation"""
        self.client.login(username="adminuser", password="password123")
        
        # Créer un nouvel utilisateur pour tester l'affiliation
        new_user = User.objects.create_user(
            username="newuser", 
            email="newuser@example.com", 
            password="password123",
            user_type="member"
        )
        
        response = self.client.get(reverse("dashboard:fix_affiliation", args=[
            self.ambassador.username, new_user.username
        ]))
        
        self.assertEqual(response.status_code, 302)  # Redirection
        
        # Vérifier que l'affiliation a été établie
        new_user.refresh_from_db()
        self.assertEqual(new_user.referred_by, self.ambassador)
        
        # Vérifier qu'une entrée de parrainage a été créée
        self.assertTrue(Referral.objects.filter(referrer=self.ambassador, referred=new_user).exists()) 