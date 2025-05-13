from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse, FileResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import uuid
import logging
from decimal import Decimal
from apps.dashboard.telegram_bot import TelegramNotifier
import datetime
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models.functions import TruncDay
from django.db.models import Q
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import (
    ReferralClick,
    Referral,
    Commission,
    Transaction,
    Payout,
    CommissionRate,
    WhiteLabel,
    AffiliateLevel,
    Badge,
    PaymentMethod,
    MarketingMaterial,
    Notification,
)
from apps.accounts.models import User
from .forms import (
    CommissionRateForm,
    WhiteLabelForm,
    CryptoPaymentForm,
    PaymentMethodForm,
)
from .services import SupabaseService

# Configurer le logger
logger = logging.getLogger(__name__)


# Page d'accueil de l'affiliation
@login_required
def home(request):
    # Statistiques des 30 derniers jours
    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)

    # Statistiques des clics
    clicks = ReferralClick.objects.filter(ambassador=request.user, created_at__gte=thirty_days_ago)

    # Statistiques des inscriptions
    referrals = Referral.objects.filter(ambassador=request.user, created_at__gte=thirty_days_ago)

    # Statistiques des commissions
    commissions = Commission.objects.filter(
        referral__ambassador=request.user, created_at__gte=thirty_days_ago
    )

    # Calcul des totaux
    total_clicks = clicks.count()
    total_referrals = referrals.count()
    total_earnings = (
        commissions.filter(status="approved").aggregate(Sum("amount"))["amount__sum"] or 0
    )

    # Calcul du taux de conversion
    conversion_rate = (total_referrals / total_clicks * 100) if total_clicks > 0 else 0

    # Graphique des clics par jour
    clicks_by_day = (
        clicks.annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    # Graphique des inscriptions par jour
    referrals_by_day = (
        referrals.annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    # Graphique des gains par jour
    earnings_by_day = (
        commissions.filter(status="approved")
        .annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(total=Sum("amount"))
        .order_by("day")
    )

    context = {
        "total_clicks": total_clicks,
        "total_referrals": total_referrals,
        "total_earnings": total_earnings,
        "conversion_rate": round(conversion_rate, 2),
        "clicks_by_day": list(clicks_by_day),
        "referrals_by_day": list(referrals_by_day),
        "earnings_by_day": list(earnings_by_day),
    }

    return render(request, "affiliate/home.html", context)


# Gestion des liens d'affiliation
@login_required
def affiliate_links(request):
    """Page de gestion des liens d'affiliation."""
    # Créer une liste de liens d'affiliation prédéfinis
    base_url = request.build_absolute_uri("/").rstrip("/")
    affiliate_links = [
        {
            "name": "Page d'accueil",
            "url": f"{base_url}/?ref={request.user.referral_code}",
            "description": "Lien vers la page d'accueil",
        },
        {
            "name": "Inscription",
            "url": f"{base_url}/accounts/register/?ref={request.user.referral_code}",
            "description": "Lien direct vers la page d'inscription",
        },
        # Ajoutez d'autres liens prédéfinis ici
    ]

    # Récupérer les statistiques des clics pour chaque lien
    for link in affiliate_links:
        link["clicks"] = ReferralClick.objects.filter(
            ambassador=request.user, landing_page__contains=link["url"]
        ).count()

    context = {
        "affiliate_links": affiliate_links,
        "referral_code": request.user.referral_code,
    }

    return render(request, "affiliate/links.html", context)


# Matériels marketing
@login_required
def marketing_materials(request):
    """Vue pour afficher les matériels marketing disponibles."""
    materials = MarketingMaterial.objects.filter(is_active=True).order_by("-created_at")
    return render(request, "affiliate/marketing_materials.html", {"materials": materials})


@login_required
def download_marketing_material(request, material_id):
    """Vue pour télécharger un matériel marketing."""
    try:
        material = MarketingMaterial.objects.get(id=material_id, is_active=True)
        # Incrémenter le compteur de téléchargements
        material.download_count += 1
        material.save()

        # Retourner le fichier
        response = FileResponse(material.file, as_attachment=True)
        response["Content-Disposition"] = f'attachment; filename="{material.file.name}"'
        return response
    except MarketingMaterial.DoesNotExist:
        messages.error(request, "Le matériel marketing demandé n'existe pas.")
        return redirect("affiliate:marketing_materials")


# Bannières promotionnelles
@login_required
def banners(request):
    """Page de bannières promotionnelles pour l'affiliation."""
    # Créer une liste de bannières disponibles
    banners_list = [
        {
            "name": "Bannière horizontale",
            "size": "728x90",
            "image_url": "/static/images/banners/banner-728x90.jpg",
            "html_code": f'<a href="{request.build_absolute_uri("/?")}ref={request.user.referral_code}"><img src="{request.build_absolute_uri("/static/images/banners/banner-728x90.jpg")}" alt="EscortDollars" width="728" height="90"></a>',
        },
        {
            "name": "Bannière carrée",
            "size": "300x250",
            "image_url": "/static/images/banners/banner-300x250.jpg",
            "html_code": f'<a href="{request.build_absolute_uri("/?")}ref={request.user.referral_code}"><img src="{request.build_absolute_uri("/static/images/banners/banner-300x250.jpg")}" alt="EscortDollars" width="300" height="250"></a>',
        },
        # Ajoutez d'autres bannières ici
    ]

    context = {
        "banners": banners_list,
    }

    return render(request, "affiliate/banners.html", context)


# Statistiques
@login_required
def statistics(request):
    """Page de statistiques détaillées d'affiliation."""
    # Plage de dates (par défaut: 30 derniers jours)
    date_from = request.GET.get(
        "date_from", (timezone.now() - timezone.timedelta(days=30)).strftime("%Y-%m-%d")
    )
    date_to = request.GET.get("date_to", timezone.now().strftime("%Y-%m-%d"))

    # Statistiques générales
    stats = {
        "clicks": ReferralClick.objects.filter(ambassador=request.user).count(),
        "referrals": Referral.objects.filter(ambassador=request.user).count(),
        "earnings": Commission.objects.filter(
            referral__ambassador=request.user, status__in=["approved", "paid"]
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0,
    }

    # Calcul du taux de conversion
    if stats["clicks"] > 0:
        stats["conversion_rate"] = (stats["referrals"] / stats["clicks"]) * 100
    else:
        stats["conversion_rate"] = 0

    # Données pour le graphique
    dates = []
    earnings = []

    # Récupérer les commissions par jour
    commissions_by_day = (
        Commission.objects.filter(
            referral__ambassador=request.user,
            status__in=["approved", "paid"],
            created_at__range=[date_from, date_to],
        )
        .annotate(day=TruncDay("created_at"))
        .values("day")
        .annotate(total=Sum("amount"))
        .order_by("day")
    )

    # Formater les données pour le graphique
    for commission in commissions_by_day:
        dates.append(commission["day"].strftime("%Y-%m-%d"))
        earnings.append(float(commission["total"]))

    context = {
        "stats": stats,
        "dates": json.dumps(dates),
        "earnings": json.dumps(earnings),
    }

    return render(request, "dashboard/statistics.html", context)


# Rapports
@login_required
def reports(request):
    """Page de rapports d'affiliation."""
    # Type de rapport (par défaut: commissions)
    report_type = request.GET.get("type", "commissions")

    if report_type == "commissions":
        # Rapport des commissions
        commissions = Commission.objects.filter(referral__ambassador=request.user)
        context = {"commissions": commissions, "report_type": report_type}
        return render(request, "affiliate/reports/commissions.html", context)

    elif report_type == "clicks":
        # Rapport des clics
        clicks = ReferralClick.objects.filter(ambassador=request.user)
        context = {"clicks": clicks, "report_type": report_type}
        return render(request, "affiliate/reports/clicks.html", context)

    elif report_type == "referrals":
        # Rapport des parrainages
        referrals = Referral.objects.filter(ambassador=request.user)
        context = {"referrals": referrals, "report_type": report_type}
        return render(request, "affiliate/reports/referrals.html", context)

    else:
        # Type de rapport non reconnu
        messages.error(request, "Type de rapport non valide.")
        return redirect("affiliate:home")


# Commissions
@login_required
def commissions(request):
    """Page de gestion des commissions."""
    # Filtres
    status = request.GET.get("status", "all")

    # Récupérer les commissions selon les filtres
    commissions_list = Commission.objects.filter(referral__referrer=request.user)

    if status != "all":
        commissions_list = commissions_list.filter(status=status)

    # Résumé mensuel des commissions pour l'historique
    monthly_summary = {}

    # Utiliser les commissions déjà récupérées
    for commission in commissions_list:
        # Extraire le mois et l'année
        month_year = datetime.date(commission.created_at.year, commission.created_at.month, 1)

        # Initialiser le mois s'il n'existe pas
        if month_year not in monthly_summary:
            monthly_summary[month_year] = {
                "total_amount": Decimal("0.00"),
                "paid_amount": Decimal("0.00"),
                "pending_amount": Decimal("0.00"),
                "count": 0,
                "month_name": commission.created_at.strftime("%B %Y"),
            }

        # Ajouter au total
        monthly_summary[month_year]["total_amount"] += commission.amount
        monthly_summary[month_year]["count"] += 1

        # Ajouter au statut approprié
        if commission.status == "paid":
            monthly_summary[month_year]["paid_amount"] += commission.amount
        elif commission.status in ["pending", "approved"]:
            monthly_summary[month_year]["pending_amount"] += commission.amount

    # Trier par date décroissante
    monthly_summary = sorted(
        monthly_summary.values(),
        key=lambda x: datetime.datetime.strptime(x["month_name"], "%B %Y"),
        reverse=True,
    )

    # Calculer les totaux pour le pied de tableau
    total_pending = sum(month["pending_amount"] for month in monthly_summary)
    total_paid = sum(month["paid_amount"] for month in monthly_summary)
    total_all = total_pending + total_paid

    # Sommes totales par statut
    totals = {
        "pending": Commission.objects.filter(
            referral__referrer=request.user, status="pending"
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0,
        "approved": Commission.objects.filter(
            referral__referrer=request.user, status="approved"
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0,
        "rejected": Commission.objects.filter(
            referral__referrer=request.user, status="rejected"
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0,
        "paid": Commission.objects.filter(referral__referrer=request.user, status="paid").aggregate(
            Sum("amount")
        )["amount__sum"]
        or 0,
    }

    # MÉTHODE DIRECTE: Compter les utilisateurs référés par catégorie
    referred_users = User.objects.filter(referred_by=request.user)

    # Pour tous les utilisateurs, compter normalement
    escort_count = referred_users.filter(user_category="escort").count()
    ambassador_count = referred_users.filter(user_category="ambassador").count()

    # Pour la compatibilité avec le code existant, les requêtes sur Referral ne sont plus utilisées
    # Commissions par type d'utilisateur référé
    escort_commissions = Commission.objects.filter(
        referral__referrer=request.user, referral__referred__user_category="escort"
    )
    ambassador_commissions = Commission.objects.filter(
        referral__referrer=request.user, referral__referred__user_category="ambassador"
    )

    escort_commissions_total = escort_commissions.aggregate(Sum("amount"))["amount__sum"] or 0
    ambassador_commissions_total = (
        ambassador_commissions.aggregate(Sum("amount"))["amount__sum"] or 0
    )
    total_commissions = escort_commissions_total + ambassador_commissions_total

    # Commissions par statut
    paid_commissions_count = Commission.objects.filter(
        referral__referrer=request.user, status="paid"
    ).count()
    pending_commissions_count = Commission.objects.filter(
        referral__referrer=request.user, status__in=["pending", "approved"]
    ).count()
    commissions_count = paid_commissions_count + pending_commissions_count

    paid_commissions_total = (
        Commission.objects.filter(referral__referrer=request.user, status="paid").aggregate(
            Sum("amount")
        )["amount__sum"]
        or 0
    )
    pending_commissions_total = (
        Commission.objects.filter(
            referral__referrer=request.user, status__in=["pending", "approved"]
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )

    # Commissions payées/en attente par type d'utilisateur
    escort_paid_commissions = (
        Commission.objects.filter(
            referral__referrer=request.user,
            referral__referred__user_category="escort",
            status="paid",
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )

    escort_pending_commissions = (
        Commission.objects.filter(
            referral__referrer=request.user,
            referral__referred__user_category="escort",
            status__in=["pending", "approved"],
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )

    ambassador_paid_commissions = (
        Commission.objects.filter(
            referral__referrer=request.user,
            referral__referred__user_category="ambassador",
            status="paid",
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )

    ambassador_pending_commissions = (
        Commission.objects.filter(
            referral__referrer=request.user,
            referral__referred__user_category="ambassador",
            status__in=["pending", "approved"],
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )

    # Performance des affiliations (30 derniers jours)
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    clicks = ReferralClick.objects.filter(
        user=request.user, created_at__gte=thirty_days_ago
    ).count()
    registrations = Referral.objects.filter(
        referrer=request.user, created_at__gte=thirty_days_ago
    ).count()

    # Taux de conversion
    conversion_rate = 0
    if clicks > 0:
        conversion_rate = (registrations / clicks) * 100

    # Commission moyenne
    recent_commissions = Commission.objects.filter(
        referral__referrer=request.user, created_at__gte=thirty_days_ago
    )
    avg_commission = recent_commissions.aggregate(Avg("amount"))["amount__avg"] or 0

    # Totaux des gains et croissance
    total_earnings = paid_commissions_total + pending_commissions_total

    # Calcul de la croissance (comparaison avec le mois précédent)
    current_month = timezone.now().month
    current_year = timezone.now().year

    # Commissions du mois actuel
    current_month_start = timezone.datetime(
        current_year, current_month, 1, tzinfo=timezone.get_current_timezone()
    )
    current_month_commissions = (
        Commission.objects.filter(
            referral__referrer=request.user, created_at__gte=current_month_start
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )

    # Commissions du mois précédent
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year

    prev_month_start = timezone.datetime(
        prev_year, prev_month, 1, tzinfo=timezone.get_current_timezone()
    )
    if current_month == 1:
        prev_month_end = timezone.datetime(
            current_year, 1, 1, tzinfo=timezone.get_current_timezone()
        ) - timezone.timedelta(seconds=1)
    else:
        prev_month_end = current_month_start - timezone.timedelta(seconds=1)

    prev_month_commissions = (
        Commission.objects.filter(
            referral__referrer=request.user,
            created_at__gte=prev_month_start,
            created_at__lte=prev_month_end,
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )

    # Pourcentage de croissance
    growth_percentage = 0
    if prev_month_commissions > 0:
        growth_percentage = (
            (current_month_commissions - prev_month_commissions) / prev_month_commissions
        ) * 100

    # Préparer les données des escortes affiliées pour l'affichage
    affiliated_escorts = []

    # Récupérer tous les utilisateurs de type escorte référés par cet utilisateur
    escort_users = User.objects.filter(referred_by=request.user, user_category="escort")

    for escort in escort_users:
        # Récupérer les commissions associées à cette escorte
        escort_commissions = Commission.objects.filter(
            referral__referrer=request.user, referral__referred=escort
        )

        # Calculer les montants bruts et les commissions
        gross_amount = escort_commissions.aggregate(Sum("gross_amount"))["gross_amount__sum"] or 0
        commission_amount = escort_commissions.aggregate(Sum("amount"))["amount__sum"] or 0

        # Déterminer le taux effectif
        # Récupérer le taux de commission de l'ambassadeur pour les escortes
        try:
            # Récupérer le taux personnalisé depuis le profil utilisateur
            profile = request.user.account_profile
            effective_rate = profile.escort_commission_rate
        except Exception:
            effective_rate = 30.00  # Taux par défaut

        affiliated_escorts.append(
            {
                "username": escort.username,
                "referral_date": escort.date_joined,
                "gross_amount": gross_amount,
                "commission_amount": commission_amount,
                "effective_rate": effective_rate,
                "status": (
                    "paid" if escort_commissions.filter(status="paid").exists() else "pending"
                ),
            }
        )

    # Calculer les totaux pour les escortes
    total_gross_amount = sum(escort["gross_amount"] for escort in affiliated_escorts)
    total_commission_amount = sum(escort["commission_amount"] for escort in affiliated_escorts)

    # Préparer les données des ambassadeurs affiliés pour l'affichage
    affiliated_ambassadors = []

    # Récupérer tous les utilisateurs de type ambassadeur référés par cet utilisateur
    ambassador_users = User.objects.filter(referred_by=request.user, user_category="ambassador")

    for ambassador in ambassador_users:
        # Récupérer les commissions associées à cet ambassadeur
        ambassador_commissions = Commission.objects.filter(
            referral__referrer=request.user, referral__referred=ambassador
        )

        # Calculer les montants bruts et les commissions
        gross_amount = (
            ambassador_commissions.aggregate(Sum("gross_amount"))["gross_amount__sum"] or 0
        )
        commission_amount = ambassador_commissions.aggregate(Sum("amount"))["amount__sum"] or 0

        # Déterminer le taux effectif
        try:
            # Récupérer le taux personnalisé depuis le profil utilisateur
            profile = request.user.account_profile
            effective_rate = profile.ambassador_commission_rate
        except Exception:
            effective_rate = 20.00  # Taux par défaut

        affiliated_ambassadors.append(
            {
                "username": ambassador.username,
                "referral_date": ambassador.date_joined,
                "gross_amount": gross_amount,
                "commission_amount": commission_amount,
                "effective_rate": effective_rate,
                "status": (
                    "paid" if ambassador_commissions.filter(status="paid").exists() else "pending"
                ),
            }
        )

    # Calculer les totaux pour les ambassadeurs
    total_amb_gross_amount = sum(
        ambassador["gross_amount"] for ambassador in affiliated_ambassadors
    )
    total_amb_commission_amount = sum(
        ambassador["commission_amount"] for ambassador in affiliated_ambassadors
    )

    context = {
        "commissions": commissions_list,
        "monthly_summary": monthly_summary,
        "total_pending": total_pending,
        "total_paid": total_paid,
        "total_all": total_all,
        "totals": totals,
        "escort_count": escort_count,
        "ambassador_count": ambassador_count,
        "escort_commissions_total": escort_commissions_total,
        "ambassador_commissions_total": ambassador_commissions_total,
        "total_commissions": total_commissions,
        "paid_commissions_count": paid_commissions_count,
        "pending_commissions_count": pending_commissions_count,
        "commissions_count": commissions_count,
        "paid_commissions_total": paid_commissions_total,
        "pending_commissions_total": pending_commissions_total,
        "escort_paid_commissions": escort_paid_commissions,
        "escort_pending_commissions": escort_pending_commissions,
        "ambassador_paid_commissions": ambassador_paid_commissions,
        "ambassador_pending_commissions": ambassador_pending_commissions,
        "clicks": clicks,
        "registrations": registrations,
        "conversion_rate": conversion_rate,
        "avg_commission": avg_commission,
        "total_earnings": total_earnings,
        "current_month_commissions": current_month_commissions,
        "prev_month_commissions": prev_month_commissions,
        "growth_percentage": growth_percentage,
        "affiliated_escorts": affiliated_escorts,
        "affiliated_ambassadors": affiliated_ambassadors,
        "total_gross_amount": total_gross_amount,
        "total_commission_amount": total_commission_amount,
        "total_amb_gross_amount": total_amb_gross_amount,
        "total_amb_commission_amount": total_amb_commission_amount,
        "status": status,
    }

    return render(request, "affiliate/commissions.html", context)


@login_required
def commission_detail(request, commission_id):
    """Page de détail d'une commission."""
    commission = get_object_or_404(Commission, id=commission_id, referral__ambassador=request.user)

    context = {
        "commission": commission,
    }

    return render(request, "affiliate/commission_detail.html", context)


# Paiements
@login_required
def payouts(request):
    """Page de gestion des paiements."""
    # Récupérer les paiements
    payouts_list = Payout.objects.filter(user=request.user)

    # Somme totale des paiements
    total_paid = (
        payouts_list.filter(status="completed").aggregate(Sum("amount"))["amount__sum"] or 0
    )

    # Montant disponible pour paiement (commissions approuvées non payées)
    available_amount = (
        Commission.objects.filter(referral__ambassador=request.user, status="approved").aggregate(
            Sum("amount")
        )["amount__sum"]
        or 0
    )

    # Méthodes de paiement
    payment_methods = PaymentMethod.objects.filter(user=request.user)

    context = {
        "payouts": payouts_list,
        "total_paid": total_paid,
        "available_amount": available_amount,
        "payment_methods": payment_methods,
    }

    return render(request, "affiliate/payouts.html", context)


@login_required
def payout_detail(request, pk):
    """Page de détail d'un paiement."""
    payout = get_object_or_404(Payout, pk=pk, user=request.user)

    # Commissions liées à ce paiement
    commissions = payout.commissions.all()

    context = {
        "payout": payout,
        "commissions": commissions,
    }

    return render(request, "affiliate/payout_detail.html", context)


# Méthodes de paiement
@login_required
def payment_methods(request):
    """Vue pour gérer les méthodes de paiement."""
    payment_methods = PaymentMethod.objects.filter(user=request.user).order_by(
        "-is_default", "-created_at"
    )
    return render(request, "affiliate/payment_methods.html", {"payment_methods": payment_methods})


@login_required
def add_payment_method(request):
    """Vue pour ajouter une méthode de paiement."""
    if request.method == "POST":
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            payment_method = form.save(commit=False)
            payment_method.user = request.user
            payment_method.save()
            messages.success(request, "Méthode de paiement ajoutée avec succès.")
            return redirect("affiliate:payment_methods")
    else:
        form = PaymentMethodForm()

    return render(
        request,
        "affiliate/payment_method_form.html",
        {"form": form, "title": "Ajouter une méthode de paiement"},
    )


@login_required
def edit_payment_method(request, method_id):
    """Vue pour modifier une méthode de paiement."""
    try:
        payment_method = PaymentMethod.objects.get(id=method_id, user=request.user)
        if request.method == "POST":
            form = PaymentMethodForm(request.POST, instance=payment_method)
            if form.is_valid():
                form.save()
                messages.success(request, "Méthode de paiement modifiée avec succès.")
                return redirect("affiliate:payment_methods")
        else:
            form = PaymentMethodForm(instance=payment_method)

        return render(
            request,
            "affiliate/payment_method_form.html",
            {"form": form, "title": "Modifier la méthode de paiement"},
        )
    except PaymentMethod.DoesNotExist:
        messages.error(request, "La méthode de paiement demandée n'existe pas.")
        return redirect("affiliate:payment_methods")


@login_required
def delete_payment_method(request, method_id):
    """Vue pour supprimer une méthode de paiement."""
    try:
        payment_method = PaymentMethod.objects.get(id=method_id, user=request.user)
        if request.method == "POST":
            payment_method.delete()
            messages.success(request, "Méthode de paiement supprimée avec succès.")
        return redirect("affiliate:payment_methods")
    except PaymentMethod.DoesNotExist:
        messages.error(request, "La méthode de paiement demandée n'existe pas.")
        return redirect("affiliate:payment_methods")


# Redirection et suivi
def referral_redirect(request, referral_code):
    """Redirection à partir d'un lien d'affiliation avec suivi du clic."""
    try:
        ambassador = User.objects.get(referral_code=referral_code)

        # Enregistrement du clic
        click = ReferralClick(
            ambassador=ambassador,
            ip_address=request.META.get("REMOTE_ADDR", "0.0.0.0"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            referrer=request.META.get("HTTP_REFERER", ""),
            landing_page=request.GET.get("next", "/"),
        )
        click.save()

        # Stockage du code de référence dans la session
        request.session["referral_code"] = referral_code
        request.session["referral_click_id"] = str(click.id)

        # Redirection vers la page demandée ou la page d'accueil avec le paramètre ref
        next_url = request.GET.get("next", "/")
        # Ajouter le code de référence à l'URL de redirection
        if "?" in next_url:
            next_url += f"&ref={referral_code}"
        else:
            next_url += f"?ref={referral_code}"

        return redirect(next_url)

    except User.DoesNotExist:
        # Code de référence invalide
        messages.error(request, "Code de référence invalide.")
        return redirect("home")


@csrf_exempt
def track_click(request, referral_code):
    """API pour suivi des clics (utilisable via pixel ou JavaScript)."""
    try:
        ambassador = User.objects.get(referral_code=referral_code)

        # Enregistrement du clic
        ReferralClick.objects.create(
            ambassador=ambassador,
            ip_address=request.META.get("REMOTE_ADDR", "0.0.0.0"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            referrer=request.META.get("HTTP_REFERER", ""),
            landing_page=request.META.get("HTTP_REFERER", ""),
        )

        # Retourner une image transparente 1x1 pixel
        return HttpResponse(
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )

    except User.DoesNotExist:
        # Code de référence invalide
        return HttpResponse(
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )


# API pour applications
@login_required
def api_stats(request):
    """API pour récupérer les statistiques d'affiliation."""
    # Récupérer le paramètre de période si présent
    period = request.GET.get("period", "30")

    # Calculer la date de début de période
    today = timezone.now()
    if period == "7":
        start_date = today - timezone.timedelta(days=7)
    elif period == "30":
        start_date = today - timezone.timedelta(days=30)
    elif period == "90":
        start_date = today - timezone.timedelta(days=90)
    elif period == "365":
        start_date = today - timezone.timedelta(days=365)
    else:
        # Pour 'all' ou autres valeurs, on prend toutes les données
        start_date = None

    # Base de filtrage pour les commissions
    commission_filter = {"referral__ambassador": request.user}
    if start_date:
        commission_filter["created_at__gte"] = start_date

    # Statistiques générales
    clicks_count = ReferralClick.objects.filter(ambassador=request.user).count()
    referrals_count = Referral.objects.filter(ambassador=request.user).count()

    # Commissions par statut
    total_commissions = Commission.objects.filter(**commission_filter)

    # Commissions payées
    paid_commissions = total_commissions.filter(status="paid")
    paid_amount = paid_commissions.aggregate(Sum("amount"))["amount__sum"] or 0

    # Commissions en attente
    pending_commissions = total_commissions.filter(status__in=["pending", "approved"])
    pending_amount = pending_commissions.aggregate(Sum("amount"))["amount__sum"] or 0

    # Total des commissions (payées + en attente)
    total_earnings = paid_amount + pending_amount

    # Statistiques ambassadeurs et escortes
    ambassador_count = Referral.objects.filter(
        ambassador=request.user, referred__user_category="ambassador"
    ).count()

    escort_count = Referral.objects.filter(
        ambassador=request.user, referred__user_category="escort"
    ).count()

    # Calcul du taux de conversion
    conversion_rate = 0
    if clicks_count > 0:
        conversion_rate = (referrals_count / clicks_count) * 100

    # Données pour graphique
    dates = []
    ambassadors_data = []
    escorts_data = []
    total_data = []

    # Si une date de début est spécifiée, générer des données de tendance
    if start_date:
        # Générer des dates pour la période
        date_list = []
        days = (today - start_date).days + 1
        for i in range(days):
            date = (today - timezone.timedelta(days=days - i - 1)).date()
            date_list.append(date)

        # Pour chaque date, calculer le nombre d'affiliés
        for date in date_list:
            date_str = date.strftime("%Y-%m-%d")
            dates.append(date_str)

            # Calculer le nombre d'ambassadeurs à cette date
            ambassadors = Referral.objects.filter(
                ambassador=request.user,
                referred__user_category="ambassador",
                created_at__date__lte=date,
            ).count()
            ambassadors_data.append(ambassadors)

            # Calculer le nombre d'escortes à cette date
            escorts = Referral.objects.filter(
                ambassador=request.user,
                referred__user_category="escort",
                created_at__date__lte=date,
            ).count()
            escorts_data.append(escorts)

            # Total des affiliés à cette date
            total_data.append(ambassadors + escorts)

    data = {
        "ambassador_count": ambassador_count,
        "escort_count": escort_count,
        "total_commission_amount": float(total_earnings),
        "paid_commission_amount": float(paid_amount),
        "pending_commission_amount": float(pending_amount),
        "conversion_rate": round(conversion_rate, 2),
        "dates": dates,
        "ambassador_data": ambassadors_data,
        "escort_data": escorts_data,
        "total_affiliate_data": total_data,
    }

    return JsonResponse(data)


@login_required
def api_commissions(request):
    """API pour récupérer les commissions."""
    # Récupérer les commissions
    commissions = Commission.objects.filter(referral__ambassador=request.user)

    # Sérialisation des commissions (version simplifiée)
    commissions_data = []
    for commission in commissions:
        commissions_data.append(
            {
                "id": str(commission.id),
                "amount": float(commission.amount),
                "status": commission.status,
                "created_at": commission.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "description": commission.description,
            }
        )

    data = {
        "commissions": commissions_data,
    }

    return JsonResponse(data)


@login_required
def api_user_info(request):
    """API pour récupérer les informations d'affiliation de l'utilisateur connecté."""
    user = request.user

    # Construire les données de base
    data = {
        "username": user.username,
        "user_type": user.user_type,
        "referral_code": user.referral_code,
        "is_referred": user.referred_by is not None,
        "status": {
            "is_verified": user.is_verified,
            "is_active": user.is_active,
        },
    }

    # Ajouter des informations sur qui l'a référé, si applicable
    if user.referred_by:
        data["referred_by"] = {
            "username": user.referred_by.username,
            "referral_code": user.referred_by.referral_code,
        }

    # Ajouter des statistiques de base
    clicks_count = ReferralClick.objects.filter(ambassador=user).count()
    referrals_count = Referral.objects.filter(ambassador=user).count()
    data["stats"] = {"clicks": clicks_count, "referrals": referrals_count}

    return JsonResponse(data)


@login_required
def api_ambassadors(request):
    """API pour récupérer la liste des ambassadeurs affiliés."""
    # Récupérer les utilisateurs ambassadeurs référés par l'utilisateur actuel
    ambassadors = User.objects.filter(
        referred_by=request.user, user_category="ambassador"
    ).order_by("-date_joined")[
        :10
    ]  # Limiter à 10 ambassadeurs

    # Préparer les données pour le JSON
    ambassadors_data = []
    for ambassador in ambassadors:
        # Compter les utilisateurs référés par cet ambassadeur
        referred_count = User.objects.filter(referred_by=ambassador).count()

        ambassadors_data.append(
            {
                "username": ambassador.username,
                "full_name": (
                    ambassador.get_full_name()
                    if hasattr(ambassador, "get_full_name")
                    else ambassador.username
                ),
                "referral_code": ambassador.referral_code,
                "date_joined": ambassador.date_joined.strftime("%Y-%m-%d"),
                "referred_count": referred_count,
            }
        )

    return JsonResponse(ambassadors_data, safe=False)


@login_required
def api_escorts(request):
    """API pour récupérer la liste des escortes affiliées."""
    # Récupérer les utilisateurs escortes référés par l'utilisateur actuel
    escorts = User.objects.filter(referred_by=request.user, user_category="escort").order_by(
        "-date_joined"
    )[
        :10
    ]  # Limiter à 10 escortes

    # Préparer les données pour le JSON
    escorts_data = []
    for escort in escorts:
        escorts_data.append(
            {
                "username": escort.username,
                "referral_code": getattr(escort, "referral_code", ""),
                "date_joined": escort.date_joined.strftime("%Y-%m-%d"),
            }
        )

    return JsonResponse(escorts_data, safe=False)


@csrf_exempt
@require_POST
def process_external_referral(request):
    """
    Traite une référence provenant d'un site white label externe.
    Cette API est utilisée par les sites white label pour envoyer des événements d'affiliation.
    """
    # Vérifier l'API key pour la sécurité
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != settings.EXTERNAL_API_KEY:
        logger.warning(f"Tentative d'accès avec une API key invalide: {api_key}")
        return JsonResponse({"error": "API key invalide"}, status=403)

    try:
        # Décoder le corps de la requête
        data = json.loads(request.body)
        logger.info(f"Traitement d'une référence externe: {data}")

        # Vérifier les champs obligatoires
        required_fields = ["affiliate_id", "visitor_id", "source", "event"]
        for field in required_fields:
            if field not in data:
                logger.error(f"Champ manquant dans la requête: {field}")
                return JsonResponse({"error": f"Champ manquant: {field}"}, status=400)

        # Extraire les données
        affiliate_id = data.get("affiliate_id")
        data.get("visitor_id")
        source = data.get("source")
        event_type = data.get("event")

        # Récupérer l'ambassadeur
        try:
            ambassador = User.objects.get(referral_code=affiliate_id)
            logger.info(f"Ambassadeur trouvé: {ambassador.username}")
        except User.DoesNotExist:
            logger.warning(f"Aucun ambassadeur trouvé avec le code: {affiliate_id}")
            return JsonResponse({"error": "Code d'affiliation invalide"}, status=404)

        # Traiter selon le type d'événement
        if event_type == "visit":
            # Enregistrer un clic sur le lien de parrainage
            click = ReferralClick.objects.create(
                ambassador=ambassador,
                ip_address=request.META.get("REMOTE_ADDR", "0.0.0.0"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                referrer=source,
                landing_page=data.get("landing_page", ""),
            )
            logger.info(f"Clic enregistré: {click.id}")

            return JsonResponse(
                {
                    "success": True,
                    "message": "Visite enregistrée avec succès",
                    "click_id": str(click.id),
                }
            )

        elif event_type == "signup":
            # Récupérer les données de l'utilisateur
            escort_id = data.get("escort_id")
            escort_username = data.get("escort_username", f"escort_{escort_id}")

            # Envoyer une notification à l'ambassadeur
            try:
                notifier = TelegramNotifier()

                # Créer un objet utilisateur temporaire pour la notification
                temp_user = User()
                temp_user.username = escort_username
                temp_user.date_joined = timezone.now()

                success = notifier.send_new_ambassador_notification(ambassador, temp_user)

                if success:
                    logger.info(f"✅ Notification Telegram envoyée à {ambassador.username}")
                else:
                    logger.warning(
                        f"❌ Échec de l'envoi de la notification Telegram à {ambassador.username}"
                    )
            except Exception as e:
                logger.error(f"❌ Erreur lors de l'envoi de la notification: {str(e)}")

            return JsonResponse({"success": True, "message": "Inscription traitée avec succès"})

        elif event_type == "purchase":
            # Récupérer les données du paiement
            amount = data.get("amount")
            escort_id = data.get("escort_id")
            escort_username = data.get("escort_username", f"escort_{escort_id}")

            if not amount:
                logger.error("Montant manquant pour l'événement purchase")
                return JsonResponse(
                    {"error": "Montant manquant pour l'événement purchase"}, status=400
                )

            # Créer un utilisateur temporaire pour représenter l'escort
            temp_user = User()
            temp_user.username = escort_username

            # Trouver ou créer la relation de référence
            referral, created = Referral.objects.get_or_create(
                ambassador=ambassador,
                referred_user=None,  # Pas d'utilisateur réel
                defaults={
                    "is_active": True,
                    "created_at": timezone.now(),
                    "total_earnings": 0,
                },
            )

            # Calculer la commission (en pourcentage du montant)
            commission_rate = (
                ambassador.commission_rate / 100
            )  # La commission est stockée en pourcentage
            commission_amount = Decimal(str(amount)) * commission_rate

            # Créer une entrée de commission
            commission = Commission.objects.create(
                referral=referral,
                amount=commission_amount,
                commission_type="purchase",
                description=f"Commission pour l'achat de l'escort #{escort_id}",
                status="approved",
                reference_id=data.get("transaction_id", str(uuid.uuid4())),
            )

            # Mettre à jour le total des gains
            referral.total_earnings += commission_amount
            referral.save()

            # Envoyer une notification de commission
            try:
                notifier = TelegramNotifier()

                success = notifier.send_commission_notification(
                    referrer=ambassador,
                    referred_user=temp_user,
                    amount=float(commission_amount),
                    total_earnings=float(referral.total_earnings),
                )

                if success:
                    logger.info(f"✅ Notification de commission envoyée à {ambassador.username}")
                else:
                    logger.warning(
                        f"❌ Échec de l'envoi de la notification de commission à {ambassador.username}"
                    )

            except Exception as e:
                logger.error(
                    f"❌ Erreur lors de l'envoi de la notification de commission: {str(e)}"
                )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Commission créée avec succès",
                    "commission_id": str(commission.id),
                    "commission_amount": float(commission_amount),
                }
            )

        else:
            logger.warning(f"Type d'événement non géré: {event_type}")
            return JsonResponse({"error": f"Type d'événement non géré: {event_type}"}, status=400)

    except json.JSONDecodeError:
        logger.error("Corps de la requête JSON invalide")
        return JsonResponse({"error": "Corps de la requête JSON invalide"}, status=400)
    except Exception as e:
        logger.exception(f"Erreur lors du traitement de la référence: {str(e)}")
        return JsonResponse({"error": "Erreur interne"}, status=500)


class DashboardView(LoginRequiredMixin, View):
    template_name = "affiliate/dashboard.html"

    def get(self, request):
        if request.user.user_type != "ambassador":
            messages.error(request, "Accès non autorisé")
            return redirect("home")

        # Récupérer les statistiques
        total_commissions = (
            Commission.objects.filter(user=request.user).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        pending_commissions = (
            Commission.objects.filter(user=request.user, status="pending").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        paid_commissions = (
            Commission.objects.filter(user=request.user, status="paid").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        # Récupérer les dernières commissions
        recent_commissions = Commission.objects.filter(user=request.user).order_by("-created_at")[
            :5
        ]

        # Récupérer les statistiques depuis Supabase
        stats = {}  # Empty stats for now

        context = {
            "total_commissions": total_commissions,
            "pending_commissions": pending_commissions,
            "paid_commissions": paid_commissions,
            "recent_commissions": recent_commissions,
            "stats": stats,
        }
        return render(request, self.template_name, context)


@login_required
def commission_list(request):
    """Vue pour afficher la liste des commissions de l'utilisateur."""
    # Récupération des commissions de l'utilisateur
    commissions = Commission.objects.filter(user=request.user).order_by("-created_at")

    # Calcul des statistiques
    total_earnings = commissions.aggregate(total=Sum("amount"))["total"] or 0
    paid_earnings = commissions.filter(status="paid").aggregate(total=Sum("amount"))["total"] or 0
    pending_earnings = (
        commissions.filter(status="pending").aggregate(total=Sum("amount"))["total"] or 0
    )

    # Statistiques par période
    today = timezone.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    monthly_earnings = (
        commissions.filter(created_at__gte=start_of_month).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    monthly_count = commissions.filter(created_at__gte=start_of_month).count()

    # Pagination
    paginator = Paginator(commissions, 10)  # 10 commissions par page
    page = request.GET.get("page")
    try:
        commissions_page = paginator.page(page)
    except PageNotAnInteger:
        commissions_page = paginator.page(1)
    except EmptyPage:
        commissions_page = paginator.page(paginator.num_pages)

    context = {
        "commissions": commissions_page,
        "total_earnings": total_earnings,
        "paid_earnings": paid_earnings,
        "pending_earnings": pending_earnings,
        "monthly_earnings": monthly_earnings,
        "monthly_count": monthly_count,
        "commission_statuses": {
            "pending": _("En attente"),
            "paid": _("Payée"),
            "cancelled": _("Annulée"),
        },
    }

    return render(request, "affiliate/commission_list.html", context)


@login_required
def transaction_list(request):
    """Liste des transactions"""
    if request.user.user_type != "escort":
        messages.error(request, "Accès non autorisé")
        return redirect("home")

    transactions = Transaction.objects.filter(escort=request.user).order_by("-created_at")
    return render(request, "affiliate/transaction_list.html", {"transactions": transactions})


@login_required
def transaction_detail(request, pk):
    """Détails d'une transaction"""
    transaction = get_object_or_404(Transaction, pk=pk, escort=request.user)
    return render(request, "affiliate/transaction_detail.html", {"transaction": transaction})


@login_required
def payout_list(request):
    """Vue pour afficher la liste des paiements."""
    payouts = Payout.objects.filter(user=request.user).order_by("-created_at")
    context = {"payouts": payouts}
    return render(request, "affiliate/payout_list.html", context)


@login_required
def commission_rate_list(request):
    """Liste des taux de commission"""
    if request.user.user_type != "ambassador":
        messages.error(request, "Accès non autorisé")
        return redirect("home")

    rates = CommissionRate.objects.filter(ambassador=request.user)
    return render(request, "affiliate/commission_rate_list.html", {"rates": rates})


@login_required
def commission_rate_edit(request, pk=None):
    """Édition d'un taux de commission"""
    if request.user.user_type != "ambassador":
        messages.error(request, "Accès non autorisé")
        return redirect("home")

    if pk:
        rate = get_object_or_404(CommissionRate, pk=pk, ambassador=request.user)
    else:
        rate = None

    if request.method == "POST":
        form = CommissionRateForm(request.POST, instance=rate)
        if form.is_valid():
            rate = form.save(commit=False)
            rate.ambassador = request.user
            rate.save()
            messages.success(request, "Taux de commission mis à jour avec succès")
            return redirect("commission_rate_list")
    else:
        form = CommissionRateForm(instance=rate)

    return render(request, "affiliate/commission_rate_form.html", {"form": form})


@login_required
def white_label_list(request):
    """Liste des sites white label"""
    if request.user.user_type != "ambassador":
        messages.error(request, "Accès non autorisé")
        return redirect("home")

    white_labels = WhiteLabel.objects.filter(ambassador=request.user)
    return render(request, "affiliate/white_label_list.html", {"white_labels": white_labels})


@login_required
def white_label_edit(request, pk=None):
    """Édition d'un site white label"""
    if request.user.user_type != "ambassador":
        messages.error(request, "Accès non autorisé")
        return redirect("home")

    if pk:
        white_label = get_object_or_404(WhiteLabel, pk=pk, ambassador=request.user)
    else:
        white_label = None

    if request.method == "POST":
        form = WhiteLabelForm(request.POST, request.FILES, instance=white_label)
        if form.is_valid():
            white_label = form.save(commit=False)
            white_label.ambassador = request.user
            white_label.save()
            messages.success(request, "Site white label mis à jour avec succès")
            return redirect("white_label_list")
    else:
        form = WhiteLabelForm(instance=white_label)

    return render(request, "affiliate/white_label_form.html", {"form": form})


@login_required
def crypto_payment(request):
    """Vue pour le paiement en crypto"""
    if request.method == "POST":
        form = CryptoPaymentForm(request.POST)
        if form.is_valid():
            # Générer une adresse de portefeuille unique
            wallet_address = form.cleaned_data["wallet_address"]
            amount = form.cleaned_data["amount"]
            currency = form.cleaned_data["currency"]

            # Créer une transaction en attente
            transaction = Transaction.objects.create(
                escort=request.user,
                amount=amount,
                status="pending",
                payment_method=f"crypto_{currency.lower()}",
                payment_id=wallet_address,
            )

            # Synchroniser avec Supabase
            supabase_service = SupabaseService()
            supabase_service.sync_transaction(transaction)

            messages.success(request, "Transaction créée avec succès")
            return redirect("transaction_detail", pk=transaction.pk)
    else:
        form = CryptoPaymentForm()

    return render(request, "affiliate/crypto_payment.html", {"form": form})


class PayoutView(LoginRequiredMixin, View):
    template_name = "affiliate/payouts.html"

    def get(self, request):
        # Récupérer le solde disponible
        available_balance = (
            Commission.objects.filter(ambassador=request.user, status="pending").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        # Récupérer l'historique des paiements
        payouts = Payout.objects.filter(user=request.user)

        context = {
            "available_balance": available_balance,
            "payouts": payouts,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        amount = Decimal(request.POST.get("amount", 0))
        payment_method = request.POST.get("payment_method")
        wallet_address = request.POST.get("wallet_address")

        # Vérifier le solde disponible
        available_balance = (
            Commission.objects.filter(ambassador=request.user, status="pending").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )

        if amount > available_balance:
            messages.error(request, "Le montant demandé dépasse votre solde disponible.")
            return redirect("payouts")

        if amount < 50:
            messages.error(request, "Le montant minimum pour un paiement est de 50€.")
            return redirect("payouts")

        # Créer la demande de paiement
        Payout.objects.create(
            user=request.user,
            amount=amount,
            payment_method=payment_method,
            wallet_address=wallet_address,
        )

        # Marquer les commissions comme payées
        commissions = Commission.objects.filter(ambassador=request.user, status="pending").order_by(
            "created_at"
        )

        remaining_amount = amount
        for commission in commissions:
            if remaining_amount <= 0:
                break
            if commission.amount <= remaining_amount:
                commission.status = "paid"
                commission.save()
                remaining_amount -= commission.amount

        # Envoyer une notification
        Notification.objects.create(
            user=request.user,
            title="Demande de paiement reçue",
            message=f"Votre demande de paiement de {amount}€ a été reçue et est en cours de traitement.",
            notification_type="payout",
        )

        messages.success(request, "Votre demande de paiement a été enregistrée avec succès.")
        return redirect("payouts")


class AmbassadorManagerView(LoginRequiredMixin, View):
    template_name = "affiliate/ambassador_manager.html"

    def get(self, request):
        # Vérifier si l'utilisateur est un admin
        if not request.user.is_staff:
            messages.error(request, "Accès non autorisé")
            return redirect("home")

        # Récupérer tous les ambassadeurs
        ambassadors = User.objects.filter(user_type="ambassador").annotate(
            total_referrals=Count("referrals_made"),
            total_commissions=Sum("commissions__amount"),
            active_referrals=Count("referrals_made", filter=Q(referrals_made__is_active=True)),
            pending_commissions=Sum("commissions__amount", filter=Q(commissions__status="pending")),
            paid_commissions=Sum("commissions__amount", filter=Q(commissions__status="paid")),
        )

        # Statistiques globales
        total_ambassadors = ambassadors.count()
        total_referrals = sum(amb.total_referrals for amb in ambassadors)
        total_commissions = sum(amb.total_commissions or 0 for amb in ambassadors)
        active_referrals = sum(amb.active_referrals for amb in ambassadors)

        context = {
            "ambassadors": ambassadors,
            "total_ambassadors": total_ambassadors,
            "total_referrals": total_referrals,
            "total_commissions": total_commissions,
            "active_referrals": active_referrals,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        # Vérifier si l'utilisateur est un admin
        if not request.user.is_staff:
            messages.error(request, "Accès non autorisé")
            return redirect("home")

        action = request.POST.get("action")
        ambassador_id = request.POST.get("ambassador_id")

        try:
            ambassador = User.objects.get(id=ambassador_id, user_type="ambassador")
        except User.DoesNotExist:
            messages.error(request, "Ambassadeur non trouvé")
            return redirect("ambassador_manager")

        if action == "activate":
            ambassador.is_active = True
            ambassador.save()
            messages.success(request, f"L'ambassadeur {ambassador.username} a été activé")
        elif action == "deactivate":
            ambassador.is_active = False
            ambassador.save()
            messages.success(request, f"L'ambassadeur {ambassador.username} a été désactivé")
        elif action == "update_commission":
            new_rate = request.POST.get("commission_rate")
            if new_rate and 5 <= float(new_rate) <= 50:
                ambassador.commission_rate = float(new_rate)
                ambassador.save()
                messages.success(
                    request,
                    f"Le taux de commission de {ambassador.username} a été mis à jour",
                )
            else:
                messages.error(request, "Le taux de commission doit être entre 5% et 50%")

        return redirect("ambassador_manager")


class AffiliateLevelsView(LoginRequiredMixin, View):
    template_name = "affiliate/levels.html"

    def get(self, request):
        # Récupérer le profil de l'affilié
        profile = request.user.affiliate_profile

        # Récupérer tous les niveaux
        levels = AffiliateLevel.objects.all().order_by("min_earnings")

        # Calculer la progression pour chaque niveau
        level_progress = {}
        for level in levels:
            level_progress[level.id] = level.calculate_progress(profile)

        # Récupérer les badges
        badges = Badge.objects.all()

        # Récupérer les statistiques de l'utilisateur
        stats = {
            "total_earnings": profile.total_earnings,
            "total_referrals": profile.total_referrals,
            "conversion_rate": profile.conversion_rate,
            "points": profile.points,
            "badges_earned": profile.badges.count(),
        }

        context = {
            "profile": profile,
            "levels": levels,
            "level_progress": level_progress,
            "badges": badges,
            "stats": stats,
        }
        return render(request, self.template_name, context)


@login_required
def commission_mark_paid(request, pk):
    """
    Marque une commission comme payée
    """
    try:
        commission = Commission.objects.get(pk=pk)

        # Vérifier les permissions
        if not request.user.is_staff and commission.referral.ambassador != request.user:
            messages.error(
                request,
                _("Vous n'avez pas la permission de modifier cette commission."),
            )
            return redirect("affiliate:commission_list")

        # Mettre à jour le statut
        commission.status = "paid"
        commission.paid_at = timezone.now()
        commission.save()

        # Envoyer une notification Telegram
        try:
            from apps.dashboard.telegram_bot import TelegramNotifier

            notifier = TelegramNotifier()

            if commission.referral.ambassador.telegram_chat_id:
                # Messages multilingues
                languages = {
                    "en": f"Your commission of {commission.amount}€ has been marked as paid!",
                    "fr": f"Votre commission de {commission.amount}€ a été marquée comme payée !",
                    "es": f"¡Tu comisión de {commission.amount}€ ha sido marcada como pagada!",
                    "de": f"Ihre Provision von {commission.amount}€ wurde als bezahlt markiert!",
                    "ru": f"Ваша комиссия в размере {commission.amount}€ была отмечена как оплаченная!",
                    "zh": f"您的{commission.amount}€佣金已被标记为已支付！",
                    "it": f"La tua commissione di {commission.amount}€ è stata contrassegnata come pagata!",
                    "ar": f"تم تحديد عمولتك البالغة {commission.amount}€ كمدفوعة!",
                }

                # Déterminer la langue de l'utilisateur
                lang = (
                    commission.referral.ambassador.telegram_language
                    if commission.referral.ambassador.telegram_language in languages
                    else "en"
                )
                message = languages[lang]

                # Titre de la notification
                titles = {
                    "en": "Commission Paid",
                    "fr": "Commission Payée",
                    "es": "Comisión Pagada",
                    "de": "Provision Bezahlt",
                    "ru": "Комиссия Оплачена",
                    "zh": "佣金已支付",
                    "it": "Commissione Pagata",
                    "ar": "تم دفع العمولة",
                }
                title = titles.get(lang, titles["en"])

                # Envoyer la notification
                notifier.send_message(
                    chat_id=commission.referral.ambassador.telegram_chat_id,
                    message=f"*{title}*\n\n{message}",
                )
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")

        messages.success(request, _("La commission a été marquée comme payée avec succès."))

    except Commission.DoesNotExist:
        messages.error(request, _("Commission non trouvée."))
    except Exception as e:
        messages.error(
            request,
            _("Une erreur est survenue lors de la mise à jour de la commission."),
        )
        logger.error(f"Error marking commission as paid: {str(e)}")

    return redirect("affiliate:commission_list")


@login_required
@user_passes_test(lambda u: u.is_staff)
def affiliate_manager_dashboard(request):
    """Vue du tableau de bord de l'affiliate manager."""
    # Statistiques globales
    total_affiliates = User.objects.filter(is_affiliate=True).count()
    active_affiliates = User.objects.filter(is_affiliate=True, is_active=True).count()
    total_commissions = Commission.objects.aggregate(total=Sum("amount"))["total"] or 0
    pending_commissions = (
        Commission.objects.filter(status="pending").aggregate(total=Sum("amount"))["total"] or 0
    )

    # Statistiques des 30 derniers jours
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    new_affiliates = User.objects.filter(
        is_affiliate=True, date_joined__gte=thirty_days_ago
    ).count()
    recent_commissions = (
        Commission.objects.filter(created_at__gte=thirty_days_ago).aggregate(total=Sum("amount"))[
            "total"
        ]
        or 0
    )

    # Top affiliés
    top_affiliates = (
        User.objects.filter(is_affiliate=True)
        .annotate(
            total_earnings=Sum("commissions__amount"),
            total_referrals=Count("referrals"),
        )
        .order_by("-total_earnings")[:5]
    )

    # Dernières commissions
    recent_commissions_list = Commission.objects.select_related("user", "referral").order_by(
        "-created_at"
    )[:10]

    # Statistiques de conversion
    total_referrals = Referral.objects.count()
    successful_referrals = Referral.objects.filter(status="completed").count()
    conversion_rate = (successful_referrals / total_referrals * 100) if total_referrals > 0 else 0

    context = {
        "total_affiliates": total_affiliates,
        "active_affiliates": active_affiliates,
        "total_commissions": total_commissions,
        "pending_commissions": pending_commissions,
        "new_affiliates": new_affiliates,
        "recent_commissions": recent_commissions,
        "top_affiliates": top_affiliates,
        "recent_commissions_list": recent_commissions_list,
        "conversion_rate": conversion_rate,
        "total_referrals": total_referrals,
        "successful_referrals": successful_referrals,
    }

    return render(request, "affiliate/manager/dashboard.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def affiliate_list(request):
    """Vue pour la liste des affiliés."""
    affiliates = (
        User.objects.filter(is_affiliate=True)
        .annotate(
            total_earnings=Sum("commissions__amount"),
            total_referrals=Count("referrals"),
            successful_referrals=Count("referrals", filter=Q(referrals__status="completed")),
        )
        .order_by("-date_joined")
    )

    # Filtres
    status = request.GET.get("status")
    if status == "active":
        affiliates = affiliates.filter(is_active=True)
    elif status == "inactive":
        affiliates = affiliates.filter(is_active=False)

    # Recherche
    search_query = request.GET.get("q")
    if search_query:
        affiliates = affiliates.filter(
            Q(username__icontains=search_query) | Q(email__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(affiliates, 20)
    page = request.GET.get("page")
    try:
        affiliates_page = paginator.page(page)
    except PageNotAnInteger:
        affiliates_page = paginator.page(1)
    except EmptyPage:
        affiliates_page = paginator.page(paginator.num_pages)

    context = {
        "affiliates": affiliates_page,
        "status": status,
        "search_query": search_query,
    }

    return render(request, "affiliate/manager/affiliate_list.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def affiliate_detail(request, user_id):
    """Vue pour les détails d'un affilié."""
    affiliate = get_object_or_404(User.objects.filter(is_affiliate=True), id=user_id)

    # Statistiques de l'affilié
    stats = {
        "total_earnings": Commission.objects.filter(user=affiliate).aggregate(total=Sum("amount"))[
            "total"
        ]
        or 0,
        "pending_earnings": Commission.objects.filter(user=affiliate, status="pending").aggregate(
            total=Sum("amount")
        )["total"]
        or 0,
        "total_referrals": Referral.objects.filter(ambassador=affiliate).count(),
        "successful_referrals": Referral.objects.filter(
            ambassador=affiliate, status="completed"
        ).count(),
    }

    # Historique des commissions
    commissions = Commission.objects.filter(user=affiliate).order_by("-created_at")[:10]

    # Historique des parrainages
    referrals = Referral.objects.filter(ambassador=affiliate).order_by("-created_at")[:10]

    context = {
        "affiliate": affiliate,
        "stats": stats,
        "commissions": commissions,
        "referrals": referrals,
    }

    return render(request, "affiliate/manager/affiliate_detail.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def commission_management(request):
    """Vue pour la gestion des commissions."""
    commissions = Commission.objects.select_related("user", "referral").order_by("-created_at")

    # Filtres
    status = request.GET.get("status")
    if status:
        commissions = commissions.filter(status=status)

    # Recherche
    search_query = request.GET.get("q")
    if search_query:
        commissions = commissions.filter(
            Q(user__username__icontains=search_query)
            | Q(referral__referred__username__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(commissions, 20)
    page = request.GET.get("page")
    try:
        commissions_page = paginator.page(page)
    except PageNotAnInteger:
        commissions_page = paginator.page(1)
    except EmptyPage:
        commissions_page = paginator.page(paginator.num_pages)

    context = {
        "commissions": commissions_page,
        "status": status,
        "search_query": search_query,
    }

    return render(request, "affiliate/manager/commission_management.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def commission_approve(request, commission_id):
    """Vue pour approuver une commission."""
    commission = get_object_or_404(Commission, id=commission_id)

    if request.method == "POST":
        commission.status = "paid"
        commission.paid_at = timezone.now()
        commission.save()

        # Envoyer une notification à l'affilié
        messages.success(request, f"La commission #{commission.id} a été approuvée.")
        return redirect("commission_management")

    context = {
        "commission": commission,
    }

    return render(request, "affiliate/manager/commission_approve.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def commission_reject(request, commission_id):
    """Vue pour rejeter une commission."""
    commission = get_object_or_404(Commission, id=commission_id)

    if request.method == "POST":
        commission.status = "cancelled"
        commission.save()

        # Envoyer une notification à l'affilié
        messages.success(request, f"La commission #{commission.id} a été rejetée.")
        return redirect("commission_management")

    context = {
        "commission": commission,
    }

    return render(request, "affiliate/manager/commission_reject.html", context)


@login_required
def verify_domain(request, whitelabel_id):
    """Vue pour vérifier la configuration DNS d'un domaine personnalisé."""
    whitelabel = get_object_or_404(WhiteLabel, id=whitelabel_id, ambassador=request.user)

    if request.method == "POST":
        if whitelabel.verify_dns():
            messages.success(request, _("Le domaine a été vérifié avec succès !"))
        else:
            messages.error(
                request,
                _(
                    "La vérification du domaine a échoué. Veuillez vérifier votre configuration DNS."
                ),
            )
        return redirect("affiliate:whitelabel_detail", whitelabel_id=whitelabel.id)

    dns_instructions = whitelabel.get_dns_instructions()
    context = {
        "whitelabel": whitelabel,
        "dns_instructions": dns_instructions,
    }
    return render(request, "affiliate/verify_domain.html", context)


@login_required
def whitelabel_detail(request, whitelabel_id):
    """Vue détaillée d'un site white label."""
    whitelabel = get_object_or_404(WhiteLabel, id=whitelabel_id, ambassador=request.user)

    # Statistiques du site
    stats = {
        "clicks": ReferralClick.objects.filter(whitelabel=whitelabel).count(),
        "referrals": Referral.objects.filter(whitelabel=whitelabel).count(),
        "commissions": Commission.objects.filter(referral__whitelabel=whitelabel).aggregate(
            total=Sum("amount")
        )["total"]
        or 0,
    }

    # Dernières commissions
    recent_commissions = Commission.objects.filter(referral__whitelabel=whitelabel).order_by(
        "-created_at"
    )[:5]

    # Derniers parrainages
    recent_referrals = Referral.objects.filter(whitelabel=whitelabel).order_by("-created_at")[:5]

    context = {
        "whitelabel": whitelabel,
        "stats": stats,
        "recent_commissions": recent_commissions,
        "recent_referrals": recent_referrals,
        "dns_instructions": (
            whitelabel.get_dns_instructions() if whitelabel.custom_domain else None
        ),
    }
    return render(request, "affiliate/whitelabel_detail.html", context)


def banner_page(request):
    """
    Affiche la page des bannières publicitaires pour les affiliés.
    """
    if not request.user.is_authenticated:
        return redirect("login")

    # Récupérer les bannières disponibles
    banners = MarketingMaterial.objects.filter(type="banner", is_active=True).order_by(
        "-created_at"
    )

    context = {
        "banners": banners,
        "page_title": _("Bannières publicitaires"),
    }

    return render(request, "affiliate/banners.html", context)
