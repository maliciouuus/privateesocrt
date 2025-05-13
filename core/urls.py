"""
URL configuration for escortdollars project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.i18n import JavaScriptCatalog
from django.contrib.sitemaps.views import sitemap
from apps.affiliate.views import process_external_referral, banner_page
from .sitemaps import StaticViewSitemap, EscortSitemap, WhiteLabelSitemap
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from core import views  # Import views from core module

schema_view = get_schema_view(
    openapi.Info(
        title="EscortDollars API",
        default_version="v1",
        description="API pour le système d'affiliation EscortDollars",
        terms_of_service="https://escortdollars.com/terms/",
        contact=openapi.Contact(email="contact@escortdollars.com"),
        license=openapi.License(name="Propriétaire"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

sitemaps = {
    "static": StaticViewSitemap,
    "escorts": EscortSitemap,
    "whitelabels": WhiteLabelSitemap,
}

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Authentification et gestion des comptes
    path("accounts/", include("allauth.urls")),  # Allauth URLs sous /accounts/
    path("accounts/", include("apps.accounts.urls")),  # Nos vues personnalisées
    # Affiliation et gestion des liens
    path("affiliate/", include("apps.affiliate.urls")),
    # Whitelabel
    path("whitelabel/", include("apps.whitelabel.urls")),
    # Tableau de bord
    path("dashboard/", include("apps.dashboard.urls")),
    # API pour l'affiliation externe (utilisée par les sites white label)
    path("api/affiliate/refer/", process_external_referral, name="external_referral"),
    # Health check endpoint
    path("health/", views.health_check, name="health_check"),
    # Pages du site principal avec la vue dynamique pour la page d'accueil
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    path("pricing/", TemplateView.as_view(template_name="pricing.html"), name="pricing"),
    path("contact/", TemplateView.as_view(template_name="contact.html"), name="contact"),
    path("terms/", TemplateView.as_view(template_name="terms.html"), name="terms"),
    path("privacy/", TemplateView.as_view(template_name="privacy.html"), name="privacy"),
    path("faq/", TemplateView.as_view(template_name="faq.html"), name="faq"),
    path("blog/", TemplateView.as_view(template_name="blog.html"), name="blog"),
    path("banners/", banner_page, name="banners"),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    # Documentation Swagger
    path("swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("luxury/", views.home_luxury, name="home_luxury"),
    path("ultra-luxury/", views.home_ultra_luxury, name="home_ultra_luxury"),
    path("api/", include("apps.affiliate.api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
