from django.apps import AppConfig


class AffiliateConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.affiliate"
    verbose_name = "Système d'affiliation"

    def ready(self):
        pass
