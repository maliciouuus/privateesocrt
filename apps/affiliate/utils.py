import string
import random
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum
from decimal import Decimal
import logging

from apps.accounts.models import User
from .models import ReferralClick, Referral, Commission

logger = logging.getLogger(__name__)


class AffiliateService:
    """
    Service pour gérer les fonctionnalités d'affiliation.
    Fournit des méthodes pour générer, valider et traiter les codes de référence.
    """

    @staticmethod
    def generate_referral_code(user=None, length=8):
        """
        Génère un code de référence unique pour un utilisateur.
        """
        # Caractères autorisés (lettres majuscules et chiffres, excluant les caractères ambigus)
        chars = "".join(c for c in string.ascii_uppercase + string.digits if c not in "OIL01")

        # Si un utilisateur est fourni, utiliser les deux premières lettres de son nom d'utilisateur
        prefix = ""
        if user and user.username:
            prefix = "".join(c.upper() for c in user.username[:2] if c.isalpha())

        # Compléter jusqu'à la longueur demandée avec des caractères aléatoires
        remaining_length = length - len(prefix)
        if remaining_length > 0:
            random_part = "".join(random.choices(chars, k=remaining_length))
            code = prefix + random_part
        else:
            code = "".join(random.choices(chars, k=length))

        # Vérifier l'unicité
        while User.objects.filter(referral_code=code).exists():
            random_part = "".join(random.choices(chars, k=length - len(prefix)))
            code = prefix + random_part

        return code

    @staticmethod
    def process_referral(referred_user, referrer_code):
        """
        Traite un parrainage entre un utilisateur et un code de parrain.
        Retourne True si le parrainage a été traité avec succès, False sinon.

        Args:
            referred_user (User): L'utilisateur parrainé
            referrer_code (str): Le code de parrainage

        Returns:
            bool: True si le parrainage a été créé/mis à jour avec succès
        """
        # AMÉLIORATION: Validation approfondie des paramètres
        if not referred_user or not referrer_code:
            if not referred_user:
                logger.error("❌ Erreur critique: Aucun utilisateur fourni pour le parrainage")
            if not referrer_code:
                logger.error("❌ Erreur critique: Aucun code de parrainage fourni")
            return False

        # AMÉLIORATION: Journalisation avec identifiants pour faciliter le débogage
        user_id = getattr(referred_user, "id", "inconnu")
        username = getattr(referred_user, "username", "inconnu")
        logger.info(
            f"🔄 Traitement de la relation d'affiliation pour {username} (ID: {user_id}) avec le code {referrer_code}"
        )

        # Chercher le parrain par son code avec gestion d'erreur améliorée
        try:
            referrer = User.objects.get(referral_code=referrer_code)
            logger.info(f"✅ Parrain trouvé: {referrer.username} (ID: {referrer.id})")

            # AMÉLIORATION: Vérifications renforcées et gestion des cas d'erreur
            # Vérifier que l'utilisateur n'est pas déjà parrainé
            if referred_user.referred_by:
                current_referrer = referred_user.referred_by
                logger.warning(
                    f"⚠️ L'utilisateur a déjà un parrain: {current_referrer.username} (ID: {current_referrer.id})"
                )

                # Vérifier si c'est le même parrain (cas de réinscription)
                if current_referrer.id == referrer.id:
                    logger.info(f"✅ Même parrain détecté, mise à jour des relations existantes")
                else:
                    # AMÉLIORATION: Option pour forcer le nouveau parrain (désactivée par défaut)
                    force_update = getattr(settings, "AFFILIATE_FORCE_UPDATE_REFERRER", False)
                    if force_update:
                        logger.warning(
                            f"⚠️ Modification du parrain: {current_referrer.username} -> {referrer.username}"
                        )
                    else:
                        logger.warning(f"❌ Conservation du parrain existant (force_update=False)")
                        return False

            # Vérifier qu'un utilisateur ne peut pas se parrainer lui-même
            if referrer.id == referred_user.id:
                logger.error(
                    f"❌ Un utilisateur ne peut pas se parrainer lui-même: {username} (ID: {user_id})"
                )
                return False

            # Vérifier si referrer est un ambassadeur (validité du parrainage)
            if getattr(referrer, "user_type", None) not in ["ambassador", "admin"]:
                logger.warning(
                    f"⚠️ Le parrain {referrer.username} n'est pas un ambassadeur (type: {getattr(referrer, 'user_type', 'unknown')})"
                )
                # AMÉLIORATION: Option pour permettre ou non les parrains non-ambassadeurs
                allow_non_ambassador = getattr(
                    settings, "AFFILIATE_ALLOW_NON_AMBASSADOR_REFERRER", True
                )
                if not allow_non_ambassador:
                    logger.error(
                        f"❌ Parrainage rejeté: seuls les ambassadeurs peuvent parrainer (allow_non_ambassador=False)"
                    )
                    return False

            # AMÉLIORATION: Transaction atomique pour garantir l'intégrité des données
            from django.db import transaction

            with transaction.atomic():
                # Assigner le parrain à l'utilisateur
                referred_user.referred_by = referrer
                referred_user.save(update_fields=["referred_by"])
                logger.info(
                    f"✅ Parrain assigné à l'utilisateur: {username} -> {referrer.username}"
                )

                # Créer une entrée de parrainage dans l'application affiliate
                referral, created = Referral.objects.get_or_create(
                    ambassador=referrer,
                    referred_user=referred_user,
                    defaults={
                        "is_active": True,
                        "created_at": timezone.now(),
                        "total_earnings": Decimal("0.00"),
                    },
                )

                if created:
                    logger.info(
                        f"✅ Nouvelle entrée Referral créée: {referrer.username} -> {username}"
                    )
                else:
                    logger.info(
                        f"ℹ️ Entrée Referral existante mise à jour: {referrer.username} -> {username}"
                    )

            # AMÉLIORATION: Gestion des notifications dans un bloc séparé pour éviter l'échec complet
            # du parrainage si la notification échoue

            try:
                send_referral_notification(referrer, referred_user)
            except Exception as e:
                logger.error(
                    f"❌ Erreur lors de l'envoi de la notification Telegram: {str(e)}",
                    exc_info=True,
                )

            # AMÉLIORATION: Création des commissions adaptée au type d'utilisateur
            try:
                # Commission uniquement si c'est un nouvel ambassadeur (pas pour les utilisateurs standard)
                if referred_user.user_type == "ambassador" and created:
                    commission = AffiliateService.create_signup_commission(referral)
                    if commission:
                        logger.info(
                            f"💰 Commission d'inscription créée: {commission.amount}€ pour {referrer.username}"
                        )
            except Exception as e:
                logger.error(
                    f"❌ Erreur lors de la création de la commission: {str(e)}",
                    exc_info=True,
                )

            return True

        except User.DoesNotExist:
            logger.error(f"❌ Aucun utilisateur trouvé avec le code de parrainage: {referrer_code}")
            return False
        except Exception as e:
            logger.error(
                f"❌ Exception non gérée lors du traitement du parrainage: {str(e)}",
                exc_info=True,
            )
            return False

    @staticmethod
    def create_signup_commission(referral, amount=None):
        """
        Crée une commission pour l'inscription d'un nouvel ambassadeur.
        """
        if amount is None:
            # Utiliser un montant fixe pour les inscriptions d'ambassadeurs
            amount = Decimal("10.00")

        commission = Commission.objects.create(
            referral=referral,
            amount=amount,
            commission_type="signup",
            description=f"Commission pour l'inscription de {referral.referred_user.username}",
            status="approved",  # Auto-approuver les commissions d'inscription
        )

        # Mettre à jour le total des gains du parrainage
        referral.total_earnings = referral.commissions.filter(
            status__in=["approved", "paid"]
        ).aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00")
        referral.save(update_fields=["total_earnings"])

        return commission

    @staticmethod
    def track_click(ambassador, request):
        """
        Enregistre un clic sur le lien de parrainage d'un ambassadeur.
        """
        # Créer ou récupérer une entrée de clic
        click = ReferralClick.objects.create(
            user=ambassador,
            ip_address=request.META.get("REMOTE_ADDR", "0.0.0.0"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            referrer=request.META.get("HTTP_REFERER", ""),
            landing_page=request.build_absolute_uri(),
        )

        return click

    @staticmethod
    def get_ambassador_stats(ambassador):
        """
        Récupère les statistiques d'un ambassadeur.
        """
        # Récupérer tous les utilisateurs référés
        all_referred_users = User.objects.filter(referred_by=ambassador)

        # Séparer les ambassadeurs des utilisateurs standard
        ambassador_referrals = all_referred_users.filter(user_type="ambassador").count()
        standard_referrals = all_referred_users.filter(user_type="standard").count()

        stats = {
            "clicks": ReferralClick.objects.filter(user=ambassador).count(),
            "referrals": Referral.objects.filter(referrer=ambassador).count(),
            "ambassador_referrals": ambassador_referrals,
            "standard_referrals": standard_referrals,
            "earnings": Commission.objects.filter(
                referral__referrer=ambassador, status__in=["approved", "paid"]
            ).aggregate(Sum("amount"))["amount__sum"]
            or Decimal("0.00"),
            "pending_earnings": Commission.objects.filter(
                referral__referrer=ambassador, status="pending"
            ).aggregate(Sum("amount"))["amount__sum"]
            or Decimal("0.00"),
        }

        # Calcul du taux de conversion
        if stats["clicks"] > 0:
            stats["conversion_rate"] = (stats["referrals"] / stats["clicks"]) * 100
        else:
            stats["conversion_rate"] = 0

        return stats


# AMÉLIORATION: Fonction auxiliaire pour l'envoi de notification avec retry
def send_referral_notification(referrer, referred_user):
    """
    Envoie une notification Telegram au parrain avec mécanisme de retry
    """
    notification_sent = False
    max_retries = getattr(settings, "AFFILIATE_NOTIFICATION_MAX_RETRIES", 3)
    retry_count = 0

    while not notification_sent and retry_count < max_retries:
        try:
            from apps.dashboard.telegram_bot import TelegramNotifier

            notifier = TelegramNotifier()
            success = notifier.send_new_ambassador_notification(referrer, referred_user)

            if success:
                logger.info(
                    f"✅ Notification Telegram envoyée à {referrer.username} (tentative {retry_count+1}/{max_retries})"
                )
                notification_sent = True
            else:
                logger.warning(
                    f"⚠️ Tentative {retry_count+1}/{max_retries}: Échec de l'envoi de la notification Telegram à {referrer.username}"
                )
                retry_count += 1
                import time

                time.sleep(1)  # Attendre 1 seconde avant de réessayer
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'envoi de la notification Telegram: {str(e)}")
            retry_count += 1
            import time

            time.sleep(1)  # Attendre 1 seconde avant de réessayer

    return notification_sent
