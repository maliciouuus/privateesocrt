from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import logging
from apps.accounts.models import User
from django.utils.timezone import now

logger = logging.getLogger(__name__)
logger_audit = logging.getLogger("affiliate.audit")


class AffiliateMiddleware(MiddlewareMixin):
    """
    Middleware qui capture les codes d'affiliation et les stocke dans un cookie persistant.
    Le cookie est conservé pendant 30 jours pour maximiser les chances de conversion,
    même si l'utilisateur revient après plusieurs jours.
    """

    def process_request(self, request):
        # Configuration
        REF_PARAM = getattr(settings, "AFFILIATE_REF_PARAM", "ref")
        COOKIE_NAME = getattr(settings, "AFFILIATE_COOKIE_NAME", "affiliate_code")
        # Durée explicite de 30 jours en secondes (2 592 000 secondes)
        COOKIE_AGE = getattr(
            settings, "AFFILIATE_COOKIE_AGE", 60 * 60 * 24 * 30
        )  # 30 jours par défaut
        AFFILIATE_FIRST_TOUCH = getattr(
            settings, "AFFILIATE_FIRST_TOUCH", True
        )  # Conserver le premier affiliateur

        # AMÉLIORATION: Logging plus détaillé des paramètres d'URL pour le débogage
        full_path = request.get_full_path()
        if "?" in full_path:
            logger.info(f"📥 URL avec paramètres: {full_path}")
            # Journaliser de manière plus détaillée chaque paramètre (utile pour debug)
            for key, value in request.GET.items():
                logger.info(f"📝 Paramètre URL: {key}={value}")

        # Vérifier s'il y a un code de référence dans l'URL
        ref_code = request.GET.get(REF_PARAM)

        if ref_code:
            # AMÉLIORATION: Vérification de la validité du code
            try:
                referrer = User.objects.get(referral_code=ref_code)
                logger.info(
                    f"✅ Code de référence valide dans l'URL: {ref_code} (Utilisateur: {referrer.username})"
                )
                is_valid = True
            except User.DoesNotExist:
                logger.warning(f"❌ Code de référence invalide dans l'URL: {ref_code}")
                is_valid = False
            except Exception as e:
                logger.error(f"❌ Erreur lors de la vérification du code de référence: {str(e)}")
                is_valid = False

            # Continuer uniquement si le code est valide
            if is_valid:
                # Ajouter le code à l'objet request pour faciliter l'accès
                request.affiliate_code = ref_code

                # Vérifier si nous respectons le "first touch" (premier contact)
                cookie_ref_code = request.COOKIES.get(COOKIE_NAME)
                if cookie_ref_code and AFFILIATE_FIRST_TOUCH:
                    logger.info(
                        f"ℹ️ Cookie existant trouvé: {cookie_ref_code}, respectant 'first touch'"
                    )
                    request.affiliate_code = cookie_ref_code
                    return

                # AMÉLIORATION: Ajout de méta-données supplémentaires
                request._affiliate_meta = {
                    "referrer_username": referrer.username,
                    "referrer_id": referrer.id,
                    "source": "url_param",
                    "timestamp": request.META.get("REQUEST_TIME", 0),
                }

                # Définir un cookie qui sera placé dans la réponse
                request._affiliate_cookie_to_set = {
                    "name": COOKIE_NAME,
                    "value": ref_code,
                    "max_age": COOKIE_AGE,
                    "secure": request.is_secure(),
                    "httponly": True,
                    "samesite": "Lax",  # Permet le suivi lors d'une redirection depuis un site externe
                    "expires": None,  # Laissez Django calculer la date d'expiration à partir de max_age
                }
        else:
            # AMÉLIORATION: Récupérer le code depuis le cookie avec validation
            cookie_ref_code = request.COOKIES.get(COOKIE_NAME)
            if cookie_ref_code:
                # Vérifier si le code dans le cookie est toujours valide
                try:
                    referrer = User.objects.get(referral_code=cookie_ref_code)
                    logger.info(
                        f"✅ Code de référence valide dans le cookie: {cookie_ref_code} (Utilisateur: {referrer.username})"
                    )
                    request.affiliate_code = cookie_ref_code

                    # AMÉLIORATION: Ajout de méta-données supplémentaires
                    request._affiliate_meta = {
                        "referrer_username": referrer.username,
                        "referrer_id": referrer.id,
                        "source": "cookie",
                        "timestamp": request.META.get("REQUEST_TIME", 0),
                    }
                except User.DoesNotExist:
                    logger.warning(
                        f"❌ Code de référence invalide dans le cookie: {cookie_ref_code}"
                    )
                    request.affiliate_code = None
                except Exception as e:
                    logger.error(
                        f"❌ Erreur lors de la vérification du code de référence dans le cookie: {str(e)}"
                    )
                    request.affiliate_code = None
            else:
                logger.debug(f"ℹ️ Aucun code de référence trouvé (ni URL, ni cookie)")
                request.affiliate_code = None

    def process_response(self, request, response):
        # AMÉLIORATION: Gestion plus robuste du cookie avec logging détaillé
        if hasattr(request, "_affiliate_cookie_to_set"):
            cookie_data = request._affiliate_cookie_to_set
            logger.info(f"🍪 Définition du cookie d'affiliation: {cookie_data['value']}")

            # Définir le cookie pour la durée spécifiée
            try:
                response.set_cookie(
                    cookie_data["name"],
                    cookie_data["value"],
                    max_age=cookie_data["max_age"],
                    secure=cookie_data["secure"],
                    httponly=cookie_data["httponly"],
                    samesite=cookie_data["samesite"],
                )
                logger.info(f"✅ Cookie d'affiliation défini avec succès: {cookie_data['value']}")
            except Exception as e:
                logger.error(f"❌ Erreur lors de la définition du cookie d'affiliation: {str(e)}")

        return response


class ReferralMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Ne pas traiter les requêtes pour les fichiers statiques
        if request.path.startswith("/static/"):
            return None

        # Récupérer le code de référence de l'URL ou du cookie
        ref_code = request.GET.get("ref") or request.COOKIES.get("ref_code")

        if ref_code:
            # Si un code est trouvé, on le stocke dans la session
            request.session["ref_code"] = ref_code
            logger.debug(f"✅ Code de référence trouvé : {ref_code}")
        else:
            # Ne pas logger pour les requêtes statiques ou les assets
            if not any(request.path.startswith(p) for p in ["/static/", "/media/", "/favicon.ico"]):
                logger.debug("ℹ️ Aucun code de référence trouvé")

        return None

    def process_response(self, request, response):
        # Si un code de référence est trouvé dans l'URL, on le stocke dans un cookie
        ref_code = request.GET.get("ref")
        if ref_code:
            # Définir le cookie pour 30 jours
            response.set_cookie("ref_code", ref_code, max_age=30 * 24 * 60 * 60)
        return response


SENSITIVE_PATHS = [
    "/admin/",
    "/api/commission-rates/",
    "/api/payouts/mark_paid/",
    "/api/white-labels/",
]


class AuditLogMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path
        if any(path.startswith(p) for p in SENSITIVE_PATHS):
            user = getattr(request, "user", None)
            username = user.username if user and user.is_authenticated else "anonymous"
            method = request.method
            data = request.POST.dict() if method in ["POST", "PUT"] else {}
            logger_audit.info(
                f"[AUDIT] {now()} | User: {username} | Method: {method} | Path: {path} | Data: {data}"
            )
        return None
