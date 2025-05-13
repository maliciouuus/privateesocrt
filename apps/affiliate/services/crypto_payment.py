import requests
import hmac
import hashlib
from decimal import Decimal
from django.conf import settings
from ..models import Transaction
import logging

logger = logging.getLogger(__name__)


class CryptoPaymentService:
    """Service pour gérer les paiements en cryptomonnaies"""

    SUPPORTED_COINS = {
        "BTC": {"name": "Bitcoin", "min_amount": Decimal("0.0001"), "decimals": 8},
        "ETH": {"name": "Ethereum", "min_amount": Decimal("0.01"), "decimals": 18},
        "USDT": {"name": "Tether", "min_amount": Decimal("1"), "decimals": 6},
    }

    def __init__(self):
        self.api_key = settings.COINPAYMENTS_API_KEY
        self.api_secret = settings.COINPAYMENTS_API_SECRET
        self.base_url = "https://www.coinpayments.net/api.php"

    def _generate_signature(self, params):
        """
        Génère la signature HMAC pour l'authentification
        """
        # Trier les paramètres par clé
        sorted_params = sorted(params.items())
        # Créer la chaîne de paramètres
        param_string = "&".join(f"{k}={v}" for k, v in sorted_params)
        # Générer la signature HMAC
        return hmac.new(self.api_secret.encode(), param_string.encode(), hashlib.sha512).hexdigest()

    def _make_request(self, cmd, params=None):
        """
        Fait une requête à l'API CoinPayments
        """
        if params is None:
            params = {}

        # Ajouter les paramètres requis
        params.update({"cmd": cmd, "key": self.api_key, "version": "1"})

        # Générer la signature
        params["sign"] = self._generate_signature(params)

        try:
            response = requests.post(self.base_url, data=params)
            response.raise_for_status()
            result = response.json()

            if result.get("error") == "ok":
                return result.get("result")
            else:
                logger.error(f"Erreur API CoinPayments: {result.get('error')}")
                return None

        except Exception as e:
            logger.exception(f"Erreur lors de la requête à l'API CoinPayments: {str(e)}")
            return None

    def create_payment(self, amount, currency="EUR", buyer_email=None):
        """
        Crée un paiement crypto
        """
        params = {
            "amount": amount,
            "currency1": currency,
            "currency2": "BTC",  # Devise de paiement
            "buyer_email": buyer_email,
            "item_name": "Paiement EscortDollars",
            "ipn_url": settings.COINPAYMENTS_IPN_URL,
        }

        result = self._make_request("create_transaction", params)
        if result:
            logger.info(f"Transaction crypto créée: {result.get('txn_id')}")
            return result
        return None

    def get_payment_info(self, txn_id):
        """
        Récupère les informations d'un paiement
        """
        params = {"txid": txn_id}
        result = self._make_request("get_tx_info", params)
        if result:
            logger.info(f"Informations de paiement récupérées pour {txn_id}")
            return result
        return None

    def create_payout(self, amount, currency, address):
        """
        Crée un paiement sortant
        """
        params = {
            "amount": amount,
            "currency": currency,
            "address": address,
            "auto_confirm": 1,
        }

        result = self._make_request("create_withdrawal", params)
        if result:
            logger.info(f"Paiement sortant créé: {result.get('id')}")
            return result
        return None

    def get_payout_info(self, payout_id):
        """
        Récupère les informations d'un paiement sortant
        """
        params = {"id": payout_id}
        result = self._make_request("get_withdrawal_info", params)
        if result:
            logger.info(f"Informations de paiement sortant récupérées pour {payout_id}")
            return result
        return None

    def get_exchange_rate(self, from_currency, to_currency):
        """
        Récupère le taux de change entre deux devises
        """
        params = {"from": from_currency, "to": to_currency}

        result = self._make_request("rates", params)
        if result:
            rate = result.get(to_currency, {}).get("rate")
            if rate:
                logger.info(f"Taux de change récupéré: {from_currency} -> {to_currency} = {rate}")
                return float(rate)
        return None

    def check_payment_status(self, transaction: Transaction) -> str:
        """Vérifie le statut d'un paiement"""
        params = {
            "cmd": "get_tx_info",
            "version": "1",
            "key": self.api_key,
            "txid": transaction.payment_id,
        }

        # Ajouter la signature
        params["signature"] = self._generate_signature(params)

        # Appeler l'API
        response = requests.post(self.base_url, data=params)
        response.raise_for_status()
        result = response.json()

        if result["error"] != "ok":
            raise Exception(f"Erreur CoinPayments: {result['error']}")

        status = result["result"]["status"]

        # Mettre à jour le statut de la transaction
        if status >= 100:  # Paiement confirmé
            transaction.status = "completed"
            transaction.save()
        elif status < 0:  # Erreur ou annulation
            transaction.status = "failed"
            transaction.save()

        return status

    def create_payout_coinpayments(self, amount, currency, address):
        """
        Crée un paiement sortant
        """
        try:
            payout = self.client.create_withdrawal(
                amount=amount, currency=currency, address=address, auto_confirm=1
            )

            logger.info(f"Paiement sortant créé: {payout['id']}")
            return payout

        except Exception as e:
            logger.exception(f"Erreur lors de la création du paiement sortant: {str(e)}")
            return None

    def create_payment_coinpayments(self, amount, currency="EUR", buyer_email=None):
        """
        Crée un paiement crypto
        """
        try:
            # Créer la transaction
            transaction = self.client.create_transaction(
                amount=amount,
                currency1=currency,
                currency2="BTC",  # Devise de paiement
                buyer_email=buyer_email,
                item_name="Paiement EscortDollars",
                ipn_url=settings.COINPAYMENTS_IPN_URL,
            )

            logger.info(f"Transaction crypto créée: {transaction['txn_id']}")
            return transaction

        except Exception as e:
            logger.exception(f"Erreur lors de la création du paiement crypto: {str(e)}")
            return None
