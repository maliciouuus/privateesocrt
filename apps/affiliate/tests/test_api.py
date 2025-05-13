from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from apps.accounts.models import User
from apps.affiliate.models import (
    Referral,
    Commission,
    CommissionRate,
    WhiteLabel,
    Banner,
)


class APITestCase(TestCase):
    def setUp(self):
        # Créer uniquement des ambassadeurs
        self.ambassador = User.objects.create_user(
            username="ambassador",
            email="ambassador@test.com",
            password="testpass123",
            user_type="ambassador",
        )
        self.ambassador2 = User.objects.create_user(
            username="ambassador2",
            email="ambassador2@test.com",
            password="testpass123",
            user_type="ambassador",
        )
        self.referral = Referral.objects.create(
            referrer=self.ambassador, referred=self.ambassador2, referral_code="TEST123"
        )
        self.commission = Commission.objects.create(
            user=self.ambassador,
            referral=self.referral,
            amount=Decimal("100.00"),
            status="pending",
        )
        self.commission_rate = CommissionRate.objects.create(
            ambassador=self.ambassador, target_type="ambassador", rate=Decimal("0.10")
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
        self.client = APIClient()

    def test_commissions_list(self):
        self.client.force_authenticate(user=self.ambassador)
        url = reverse("commission-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["amount"], "100.00")

    def test_mark_commission_paid(self):
        self.client.force_authenticate(user=self.ambassador)
        url = reverse("commission-mark-paid", args=[self.commission.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.commission.refresh_from_db()
        self.assertEqual(self.commission.status, "paid")

    def test_white_label_stats(self):
        self.client.force_authenticate(user=self.ambassador)
        url = reverse("white-label-stats", args=[self.white_label.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_clicks", response.data)
        self.assertIn("total_conversions", response.data)
        self.assertIn("conversion_rate", response.data)

    def test_ambassador_stats(self):
        self.client.force_authenticate(user=self.ambassador)
        url = reverse("stats-ambassador")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_referrals", response.data)
        self.assertIn("total_commissions", response.data)
        self.assertIn("pending_commissions", response.data)
        self.assertIn("conversion_rate", response.data)

    def test_commission_rate_creation(self):
        self.client.force_authenticate(user=self.ambassador)
        url = reverse("commission-rate-list")
        data = {"target_type": "ambassador", "rate": "0.15"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["rate"], "0.15")

    def test_banner_creation(self):
        self.client.force_authenticate(user=self.ambassador)
        url = reverse("banner-list")
        data = {
            "white_label": self.white_label.id,
            "title": "New Banner",
            "link": "https://new-test.com",
            "is_active": True,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "New Banner")

    def test_permission_denied(self):
        url = reverse("commission-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pagination(self):
        for i in range(15):
            Commission.objects.create(
                user=self.ambassador,
                referral=self.referral,
                amount=Decimal("100.00"),
                status="pending",
            )
        self.client.force_authenticate(user=self.ambassador)
        url = reverse("commission-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10)  # PAGE_SIZE = 10
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
