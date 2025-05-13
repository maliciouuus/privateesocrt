from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
import json
import hashlib
import hmac
import logging
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import User
from apps.affiliate.models import Referral, Commission
from apps.dashboard.telegram_bot import TelegramNotifier
from apps.affiliate.services import SupabaseService

logger = logging.getLogger(__name__)
User = get_user_model()

# Clé d'API pour sécuriser les requêtes
API_KEY = getattr(settings, "EXTERNAL_API_KEY", "change_this_to_a_secret_key")


def verify_signature(request):
    """Vérifie la signature de la requête pour s'assurer qu'elle provient d'une source autorisée."""
    provided_signature = request.headers.get("X-Api-Signature")
    if not provided_signature:
        return False

    # Calculer la signature attendue
    body = request.body
    expected_signature = hmac.new(API_KEY.encode(), body, hashlib.sha256).hexdigest()

    # Comparer les signatures (constante pour éviter les attaques timing)
    return hmac.compare_digest(expected_signature, provided_signature)


@csrf_exempt
@require_POST
def register_external_escort(request):
    """
    API pour enregistrer une escorte depuis un site white label
    """
    try:
        # Vérifier l'API key
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != settings.EXTERNAL_API_KEY:
            logger.warning(f"Tentative d'accès avec une API key invalide: {api_key}")
            return JsonResponse({"error": "API key invalide"}, status=403)

        # Décoder les données
        data = json.loads(request.body)
        logger.info(f"Traitement de l'enregistrement d'une escorte externe: {data}")

        # Vérifier les champs obligatoires
        required_fields = [
            "affiliate_id",
            "escort_id",
            "escort_username",
            "escort_email",
        ]
        for field in required_fields:
            if field not in data:
                logger.error(f"Champ manquant dans la requête: {field}")
                return JsonResponse({"error": f"Champ manquant: {field}"}, status=400)

        # Récupérer l'ambassadeur
        try:
            ambassador = User.objects.get(referral_code=data["affiliate_id"])
            logger.info(f"Ambassadeur trouvé: {ambassador.username}")
        except User.DoesNotExist:
            logger.warning(f"Aucun ambassadeur trouvé avec le code: {data['affiliate_id']}")
            return JsonResponse({"error": "Code d'affiliation invalide"}, status=404)

        # Créer l'utilisateur escorte
        escort = User.objects.create_user(
            username=data["escort_username"],
            email=data["escort_email"],
            password=User.objects.make_random_password(),
            user_type="escort",
            referred_by=ambassador,
            is_active=True,
        )

        # Créer la relation de référence
        referral = Referral.objects.create(
            ambassador=ambassador,
            referred_user=escort,
            is_active=True,
            created_at=timezone.now(),
            total_earnings=0,
        )

        # Synchroniser avec Supabase
        supabase_service = SupabaseService()
        supabase_service.sync_referral(referral)

        # Envoyer une notification Telegram à l'ambassadeur
        try:
            notifier = TelegramNotifier()

            if ambassador.telegram_chat_id:
                # Messages multilingues
                languages = {
                    "en": f"New escort registered through your referral link: {escort.username}",
                    "fr": f"Nouvelle escorte inscrite via votre lien de parrainage : {escort.username}",
                    "es": f"Nueva escort registrada a través de tu enlace de referido: {escort.username}",
                    "de": f"Neue Escort über Ihren Empfehlungslink registriert: {escort.username}",
                    "ru": f"Новая эскорт зарегистрирована по вашей реферальной ссылке: {escort.username}",
                    "zh": f"通过您的推荐链接注册的新伴游：{escort.username}",
                    "it": f"Nuova escort registrata tramite il tuo link di referral: {escort.username}",
                    "ar": f"تم تسجيل مرافقة جديدة من خلال رابط الإحالة الخاص بك: {escort.username}",
                }

                # Déterminer la langue de l'utilisateur
                lang = (
                    ambassador.telegram_language
                    if ambassador.telegram_language in languages
                    else "en"
                )
                message = languages[lang]

                # Titre de la notification
                titles = {
                    "en": "New Referral",
                    "fr": "Nouveau Parrainage",
                    "es": "Nueva Referencia",
                    "de": "Neue Empfehlung",
                    "ru": "Новая Реферальная",
                    "zh": "新推荐",
                    "it": "Nuovo Referral",
                    "ar": "إحالة جديدة",
                }
                title = titles.get(lang, titles["en"])

                # Envoyer la notification
                notifier.send_message(
                    chat_id=ambassador.telegram_chat_id,
                    message=f"*{title}*\n\n{message}",
                )
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")

        return JsonResponse(
            {
                "success": True,
                "message": "Escort registered successfully",
                "escort_id": str(escort.id),
                "referral_id": str(referral.id),
            }
        )

    except json.JSONDecodeError:
        logger.error("Invalid JSON request body")
        return JsonResponse({"error": "Invalid JSON request body"}, status=400)
    except Exception as e:
        logger.exception(f"Error processing escort registration: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@csrf_exempt
@require_POST
def register_external_payment(request):
    """
    Enregistre un paiement provenant d'un système externe.

    Exemple de payload:
    {
        "username": "escort_username",
        "amount": 100.50,
        "source": "external_site_A",
        "payment_id": "PAYMENT123",
        "payment_date": "2023-05-15T14:30:00Z",
        "description": "Premium subscription payment"
    }
    """
    # Vérifier l'authentification
    if not verify_signature(request):
        logger.warning("Tentative d'accès non autorisé à l'API register_external_payment")
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body)
        username = data.get("username")
        amount = data.get("amount")
        source = data.get("source", "unknown")
        payment_id = data.get("payment_id")
        data.get("payment_date")
        description = data.get("description", "External payment")

        if not username or not amount or not payment_id:
            return JsonResponse(
                {"status": "error", "message": "Missing required fields"}, status=400
            )

        # Vérifier si l'escorte existe
        try:
            escort = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": f"User {username} not found"}, status=404
            )

        # Vérifier si l'escorte a un référent
        if not escort.referred_by:
            return JsonResponse(
                {"status": "warning", "message": f"User {username} has no referrer"},
                status=200,
            )

        # Calculer la commission (à personnaliser selon votre modèle économique)
        # Par exemple, 10% du montant du paiement
        commission_amount = amount * 0.10

        # Créer l'entrée Commission
        commission = Commission.objects.create(
            referral=Referral.objects.get(ambassador=escort.referred_by, referred_user=escort),
            amount=commission_amount,
            description=f"{description} - {source} - {payment_id}",
            status="approved",  # Ou 'pending' selon votre logique métier
        )

        # Mettre à jour le total des gains dans Referral
        referral = commission.referral
        referral.total_earnings += Decimal(str(commission_amount))
        referral.save()

        # Envoyer une notification Telegram au référent
        try:
            notifier = TelegramNotifier()
            # Utiliser la méthode dédiée pour envoyer une notification de commission
            notification_sent = notifier.send_commission_notification(
                referrer=escort.referred_by,
                referred_user=escort,
                amount=commission_amount,
                total_earnings=referral.total_earnings,
            )
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")
            notification_sent = False

        return JsonResponse(
            {
                "status": "success",
                "message": "Payment registered successfully",
                "commission_id": commission.id,
                "commission_amount": float(commission_amount),
                "notification_sent": notification_sent,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception(f"Error in register_external_payment: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
