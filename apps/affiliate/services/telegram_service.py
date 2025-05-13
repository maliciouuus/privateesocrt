import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_message(self, message):
        """
        Envoie un message via l'API Telegram
        """
        try:
            response = requests.post(
                self.api_url,
                json={"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"},
            )
            if response.status_code == 200:
                logger.info(f"Message Telegram envoyé avec succès: {message}")
                return True
            else:
                logger.error(f"Erreur lors de l'envoi du message Telegram: {response.text}")
                return False
        except Exception as e:
            logger.exception(f"Erreur lors de l'envoi du message Telegram: {str(e)}")
            return False

    def notify_new_referral(self, referrer, referred):
        """
        Notifie un nouveau parrainage
        """
        message = (
            f"🎉 <b>Nouveau Parrainage !</b>\n\n"
            f"Ambassadeur: {referrer.username}\n"
            f"Parrainé: {referred.username}\n"
            f"Date: {referred.date_joined.strftime('%d/%m/%Y %H:%M')}"
        )
        return self.send_message(message)

    def notify_commission(self, commission):
        """
        Notifie une nouvelle commission
        """
        message = (
            f"💰 <b>Nouvelle Commission !</b>\n\n"
            f"Ambassadeur: {commission.user.username}\n"
            f"Montant: {commission.amount}€\n"
            f"Type: {commission.commission_type}\n"
            f"Date: {commission.created_at.strftime('%d/%m/%Y %H:%M')}"
        )
        return self.send_message(message)

    def notify_white_label_creation(self, white_label):
        """
        Notifie la création d'un site white label
        """
        message = (
            f"🌐 <b>Nouveau Site White Label !</b>\n\n"
            f"Nom: {white_label.name}\n"
            f"Domaine: {white_label.domain}\n"
            f"Date: {white_label.created_at.strftime('%d/%m/%Y %H:%M')}"
        )
        return self.send_message(message)

    def notify_payout(self, payout):
        """
        Notifie un nouveau paiement
        """
        message = (
            f"💸 <b>Nouveau Paiement !</b>\n\n"
            f"Ambassadeur: {payout.ambassador.username}\n"
            f"Montant: {payout.amount}€\n"
            f"Méthode: {payout.get_payment_method_display()}\n"
            f"Date: {payout.created_at.strftime('%d/%m/%Y %H:%M')}"
        )
        return self.send_message(message)
