import hashlib
import hmac
import json
import stripe
from typing import Dict
from django.conf import settings
from django.http import HttpResponse
from ..models import Transaction, Payout
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

    def handle_coinpayments_ipn(self, request) -> HttpResponse:
        """Gère les notifications IPN de CoinPayments"""
        try:
            # Vérifier la signature
            signature = request.headers.get("X-Signature")
            if not signature or not self._verify_signature(request.POST, signature):
                return HttpResponse("Invalid signature", status=400)

            # Extraire les données
            txn_id = request.POST.get("txn_id")
            status = int(request.POST.get("status", 0))
            request.POST.get("amount")
            request.POST.get("currency")

            # Trouver la transaction
            try:
                transaction = Transaction.objects.get(payment_id=txn_id)
            except Transaction.DoesNotExist:
                return HttpResponse("Transaction not found", status=404)

            # Mettre à jour le statut de la transaction
            if status >= 100:  # Paiement confirmé
                transaction.status = "completed"
                transaction.save()

                # Envoyer une notification
                self.telegram_service.send_transaction_notification(
                    transaction,
                    f"Paiement confirmé pour la transaction #{transaction.id}",
                )

            elif status < 0:  # Erreur ou annulation
                transaction.status = "failed"
                transaction.save()

                # Envoyer une notification
                self.telegram_service.send_transaction_notification(
                    transaction,
                    f"Échec du paiement pour la transaction #{transaction.id}",
                )

            return HttpResponse("OK")

        except Exception as e:
            # Envoyer une notification d'erreur
            self.telegram_service.send_error_notification(f"Erreur webhook CoinPayments: {str(e)}")
            return HttpResponse(str(e), status=500)

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

    @staticmethod
    def handle_coinpayments_webhook(request):
        """
        Gère les webhooks de CoinPayments
        """
        try:
            # Vérifier la signature
            signature = request.headers.get("X-Signature")
            if not signature:
                logger.error("Signature manquante dans les headers")
                return False

            # Calculer la signature HMAC
            payload = request.body
            expected_signature = hmac.new(
                settings.COINPAYMENTS_IPN_SECRET.encode(), payload, hashlib.sha512
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_signature):
                logger.error("Signature invalide")
                return False

            # Parser le payload
            data = json.loads(payload)
            status = int(data.get("status", 0))

            # Importer les modèles ici pour éviter l'importation circulaire
            from ..models import Transaction

            if status == 100:  # Paiement complété
                transaction = Transaction.objects.get(transaction_id=data["txn_id"])
                transaction.status = "completed"
                transaction.save()

                # Créer les commissions associées
                transaction.create_commissions()

                logger.info(f"Paiement CoinPayments complété: {data['txn_id']}")
                return True

            elif status == -1:  # Paiement échoué
                transaction = Transaction.objects.get(transaction_id=data["txn_id"])
                transaction.status = "failed"
                transaction.save()
                logger.info(f"Paiement CoinPayments échoué: {data['txn_id']}")
                return True

            return False

        except json.JSONDecodeError:
            logger.error("Erreur de décodage JSON")
            return False
        except Exception as e:
            logger.exception(f"Erreur lors du traitement du webhook CoinPayments: {str(e)}")
            return False

    @staticmethod
    def handle_stripe_webhook(request):
        """
        Gère les webhooks de Stripe
        """
        try:
            # Vérifier la signature
            signature = request.headers.get("Stripe-Signature")
            if not signature:
                logger.error("Signature Stripe manquante")
                return False

            # Importer les modèles ici pour éviter l'importation circulaire
            from ..models import Transaction

            # Vérifier la signature avec la clé secrète
            event = stripe.Webhook.construct_event(
                request.body, signature, settings.STRIPE_WEBHOOK_SECRET
            )

            if event.type == "payment_intent.succeeded":
                payment_intent = event.data.object
                transaction = Transaction.objects.get(transaction_id=payment_intent.id)
                transaction.status = "completed"
                transaction.save()

                # Créer les commissions associées
                transaction.create_commissions()

                logger.info(f"Paiement Stripe complété: {payment_intent.id}")
                return True

            elif event.type == "payment_intent.payment_failed":
                payment_intent = event.data.object
                transaction = Transaction.objects.get(transaction_id=payment_intent.id)
                transaction.status = "failed"
                transaction.save()
                logger.info(f"Paiement Stripe échoué: {payment_intent.id}")
                return True

            return False

        except stripe.error.SignatureVerificationError:
            logger.error("Signature Stripe invalide")
            return False
        except Exception as e:
            logger.exception(f"Erreur lors du traitement du webhook Stripe: {str(e)}")
            return False
