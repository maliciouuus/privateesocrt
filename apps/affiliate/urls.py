from django.urls import path
from . import views
from .services.webhook_handler import WebhookHandler

app_name = "affiliate"

webhook_handler = WebhookHandler()

urlpatterns = [
    # Pages principales
    path("", views.home, name="home"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("links/", views.affiliate_links, name="links"),
    path("marketing-materials/", views.marketing_materials, name="marketing_materials"),
    path("banners/", views.banners, name="banners"),
    path("statistics/", views.statistics, name="statistics"),
    path("reports/", views.reports, name="reports"),
    # Commissions et paiements
    path("commissions/", views.commissions, name="commissions"),
    path(
        "commissions/<int:commission_id>/",
        views.commission_detail,
        name="commission_detail",
    ),
    path("payouts/", views.payouts, name="payouts"),
    path("payouts/<int:payout_id>/", views.payout_detail, name="payout_detail"),
    path("payment-methods/", views.payment_methods, name="payment_methods"),
    path("payment-methods/add/", views.add_payment_method, name="add_payment_method"),
    path(
        "payment-methods/<int:pk>/edit/",
        views.edit_payment_method,
        name="edit_payment_method",
    ),
    path(
        "payment-methods/<int:pk>/delete/",
        views.delete_payment_method,
        name="delete_payment_method",
    ),
    # API endpoints
    path("api/stats/", views.api_stats, name="api_stats"),
    path("api/commissions/", views.api_commissions, name="api_commissions"),
    path("api/user-info/", views.api_user_info, name="api_user_info"),
    path("api/ambassadors/", views.api_ambassadors, name="api_ambassadors"),
    path("api/escorts/", views.api_escorts, name="api_escorts"),
    # Redirection et tracking
    path("ref/<str:referral_code>/", views.referral_redirect, name="referral_redirect"),
    path("track/<str:referral_code>/", views.track_click, name="track_click"),
    path(
        "process-referral/",
        views.process_external_referral,
        name="process_external_referral",
    ),
    # Gestion des commissions
    path("commission-list/", views.commission_list, name="commission_list"),
    path(
        "commission/<int:pk>/mark-paid/",
        views.commission_mark_paid,
        name="commission_mark_paid",
    ),
    # Transactions et paiements
    path("transactions/", views.transaction_list, name="transaction_list"),
    path("transactions/<int:pk>/", views.transaction_detail, name="transaction_detail"),
    path("payout-list/", views.payout_list, name="payout_list"),
    path("payout/<int:pk>/", views.payout_detail, name="payout_detail"),
    # Configuration
    path("commission-rates/", views.commission_rate_list, name="commission_rate_list"),
    path(
        "commission-rates/<int:pk>/edit/",
        views.commission_rate_edit,
        name="commission_rate_edit",
    ),
    # Crypto
    path("crypto-payment/", views.crypto_payment, name="crypto_payment"),
    # Niveaux
    path("levels/", views.AffiliateLevelsView.as_view(), name="levels"),
    # Administration
    path("manager/", views.affiliate_manager_dashboard, name="manager_dashboard"),
    path("manager/affiliates/", views.affiliate_list, name="affiliate_list"),
    path(
        "manager/affiliates/<int:user_id>/",
        views.affiliate_detail,
        name="affiliate_detail",
    ),
    path(
        "manager/commissions/",
        views.commission_management,
        name="commission_management",
    ),
    path(
        "manager/commissions/<int:commission_id>/approve/",
        views.commission_approve,
        name="commission_approve",
    ),
    path(
        "manager/commissions/<int:commission_id>/reject/",
        views.commission_reject,
        name="commission_reject",
    ),
    path(
        "webhooks/coinpayments/",
        webhook_handler.handle_coinpayments_ipn,
        name="coinpayments-webhook",
    ),
    path(
        "webhooks/payout/",
        webhook_handler.handle_payout_notification,
        name="payout-webhook",
    ),
]
