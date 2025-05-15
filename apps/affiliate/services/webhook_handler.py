import hashlib
import hmac
import json
import stripe
from typing import Dict
from django.conf import settings
from django.http import HttpResponse
from ..models import Payout
from .crypto_payment import CryptoPaymentService
from .telegram_service import TelegramService
import logging

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Gestionnaire de webhooks pour les notifications de paiement"""

    def __init__(self):
        self.crypto_service = CryptoPaymentService()
        self.telegram_service = TelegramService()

    def _verify_signature(self, data: Dict, signature: str) -> bool:
        """Vérifie la signature du webhook"""
        # Trier les paramètres par clé
        sorted_params = sorted(data.items())
        # Créer la chaîne de paramètres
        param_string = "&".join(f"{k}={v}" for k, v in sorted_params)
        # Générer la signature HMAC
        expected_signature = hmac.new(
            settings.COINPAYMENTS_IPN_SECRET.encode(),
            param_string.encode(),
            hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)

    # Fonction désactivée - Transaction model supprimé
    def handle_coinpayments_ipn(self, request) -> HttpResponse:
        """Gère les notifications IPN de CoinPayments"""
        logger.warning("handle_coinpayments_ipn appelé mais Transaction model a été supprimé")
        return HttpResponse("Transaction model supprimé", status=500)

    def handle_payout_notification(self, request) -> HttpResponse:
        """Gère les notifications de paiement sortant"""
        try:
            # Vérifier la signature
            signature = request.headers.get("X-Signature")
            if not signature or not self._verify_signature(request.POST, signature):
                return HttpResponse("Invalid signature", status=400)

            # Extraire les données
            payout_id = request.POST.get("id")
            status = int(request.POST.get("status", 0))

            # Trouver le paiement
            try:
                payout = Payout.objects.get(payment_id=payout_id)
            except Payout.DoesNotExist:
                return HttpResponse("Payout not found", status=404)

            # Mettre à jour le statut du paiement
            if status == 2:  # Paiement complété
                payout.status = "completed"
                payout.save()

                # Envoyer une notification
                self.telegram_service.send_payout_notification(
                    payout, f"Paiement complété pour le payout #{payout.id}"
                )

            elif status == -1:  # Erreur
                payout.status = "failed"
                payout.save()

                # Envoyer une notification
                self.telegram_service.send_payout_notification(
                    payout, f"Échec du paiement pour le payout #{payout.id}"
                )

            return HttpResponse("OK")

        except Exception as e:
            # Envoyer une notification d'erreur
            self.telegram_service.send_error_notification(f"Erreur webhook Payout: {str(e)}")
            return HttpResponse(str(e), status=500)

    # Fonction désactivée - Transaction model supprimé
    @staticmethod
    def handle_coinpayments_webhook(request):
        """
        Gère les webhooks de CoinPayments
        """
        logger.warning("handle_coinpayments_webhook appelé mais Transaction model a été supprimé")
        return False

    # Fonction désactivée - Transaction model supprimé
    @staticmethod
    def handle_stripe_webhook(request):
        """
        Gère les webhooks de Stripe
        """
        logger.warning("handle_stripe_webhook appelé mais Transaction model a été supprimé")
        return False
