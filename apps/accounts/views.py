import uuid
import datetime
import logging
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, update_session_auth_hash, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone
import sys

from .models import User, UserProfile
from .forms import (
    ProfileEditForm,
)
from apps.affiliate.utils import AffiliateService

# Create your views here.


def login_view(request):
    """Vue de connexion simplifiée utilisant les modèles Django"""
    # Logger pour aider au débogage
    logger = logging.getLogger(__name__)
    
    if request.user.is_authenticated:
        logger.info(f"Utilisateur {request.user.username} déjà authentifié, redirection dashboard")
        return redirect("dashboard:home")
        
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        logger.info(f"Tentative de connexion pour l'utilisateur: {username}")
        
        # Authentifier l'utilisateur directement avec username/password
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            logger.info(f"Authentification réussie pour {username}, type={user.user_type}")
            login(request, user)
            messages.success(request, "Connexion réussie!")
            
            # Vérifier le type d'utilisateur
            if user.is_superuser:
                logger.info(f"Utilisateur {username} est admin, redirection dashboard admin")
                redirect_url = "dashboard:admin"
            else:
                logger.info(f"Utilisateur {username} est {user.user_type}, redirection dashboard")
                redirect_url = "dashboard:home"
                
            # Rediriger directement vers le tableau de bord après la connexion réussie
            return redirect(redirect_url)
        else:
            logger.error(f"Échec d'authentification pour {username}")
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    
    return render(request, "account/login.html")

def logout_view(request):
    """Vue de déconnexion standard utilisant les modèles Django"""
    logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect('home')

# Vue pour notre inscription personnalisée (escort ou membre)
def custom_signup_view(request, site_slug=None):
    """Vue pour l'inscription avec choix entre compte escort ou membre."""
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    logger = logging.getLogger(__name__)

    # Contexte pour le site en marque blanche si applicable
    site = None
    is_whitelabel = False

    # Cas spécial pour le slug indian-girls-3f5a9396
    if site_slug == "indian-girls-3f5a9396" or "indian-girls-3f5a9396" in request.path:
        # Créer un objet site minimal pour éviter les erreurs
        from types import SimpleNamespace

        site = SimpleNamespace(
            id=uuid.uuid4(),  # Générer un ID unique
            name="Indian Girls",
            slug="indian-girls-3f5a9396",
            primary_color="#ff4081",
            secondary_color="#3f51b5",
            accent_color="#ff9800",
            primary_rgb="255, 78, 80",
            # Attributs nécessaires pour le context_processor
            logo=None,
            favicon=None,
            custom_css=None,
            custom_js=None,
            commission_rates_override=False,
            escort_commission_rate=15.0,
            ambassador_commission_rate=5.0,
            full_domain="indian-girls-3f5a9396.escortdollars.com",
            status="active",
            custom_domain=None,
            subdomain="indian-girls-3f5a9396",
            get_absolute_url=lambda: f"/public/site/indian-girls-3f5a9396/",
            description="Découvrez des escortes indiennes authentiques",
            description_short="Service d'escortes indiennes premium",
            slogan="Le meilleur des escortes indiennes",
        )
        is_whitelabel = True
        # Set attribute on request for middleware
        request.whitelabel_site = site
        request.is_public_preview = True

        logger.info(f"Cas spécial : création d'un objet site pour indian-girls-3f5a9396")
    # Si on vient d'un site en marque blanche, récupérer les informations du site
    elif site_slug:
        try:
            from escort_platform.shared_core.whitelabel.models import WhiteLabelSite

            site = WhiteLabelSite.objects.get(slug=site_slug)
            is_whitelabel = True
            # Set attribute on request for middleware
            request.whitelabel_site = site
            request.is_public_preview = True

            # Debug log pour tracer les attributs
            logger.info(
                f"Attributs de whitelabel pour la page signup: site={site.name}, is_whitelabel={is_whitelabel}"
            )

        except Exception as e:
            logger.error(f"Erreur lors de la récupération du site whitelabel: {str(e)}")

    # Récupérer le code de parrainage s'il existe
    referral_code = None

    # Vérifier dans l'URL, cookie, ou session
    if "ref" in request.GET:
        referral_code = request.GET.get("ref")
    elif getattr(settings, "AFFILIATE_COOKIE_NAME", "affiliate_code") in request.COOKIES:
        referral_code = request.COOKIES.get(
            getattr(settings, "AFFILIATE_COOKIE_NAME", "affiliate_code")
        )
    elif hasattr(request, "affiliate_code") and request.affiliate_code:
        referral_code = request.affiliate_code

    # Vérifier si le code est valide
    ambassador = None
    if referral_code:
        try:
            ambassador = User.objects.get(referral_code=referral_code)
            logger.info(
                f"Code de référence valide pour l'inscription: {referral_code} ({ambassador.username})"
            )
        except User.DoesNotExist:
            logger.warning(f"Code de référence invalide pour l'inscription: {referral_code}")
            referral_code = None

    if request.method == "POST":
        # Extraire les données du formulaire
        account_type = request.POST.get("account_type")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        date_of_birth = request.POST.get("date_of_birth")

        # Validation de base
        if password1 != password2:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            # IMPORTANT: Utiliser TemplateResponse au lieu de render pour permettre le traitement par le middleware
            from django.template.response import TemplateResponse

            # Utiliser le bon template selon le contexte (whitelabel ou non)
            template_name = (
                "accounts/whitelabel/signup.html" if is_whitelabel else "accounts/signup.html"
            )
            return TemplateResponse(
                request,
                template_name,
                {
                    "referral_code": referral_code,
                    "site": site,
                    "is_whitelabel": is_whitelabel,
                    "whitelabel_site": site,
                },
            )

        # Vérifier si l'email est déjà utilisé
        if User.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
            # IMPORTANT: Utiliser TemplateResponse au lieu de render pour permettre le traitement par le middleware
            from django.template.response import TemplateResponse

            # Utiliser le bon template selon le contexte (whitelabel ou non)
            template_name = (
                "accounts/whitelabel/signup.html" if is_whitelabel else "accounts/signup.html"
            )
            return TemplateResponse(
                request,
                template_name,
                {
                    "referral_code": referral_code,
                    "site": site,
                    "is_whitelabel": is_whitelabel,
                    "whitelabel_site": site,
                },
            )

        # Générer un nom d'utilisateur unique basé sur l'email
        username = email.split("@")[0]
        # Assurer l'unicité en ajoutant un suffixe si nécessaire
        if User.objects.filter(username=username).exists():
            username = f"{username}_{uuid.uuid4().hex[:6]}"

        # Générer un code de parrainage unique
        new_referral_code = AffiliateService.generate_referral_code(length=8)

        # Créer l'utilisateur avec le type approprié
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            user_type=account_type,  # 'escort' ou 'member'
            referral_code=new_referral_code,
            referred_by=ambassador,
            is_active=False,  # Compte inactif jusqu'à la vérification par email
        )

        # Créer ou mettre à jour le profil utilisateur
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.date_of_birth = date_of_birth

        # Traiter les champs spécifiques selon le type de compte
        if account_type == "escort":
            escort_name = request.POST.get("escort_name")
            gender = request.POST.get("gender")
            location = request.POST.get("location")
            hourly_rate = request.POST.get("hourly_rate")
            description = request.POST.get("description")

            # Mettre à jour le profil avec les informations d'escort
            profile.professional_name = escort_name or f"{first_name} {last_name}"
            profile.gender = gender
            profile.location = location
            profile.hourly_rate = hourly_rate
            profile.description = description

            # Traiter l'image de profil si fournie
            profile_image = request.FILES.get("profile_image")
            if profile_image:
                profile.profile_image = profile_image

            # Marquer le compte comme en attente de vérification
            profile.verification_status = "pending"
        else:  # member
            location_member = request.POST.get("location_member")
            profile.location = location_member

            # Traiter les préférences
            preferences = request.POST.getlist("preferences[]")
            if preferences:
                profile.preferences = ",".join(preferences)

        # Sauvegarder le profil
        profile.save()

        # Envoyer l'email de vérification
        # ... (code pour l'envoi d'email)

        # Afficher un message de succès
        messages.success(
            request,
            "Votre compte a été créé avec succès. Veuillez vérifier votre email pour activer votre compte.",
        )

        # Rediriger vers la page d'activation envoyée ou vers le site whitelabel
        if site_slug:
            # Option 2: Rediriger vers la page d'activation en préservant le contexte whitelabel
            # Pour cela, on utilise une HttpResponseRedirect personnalisée

            # Conserver les attributs whitelabel pour la prochaine requête
            request.session["whitelabel_site_slug"] = site_slug

            # Rediriger vers la page d'activation
            response = HttpResponseRedirect(reverse("accounts:activation_sent"))

            # Log pour debugger
            logger.info(f"Redirection vers activation_sent avec whitelabel_site_slug={site_slug}")

            return response
        else:
            return redirect("accounts:activation_sent")

    # Préparer des variables de contexte pour le template
    context = {
        "referral_code": referral_code,
    }

    # Ajouter le site au contexte seulement s'il a un slug valide
    if site and hasattr(site, "slug") and site.slug:
        context.update(
            {
                "site": site,
                "is_whitelabel": True,
                "whitelabel_site": site,  # Ajouter explicitement pour la cohérence
            }
        )
    else:
        context.update(
            {
                "site": None,
                "is_whitelabel": False,
                "whitelabel_site": None,
            }
        )

    # Debug log pour vérifier le contexte
    logger.info(
        f"Contexte pour le template signup: is_whitelabel={is_whitelabel}, site présent={site is not None}"
    )
    if site:
        logger.info(f"Détails du site: id={site.id}, slug={getattr(site, 'slug', 'Pas de slug')}")

    # IMPORTANT: Utiliser TemplateResponse au lieu de render
    # Cela permet aux middleware (notamment WhiteLabelMiddleware) de traiter la réponse
    # et d'ajouter les informations nécessaires au contexte pour le rendu correct du header et footer
    from django.template.response import TemplateResponse

    # Choisir le template approprié selon que l'on est dans un contexte de whitelabel ou non
    # Pour WhiteLabel, utiliser le template dans accounts/whitelabel/
    template_name = (
        "accounts/whitelabel/signup.html"
        if is_whitelabel and site and hasattr(site, "slug") and site.slug
        else "accounts/signup.html"
    )

    # Mettre à jour les valeurs dans le middleware
    if is_whitelabel and site and hasattr(site, "slug") and site.slug:
        request.whitelabel_site = site
        request.is_public_preview = True
        logger.info(
            f"Attributs whitelabel définis sur la requête avant TemplateResponse: site={site.name}"
        )

    return TemplateResponse(request, template_name, context)


# Vues d'inscription
def register_view(request):
    """Vue pour rediriger directement vers l'inscription ambassadeur."""
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    # Redirection directe vers l'inscription ambassadeur
    return redirect("accounts:register_ambassador")


# Nouvelle fonction pour intercepter les inscriptions Allauth
def signup_redirect(request):
    """
    Intercepte les inscriptions standards Allauth et les redirige vers la page
    d'inscription personnalisée en préservant le code de parrainage.
    """
    # Récupérer le code de parrainage s'il existe
    ref_code = None

    # Vérifier si le code est dans l'URL
    if settings.AFFILIATE_REF_PARAM in request.GET:
        ref_code = request.GET.get(settings.AFFILIATE_REF_PARAM)

    # Sinon, vérifier dans les cookies
    elif settings.AFFILIATE_COOKIE_NAME in request.COOKIES:
        ref_code = request.COOKIES.get(settings.AFFILIATE_COOKIE_NAME)

    # Sinon, vérifier dans la session (middleware peut l'avoir stocké)
    elif "affiliate_code" in request.session:
        ref_code = request.session.get("affiliate_code")

    # Construire l'URL de redirection
    redirect_url = reverse("accounts:register_ambassador")
    if ref_code:
        redirect_url += f"?{settings.AFFILIATE_REF_PARAM}={ref_code}"

    # Journaliser la redirection
    logger = logging.getLogger(__name__)
    logger.info(
        f"Redirection de l'inscription standard vers inscription ambassadeur. Code de parrainage: {ref_code}"
    )

    return redirect(redirect_url)


def register_ambassador_view(request):
    """Vue d'inscription pour ambassadeur."""
    # Ajouter des logs de débogage
    print("======= DÉBUT DE REGISTER_AMBASSADOR_VIEW =======", file=sys.stderr)
    print(f"Method: {request.method}", file=sys.stderr)
    
    if request.user.is_authenticated:
        print("Utilisateur déjà authentifié, redirection vers dashboard:home", file=sys.stderr)
        return redirect("dashboard:home")

    # Définir le logger pour cette fonction
    logger = logging.getLogger(__name__)

    # 1. AMÉLIORATION: Capture plus robuste du code de référence avec journalisation détaillée
    referral_code = None

    # Récupérer depuis l'URL avec logging amélioré
    url_ref_code = request.GET.get("ref")
    if url_ref_code:
        referral_code = url_ref_code
        print(f"Code de référence détecté dans l'URL: {referral_code}", file=sys.stderr)
        logger.info(f"🔍 Code de référence détecté dans l'URL: {referral_code}")

    # Récupérer depuis le cookie
    cookie_ref_code = request.COOKIES.get(
        getattr(settings, "AFFILIATE_COOKIE_NAME", "affiliate_code")
    )
    if cookie_ref_code and not referral_code:
        referral_code = cookie_ref_code
        print(f"Code de référence récupéré depuis le cookie: {referral_code}", file=sys.stderr)
        logger.info(f"🔍 Code de référence récupéré depuis le cookie: {referral_code}")

    # Récupérer depuis le middleware
    middleware_code = getattr(request, "affiliate_code", None)
    if middleware_code and not referral_code:
        referral_code = middleware_code
        print(f"Code de référence récupéré depuis le middleware: {referral_code}", file=sys.stderr)
        logger.info(f"🔍 Code de référence récupéré depuis le middleware: {referral_code}")

    # 2. AMÉLIORATION: Vérification préliminaire de la validité du code
    ambassador = None
    if referral_code:
        try:
            ambassador = User.objects.get(referral_code=referral_code)
            print(f"Code de référence valide, appartient à: {ambassador.username}", file=sys.stderr)
            logger.info(f"✅ Code de référence valide, appartient à: {ambassador.username}")
        except User.DoesNotExist:
            print(f"Code de référence invalide ou inexistant: {referral_code}", file=sys.stderr)
            logger.warning(f"⚠️ Code de référence invalide ou inexistant: {referral_code}")
            referral_code = None

    print(f"Vue d'inscription - Code de référence final: {referral_code}", file=sys.stderr)
    logger.info(f"📋 Vue d'inscription - Code de référence final: {referral_code}")

    if request.method == "POST":
        print("Traitement d'une requête POST", file=sys.stderr)
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        
        print(f"Données du formulaire - Username: {username}, Email: {email}", file=sys.stderr)

        # 3. AMÉLIORATION: Conservation prioritaire du code de formulaire
        form_ref_code = request.POST.get("referral_code")
        if form_ref_code:
            # Vérifier si le code du formulaire est valide
            try:
                form_ambassador = User.objects.get(referral_code=form_ref_code)
                referral_code = form_ref_code
                ambassador = form_ambassador
                logger.info(
                    f"✅ Code de référence du formulaire valide: {referral_code} ({ambassador.username})"
                )
            except User.DoesNotExist:
                logger.warning(f"⚠️ Code de référence du formulaire invalide: {form_ref_code}")

        # Validations de base
        if password1 != password2:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            response = render(
                request,
                "accounts/register_ambassador.html",
                {"referral_code": referral_code},
            )
            return response

        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur est déjà utilisé.")
            response = render(
                request,
                "accounts/register_ambassador.html",
                {"referral_code": referral_code},
            )
            return response

        if User.objects.filter(email=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
            response = render(
                request,
                "accounts/register_ambassador.html",
                {"referral_code": referral_code},
            )
            return response

        # Générer un code de référence unique pour le nouvel utilisateur
        new_referral_code = AffiliateService.generate_referral_code(length=8)

        # 4. AMÉLIORATION: Assignation directe du parrain si disponible
        referred_by = ambassador if ambassador else None

        # Créer l'utilisateur ambassadeur avec référent si disponible
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            user_type="ambassador",
            referral_code=new_referral_code,
            referred_by=referred_by,  # Assigner directement le parrain
            is_active=False,  # Compte inactif jusqu'à la vérification par email
        )

        # 5. AMÉLIORATION: Traitement plus robuste de l'affiliation
        if referral_code and ambassador:
            logger.info(
                f"🔄 Établissement de la relation d'affiliation pour {username} avec {ambassador.username} (code: {referral_code})"
            )

            # Double vérification que le referred_by est bien assigné
            if not user.referred_by:
                user.referred_by = ambassador
                user.save(update_fields=["referred_by"])
                logger.info(f"✅ Référent assigné manuellement: {ambassador.username}")

            # Créer l'entrée dans Referral si elle n'existe pas
            from apps.affiliate.models import Referral

            referral, created = Referral.objects.get_or_create(
                ambassador=ambassador,
                referred_user=user,
                defaults={
                    "is_active": True,
                    "created_at": timezone.now(),
                    "total_earnings": 0,
                },
            )

            if created:
                logger.info(
                    f"✅ Nouvelle entrée Referral créée: {ambassador.username} -> {user.username}"
                )
            else:
                logger.info(
                    f"ℹ️ Entrée Referral existante: {ambassador.username} -> {user.username}"
                )

            # Notification Telegram et commissions seront traitées après activation du compte

        # Envoyer l'email de vérification
        from django.template.loader import render_to_string
        from django.contrib.sites.shortcuts import get_current_site
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.core.mail import EmailMessage

        # Générer le token d'activation
        from django.contrib.auth.tokens import default_token_generator

        token = default_token_generator.make_token(user)

        current_site = get_current_site(request)
        mail_subject = "Activez votre compte EscortDollars"

        # Préparer le contexte pour le template d'email
        message = render_to_string(
            "accounts/email/account_activation_email.html",
            {
                "user": user,
                "domain": current_site.domain,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": token,
                "protocol": "https" if request.is_secure() else "http",
            },
        )

        # Envoyer l'email
        to_email = email
        email_message = EmailMessage(mail_subject, message, to=[to_email])
        email_message.content_subtype = "html"  # Pour envoyer en HTML

        try:
            email_message.send()
            logger.info(f"✅ Email de vérification envoyé à {email}")
        except Exception as e:
            logger.error(
                f"❌ Erreur lors de l'envoi de l'email de vérification: {str(e)}",
                exc_info=True,
            )
            # En cas d'erreur d'envoi, on active quand même le compte en dev
            if settings.DEBUG:
                user.is_active = True
                user.save()
                logger.warning(
                    "⚠️ Compte activé automatiquement en mode DEBUG malgré l'échec d'envoi de l'email"
                )

        # Rediriger vers la page de confirmation d'envoi d'email
        if referral_code:
            cookie_name = getattr(settings, "AFFILIATE_COOKIE_NAME", "affiliate_code")
            cookie_age = getattr(settings, "AFFILIATE_COOKIE_AGE", 60 * 60 * 24 * 30)
            response = redirect("accounts:activation_sent")
            response.set_cookie(
                cookie_name,
                referral_code,
                max_age=cookie_age,
                httponly=True,
                samesite="Lax",
            )
            return response

        return redirect("accounts:activation_sent")

    # Avant de rendre le template
    print("Rendu du template accounts/register_ambassador.html", file=sys.stderr)
    try:
        return render(
            request,
            "accounts/register_ambassador.html",
            {"referral_code": referral_code},
        )
    except Exception as e:
        print(f"ERREUR lors du rendu du template: {str(e)}", file=sys.stderr)
        raise


def activate_account(request, uidb64, token):
    """Active le compte utilisateur après confirmation par e-mail."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)

        # Vérifier le token
        from django.contrib.auth.tokens import default_token_generator

        if default_token_generator.check_token(user, token):
            logger = logging.getLogger(__name__)
            logger.info(f"✅ Activation du compte de {user.username}")

            # Si le compte est déjà activé
            if user.is_active:
                messages.info(request, "Votre compte est déjà activé. Vous pouvez vous connecter.")
                return redirect("accounts:login")

            # Activer le compte
            user.is_active = True
            user.save()

            # Traiter les notifications et commissions qui n'ont pas été traitées à l'inscription
            if user.referred_by:
                ambassador = user.referred_by

                # Récupérer l'entrée Referral
                from apps.affiliate.models import Referral

                referral = Referral.objects.filter(
                    ambassador=ambassador, referred_user=user
                ).first()

                if referral:
                    # Envoyer notification Telegram au parrain
                    try:
                        from apps.dashboard.telegram_bot import TelegramNotifier

                        notifier = TelegramNotifier()

                        # Implémentation de retry
                        max_attempts = 3
                        for attempt in range(1, max_attempts + 1):
                            telegram_success = notifier.send_new_ambassador_notification(
                                ambassador, user
                            )
                            if telegram_success:
                                logger.info(
                                    f"✅ Notification Telegram envoyée à {ambassador.username} (tentative {attempt}/{max_attempts})"
                                )
                                break
                            else:
                                logger.warning(
                                    f"⚠️ Échec de l'envoi de la notification Telegram à {ambassador.username} (tentative {attempt}/{max_attempts})"
                                )
                                if attempt < max_attempts:
                                    import time

                                    time.sleep(1)  # Attendre 1 seconde avant de réessayer
                    except Exception as e:
                        logger.error(
                            f"❌ Erreur lors de l'envoi de la notification Telegram: {str(e)}",
                            exc_info=True,
                        )

                    # Créer la commission pour le parrain
                    try:
                        from apps.affiliate.utils import AffiliateService

                        AffiliateService.create_signup_commission(referral)
                        logger.info(f"✅ Commission d'inscription créée pour {ambassador.username}")
                    except Exception as e:
                        logger.error(
                            f"❌ Erreur lors de la création de la commission: {str(e)}",
                            exc_info=True,
                        )

            messages.success(
                request,
                "Votre compte a été activé avec succès! Vous pouvez maintenant vous connecter.",
            )
            return redirect("accounts:login")
        else:
            messages.error(request, "Le lien d'activation est invalide ou a expiré.")
            return redirect("accounts:login")
    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist,
        ValidationError,
    ) as e:
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Erreur lors de l'activation du compte: {str(e)}", exc_info=True)
        messages.error(request, "Le lien d'activation est invalide ou a expiré.")
        return redirect("accounts:login")


def activation_sent(request):
    """Page affichée après envoi de l'e-mail d'activation."""
    # Vérifier si nous sommes dans un contexte de site en marque blanche
    is_whitelabel = False
    site = None

    # Cas spécial pour le site indian-girls-3f5a9396
    if "indian-girls-3f5a9396" in request.path or (
        "whitelabel_site_slug" in request.session
        and request.session["whitelabel_site_slug"] == "indian-girls-3f5a9396"
    ):
        # Créer un objet site minimal pour éviter les erreurs
        from types import SimpleNamespace

        site = SimpleNamespace(
            id=uuid.uuid4(),  # Générer un ID unique
            name="Indian Girls",
            slug="indian-girls-3f5a9396",
            primary_color="#ff4081",
            secondary_color="#3f51b5",
            accent_color="#ff9800",
            primary_rgb="255, 78, 80",
            # Attributs nécessaires pour le context_processor
            logo=None,
            favicon=None,
            custom_css=None,
            custom_js=None,
            commission_rates_override=False,
            escort_commission_rate=15.0,
            ambassador_commission_rate=5.0,
            full_domain="indian-girls-3f5a9396.escortdollars.com",
            status="active",
            custom_domain=None,
            subdomain="indian-girls-3f5a9396",
            get_absolute_url=lambda: f"/public/site/indian-girls-3f5a9396/",
            description="Découvrez des escortes indiennes authentiques",
            description_short="Service d'escortes indiennes premium",
            slogan="Le meilleur des escortes indiennes",
        )
        is_whitelabel = True
        # Set attribute on request for middleware
        request.whitelabel_site = site
        request.is_public_preview = True

        logger = logging.getLogger(__name__)
        logger.info(
            f"Cas spécial : création d'un objet site pour indian-girls-3f5a9396 dans activation_sent"
        )

    # 1. Vérifier si le site est déjà défini dans la requête par le middleware
    elif hasattr(request, "whitelabel_site") and request.whitelabel_site:
        is_whitelabel = True
        site = request.whitelabel_site

    # 2. Sinon, vérifier si le slug du site est dans la session
    elif "whitelabel_site_slug" in request.session:
        site_slug = request.session.get("whitelabel_site_slug")
        try:
            from escort_platform.shared_core.whitelabel.models import WhiteLabelSite

            site = WhiteLabelSite.objects.get(slug=site_slug)
            is_whitelabel = True

            # Définir les attributs sur la requête pour le middleware
            request.whitelabel_site = site
            request.is_public_preview = True

            # Supprimer le slug de la session pour éviter les problèmes futurs
            del request.session["whitelabel_site_slug"]
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur lors de la récupération du site whitelabel: {str(e)}")

    logger = logging.getLogger(__name__)
    logger.info(
        f"Page activation_sent - whitelabel: {is_whitelabel}, site: {site.name if site else None}"
    )

    # Vérifier que le site a un slug valide
    if site and not hasattr(site, "slug"):
        logger.error(f"Le site whitelabel n'a pas d'attribut slug: {site}")
        site = None
        is_whitelabel = False

    # Choisir le bon template selon le contexte
    template_name = (
        "accounts/whitelabel/activation_sent.html"
        if is_whitelabel
        else "accounts/activation_sent.html"
    )

    return render(request, template_name, {"is_whitelabel": is_whitelabel, "site": site})


# Gestion de profil
@login_required
def profile_view(request):
    """Affiche le profil de l'utilisateur connecté."""
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    return render(
        request,
        "accounts/profile.html",
        {"user": request.user, "profile": user_profile},
    )


@login_required
def edit_profile(request):
    """Vue pour modifier les informations du profil."""
    user_profile = request.user.account_profile

    if request.method == "POST":
        form = ProfileEditForm(request.POST, instance=user_profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Votre profil a été mis à jour avec succès.")
            return redirect("accounts:profile")
    else:
        form = ProfileEditForm(instance=user_profile, user=request.user)

    return render(request, "accounts/edit_profile.html", {"form": form})


@login_required
def change_password(request):
    """Vue pour changer le mot de passe."""
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Important pour garder l'utilisateur connecté après changement de mot de passe
            update_session_auth_hash(request, user)
            messages.success(request, "Votre mot de passe a été mis à jour avec succès!")
            return redirect("accounts:profile")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "accounts/change_password.html", {"form": form})


@login_required
def delete_account(request):
    """Vue pour supprimer le compte utilisateur."""
    if request.method == "POST":
        password = request.POST.get("password")
        user = authenticate(username=request.user.username, password=password)

        if user is not None:
            # Désactiver le compte plutôt que de le supprimer complètement
            user.is_active = False
            user.save()

            messages.success(request, "Votre compte a été désactivé avec succès.")
            return redirect("home")
        else:
            messages.error(request, "Mot de passe incorrect.")

    return render(request, "accounts/delete_account.html")


# Vue explicite pour rediriger la page d'inscription Allauth
@require_GET
def redirect_signup(request):
    """
    Redirige vers la page d'inscription d'allauth.
    """
    logger = logging.getLogger(__name__)
    logger.info("Redirection vers la page d'inscription d'allauth")

    # Récupérer tous les paramètres d'URL et les conserver dans la redirection
    params = request.GET.copy()
    redirect_url = reverse("accounts:signup")

    # Ajouter les paramètres d'URL s'il y en a
    if params:
        # Transformer les paramètres en chaîne de requête
        query_string = params.urlencode()
        redirect_url = f"{redirect_url}?{query_string}"

    return redirect(redirect_url)
