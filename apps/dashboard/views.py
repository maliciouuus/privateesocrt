from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta, datetime
from django.views.decorators.http import require_POST
import json
import uuid
from django.utils.translation import gettext_lazy as _
import logging
from django.core.paginator import Paginator
from django.contrib.auth import update_session_auth_hash
import os
from supabase import create_client, Client

from .models import Notification
from apps.affiliate.models import (
    ReferralClick,
    Referral,
    Commission,
)
from apps.accounts.models import (
    User,
    UserProfile,
)  # Importer le modèle User et UserProfile


# Simple dashboard for allauth users
@login_required
def simple_dashboard(request):
    """A simplified dashboard page for django-allauth users."""
    # Rediriger directement vers le tableau de bord principal
    return redirect("dashboard:home")


# Tableau de bord principal
@login_required
def dashboard_home(request):
    """Page d'accueil du tableau de bord."""
    # Rediriger les administrateurs vers la page des ambassadeurs
    if request.user.is_staff or request.user.is_superuser:
        return redirect("dashboard:manage_ambassadors")

    # Récupérer les statistiques de l'utilisateur
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)

    # Calcul des statistiques pour le tableau de bord
    stats = {
        "clicks": ReferralClick.objects.filter(
            user=request.user, clicked_at__date__gte=thirty_days_ago
        ).count(),
        "referrals": Referral.objects.filter(
            referrer=request.user, created_at__date__gte=thirty_days_ago
        ).count(),
        "earnings": Commission.objects.filter(
            referral__referrer=request.user,
            status__in=["approved", "paid"],
            created_at__date__gte=thirty_days_ago,
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0,
    }

    # Calcul du taux de conversion
    if stats["clicks"] > 0:
        stats["conversion_rate"] = (stats["referrals"] / stats["clicks"]) * 100
    else:
        stats["conversion_rate"] = 0

    # Récupérer les dernières notifications
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by(
        "-created_at"
    )[:5]

    context = {
        "stats": stats,
        "notifications": notifications,
    }

    return render(request, "dashboard/home.html", context)


# Vue d'ensemble
@login_required
def overview(request):
    """Page de vue d'ensemble des statistiques et performances."""
    # Période (par défaut: 30 derniers jours)
    period = request.GET.get("period", "30days")

    today = timezone.now().date()

    if period == "7days":
        start_date = today - timedelta(days=7)
    elif period == "30days":
        start_date = today - timedelta(days=30)
    elif period == "90days":
        start_date = today - timedelta(days=90)
    elif period == "year":
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)

    # Statistiques pour la période
    stats = {
        "clicks": ReferralClick.objects.filter(
            user=request.user, created_at__date__gte=start_date
        ).count(),
        "referrals": Referral.objects.filter(
            referrer=request.user, created_at__date__gte=start_date
        ).count(),
        "earnings": Commission.objects.filter(
            referral__referrer=request.user,
            status__in=["approved", "paid"],
            created_at__date__gte=start_date,
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0,
    }

    # Calcul du taux de conversion
    if stats["clicks"] > 0:
        stats["conversion_rate"] = (stats["referrals"] / stats["clicks"]) * 100
    else:
        stats["conversion_rate"] = 0

    context = {
        "stats": stats,
        "period": period,
        "start_date": start_date,
        "end_date": today,
    }

    return render(request, "dashboard/overview.html", context)


# Statistiques
@login_required
def statistics(request):
    """Page de statistiques détaillées."""
    # Période (par défaut: 30 derniers jours)
    period = request.GET.get("period", "30days")
    today = timezone.now().date()

    if period == "7days":
        start_date = today - timedelta(days=7)
    elif period == "30days":
        start_date = today - timedelta(days=30)
    elif period == "90days":
        start_date = today - timedelta(days=90)
    elif period == "year":
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)

    # Statistiques de base
    clicks = ReferralClick.objects.filter(
        user=request.user, clicked_at__date__gte=start_date
    ).count()
    referrals = Referral.objects.filter(referrer=request.user, created_at__date__gte=start_date)
    total_referrals = referrals.count()

    # Statistiques par type de parrainage
    ambassador_referrals = referrals.filter(referred__user_type="ambassador").count()
    escort_referrals = referrals.filter(referred__user_type="escort").count()

    # Revenus
    commissions = Commission.objects.filter(
        referral__referrer=request.user, created_at__date__gte=start_date
    )

    total_earnings = commissions.aggregate(Sum("amount"))["amount__sum"] or 0
    pending_earnings = (
        commissions.filter(status="pending").aggregate(Sum("amount"))["amount__sum"] or 0
    )
    paid_earnings = commissions.filter(status="paid").aggregate(Sum("amount"))["amount__sum"] or 0

    # Revenus par type de parrainage
    ambassador_earnings = (
        commissions.filter(referral__referred__user_type="ambassador").aggregate(Sum("amount"))[
            "amount__sum"
        ]
        or 0
    )

    escort_earnings = (
        commissions.filter(referral__referred__user_type="escort").aggregate(Sum("amount"))[
            "amount__sum"
        ]
        or 0
    )

    # Taux de conversion
    conversion_rate = (total_referrals / clicks * 100) if clicks > 0 else 0

    # Statistiques quotidiennes pour le graphique
    daily_stats = []
    current_date = start_date
    while current_date <= today:
        day_clicks = ReferralClick.objects.filter(
            user=request.user, clicked_at__date=current_date
        ).count()

        day_referrals = Referral.objects.filter(
            referrer=request.user, created_at__date=current_date
        ).count()

        day_earnings = (
            Commission.objects.filter(
                referral__referrer=request.user, created_at__date=current_date
            ).aggregate(Sum("amount"))["amount__sum"]
            or 0
        )

        # Distinguer les affiliés par type
        day_ambassador_referrals = Referral.objects.filter(
            referrer=request.user,
            referred__user_type="ambassador",
            created_at__date=current_date,
        ).count()

        day_escort_referrals = Referral.objects.filter(
            referrer=request.user,
            referred__user_type="escort",
            created_at__date=current_date,
        ).count()

        daily_stats.append(
            {
                "date": current_date.strftime("%Y-%m-%d"),
                "clicks": day_clicks,
                "referrals": day_referrals,
                "earnings": float(day_earnings),
                "ambassador_referrals": day_ambassador_referrals,
                "escort_referrals": day_escort_referrals,
            }
        )

        current_date += timedelta(days=1)

    # Statistiques de performance
    avg_commission = total_earnings / total_referrals if total_referrals > 0 else 0
    avg_daily_earnings = (
        total_earnings / (today - start_date).days if (today - start_date).days > 0 else 0
    )

    # Statistiques de croissance (comparaison avec la période précédente)
    previous_start_date = start_date - (today - start_date)

    previous_clicks = ReferralClick.objects.filter(
        user=request.user,
        clicked_at__date__gte=previous_start_date,
        clicked_at__date__lt=start_date,
    ).count()

    previous_referrals = Referral.objects.filter(
        referrer=request.user,
        created_at__date__gte=previous_start_date,
        created_at__date__lt=start_date,
    ).count()

    previous_earnings = (
        Commission.objects.filter(
            referral__referrer=request.user,
            status__in=["approved", "paid"],
            created_at__date__gte=previous_start_date,
            created_at__date__lt=start_date,
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )

    # Calcul des taux de croissance
    clicks_growth = calculate_growth(clicks, previous_clicks)
    referrals_growth = calculate_growth(total_referrals, previous_referrals)
    earnings_growth = calculate_growth(total_earnings, previous_earnings)

    # Préparation des données pour les graphiques
    dates = [stat["date"] for stat in daily_stats]
    earnings_data = [stat["earnings"] for stat in daily_stats]
    clicks_data = [stat["clicks"] for stat in daily_stats]
    referrals_data = [stat["referrals"] for stat in daily_stats]
    ambassador_data = [stat["ambassador_referrals"] for stat in daily_stats]
    escort_data = [stat["escort_referrals"] for stat in daily_stats]

    # Trouver le jour avec le plus de performances
    if daily_stats:
        best_day_by_clicks = max(daily_stats, key=lambda x: x["clicks"])
        best_day_by_referrals = max(daily_stats, key=lambda x: x["referrals"])
        best_day_by_earnings = max(daily_stats, key=lambda x: x["earnings"])

        highest_clicks = best_day_by_clicks["clicks"]
        highest_referrals = best_day_by_referrals["referrals"]
        highest_earnings = best_day_by_earnings["earnings"]

        best_day_format = "%A, %d %B %Y"
        best_day_clicks = (
            datetime.strptime(best_day_by_clicks["date"], "%Y-%m-%d").strftime(best_day_format)
            if highest_clicks > 0
            else "Aucun"
        )
        best_day_referrals = (
            datetime.strptime(best_day_by_referrals["date"], "%Y-%m-%d").strftime(best_day_format)
            if highest_referrals > 0
            else "Aucun"
        )
        best_day_earnings = (
            datetime.strptime(best_day_by_earnings["date"], "%Y-%m-%d").strftime(best_day_format)
            if highest_earnings > 0
            else "Aucun"
        )
    else:
        highest_clicks = 0
        highest_referrals = 0
        highest_earnings = 0
        best_day_clicks = "Aucun"
        best_day_referrals = "Aucun"
        best_day_earnings = "Aucun"

    # Calculer les moyennes journalières
    avg_daily_clicks = clicks / (today - start_date).days if (today - start_date).days > 0 else 0
    avg_daily_referrals = (
        total_referrals / (today - start_date).days if (today - start_date).days > 0 else 0
    )

    # Nombre de jours avec des revenus, des clics et des parrainages
    earnings_days = sum(1 for stat in daily_stats if stat["earnings"] > 0)
    clicks_days = sum(1 for stat in daily_stats if stat["clicks"] > 0)
    referrals_days = sum(1 for stat in daily_stats if stat["referrals"] > 0)

    # Top parrainages
    top_referrals = (
        referrals.select_related("referred")
        .annotate(total_earnings=Sum("commissions__amount"))
        .order_by("-total_earnings")[:5]
    )

    # Projection de revenus (simple projection linéaire)
    if earnings_data and len(earnings_data) > 1:
        (today - start_date).days + 1
        days_so_far = len([e for e in earnings_data if e > 0])
        if days_so_far > 0:
            daily_avg = sum(earnings_data) / days_so_far
            projected_earnings = []

            for i, earning in enumerate(earnings_data):
                if (
                    earning == 0 and i > len(earnings_data) // 2
                ):  # Projection seulement pour la seconde moitié
                    projected_earnings.append(daily_avg)
                else:
                    projected_earnings.append(
                        None
                    )  # Pas de projection pour les jours avec des données réelles
        else:
            projected_earnings = [None] * len(earnings_data)
    else:
        projected_earnings = [None] * len(earnings_data)

    # Statistiques d'utilisateurs affiliés
    total_users = User.objects.count()
    referred_users_count = User.objects.filter(referred_by__isnull=False).count()
    referred_by_user_count = User.objects.filter(referred_by=request.user).count()
    referred_percentage = (referred_users_count / total_users * 100) if total_users > 0 else 0

    # Répartition des types d'utilisateurs affiliés
    referred_by_user_types = (
        User.objects.filter(referred_by=request.user)
        .values("user_type")
        .annotate(count=Count("id"))
    )
    user_type_counts = {item["user_type"]: item["count"] for item in referred_by_user_types}

    # Données pour graphique en donut (répartition par type d'utilisateur)
    user_type_labels = []
    user_type_data = []
    user_type_colors = []

    if "ambassador" in user_type_counts:
        user_type_labels.append("Ambassadeurs")
        user_type_data.append(user_type_counts["ambassador"])
        user_type_colors.append("#4CAF50")  # vert

    if "escort" in user_type_counts:
        user_type_labels.append("Escortes")
        user_type_data.append(user_type_counts["escort"])
        user_type_colors.append("#2196F3")  # bleu

    if "member" in user_type_counts:
        user_type_labels.append("Membres")
        user_type_data.append(user_type_counts["member"])
        user_type_colors.append("#FFC107")  # jaune

    # Autres types d'utilisateurs (si présents)
    other_user_types = {
        k: v for k, v in user_type_counts.items() if k not in ["ambassador", "escort", "member"]
    }
    if other_user_types:
        user_type_labels.append("Autres")
        user_type_data.append(sum(other_user_types.values()))
        user_type_colors.append("#9E9E9E")  # gris

    context = {
        "period": period,
        "stats": {
            "clicks": clicks,
            "total_referrals": total_referrals,
            "ambassador_referrals": ambassador_referrals,
            "escort_referrals": escort_referrals,
            "total_earnings": total_earnings,
            "pending_earnings": pending_earnings,
            "paid_earnings": paid_earnings,
            "ambassador_earnings": ambassador_earnings,
            "escort_earnings": escort_earnings,
            "conversion_rate": conversion_rate,
            "avg_commission": avg_commission,
            "avg_daily_earnings": avg_daily_earnings,
            "referred_by_user_count": referred_by_user_count,
            "referred_percentage": referred_percentage,
        },
        "daily_stats": daily_stats,
        "top_referrals": top_referrals,
        # Données pour les graphiques
        "dates": json.dumps(dates),
        "earnings_data": json.dumps(earnings_data),
        "clicks_data": json.dumps(clicks_data),
        "referrals_data": json.dumps(referrals_data),
        "ambassador_data": json.dumps(ambassador_data),
        "escort_data": json.dumps(escort_data),
        "projected_earnings": json.dumps(projected_earnings),
        # Métriques de croissance
        "clicks_growth": clicks_growth,
        "referrals_growth": referrals_growth,
        "earnings_growth": earnings_growth,
        # Métriques de performance
        "highest_clicks": highest_clicks,
        "highest_referrals": highest_referrals,
        "highest_earnings": highest_earnings,
        "best_day_clicks": best_day_clicks,
        "best_day_referrals": best_day_referrals,
        "best_day_earnings": best_day_earnings,
        "avg_daily_clicks": avg_daily_clicks,
        "avg_daily_referrals": avg_daily_referrals,
        "earnings_days": earnings_days,
        "clicks_days": clicks_days,
        "referrals_days": referrals_days,
        # Graphique de distribution des utilisateurs
        "user_type_labels": json.dumps(user_type_labels),
        "user_type_data": json.dumps(user_type_data),
        "user_type_colors": json.dumps(user_type_colors),
    }

    return render(request, "affiliate/statistics.html", context)


# Fonction utilitaire pour calculer le taux de croissance
def calculate_growth(current_value, previous_value):
    if previous_value == 0:
        return 100 if current_value > 0 else 0
    return ((current_value - previous_value) / previous_value) * 100


# Rapports
@login_required
def reports(request):
    """Page de rapports analytiques."""
    report_type = request.GET.get("type", "commissions")
    period = request.GET.get("period", "30days")

    today = timezone.now().date()

    if period == "7days":
        start_date = today - timedelta(days=7)
    elif period == "30days":
        start_date = today - timedelta(days=30)
    elif period == "90days":
        start_date = today - timedelta(days=90)
    elif period == "year":
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)

    # Commissions
    if report_type == "commissions":
        commissions = Commission.objects.filter(
            referral__referrer=request.user, created_at__date__gte=start_date
        ).order_by("-created_at")

        # Agrégations
        by_status = commissions.values("status").annotate(count=Count("id"), sum=Sum("amount"))

        context = {
            "report_type": report_type,
            "period": period,
            "commissions": commissions,
            "by_status": by_status,
        }

        return render(request, "dashboard/reports/commissions.html", context)

    # Conversions
    elif report_type == "conversions":
        referrals = Referral.objects.filter(
            referrer=request.user, created_at__date__gte=start_date
        ).order_by("-created_at")

        context = {
            "report_type": report_type,
            "period": period,
            "referrals": referrals,
        }

        return render(request, "dashboard/reports/conversions.html", context)

    # Trafic
    elif report_type == "traffic":
        clicks = ReferralClick.objects.filter(
            user=request.user, created_at__date__gte=start_date
        ).order_by("-created_at")

        # Agrégations
        by_day = (
            clicks.extra({"day": "date(created_at)"})
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        context = {
            "report_type": report_type,
            "period": period,
            "clicks": clicks,
            "by_day": by_day,
        }

        return render(request, "dashboard/reports/traffic.html", context)

    else:
        messages.error(request, "Type de rapport non valide.")
        return redirect("dashboard:home")


# Notifications
@login_required
def notifications(request):
    """
    Liste des notifications de l'utilisateur
    """
    notifications_list = Notification.objects.filter(user=request.user).order_by("-created_at")
    paginator = Paginator(notifications_list, 20)
    page = request.GET.get("page")
    notifications = paginator.get_page(page)

    context = {
        "notifications": notifications,
    }

    return render(request, "dashboard/notifications/list.html", context)


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """
    Marquer une notification comme lue
    """
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()

    return JsonResponse({"status": "success"})


@login_required
@require_POST
def mark_all_notifications_read(request):
    """
    Marquer toutes les notifications comme lues
    """
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, _("Toutes les notifications ont été marquées comme lues."))

    return redirect("dashboard:notifications")


# Tâches et objectifs
@login_required
def tasks(request):
    """Page de gestion des tâches et objectifs."""
    messages.info(request, _("The tasks feature has been removed."))
    return redirect("dashboard:home")


@login_required
def task_detail(request, task_id):
    """Page de détail d'une tâche."""
    messages.info(request, _("The tasks feature has been removed."))
    return redirect("dashboard:home")


# Badges et réalisations
@login_required
def achievements(request):
    """Page des badges et réalisations."""
    messages.info(request, _("The achievements feature has been removed."))
    return redirect("dashboard:home")


@login_required
def achievement_detail(request, badge_id):
    """Page de détail d'un badge."""
    messages.info(request, _("The achievements feature has been removed."))
    return redirect("dashboard:home")


# Paramètres du tableau de bord
@login_required
def dashboard_settings(request):
    """Page des paramètres du tableau de bord."""
    from apps.accounts.models import UserProfile

    # S'assurer que l'utilisateur a un profil
    try:
        user_profile = request.user.account_profile
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)

    if request.method == "POST":
        # Traitement des paramètres
        email_notifications = request.POST.get("email_notifications") == "on"
        sms_notifications = request.POST.get("sms_notifications") == "on"
        newsletter_subscribed = request.POST.get("newsletter_subscribed") == "on"

        # Enregistrer les paramètres dans UserProfile
        user_profile.email_notifications = email_notifications
        user_profile.sms_notifications = sms_notifications
        user_profile.newsletter_subscribed = newsletter_subscribed
        user_profile.save()

        messages.success(request, "Vos paramètres ont été mis à jour avec succès.")

    context = {
        "user_profile": user_profile,
    }

    return render(request, "dashboard/settings.html", context)


# Thème du tableau de bord
@login_required
def dashboard_theme(request):
    """Page des paramètres de thème du tableau de bord."""
    from apps.accounts.models import UserProfile

    # S'assurer que l'utilisateur a un profil
    try:
        user_profile = request.user.account_profile
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)

    if request.method == "POST":
        # Traitement du formulaire de thème
        theme_color = request.POST.get("theme_color")
        dark_mode = request.POST.get("dark_mode") == "on"

        # Enregistrer les préférences
        user_profile.theme_color = theme_color
        user_profile.dark_mode = dark_mode
        user_profile.save()

        messages.success(request, "Vos préférences de thème ont été mises à jour.")

    context = {
        "user_profile": user_profile,
    }

    return render(request, "dashboard/theme.html", context)


# API pour widgets et données
@login_required
def api_summary(request):
    """API pour récupérer un résumé des statistiques."""
    # Statistiques de base
    thirty_days_ago = timezone.now().date() - timedelta(days=30)

    clicks = ReferralClick.objects.filter(
        user=request.user, created_at__date__gte=thirty_days_ago
    ).count()
    referrals = Referral.objects.filter(
        referrer=request.user, created_at__date__gte=thirty_days_ago
    ).count()
    earnings = (
        Commission.objects.filter(
            referral__referrer=request.user,
            status__in=["approved", "paid"],
            created_at__date__gte=thirty_days_ago,
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )

    # Calcul du taux de conversion
    if clicks > 0:
        conversion_rate = (referrals / clicks) * 100
    else:
        conversion_rate = 0

    # Notifications non lues
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()

    data = {
        "clicks": clicks,
        "referrals": referrals,
        "earnings": float(earnings),
        "conversion_rate": conversion_rate,
        "unread_notifications": unread_notifications,
    }

    return JsonResponse(data)


@login_required
def api_chart_data(request, period):
    """API endpoint pour récupérer les données du graphique de performance."""
    try:
        # Calculer les dates en fonction de la période
        end_date = timezone.now()
        start_date = end_date - timedelta(days=int(period))

        # Récupérer les données des commissions
        commissions = Commission.objects.filter(
            ambassador=request.user, created_at__range=(start_date, end_date)
        ).order_by("created_at")

        # Récupérer les données des parrainages
        referrals = Referral.objects.filter(
            referrer=request.user, created_at__range=(start_date, end_date)
        ).order_by("created_at")

        # Préparer les données pour le graphique
        dates = []
        commission_data = []
        ambassador_data = []
        escort_data = []

        # Créer un dictionnaire pour stocker les données par date
        data_by_date = {}

        # Initialiser toutes les dates avec des valeurs nulles
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            data_by_date[date_str] = {"commissions": 0, "ambassadors": 0, "escorts": 0}
            current_date += timedelta(days=1)

        # Remplir les données des commissions
        for commission in commissions:
            date_str = commission.created_at.strftime("%Y-%m-%d")
            data_by_date[date_str]["commissions"] += commission.amount

        # Remplir les données des parrainages
        for referral in referrals:
            date_str = referral.created_at.strftime("%Y-%m-%d")
            if referral.referred.is_ambassador:
                data_by_date[date_str]["ambassadors"] += 1
            else:
                data_by_date[date_str]["escorts"] += 1

        # Convertir les données en listes pour le graphique
        for date_str in sorted(data_by_date.keys()):
            dates.append(date_str)
            commission_data.append(data_by_date[date_str]["commissions"])
            ambassador_data.append(data_by_date[date_str]["ambassadors"])
            escort_data.append(data_by_date[date_str]["escorts"])

        return JsonResponse(
            {
                "labels": dates,
                "commissions": commission_data,
                "ambassadors": ambassador_data,
                "escorts": escort_data,
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def telegram_settings(request):
    """
    Vue pour configurer les notifications Telegram
    """
    from .forms import TelegramSettingsForm

    if request.method == "POST":
        form = TelegramSettingsForm(request.user, request.POST)
        if form.is_valid():
            telegram_chat_id = form.cleaned_data.get("telegram_chat_id", "")
            enable_telegram = form.cleaned_data.get("enable_telegram", False)
            telegram_language = form.cleaned_data.get("telegram_language", "fr")

            # Mettre à jour l'utilisateur directement
            if enable_telegram:
                request.user.telegram_chat_id = telegram_chat_id
            else:
                request.user.telegram_chat_id = None  # Désactiver les notifications Telegram

            # Toujours mettre à jour la langue
            request.user.telegram_language = telegram_language

            request.user.save(update_fields=["telegram_chat_id", "telegram_language"])

            messages.success(request, "Votre configuration Telegram a été mise à jour avec succès.")

            # Si c'est la première configuration, proposer un test
            if enable_telegram and telegram_chat_id:
                messages.info(
                    request,
                    "Vous pouvez maintenant tester l'envoi de notifications Telegram.",
                )
    else:
        form = TelegramSettingsForm(request.user)

    return render(request, "dashboard/notifications/telegram_settings.html", {"form": form})


@login_required
def test_telegram_notification(request):
    """
    Vue pour tester l'envoi d'une notification Telegram
    """
    if request.method == "POST":
        from .telegram_bot import TelegramNotifier
        from .models import Notification

        # Vérifier si l'utilisateur a configuré son ID Telegram
        if not request.user.telegram_chat_id:
            messages.error(request, "Vous devez d'abord configurer votre ID de chat Telegram.")
            return redirect("dashboard:telegram_settings")

        # Créer une notification de test
        test_notification = Notification.objects.create(
            user=request.user,
            title=(
                "Notification test"
                if request.user.telegram_language == "en"
                else (
                    "Test de notification Telegram"
                    if request.user.telegram_language == "fr"
                    else (
                        "Prueba de notificación"
                        if request.user.telegram_language == "es"
                        else (
                            "Benachrichtigungstest"
                            if request.user.telegram_language == "de"
                            else (
                                "Тестовое уведомление"
                                if request.user.telegram_language == "ru"
                                else (
                                    "测试通知"
                                    if request.user.telegram_language == "zh"
                                    else (
                                        "Test di notifica"
                                        if request.user.telegram_language == "it"
                                        else (
                                            "اختبار الإشعار"
                                            if request.user.telegram_language == "ar"
                                            else "Test de notification Telegram"
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            ),
            message=(
                "This is a test notification sent via Telegram. If you receive this message, the configuration was successful!"
                if request.user.telegram_language == "en"
                else (
                    "Ceci est un test d'envoi de notification via Telegram. Si vous recevez ce message, la configuration est réussie!"
                    if request.user.telegram_language == "fr"
                    else (
                        "Esta es una prueba de envío de notificación a través de Telegram. Si recibe este mensaje, ¡la configuración fue exitosa!"
                        if request.user.telegram_language == "es"
                        else (
                            "Dies ist ein Test zum Senden von Benachrichtigungen über Telegram. Wenn Sie diese Nachricht erhalten, war die Konfiguration erfolgreich!"
                            if request.user.telegram_language == "de"
                            else (
                                "Это тестовое уведомление, отправленное через Telegram. Если вы получили это сообщение, настройка прошла успешно!"
                                if request.user.telegram_language == "ru"
                                else (
                                    "这是通过Telegram发送的测试通知。如果您收到此消息，则表示配置成功！"
                                    if request.user.telegram_language == "zh"
                                    else (
                                        "Questo è un test di invio di notifiche tramite Telegram. Se ricevi questo messaggio, la configurazione è riuscita!"
                                        if request.user.telegram_language == "it"
                                        else (
                                            "هذا اختبار إرسال الإشعارات عبر تلجرام. إذا تلقيت هذه الرسالة، فقد نجح التكوين!"
                                            if request.user.telegram_language == "ar"
                                            else "Ceci est un test d'envoi de notification via Telegram. Si vous recevez ce message, la configuration est réussie!"
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            ),
            notification_type="info",
            is_read=False,
        )
        test_notification.save()

        # Envoyer la notification via Telegram en utilisant la langue préférée
        notifier = TelegramNotifier()
        message = notifier.format_notification(test_notification, request.user.telegram_language)
        success = notifier.send_message(chat_id=request.user.telegram_chat_id, message=message)

        if success:
            messages.success(
                request,
                "La notification de test a été envoyée avec succès. Vérifiez votre compte Telegram.",
            )
        else:
            messages.error(
                request,
                "L'envoi de la notification de test a échoué. Vérifiez votre configuration Telegram.",
            )

    return redirect("dashboard:telegram_settings")


# Vue temporaire pour déboguer le problème d'affiliation
@login_required
def debug_affiliate_relations(request, username=None):
    """Vue temporaire pour déboguer les relations d'affiliation."""
    from django.http import HttpResponse
    from apps.affiliate.models import Referral
    from apps.accounts.models import User
    import json

    if username:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return HttpResponse(f"Utilisateur {username} non trouvé", content_type="text/plain")
    else:
        user = request.user

    # Récupérer les utilisateurs qui ont référé cet utilisateur
    referred_by = user.referred_by.username if user.referred_by else "Aucun"

    # Récupérer les utilisateurs référés par cet utilisateur
    referred_users = User.objects.filter(referred_by=user)
    referred_ambassadors = referred_users.filter(user_type="ambassador")

    # Récupérer les entrées dans le modèle Referral
    referrals_as_ambassador = Referral.objects.filter(user=user)

    # Préparer la réponse
    response_data = {
        "user": {
            "username": user.username,
            "referral_code": user.referral_code,
            "user_type": user.user_type,
            "referred_by": referred_by,
        },
        "referred_users": [
            {
                "username": u.username,
                "user_type": u.user_type,
                "date_joined": u.date_joined.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for u in referred_users
        ],
        "referred_ambassadors": [
            {
                "username": a.username,
                "date_joined": a.date_joined.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for a in referred_ambassadors
        ],
        "referrals_in_model": [
            {
                "referred_user": r.referred.username,
                "date": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in referrals_as_ambassador
        ],
    }

    return HttpResponse(json.dumps(response_data, indent=2), content_type="application/json")


@login_required
def fix_affiliation(request, ambassador_username, user_username):
    """
    Vue pour corriger manuellement l'affiliation entre un ambassadeur et un utilisateur.
    Réservé aux administrateurs.
    """
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "Vous n'avez pas les droits pour effectuer cette action.")
        return redirect("dashboard:home")

    try:
        ambassador = User.objects.get(username=ambassador_username)
        referred_user = User.objects.get(username=user_username)
    except User.DoesNotExist:
        messages.error(request, "Utilisateur ou ambassadeur non trouvé.")
        return redirect("dashboard:debug_affiliate_relations")

    # Vérifier si l'utilisateur a déjà un parrain
    if referred_user.referred_by:
        old_referrer = referred_user.referred_by.username
        messages.warning(
            request,
            f"L'utilisateur {user_username} était déjà parrainé par {old_referrer}. Le parrainage a été remplacé.",
        )

    # Établir la relation
    referred_user.referred_by = ambassador
    referred_user.save(update_fields=["referred_by"])

    # Créer ou mettre à jour l'entrée de parrainage
    referral, created = Referral.objects.get_or_create(user=ambassador, referred=referred_user)

    if created:
        messages.success(
            request,
            f"Affiliation créée avec succès entre {ambassador_username} et {user_username}.",
        )
    else:
        messages.info(
            request,
            f"L'affiliation entre {ambassador_username} et {user_username} a été mise à jour.",
        )

    # Rediriger vers la page de débogage
    return redirect("dashboard:debug_affiliate_relations")


# Fonction utilitaire pour envoyer des notifications Telegram aux référents lors d'une nouvelle inscription
def notify_referrer_new_affiliate(new_user, referrer):
    """
    Envoie une notification Telegram au référent lorsqu'un nouvel affilié s'inscrit
    """
    from .telegram_bot import TelegramNotifier

    notifier = TelegramNotifier()

    # Utiliser la méthode dédiée pour envoyer la notification
    return notifier.send_new_ambassador_notification(referrer, new_user)


@login_required
def check_user_referral(request):
    """
    Page pour vérifier si l'utilisateur connecté est affilié
    """
    user = request.user

    context = {
        "user": user,
        "is_referred": user.referred_by is not None,
        "referral_code": user.referral_code,
    }

    if user.referred_by:
        context["referred_by"] = {
            "username": user.referred_by.username,
            "referral_code": user.referred_by.referral_code,
        }

        # Vérifier si l'entrée existe dans le modèle Referral
        from apps.affiliate.models import Referral

        referral = Referral.objects.filter(user=user.referred_by, referred=user).first()

        if referral:
            context["referral_entry_exists"] = True
            context["referral_created_at"] = referral.created_at
        else:
            context["referral_entry_exists"] = False

            # Option pour créer l'entrée manuellement
            if request.method == "POST" and "create_referral" in request.POST:
                try:
                    new_referral = Referral.objects.create(user=user.referred_by, referred=user)
                    context["referral_created"] = True
                    context["referral_entry_exists"] = True
                    context["referral_created_at"] = new_referral.created_at
                    messages.success(request, f"Entrée Referral créée avec succès.")
                except Exception as e:
                    messages.error(
                        request,
                        f"Erreur lors de la création de l'entrée Referral: {str(e)}",
                    )

    # Utiliser directement l'attribut telegram_chat_id sur l'utilisateur
    context["telegram_chat_id"] = user.telegram_chat_id

    return render(request, "dashboard/check_user_referral.html", context)


@login_required
def update_notification_language(request):
    """Mettre à jour la langue des notifications."""
    from apps.accounts.models import UserProfile

    if request.method == "POST":
        preferred_language = request.POST.get("preferred_language")
        valid_languages = ["en", "fr", "ru", "de", "zh", "es", "it", "ar"]

        if preferred_language in valid_languages:
            # Récupérer ou créer le profil utilisateur
            try:
                user_profile = request.user.account_profile
            except UserProfile.DoesNotExist:
                user_profile = UserProfile.objects.create(user=request.user)

            # Mettre à jour la langue préférée
            user_profile.preferred_language = preferred_language
            user_profile.save()

            messages.success(request, "Your notification language has been updated.")
        else:
            messages.error(request, "Invalid language selection.")

    return redirect("dashboard:notifications")


# Admin views
@login_required
def manage_ambassadors(request):
    """Admin dashboard to manage ambassadors and their commission rates."""
    # Make sure only staff/admins can access this view
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to access this page.")
        return redirect("dashboard:home")

    # Get all users with ambassador category - make sure both fields match
    # Précharger les profils utilisateurs pour éviter les requêtes N+1
    ambassadors = (
        User.objects.filter(user_category="ambassador", user_type="ambassador")
        .select_related("account_profile")
        .order_by("-date_joined")
    )

    # Filter by query if provided
    query = request.GET.get("q", "")
    if query:
        ambassadors = ambassadors.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(referral_code__icontains=query)
        )

    # Update commission rates if form was submitted
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        new_rate = request.POST.get("commission_rate")

        if user_id and new_rate:
            try:
                ambassador = User.objects.get(id=user_id, user_category="ambassador")
                # Validate the commission rate (5-50%)
                new_rate = float(new_rate)
                if 5 <= new_rate <= 50:
                    ambassador.commission_rate = new_rate
                    ambassador.save()
                    messages.success(
                        request,
                        f"Commission rate for {ambassador.username} updated to {new_rate}%",
                    )

                    # Log this admin action
                    admin_user = request.user.username
                    log_message = f"Commission rate updated to {new_rate}% by admin {admin_user}"
                    Notification.objects.create(
                        user=ambassador,
                        title="Commission Rate Updated",
                        message=log_message,
                        notification_type="system",
                    )
                else:
                    messages.error(request, "Commission rate must be between 5% and 50%")
            except User.DoesNotExist:
                messages.error(request, "User not found or not an ambassador")
            except ValueError:
                messages.error(request, "Invalid commission rate value")

    context = {
        "ambassadors": ambassadors,
        "query": query,
        "total_count": ambassadors.count(),
    }

    return render(request, "dashboard/admin/manage_ambassadors.html", context)


@login_required
def bulk_update_ambassadors(request):
    """Admin endpoint to bulk update ambassador commission rates."""
    # Make sure only staff/admins can access this view
    if not request.user.is_staff and not request.user.is_superuser:
        return JsonResponse(
            {"error": "You don't have permission to perform this action."}, status=403
        )

    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        data = json.loads(request.body)
        new_rate = float(data.get("commission_rate", 0))
        apply_to = data.get("apply_to", "none")
        user_ids = data.get("user_ids", [])
        query = data.get("query", "")

        # Validate commission rate
        if new_rate < 5 or new_rate > 50:
            return JsonResponse({"error": "Commission rate must be between 5% and 50%"}, status=400)

        # Get users to update based on the apply_to parameter
        users_to_update = []

        if apply_to == "all":
            users_to_update = User.objects.filter(
                user_category="ambassador", user_type="ambassador"
            )
        elif apply_to == "filtered" and query:
            users_to_update = User.objects.filter(
                user_category="ambassador", user_type="ambassador"
            ).filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(referral_code__icontains=query)
            )
        elif apply_to == "selected" and user_ids:
            users_to_update = User.objects.filter(
                id__in=user_ids, user_category="ambassador", user_type="ambassador"
            )
        else:
            return JsonResponse(
                {"error": "Invalid apply_to parameter or missing required data"},
                status=400,
            )

        # Update commission rates
        count = 0
        for user in users_to_update:
            user.commission_rate = new_rate
            user.save()

            # Create notification for user
            Notification.objects.create(
                user=user,
                title="Commission Rate Updated",
                message=f"Your base commission rate has been updated to {new_rate}% by an administrator.",
                notification_type="system",
            )
            count += 1

        # Log admin action
        admin_username = request.user.username
        logger = logging.getLogger("django")
        logger.info(
            f"Admin {admin_username} updated commission rates to {new_rate}% for {count} ambassadors"
        )

        return JsonResponse(
            {
                "success": True,
                "message": f"Successfully updated commission rate for {count} ambassadors",
                "count": count,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except ValueError:
        return JsonResponse({"error": "Invalid commission rate value"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def manage_escorts(request):
    """Admin dashboard to manage escorts and their commission rates."""
    # Make sure only staff/admins can access this view
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to access this page.")
        return redirect("dashboard:home")

    # Get all users with escort category
    escorts = User.objects.filter(user_category="escort").order_by("-date_joined")

    # Filter by query if provided
    query = request.GET.get("q", "")
    if query:
        escorts = escorts.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(referral_code__icontains=query)
        )

    # Update commission rates if form was submitted
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        new_rate = request.POST.get("commission_rate")

        if user_id and new_rate:
            try:
                escort = User.objects.get(id=user_id, user_category="escort")
                # Validate the commission rate (5-50%)
                new_rate = float(new_rate)
                if 5 <= new_rate <= 50:
                    escort.commission_rate = new_rate
                    escort.save()
                    messages.success(
                        request,
                        f"Commission rate for {escort.username} updated to {new_rate}%",
                    )

                    # Log this admin action
                    admin_user = request.user.username
                    log_message = f"Commission rate updated to {new_rate}% by admin {admin_user}"
                    Notification.objects.create(
                        user=escort,
                        title="Commission Rate Updated",
                        message=log_message,
                        notification_type="system",
                    )
                else:
                    messages.error(request, "Commission rate must be between 5% and 50%")
            except User.DoesNotExist:
                messages.error(request, "User not found or not an escort")
            except ValueError:
                messages.error(request, "Invalid commission rate value")

    context = {"escorts": escorts, "query": query, "total_count": escorts.count()}

    return render(request, "dashboard/admin/manage_escorts.html", context)


@login_required
def update_specific_rates(request):
    """Mise à jour des taux de commission spécifiques pour ambassadeurs et escortes."""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect("dashboard:home")

    if request.method != "POST":
        return redirect("dashboard:manage_ambassadors")

    user_id = request.POST.get("user_id")
    escort_rate = request.POST.get("escort_rate")
    ambassador_rate = request.POST.get("ambassador_rate")

    if not all([user_id, escort_rate, ambassador_rate]):
        messages.error(request, "All fields are required.")
        return redirect("dashboard:manage_ambassadors")

    try:
        # Validate rates
        escort_rate = float(escort_rate)
        ambassador_rate = float(ambassador_rate)

        if not (5 <= escort_rate <= 50 and 5 <= ambassador_rate <= 50):
            messages.error(request, "Commission rates must be between 5% and 50%.")
            return redirect("dashboard:manage_ambassadors")

        # Get the ambassador
        ambassador = User.objects.get(id=user_id, user_category="ambassador")

        # Update existing referrals based on type
        escort_referrals = Referral.objects.filter(user=ambassador, referred_user_type="escort")
        for referral in escort_referrals:
            referral.commission_rate = escort_rate
            referral.save()

        ambassador_referrals = Referral.objects.filter(
            user=ambassador, referred_user_type="ambassador"
        )
        for referral in ambassador_referrals:
            referral.commission_rate = ambassador_rate
            referral.save()

        # Also store these values in a config or profile for future referrals
        # This uses UserProfile to store the custom commission rates
        profile, created = UserProfile.objects.get_or_create(user=ambassador)
        profile.escort_commission_rate = escort_rate
        profile.ambassador_commission_rate = ambassador_rate
        profile.save()

        # Notify the ambassador
        Notification.objects.create(
            user=ambassador,
            title="Commission Rates Updated",
            message=f"Your commission rates have been updated by an administrator. New rates: Escorts: {escort_rate}%, Ambassadors: {ambassador_rate}%",
            notification_type="system",
        )

        # Envoyer une notification Telegram
        try:
            from .telegram_bot import TelegramNotifier

            notifier = TelegramNotifier()

            if ambassador.telegram_chat_id:
                # Messages multilingues
                languages = {
                    "en": f"Your commission rates have been updated:\n\n• Escort referrals: {escort_rate}%\n• Ambassador referrals: {ambassador_rate}%",
                    "fr": f"Vos taux de commission ont été mis à jour:\n\n• Parrainages d'escortes: {escort_rate}%\n• Parrainages d'ambassadeurs: {ambassador_rate}%",
                    "es": f"Sus tasas de comisión han sido actualizadas:\n\n• Referencias de escorts: {escort_rate}%\n• Referencias de embajadores: {ambassador_rate}%",
                    "de": f"Ihre Provisionssätze wurden aktualisiert:\n\n• Escort-Empfehlungen: {escort_rate}%\n• Botschafter-Empfehlungen: {ambassador_rate}%",
                    "ru": f"Ваши комиссионные ставки были обновлены:\n\n• Рефералы эскортов: {escort_rate}%\n• Рефералы амбассадоров: {ambassador_rate}%",
                    "zh": f"您的佣金率已更新:\n\n• 伴游推荐: {escort_rate}%\n• 大使推荐: {ambassador_rate}%",
                    "it": f"I tuoi tassi di commissione sono stati aggiornati:\n\n• Referral escort: {escort_rate}%\n• Referral ambasciatori: {ambassador_rate}%",
                    "ar": f"تم تحديث معدلات العمولة الخاصة بك:\n\n• إحالات المرافقات: {escort_rate}%\n• إحالات السفراء: {ambassador_rate}%",
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
                    "en": "Commission Rates Updated",
                    "fr": "Taux de commission mis à jour",
                    "es": "Tasas de comisión actualizadas",
                    "de": "Provisionssätze aktualisiert",
                    "ru": "Комиссионные ставки обновлены",
                    "zh": "佣金率已更新",
                    "it": "Tassi di commissione aggiornati",
                    "ar": "تم تحديث معدلات العمولة",
                }
                title = titles.get(lang, titles["en"])

                # Envoyer la notification
                notifier.send_message(
                    chat_id=ambassador.telegram_chat_id,
                    message=f"*{title}*\n\n{message}",
                )
        except Exception as e:
            # Log the change
            logger = logging.getLogger("django")
            logger.error(f"Error sending Telegram notification: {str(e)}")

        # Log the change
        logger.info(
            f"Admin {request.user.username} updated commission rates for {ambassador.username}. Escort: {escort_rate}%, Ambassador: {ambassador_rate}%"
        )

        messages.success(
            request,
            f"Commission rates for {ambassador.username} have been updated successfully.",
        )

    except User.DoesNotExist:
        messages.error(request, "User not found or not an ambassador.")
    except ValueError:
        messages.error(request, "Invalid rate values.")
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")

    return redirect("dashboard:manage_ambassadors")


@login_required
def admin_commissions(request):
    """Page d'administration des commissions."""
    # Vérifier que l'utilisateur est administrateur
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(
            request,
            "Vous n'avez pas les permissions nécessaires pour accéder à cette page.",
        )
        return redirect("dashboard:home")

    # Filtrer par mois (par défaut: mois courant)
    current_month = timezone.now().month
    current_year = timezone.now().year

    month = request.GET.get("month", current_month)
    year = request.GET.get("year", current_year)

    try:
        month = int(month)
        year = int(year)
        if month < 1 or month > 12:
            month = current_month
    except (ValueError, TypeError):
        month = current_month
        year = current_year

    # Déterminer les dates de début et de fin du mois
    start_date = timezone.datetime(year, month, 1, tzinfo=timezone.get_current_timezone())

    # Déterminer le dernier jour du mois
    if month == 12:
        end_date = timezone.datetime(
            year + 1, 1, 1, tzinfo=timezone.get_current_timezone()
        ) - timezone.timedelta(seconds=1)
    else:
        end_date = timezone.datetime(
            year, month + 1, 1, tzinfo=timezone.get_current_timezone()
        ) - timezone.timedelta(seconds=1)

    # Récupérer toutes les commissions en attente pour le mois sélectionné
    pending_commissions = (
        Commission.objects.filter(
            status__in=["pending", "approved"],
            created_at__gte=start_date,
            created_at__lte=end_date,
        )
        .select_related("referral", "referral__referrer")
        .order_by("-created_at")
    )

    # Récupérer les commissions récemment payées
    approved_commissions = (
        Commission.objects.filter(status="paid", paid_at__gte=start_date, paid_at__lte=end_date)
        .select_related("referral", "referral__referrer")
        .order_by("-paid_at")[:50]
    )  # Limiter à 50 pour performance

    # Traitement des actions de paiement
    if request.method == "POST":
        action = request.POST.get("action")
        print(f"Action reçue: {action}")  # Debug
        print(f"Données POST: {request.POST}")  # Debug

        try:
            if action == "mark_paid" and request.POST.getlist("commission_ids"):
                commission_ids = request.POST.getlist("commission_ids")
                print(f"Commission IDs: {commission_ids}")  # Debug

                if commission_ids:
                    batch_id = f"BATCH-{uuid.uuid4().hex[:8]}"
                    count = 0
                    total_amount = 0

                    for commission_id in commission_ids:
                        try:
                            commission = Commission.objects.get(id=commission_id)
                            if commission.status in ["pending", "approved"]:
                                commission.mark_as_paid(batch_id=batch_id)
                                count += 1
                                total_amount += commission.amount
                        except Commission.DoesNotExist:
                            print(f"Commission {commission_id} non trouvée")  # Debug
                            continue

                    messages.success(
                        request,
                        f"{count} commission(s) marquée(s) comme payée(s) pour un total de {total_amount}€.",
                    )
                    return redirect("dashboard:admin_commissions")

            elif action == "mark_single_paid":
                commission_id = request.POST.get("commission_id")
                print(f"Commission ID pour paiement unique: {commission_id}")  # Debug

                if commission_id:
                    try:
                        commission = Commission.objects.get(id=commission_id)
                        if commission.status in ["pending", "approved"]:
                            success = commission.mark_as_paid()
                            if success:
                                messages.success(
                                    request,
                                    f"Commission de {commission.amount}€ marquée comme payée.",
                                )
                            else:
                                messages.warning(
                                    request,
                                    f"La commission était déjà dans l'état 'payée'.",
                                )
                        else:
                            messages.warning(
                                request,
                                f"La commission n'est pas dans un état permettant le paiement (statut actuel: {commission.status}).",
                            )
                    except Commission.DoesNotExist:
                        messages.error(request, "Commission non trouvée.")
                    except Exception as e:
                        print(f"Erreur lors du marquage comme payé: {str(e)}")  # Debug
                        messages.error(request, f"Erreur lors du marquage comme payé: {str(e)}")

                    return redirect("dashboard:admin_commissions")

            elif action == "mark_all_paid":
                batch_id = f"BATCH-{uuid.uuid4().hex[:8]}"
                count = 0
                total_amount = 0

                for commission in pending_commissions:
                    try:
                        success = commission.mark_as_paid(batch_id=batch_id)
                        if success:
                            count += 1
                            total_amount += commission.amount
                    except Exception as e:
                        print(f"Erreur sur commission {commission.id}: {str(e)}")  # Debug

                if count > 0:
                    messages.success(
                        request,
                        f"{count} commission(s) marquée(s) comme payée(s) pour un total de {total_amount}€.",
                    )
                else:
                    messages.info(request, "Aucune commission à payer.")
                return redirect("dashboard:admin_commissions")

            elif action == "mark_paid" and request.POST.get("ambassador_id"):
                ambassador_id = request.POST.get("ambassador_id")
                print(f"Ambassador ID: {ambassador_id}")  # Debug

                try:
                    ambassador = User.objects.get(id=ambassador_id)
                    batch_id = f"BATCH-AMB-{uuid.uuid4().hex[:8]}"
                    count = 0
                    total_amount = 0

                    # Marquer toutes les commissions de cet ambassadeur comme payées
                    ambassador_commissions = pending_commissions.filter(
                        referral__referrer=ambassador
                    )
                    print(
                        f"Nombre de commissions pour cet ambassadeur: {ambassador_commissions.count()}"
                    )  # Debug

                    for commission in ambassador_commissions:
                        try:
                            success = commission.mark_as_paid(batch_id=batch_id)
                            if success:
                                count += 1
                                total_amount += commission.amount
                        except Exception as e:
                            print(f"Erreur sur commission {commission.id}: {str(e)}")  # Debug

                    if count > 0:
                        messages.success(
                            request,
                            f"{count} commission(s) pour {ambassador.username} marquée(s) comme payée(s) pour un total de {total_amount}€.",
                        )
                    else:
                        messages.info(
                            request,
                            f"Aucune commission à payer pour {ambassador.username}.",
                        )

                except User.DoesNotExist:
                    messages.error(request, "Ambassadeur non trouvé.")
                except Exception as e:
                    print(f"Erreur générale: {str(e)}")  # Debug
                    messages.error(request, f"Erreur: {str(e)}")

                return redirect("dashboard:admin_commissions")
            else:
                messages.warning(request, f"Action non reconnue: {action}")
                return redirect("dashboard:admin_commissions")
        except Exception as e:
            print(f"Exception non gérée: {str(e)}")  # Debug
            messages.error(request, f"Une erreur est survenue: {str(e)}")
            return redirect("dashboard:admin_commissions")

    # Récupérer la liste des mois disponibles pour le filtre
    available_months = []
    years = set()

    # Récupérer tous les mois des deux dernières années pour le dropdown
    for i in range(1, 13):
        for y in range(current_year - 1, current_year + 1):
            month_name = timezone.datetime(y, i, 1).strftime("%B")
            available_months.append((i, f"{month_name} {y}"))
            years.add(y)

    # Calculer le total des commissions en attente pour le mois
    total_pending_amount = pending_commissions.aggregate(Sum("amount"))["amount__sum"] or 0

    # Préparer la structure commissions_by_ambassador pour le template
    commissions_by_ambassador = {}

    for commission in pending_commissions:
        ambassador = commission.referral.referrer
        if ambassador not in commissions_by_ambassador:
            commissions_by_ambassador[ambassador] = {
                "count": 0,
                "amount": 0,
                "commissions": [],
            }

        commissions_by_ambassador[ambassador]["count"] += 1
        commissions_by_ambassador[ambassador]["amount"] += commission.amount
        commissions_by_ambassador[ambassador]["commissions"].append(commission)

    context = {
        "pending_commissions": pending_commissions,
        "approved_commissions": approved_commissions,
        "total_pending_amount": total_pending_amount,
        "commissions_by_ambassador": commissions_by_ambassador,
        "selected_month": month,
        "selected_year": year,
        "available_months": available_months,
        "available_years": sorted(years),
        "month_name": start_date.strftime("%B %Y"),
    }

    return render(request, "dashboard/admin_commissions.html", context)


@login_required
@require_POST
def mark_commission_paid(request, commission_id):
    """Marquer une commission individuelle comme payée."""
    # Vérifier que l'utilisateur est administrateur
    if not request.user.is_staff and not request.user.is_superuser:
        return JsonResponse({"error": "Vous n'avez pas les permissions nécessaires."}, status=403)

    try:
        commission = Commission.objects.get(id=commission_id)
        if commission.status in ["pending", "approved"]:
            commission.mark_as_paid()
            return JsonResponse(
                {
                    "success": True,
                    "message": f"Commission de {commission.amount}€ marquée comme payée.",
                }
            )
        else:
            return JsonResponse(
                {"error": "Cette commission n'est pas en attente de paiement."},
                status=400,
            )
    except Commission.DoesNotExist:
        return JsonResponse({"error": "Commission non trouvée."}, status=404)


@login_required
def user_profile(request, username):
    """Affiche le profil détaillé d'un utilisateur."""
    # Vérifier que l'utilisateur est administrateur
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(
            request,
            "Vous n'avez pas les permissions nécessaires pour accéder à cette page.",
        )
        return redirect("dashboard:home")

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        messages.error(request, f"L'utilisateur {username} n'existe pas.")
        return redirect("dashboard:admin_commissions")

    # Obtenir le profil utilisateur
    profile, created = UserProfile.objects.get_or_create(user=user)

    # Récupérer toutes les commissions pour les calculs
    if user.is_ambassador:
        all_commissions = Commission.objects.filter(referral__referrer=user)
        # Récupérer les commissions limitées pour l'affichage
        commissions = all_commissions.select_related("referral", "referral__referrer").order_by(
            "-created_at"
        )[:50]
    else:
        all_commissions = Commission.objects.filter(referral__referred=user)
        # Récupérer les commissions limitées pour l'affichage
        commissions = all_commissions.select_related("referral", "referral__referrer").order_by(
            "-created_at"
        )[:50]

    # Récupérer les parrainages
    referrals = (
        Referral.objects.filter(user=user).select_related("referred").order_by("-created_at")
    )

    context = {
        "profile_user": user,
        "profile": profile,
        "commissions": commissions,
        "referrals": referrals,
        "total_commissions": all_commissions.count(),
        "total_pending": all_commissions.filter(status="pending").aggregate(Sum("amount"))[
            "amount__sum"
        ]
        or 0,
        "total_paid": all_commissions.filter(status="paid").aggregate(Sum("amount"))["amount__sum"]
        or 0,
    }

    return render(request, "dashboard/user_profile.html", context)


@login_required
def user_settings(request):
    """Vue pour gérer les paramètres utilisateur."""
    # Initialize Supabase client
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    # Vérifier si les informations de connexion Supabase sont disponibles
    supabase = None
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
    else:
        messages.warning(request, "Supabase configuration is missing. Password change functionality is disabled.")
    
    if request.method == "POST":
        # Check the form type
        form_type = request.POST.get("form_type", "")
        
        # Password change form
        if form_type == "password_change":
            # Vérifier si Supabase est configuré
            if not supabase:
                messages.error(request, "Password change is not available at the moment. Please contact support.")
            else:
                current_password = request.POST.get("current_password")
                new_password = request.POST.get("new_password")
                confirm_password = request.POST.get("confirm_password")
                
                # Validate passwords
                if not current_password or not new_password or not confirm_password:
                    messages.error(request, "Please fill in all password fields.")
                elif new_password != confirm_password:
                    messages.error(request, "New passwords do not match.")
                elif len(new_password) < 8:
                    messages.error(request, "Password must be at least 8 characters long.")
                else:
                    try:
                        # Get user email
                        user_email = request.user.email
                        
                        if not user_email:
                            messages.error(request, "User email not found. Password change requires a valid email address.")
                            return redirect("dashboard:settings")
                        
                        # Méthode standard Supabase: d'abord authentifier puis mettre à jour
                        try:
                            # 1. Authentifier avec les identifiants actuels
                            auth_response = supabase.auth.sign_in_with_password({
                                "email": user_email,
                                "password": current_password
                            })
                            
                            # 2. Si l'authentification réussit, mettre à jour le mot de passe
                            # Cette méthode est plus sécurisée car elle vérifie d'abord le mot de passe actuel
                            update_response = supabase.auth.update_user({
                                "password": new_password
                            })
                            
                            messages.success(request, "Your password has been updated successfully.")
                            return redirect("dashboard:settings")
                            
                        except Exception as auth_error:
                            # Erreur plus détaillée pour aider au débogage
                            error_message = str(auth_error)
                            print(f"Supabase auth error: {error_message}")
                            
                            if "invalid login credentials" in error_message.lower():
                                messages.error(request, "Current password is incorrect.")
                            else:
                                messages.error(request, f"Authentication error: {error_message}")
                    
                    except Exception as e:
                        print(f"Password update error: {str(e)}")
                        messages.error(request, f"Password update failed: {str(e)}")
        
        # Regular settings form
        else:
            # Traitement des paramètres
            preferred_language = request.POST.get("language", "fr")
            theme = request.POST.get("theme", "light")
            email_notifications = request.POST.get("email_notifications", "off") == "on"
            display_mode = request.POST.get("display_mode", "light")

            # Mise à jour des préférences utilisateur
            user_profile = request.user.account_profile
            user_profile.preferred_language = preferred_language
            user_profile.theme_color = theme  # Notez que le champ est theme_color et non theme
            user_profile.email_notifications = email_notifications
            user_profile.display_mode = display_mode
            user_profile.save()

            messages.success(request, "Your settings have been updated successfully.")
            return redirect("dashboard:settings")

    context = {
        "user_profile": request.user.account_profile,
        "available_languages": [
            ("fr", "Français"),
            ("en", "English"),
            ("es", "Español"),
            ("de", "Deutsch"),
        ],
        "available_themes": [
            ("light", "Light"),
            ("dark", "Dark"),
            ("system", "System"),
        ],
        "supabase_enabled": supabase is not None,
    }
    return render(request, "dashboard/settings.html", context)
