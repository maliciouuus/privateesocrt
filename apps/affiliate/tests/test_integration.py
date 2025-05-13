from django.urls import reverse
from rest_framework import status


class TestIntegration:
    def test_complete_commission_flow(self, api_client, ambassador_user, escort_user, referral):
        """Test du flux complet de commission"""
        # 1. Créer une transaction
        api_client.force_authenticate(user=escort_user)
        transaction_data = {
            "amount": "1000.00",
            "payment_method": "crypto",
            "payment_id": "BTC123",
        }
        response = api_client.post(reverse("transaction-list"), transaction_data)
        assert response.status_code == status.HTTP_201_CREATED
        response.data["id"]

        # 2. Vérifier la création de la commission
        api_client.force_authenticate(user=ambassador_user)
        response = api_client.get(reverse("commission-list"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        commission_id = response.data["results"][0]["id"]

        # 3. Marquer la commission comme payée
        response = api_client.post(reverse("commission-mark-paid", args=[commission_id]))
        assert response.status_code == status.HTTP_200_OK

        # 4. Vérifier le statut de la commission
        response = api_client.get(reverse("commission-detail", args=[commission_id]))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "paid"

    def test_white_label_flow(self, api_client, ambassador_user, white_label):
        """Test du flux de site white label"""
        api_client.force_authenticate(user=ambassador_user)

        # 1. Créer une bannière
        banner_data = {
            "white_label": white_label.id,
            "title": "New Banner",
            "link": "https://test.com",
            "is_active": True,
        }
        response = api_client.post(reverse("banner-list"), banner_data)
        assert response.status_code == status.HTTP_201_CREATED
        response.data["id"]

        # 2. Vérifier les statistiques du site
        response = api_client.get(reverse("white-label-stats", args=[white_label.id]))
        assert response.status_code == status.HTTP_200_OK
        assert "total_clicks" in response.data
        assert "total_conversions" in response.data

        # 3. Mettre à jour le site
        update_data = {"name": "Updated Site", "primary_color": "#0000FF"}
        response = api_client.patch(
            reverse("white-label-detail", args=[white_label.id]), update_data
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Site"

    def test_referral_flow(self, api_client, ambassador_user, escort_user):
        """Test du flux de parrainage"""
        # 1. Créer un code de parrainage
        api_client.force_authenticate(user=ambassador_user)
        response = api_client.post(reverse("referral-list"))
        assert response.status_code == status.HTTP_201_CREATED
        referral_code = response.data["referral_code"]

        # 2. Simuler un clic sur le lien de parrainage
        response = api_client.post(
            reverse("referral-click-list"),
            {
                "referral_code": referral_code,
                "ip_address": "127.0.0.1",
                "user_agent": "Test Browser",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

        # 3. Vérifier les statistiques de l'ambassadeur
        response = api_client.get(reverse("stats-ambassador"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_referrals"] > 0

    def test_payout_flow(self, api_client, ambassador_user, commission):
        """Test du flux de paiement"""
        api_client.force_authenticate(user=ambassador_user)

        # 1. Marquer la commission comme payée
        response = api_client.post(reverse("commission-mark-paid", args=[commission.id]))
        assert response.status_code == status.HTTP_200_OK

        # 2. Créer un paiement
        payout_data = {
            "amount": "100.00",
            "payment_method": "crypto",
            "wallet_address": "BTC123",
        }
        response = api_client.post(reverse("payout-list"), payout_data)
        assert response.status_code == status.HTTP_201_CREATED
        payout_id = response.data["id"]

        # 3. Vérifier le statut du paiement
        response = api_client.get(reverse("payout-detail", args=[payout_id]))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "pending"

    def test_error_handling(self, api_client, ambassador_user):
        """Test de la gestion des erreurs"""
        api_client.force_authenticate(user=ambassador_user)

        # 1. Test avec des données invalides
        response = api_client.post(
            reverse("commission-list"), {"amount": "invalid", "status": "invalid"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # 2. Test avec un ID inexistant
        response = api_client.get(reverse("commission-detail", args=["999999"]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # 3. Test avec des permissions insuffisantes
        response = api_client.post(
            reverse("commission-rate-list"), {"target_type": "escort", "rate": "0.15"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
