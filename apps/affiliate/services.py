from django.conf import settings
from django.utils import timezone
import logging
from telegram import Bot
from telegram.error import TelegramError
import datetime

logger = logging.getLogger(__name__)


class SupabaseService:
    """
    Service pour interagir avec Supabase
    """

    def __init__(self):
        from .supabase_client import get_supabase_client

        self.supabase = get_supabase_client()

    def sync_commission(self, commission):
        """
        Synchronise une commission vers Supabase

        Args:
            commission: Objet Commission à synchroniser
        """
        try:
            commission_data = {
                "id": str(commission.id),
                "referrer_id": str(commission.user.id),
                "transaction_id": commission.transaction_id,
                "amount": float(commission.amount),
                "status": commission.status,
                "created_at": commission.created_at.isoformat(),
                "paid_at": (commission.paid_at.isoformat() if commission.paid_at else None),
                "type": (
                    "direct" if commission.referral.referrer == commission.user else "indirect"
                ),
            }

            # Vérifier si la commission existe déjà dans Supabase
            result = (
                self.supabase.table("commissions")
                .select("id")
                .eq("id", str(commission.id))
                .execute()
            )

            if len(result.data) > 0:
                # Mise à jour
                self.supabase.table("commissions").update(commission_data).eq(
                    "id", str(commission.id)
                ).execute()
            else:
                # Création
                self.supabase.table("commissions").insert(commission_data).execute()

            return True
        except Exception as e:
            logger.error(
                f"Erreur lors de la synchronisation de la commission {commission.id}: {str(e)}"
            )
            return False

    def sync_commission_rate(self, rate):
        """
        Synchronise un taux de commission vers Supabase

        Args:
            rate: Objet CommissionRate à synchroniser
        """
        try:
            rate_data = {
                "id": str(rate.id),
                "ambassador_id": str(rate.ambassador.id),
                "target_type": rate.target_type,
                "rate": float(rate.rate),
                "created_at": rate.created_at.isoformat(),
                "updated_at": rate.updated_at.isoformat(),
            }

            # Vérifier si le taux existe déjà dans Supabase
            result = (
                self.supabase.table("commission_rates")
                .select("id")
                .eq("id", str(rate.id))
                .execute()
            )

            if len(result.data) > 0:
                # Mise à jour
                self.supabase.table("commission_rates").update(rate_data).eq(
                    "id", str(rate.id)
                ).execute()
            else:
                # Création
                self.supabase.table("commission_rates").insert(rate_data).execute()

            return True
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation du taux {rate.id}: {str(e)}")
            return False

    def sync_white_label(self, white_label):
        """
        Synchronise un site white label vers Supabase

        Args:
            white_label: Objet WhiteLabel à synchroniser
        """
        try:
            white_label_data = {
                "id": str(white_label.id),
                "ambassador_id": str(white_label.ambassador.id),
                "site_name": white_label.name,
                "domain": white_label.domain,
                "primary_color": white_label.primary_color,
                "secondary_color": white_label.secondary_color,
                "logo_url": white_label.logo.url if white_label.logo else None,
                "favicon_url": (
                    white_label.favicon.url
                    if white_label.favicon and hasattr(white_label, "favicon")
                    else None
                ),
                "is_active": white_label.is_active,
                "created_at": white_label.created_at.isoformat(),
                "updated_at": white_label.updated_at.isoformat(),
            }

            # Vérifier si le white label existe déjà dans Supabase
            result = (
                self.supabase.table("white_labels")
                .select("id")
                .eq("id", str(white_label.id))
                .execute()
            )

            if len(result.data) > 0:
                # Mise à jour
                self.supabase.table("white_labels").update(white_label_data).eq(
                    "id", str(white_label.id)
                ).execute()
            else:
                # Création
                self.supabase.table("white_labels").insert(white_label_data).execute()

            return True
        except Exception as e:
            logger.error(
                f"Erreur lors de la synchronisation du white label {white_label.id}: {str(e)}"
            )
            return False

    def get_transactions(self, since=None, limit=100):
        """
        Récupère les transactions depuis Supabase

        Args:
            since: Date à partir de laquelle récupérer les transactions
            limit: Nombre maximum de transactions à récupérer

        Returns:
            Liste des transactions
        """
        try:
            query = (
                self.supabase.table("transactions")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
            )

            if since:
                query = query.gte("created_at", since.isoformat())

            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des transactions: {str(e)}")
            return []

    def get_users(self, user_type=None, limit=100):
        """
        Récupère les utilisateurs depuis Supabase

        Args:
            user_type: Type d'utilisateur à récupérer (escort, agency, member)
            limit: Nombre maximum d'utilisateurs à récupérer

        Returns:
            Liste des utilisateurs
        """
        try:
            query = self.supabase.table("users").select("*").limit(limit)

            if user_type:
                query = query.eq("user_type", user_type)

            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des utilisateurs: {str(e)}")
            return []

    def get_user(self, user_id):
        """
        Récupère un utilisateur depuis Supabase

        Args:
            user_id: ID de l'utilisateur à récupérer

        Returns:
            Données de l'utilisateur ou None si non trouvé
        """
        try:
            result = self.supabase.table("users").select("*").eq("id", user_id).execute()

            if len(result.data) > 0:
                return result.data[0]
            else:
                return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'utilisateur {user_id}: {str(e)}")
            return None

    def mark_commissions_paid(self, commission_ids, payout_id):
        """
        Marque des commissions comme payées dans Supabase

        Args:
            commission_ids: Liste des IDs de commissions à marquer comme payées
            payout_id: ID du paiement

        Returns:
            Booléen indiquant si la mise à jour a réussi
        """
        try:
            for commission_id in commission_ids:
                self.supabase.table("commissions").update(
                    {
                        "status": "paid",
                        "paid_at": datetime.datetime.now().isoformat(),
                        "payout_id": str(payout_id),
                    }
                ).eq("id", str(commission_id)).execute()

            return True
        except Exception as e:
            logger.error(f"Erreur lors du marquage des commissions comme payées: {str(e)}")
            return False


class TelegramService:
    """Service pour gérer les notifications Telegram"""

    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.bot = Bot(token=self.bot_token)
        self.chat_id = settings.TELEGRAM_CHAT_ID

    async def send_message(self, message: str) -> bool:
        """Envoie un message Telegram de manière asynchrone"""
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode="HTML")
            return True
        except TelegramError as e:
            logger.error(f"Erreur lors de l'envoi du message Telegram: {str(e)}")
            return False

    async def notify_new_referral(self, ambassador, referred_user) -> bool:
        """Notification pour un nouveau parrainage"""
        message = (
            f"🎉 <b>Nouveau parrainage !</b>\n\n"
            f"Ambassadeur: {ambassador.username}\n"
            f"Utilisateur référé: {referred_user.username}\n"
            f"Type: {referred_user.user_type}\n"
            f"Date: {referred_user.date_joined.strftime('%d/%m/%Y %H:%M')}"
        )
        return await self.send_message(message)

    async def notify_commission(self, commission) -> bool:
        """Notification pour une nouvelle commission"""
        message = (
            f"💰 <b>Nouvelle commission !</b>\n\n"
            f"Ambassadeur: {commission.referral.ambassador.username}\n"
            f"Montant: {commission.amount} €\n"
            f"Statut: {commission.get_status_display()}\n"
            f"Date: {commission.created_at.strftime('%d/%m/%Y %H:%M')}"
        )
        return await self.send_message(message)

    async def notify_payout(self, payout) -> bool:
        """Notification pour un nouveau paiement"""
        message = (
            f"💸 <b>Nouveau paiement !</b>\n\n"
            f"Ambassadeur: {payout.ambassador.username}\n"
            f"Montant: {payout.amount} €\n"
            f"Méthode: {payout.get_payment_method_display()}\n"
            f"Date: {payout.created_at.strftime('%d/%m/%Y %H:%M')}"
        )
        return await self.send_message(message)

    async def notify_white_label_creation(self, white_label) -> bool:
        """Notification pour la création d'un site white label"""
        message = (
            f"🌐 <b>Nouveau site white label !</b>\n\n"
            f"Ambassadeur: {white_label.ambassador.username}\n"
            f"Nom: {white_label.name}\n"
            f"Domaine: {white_label.domain}\n"
            f"Date: {white_label.created_at.strftime('%d/%m/%Y %H:%M')}"
        )
        return await self.send_message(message)

    async def notify_transaction(self, transaction) -> bool:
        """Notification pour une nouvelle transaction"""
        message = (
            f"💳 <b>Nouvelle transaction !</b>\n\n"
            f"Escort: {transaction.escort.username}\n"
            f"Montant: {transaction.amount} €\n"
            f"Méthode: {transaction.get_payment_method_display()}\n"
            f"Statut: {transaction.get_status_display()}\n"
            f"Date: {transaction.created_at.strftime('%d/%m/%Y %H:%M')}"
        )
        return await self.send_message(message)

    async def notify_error(self, error_message: str) -> bool:
        """Notification pour une erreur système"""
        message = (
            f"⚠️ <b>Erreur système !</b>\n\n"
            f"Message: {error_message}\n"
            f"Date: {timezone.now().strftime('%d/%m/%Y %H:%M')}"
        )
        return await self.send_message(message)
