from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

router = DefaultRouter()
router.register(r"referral-clicks", views.ReferralClickViewSet, basename="referral-click")
router.register(r"referrals", views.ReferralViewSet, basename="referral")
router.register(r"commissions", views.CommissionViewSet, basename="commission")
router.register(r"commission-rates", views.CommissionRateViewSet, basename="commission-rate")
router.register(r"payouts", views.PayoutViewSet, basename="payout")
router.register(r"white-labels", views.WhiteLabelViewSet, basename="white-label")
# router.register(r"banners", views.BannerViewSet, basename="banner")
router.register(r"stats", views.StatsViewSet, basename="stats")

schema_view = get_schema_view(
    openapi.Info(
        title="EscortDollars API",
        default_version="v1",
        description="Documentation de l'API d'affiliation white label",
        contact=openapi.Contact(email="support@escortdollars.com"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    
    # Nouveaux endpoints publics
    path("external/referral/", views.ExternalReferralAPI.as_view(), name="external-referral"),
    path("public/whitelabels/", views.PublicWhiteLabelAPI.as_view(), name="public-whitelabels"),
    path("signup/referral/", views.ReferralSignupAPI.as_view(), name="signup-referral"),
]
