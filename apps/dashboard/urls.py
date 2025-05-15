from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    # Simple Dashboard (for allauth users)
    path("simple/", views.simple_dashboard, name="simple_dashboard"),
    # Dashboard principal
    path("", views.dashboard_home, name="home"),
    # Vue d'ensemble et statistiques
    path("overview/", views.overview, name="overview"),
    path("stats/", views.statistics, name="stats"),
    path("reports/", views.reports, name="reports"),
    # Debug
    path(
        "debug-affiliations/",
        views.debug_affiliate_relations,
        name="debug_affiliations",
    ),
    path(
        "fix-affiliation/<str:ambassador_username>/<str:user_username>/",
        views.fix_affiliation,
        name="fix_affiliation",
    ),
    path(
        "debug-affiliation/",
        views.debug_affiliate_relations,
        name="debug_affiliate_relations",
    ),
    path("check-user-referral/", views.check_user_referral, name="check_user_referral"),
    # Notifications
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/telegram/", views.telegram_settings, name="telegram_settings"),
    # Test des notifications Telegram (à commenter en production)
    # path(
    #     "test-telegram/",
    #     views.test_telegram_notification,
    #     name="test_telegram",
    # ),
    path(
        "notifications/update-language/",
        views.update_notification_language,
        name="update_notification_language",
    ),
    path(
        "notifications/mark-read/<uuid:notification_id>/",
        views.mark_notification_read,
        name="mark_notification_read",
    ),
    path(
        "notifications/mark-all-read/",
        views.mark_all_notifications_read,
        name="mark_all_notifications_read",
    ),
    # Paramètres et personnalisation
    path("theme/", views.dashboard_theme, name="theme"),
    # Admin section
    path("admin/ambassadors/", views.manage_ambassadors, name="manage_ambassadors"),
    path(
        "admin/ambassadors/bulk-update/",
        views.bulk_update_ambassadors,
        name="bulk_update_ambassadors",
    ),
    path(
        "admin/ambassadors/update-specific-rates/",
        views.update_specific_rates,
        name="update_specific_rates",
    ),
    path("admin/commissions/", views.admin_commissions, name="admin_commissions"),
    path(
        "admin/commissions/mark-paid/<uuid:commission_id>/",
        views.mark_commission_paid,
        name="mark_commission_paid",
    ),
    path("admin/user/<str:username>/", views.user_profile, name="user_profile"),
    # API pour widgets et données
    path("api/summary/", views.api_summary, name="api_summary"),
    path("api/chart-data/<int:period>/", views.api_chart_data, name="api_chart_data"),
    # Ajout de l'URL pour les paramètres
    path("settings/", views.user_settings, name="settings"),
]
