from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    """
    Notifications pour les utilisateurs
    """

    NOTIFICATION_TYPES = (
        ("info", "Information"),
        ("success", "Succès"),
        ("warning", "Avertissement"),
        ("error", "Erreur"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES, default="info")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.user.username}"


class UserStatistics(models.Model):
    """
    Statistiques quotidiennes des utilisateurs ambassadeurs
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="statistics"
    )
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_referrals = models.PositiveIntegerField(default=0)
    total_transactions = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "User Statistics"

    def __str__(self):
        return f"Statistics for {self.user.username}"


class UserProfile(models.Model):
    """
    Profil utilisateur avec préférences et paramètres supplémentaires
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dashboard_profile",
    )

    # Informations de l'entreprise
    company_name = models.CharField(_("Nom de l'entreprise"), max_length=100, blank=True)
    vat_id = models.CharField(_("Numéro de TVA"), max_length=50, blank=True)
    website = models.URLField(_("Site web"), blank=True)

    # Adresse
    address = models.CharField(_("Adresse"), max_length=255, blank=True)
    zip_code = models.CharField(_("Code postal"), max_length=20, blank=True)
    city = models.CharField(_("Ville"), max_length=100, blank=True)
    country = models.CharField(_("Pays"), max_length=100, blank=True)

    # Langue préférée pour les notifications
    LANGUAGE_CHOICES = (
        ("en", "English"),
        ("fr", "Français"),
        ("ru", "Русский"),
        ("de", "Deutsch"),
        ("zh", "中文"),
        ("es", "Español"),
        ("it", "Italiano"),
        ("ar", "العربية"),
    )

    preferred_language = models.CharField(
        _("Langue préférée"), max_length=5, choices=LANGUAGE_CHOICES, default="en"
    )

    # Telegram
    telegram_chat_id = models.CharField(
        _("Telegram Chat ID"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("ID de chat Telegram pour recevoir les notifications"),
    )

    class Meta:
        verbose_name = _("profil utilisateur")
        verbose_name_plural = _("profils utilisateurs")

    def __str__(self):
        return f"Profil de {self.user.username}"
