from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    """
    Modèle utilisateur personnalisé pour EscortDollars avec gestion des ambassadeurs
    """

    USER_TYPE_CHOICES = (
        ("ambassador", "Ambassadeur"),
        ("administrator", "Administrateur"),
    )

    user_type = models.CharField(
        _("Type d'utilisateur"),
        max_length=15,
        choices=USER_TYPE_CHOICES,
        default="ambassador",
    )
    bio = models.TextField(_("Biographie"), blank=True)
    phone_number = models.CharField(_("Numéro de téléphone"), max_length=20, blank=True)
    birth_date = models.DateField(_("Date de naissance"), null=True, blank=True)
    profile_picture = models.ImageField(
        _("Photo de profil"), upload_to="profile_pics/", blank=True, null=True
    )

    # Champs spécifiques aux ambassadeurs
    referral_code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    referred_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals",
    )
    is_verified = models.BooleanField(_("Vérifié"), default=False)
    user_category = models.CharField(
        _("Catégorie d'utilisateur"),
        max_length=15,
        choices=[
            ("escort", _("Escorte")),
            ("ambassador", _("Ambassadeur")),
            ("admin", _("Administrateur")),
        ],
        default="ambassador",
    )

    # Paramètres d'affiliation
    payout_email = models.EmailField(_("Email pour les paiements"), blank=True)
    commission_rate = models.DecimalField(
        _("Taux de commission"),
        max_digits=5,
        decimal_places=2,
        default=20.00,
        validators=[MinValueValidator(5), MaxValueValidator(50)],
    )

    # Mémoisation des gains d'affiliation pour des performances optimales
    total_commission_earned = models.DecimalField(
        _("Total des commissions gagnées"),
        max_digits=10,
        decimal_places=2,
        default=0.00,
    )
    pending_commission = models.DecimalField(
        _("Commissions en attente"), max_digits=10, decimal_places=2, default=0.00
    )

    # Métadonnées
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)

    # Ajout des champs pour Telegram directement dans le modèle User
    telegram_chat_id = models.CharField(max_length=100, null=True, blank=True)
    telegram_username = models.CharField(max_length=32, null=True, blank=True)
    telegram_verified = models.BooleanField(default=False)
    telegram_language = models.CharField(
        _("Langue des notifications Telegram"),
        max_length=5,
        default="fr",
        choices=[
            ("fr", "Français"),
            ("en", "English"),
            ("es", "Español"),
            ("de", "Deutsch"),
            ("it", "Italiano"),
            ("ru", "Русский"),
            ("ar", "العربية"),
            ("zh", "中文"),
        ],
    )

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        super().save(*args, **kwargs)

    def generate_referral_code(self):
        import random
        import string

        while True:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not User.objects.filter(referral_code=code).exists():
                return code

    @property
    def is_ambassador(self):
        return self.user_type == "ambassador"

    @property
    def is_administrator(self):
        return self.user_type == "administrator"

    @property
    def is_escort(self):
        return self.user_category == "escort"

    @property
    def age(self):
        if self.birth_date:
            today = timezone.now().date()
            return (
                today.year
                - self.birth_date.year
                - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
            )
        return None


class UserProfile(models.Model):
    """
    Profil utilisateur avec préférences et paramètres supplémentaires
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="account_profile")

    # Informations de l'entreprise
    company_name = models.CharField(_("Nom de l'entreprise"), max_length=100, blank=True)
    vat_id = models.CharField(_("Numéro de TVA"), max_length=50, blank=True)
    website = models.URLField(_("Site web"), blank=True)

    # Adresse
    address = models.CharField(_("Adresse"), max_length=255, blank=True)
    zip_code = models.CharField(_("Code postal"), max_length=20, blank=True)
    city = models.CharField(_("Ville"), max_length=100, blank=True)
    country = models.CharField(_("Pays"), max_length=100, blank=True)

    # Adresses de portefeuille
    usdt_trc20_wallet = models.CharField(_("Adresse USDT (TRC20)"), max_length=255, blank=True)
    btc_wallet = models.CharField(_("Adresse Bitcoin"), max_length=255, blank=True)
    eth_erc20_wallet = models.CharField(_("Adresse ETH (ERC20)"), max_length=255, blank=True)

    # Préférences
    dark_mode = models.BooleanField(_("Mode sombre"), default=False)
    newsletter_subscribed = models.BooleanField(_("Abonné à la newsletter"), default=True)
    preferred_language = models.CharField(
        _("Langue préférée"),
        max_length=5,
        default="fr",
        choices=[
            ("fr", "Français"),
            ("en", "English"),
            ("es", "Español"),
            ("de", "Deutsch"),
        ],
    )

    # Personnalisation de l'interface
    theme_color = models.CharField(_("Couleur du thème"), max_length=7, default="#7C4DFF")
    display_mode = models.CharField(
        _("Mode d'affichage"),
        max_length=10,
        default="light",
        choices=[
            ("light", "Clair"),
            ("dark", "Sombre"),
            ("system", "Système"),
        ],
    )

    # Notifications
    email_notifications = models.BooleanField(_("Notifications par email"), default=True)
    sms_notifications = models.BooleanField(_("Notifications par SMS"), default=False)

    # Sécurité
    two_factor_enabled = models.BooleanField(_("Authentification à deux facteurs"), default=False)

    # Taux de commission personnalisés (pour les ambassadeurs)
    escort_commission_rate = models.DecimalField(
        _("Taux commission escortes"),
        max_digits=5,
        decimal_places=2,
        default=30.00,
        validators=[MinValueValidator(5), MaxValueValidator(50)],
    )
    ambassador_commission_rate = models.DecimalField(
        _("Taux commission ambassadeurs"),
        max_digits=5,
        decimal_places=2,
        default=10.00,
        validators=[MinValueValidator(5), MaxValueValidator(50)],
    )

    # Métadonnées
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = _("profil utilisateur")
        verbose_name_plural = _("profils utilisateurs")

    def __str__(self):
        return f"Profil de {self.user.username}"


class VerificationCode(models.Model):
    """
    Modèle pour gérer les codes de vérification (email, téléphone, etc.)
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_codes")
    code = models.CharField(max_length=6)
    type = models.CharField(
        max_length=20,
        choices=[
            ("email", "Email"),
            ("phone", "Téléphone"),
            ("2fa", "Authentification à deux facteurs"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("code de vérification")
        verbose_name_plural = _("codes de vérification")

    def __str__(self):
        return f"Code de vérification pour {self.user.username} ({self.type})"

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.account_profile.save()
