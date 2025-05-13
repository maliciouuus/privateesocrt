from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging
from django.contrib.auth import get_user_model
import secrets
import dns.resolver
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.dashboard.models import Notification

logger = logging.getLogger("affiliate")

User = get_user_model()


# Signal pour créer automatiquement un profil d'affilié
@receiver(post_save, sender=User)
def create_affiliate_profile(sender, instance, created, **kwargs):
    if created:
        AffiliateProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_affiliate_profile(sender, instance, **kwargs):
    if not hasattr(instance, "affiliate_profile"):
        AffiliateProfile.objects.create(user=instance)
    instance.affiliate_profile.save()


class ReferralClick(models.Model):
    """
    Enregistrement des clics sur un lien de parrainage
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_clicks",
    )
    referral_code = models.CharField(max_length=10)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    clicked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Referral Click"
        verbose_name_plural = "Referral Clicks"
        ordering = ["-clicked_at"]

    def __str__(self):
        return f"Click from {self.user.username} at {self.clicked_at}"


class Referral(models.Model):
    """
    Utilisateur inscrit via un lien de parrainage
    """

    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referrals_made",
    )
    referred = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referrals_received",
    )
    referral_code = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Referral"
        verbose_name_plural = "Referrals"
        ordering = ["-created_at"]
        unique_together = ["referrer", "referred"]

    def __str__(self):
        return f"{self.referrer.username} referred {self.referred.username}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            # Importer le service ici pour éviter l'importation circulaire
            from .services import TelegramService

            telegram_service = TelegramService()
            telegram_service.notify_new_referral(self.referrer, self.referred)


class CommissionManager(models.Manager):
    """
    Manager personnalisé pour créer des commissions
    """

    def create_from_transaction(
        self,
        referred_user,
        transaction_amount,
        commission_type,
        description="",
        reference_id="",
    ):
        """
        Crée une commission à partir d'une transaction d'un utilisateur référé

        Args:
            referred_user: L'utilisateur qui a effectué la transaction
            transaction_amount: Le montant de la transaction
            commission_type: Le type de commission (signup, purchase, etc.)
            description: Description de la transaction
            reference_id: Identifiant de référence externe

        Returns:
            La commission créée ou None si l'utilisateur n'a pas été référé
        """
        # Vérifier si l'utilisateur a été référé
        try:
            referral = Referral.objects.get(referred=referred_user)
        except Referral.DoesNotExist:
            return None

        # Calculer le montant de la commission en fonction du taux
        commission_amount = Decimal(transaction_amount) * (referral.commission_rate / 100)

        # Créer la commission
        commission = self.create(
            user=referral.referrer,
            referral=referral,
            amount=commission_amount,
            gross_amount=transaction_amount,
            commission_type=commission_type,
            description=description,
            reference_id=reference_id,
            status="pending",
        )

        # Mettre à jour les totaux sur le modèle Referral
        referral.commission_rate = 30.00  # 30% pour les escortes
        referral.save()

        # Mettre à jour les totaux sur l'ambassadeur
        ambassador = referral.referrer
        ambassador.pending_commission += commission_amount
        ambassador.total_commission_earned += commission_amount
        ambassador.save()

        return commission


class Commission(models.Model):
    """
    Commission générée par un utilisateur parrainé
    """

    STATUS_CHOICES = [
        ("pending", _("En attente")),
        ("approved", _("Approuvée")),
        ("paid", _("Payée")),
        ("rejected", _("Rejetée")),
    ]

    TYPE_CHOICES = [
        ("direct", _("Directe")),  # Commission sur un utilisateur directement parrainé
        (
            "indirect",
            _("Indirecte"),
        ),  # Commission sur un ambassadeur qui a parrainé des utilisateurs
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="commissions",
        verbose_name=_("Ambassadeur"),
    )
    referral = models.ForeignKey(
        Referral,
        on_delete=models.CASCADE,
        related_name="commissions",
        verbose_name=_("Parrainage"),
    )

    # Montants
    amount = models.DecimalField(_("Montant"), max_digits=10, decimal_places=2)
    gross_amount = models.DecimalField(
        _("Montant brut"), max_digits=10, decimal_places=2, default=0
    )
    rate_applied = models.DecimalField(
        _("Taux appliqué (%)"), max_digits=5, decimal_places=2, default=0
    )

    # Informations
    commission_type = models.CharField(
        _("Type"), max_length=10, choices=TYPE_CHOICES, default="direct"
    )
    status = models.CharField(_("Statut"), max_length=20, choices=STATUS_CHOICES, default="pending")
    description = models.CharField(_("Description"), max_length=255, blank=True)
    reference_id = models.CharField(_("ID de référence"), max_length=100, blank=True)

    # Transaction liée
    transaction_id = models.CharField(_("ID de transaction"), max_length=100, blank=True, null=True)

    # Dates
    created_at = models.DateTimeField(_("Créée le"), auto_now_add=True)
    approved_at = models.DateTimeField(_("Approuvée le"), null=True, blank=True)
    paid_at = models.DateTimeField(_("Payée le"), null=True, blank=True)

    # Audit
    admin_note = models.TextField(_("Note administrative"), blank=True)
    rejection_reason = models.TextField(_("Raison du rejet"), blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_commissions",
        verbose_name=_("Mis à jour par"),
    )

    # Manager personnalisé
    objects = CommissionManager()

    class Meta:
        verbose_name = _("Commission")
        verbose_name_plural = _("Commissions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Commission {self.id} - {self.user.username} - {self.amount} €"

    def save(self, *args, **kwargs):
        """
        Sauvegarde la commission avec des actions supplémentaires
        """
        is_new = self.pk is None

        # Mettre à jour les dates selon le statut
        if self.status == "approved" and not self.approved_at:
            self.approved_at = timezone.now()

        if self.status == "paid" and not self.paid_at:
            self.paid_at = timezone.now()

        super().save(*args, **kwargs)

        # Action pour les nouvelles commissions
        if is_new:
            # Notifier l'ambassadeur par Telegram
            from .services import TelegramService

            telegram_service = TelegramService()
            telegram_service.notify_commission(self)

            # Mettre à jour les totaux sur l'ambassadeur
            self.update_ambassador_stats()

        # Synchroniser avec Supabase
        try:
            from .services import SupabaseService

            supabase = SupabaseService()
            supabase.sync_commission(self)
        except Exception as e:
            logger.error(
                f"Erreur lors de la synchronisation Supabase de la commission {self.id}: {str(e)}"
            )

    def update_ambassador_stats(self):
        """
        Met à jour les statistiques de l'ambassadeur
        """
        from .services import AffiliateService

        affiliate_service = AffiliateService()
        affiliate_service.update_ambassador_stats(self.user)

    def mark_as_approved(self, admin_user=None):
        """
        Marque la commission comme approuvée
        """
        if self.status != "pending":
            raise ValidationError(_("Seules les commissions en attente peuvent être approuvées."))

        self.status = "approved"
        self.approved_at = timezone.now()

        if admin_user:
            self.updated_by = admin_user

        self.save()

        # Mettre à jour les statistiques de l'ambassadeur
        self.update_ambassador_stats()

        return True

    def mark_as_paid(self, admin_user=None, payout=None):
        """
        Marque la commission comme payée
        """
        if self.status != "approved":
            raise ValidationError(
                _("Seules les commissions approuvées peuvent être marquées comme payées.")
            )

        self.status = "paid"
        self.paid_at = timezone.now()

        if admin_user:
            self.updated_by = admin_user

        self.save()

        # Si un payout est fourni, ajouter cette commission au payout
        if payout:
            payout.commissions.add(self)

        # Mettre à jour les statistiques de l'ambassadeur
        self.update_ambassador_stats()

        return True

    def mark_as_rejected(self, admin_user=None, reason=""):
        """
        Marque la commission comme rejetée
        """
        if self.status not in ["pending", "approved"]:
            raise ValidationError(
                _("Seules les commissions en attente ou approuvées peuvent être rejetées.")
            )

        self.status = "rejected"
        self.rejection_reason = reason

        if admin_user:
            self.updated_by = admin_user

        self.save()

        # Mettre à jour les statistiques de l'ambassadeur
        self.update_ambassador_stats()

        return True

    @classmethod
    def calculate_commission_amount(cls, gross_amount, user_type, referrer=None):
        """
        Calcule le montant de la commission basé sur les taux par défaut ou personnalisés
        """
        # Taux par défaut
        default_rates = {
            "escort": Decimal("30.00"),  # 30% pour les escortes
            "ambassador": Decimal("10.00"),  # 10% pour les ambassadeurs
            "agency": Decimal("30.00"),  # 30% pour les agences
            "member": Decimal("30.00"),  # 30% pour les membres
        }

        rate = default_rates.get(user_type, Decimal("0.00"))

        # Vérifier si l'ambassadeur a un taux personnalisé
        if referrer:
            try:
                custom_rate = CommissionRate.objects.get(ambassador=referrer, target_type=user_type)
                rate = custom_rate.rate
            except CommissionRate.DoesNotExist:
                pass

        # Calculer le montant de la commission
        amount = (Decimal(gross_amount) * rate) / Decimal("100.00")

        return {
            "amount": amount.quantize(Decimal("0.01")),
            "rate": rate,
        }


class CommissionRate(models.Model):
    """
    Taux de commission personnalisés par ambassadeur
    """

    TARGET_TYPES = (
        ("escort", "Escorte"),
        ("ambassador", "Ambassadeur"),
    )

    ambassador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="commission_rates",
    )
    target_type = models.CharField(max_length=10, choices=TARGET_TYPES)
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(5), MaxValueValidator(50)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("taux de commission")
        verbose_name_plural = _("taux de commission")
        unique_together = ["ambassador", "target_type"]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.ambassador.username} - {self.get_target_type_display()} ({self.rate}%)"

    def save(self, *args, **kwargs):
        # Vérifier que l'utilisateur est un ambassadeur
        if not self.ambassador.is_ambassador:
            raise ValidationError(_("Seuls les ambassadeurs peuvent avoir des taux de commission."))
        super().save(*args, **kwargs)


class Transaction(models.Model):
    """
    Transactions générées sur le site React
    """

    STATUS_CHOICES = [
        ("pending", "En attente"),
        ("completed", "Complétée"),
        ("failed", "Échouée"),
        ("refunded", "Remboursée"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escort = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_method = models.CharField(max_length=50)
    payment_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("transaction")
        verbose_name_plural = _("transactions")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Transaction {self.id} - {self.escort.username} - {self.amount}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if self.status == "completed":
            # Calculer et créer les commissions
            self._create_commissions()

        super().save(*args, **kwargs)

        if is_new:
            # Importer le service ici pour éviter l'importation circulaire
            from .services import TelegramService

            telegram_service = TelegramService()
            telegram_service.notify_transaction(self)

        # Synchroniser avec Supabase
        try:
            from .services import SupabaseService

            supabase = SupabaseService()
            supabase.sync_transaction(self)
        except Exception as e:
            logger.error(
                f"Erreur lors de la synchronisation Supabase de la transaction {self.id}: {str(e)}"
            )

    def _create_commissions(self):
        """
        Créer les commissions pour cette transaction
        """
        # Trouver l'ambassadeur qui a recruté l'escorte
        ambassador = self.escort.referred_by
        if not ambassador:
            return

        # Obtenir le taux de commission pour les escortes
        try:
            commission_rate = CommissionRate.objects.get(
                ambassador=ambassador, target_type="escort"
            ).rate
        except CommissionRate.DoesNotExist:
            # Utiliser le taux par défaut si non défini
            commission_rate = Decimal("30.00")

        # Calculer le montant de la commission
        commission_amount = (self.amount * commission_rate) / Decimal("100")

        # Créer la commission
        Commission.objects.create(
            user=ambassador,
            referral=Referral.objects.get(referred=self.escort),
            amount=commission_amount,
            status="pending",
        )


class Payout(models.Model):
    """
    Gestion des paiements des commissions
    """

    PAYMENT_METHODS = [
        ("btc", "Bitcoin"),
        ("eth", "Ethereum"),
        ("usdt", "Tether"),
    ]

    STATUS_CHOICES = [
        ("pending", "En attente"),
        ("processing", "En cours"),
        ("completed", "Complété"),
        ("failed", "Échoué"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ambassador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payouts"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    wallet_address = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Liste des commissions incluses dans ce paiement
    commissions = models.ManyToManyField(Commission, related_name="payouts")

    class Meta:
        verbose_name = _("paiement")
        verbose_name_plural = _("paiements")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Paiement de {self.amount}€ à {self.ambassador.username}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if self.status == "completed" and not self.completed_at:
            self.completed_at = timezone.now()
            # Marquer les commissions comme payées
            for commission in self.commissions.all():
                commission.status = "paid"
                commission.paid_at = self.completed_at
                commission.save()

        super().save(*args, **kwargs)

        if is_new:
            # Importer le service ici pour éviter l'importation circulaire
            from .services import TelegramService

            telegram_service = TelegramService()
            telegram_service.notify_payout(self)

        # Synchroniser avec Supabase
        try:
            from .services import SupabaseService

            supabase = SupabaseService()
            supabase.sync_payout(self)
        except Exception as e:
            logger.error(
                f"Erreur lors de la synchronisation Supabase du paiement {self.id}: {str(e)}"
            )

    @classmethod
    def create_from_commissions(cls, ambassador, commissions, payment_method):
        """
        Crée un paiement à partir d'une liste de commissions
        """
        total_amount = sum(commission.amount for commission in commissions)
        payout = cls.objects.create(
            ambassador=ambassador,
            amount=total_amount,
            payment_method=payment_method,
            status="pending",
        )
        payout.commissions.set(commissions)
        return payout

    def get_payment_method_icon(self):
        """
        Retourne l'icône FontAwesome correspondant à la méthode de paiement
        """
        icons = {
            "btc": "fab fa-bitcoin",
            "eth": "fab fa-ethereum",
            "usdt": "fas fa-dollar-sign",
        }
        return icons.get(self.payment_method, "fas fa-money-bill")

    def get_status_class(self):
        """
        Retourne la classe CSS correspondant au statut
        """
        classes = {
            "pending": "warning",
            "processing": "info",
            "completed": "success",
            "failed": "danger",
        }
        return classes.get(self.status, "secondary")

    def mark_as_completed(self, transaction_id):
        self.status = "completed"
        self.transaction_id = transaction_id
        self.completed_at = timezone.now()
        self.save()

    def mark_as_failed(self):
        self.status = "failed"
        self.save()


class WhiteLabel(models.Model):
    """
    Modèle pour les sites white label des ambassadeurs (maximum 3 par ambassadeur)
    """

    name = models.CharField(_("Nom du site"), max_length=100)
    domain = models.CharField(_("Domaine"), max_length=255, unique=True)
    custom_domain = models.CharField(
        _("Domaine personnalisé"), max_length=255, unique=True, null=True, blank=True
    )
    dns_verified = models.BooleanField(_("DNS vérifié"), default=False)
    dns_verification_code = models.CharField(
        _("Code de vérification DNS"), max_length=64, null=True, blank=True
    )
    ambassador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="white_labels",
        verbose_name=_("Ambassadeur"),
    )

    # Personnalisation visuelle
    primary_color = models.CharField(_("Couleur principale"), max_length=7, default="#7C4DFF")
    secondary_color = models.CharField(_("Couleur secondaire"), max_length=7, default="#FF4D94")
    logo = models.ImageField(_("Logo"), upload_to="whitelabels/logos/", null=True, blank=True)
    favicon = models.ImageField(
        _("Favicon"), upload_to="whitelabels/favicons/", null=True, blank=True
    )

    # Personnalisation avancée
    meta_title = models.CharField(_("Titre meta"), max_length=255, blank=True)
    meta_description = models.TextField(_("Description meta"), blank=True)
    custom_css = models.TextField(_("CSS personnalisé"), null=True, blank=True)
    custom_js = models.TextField(_("JavaScript personnalisé"), null=True, blank=True)

    # Statut et timestamps
    is_active = models.BooleanField(_("Actif"), default=True)
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Mis à jour le"), auto_now=True)

    # Statistiques
    visits_count = models.PositiveIntegerField(_("Nombre de visites"), default=0)
    signups_count = models.PositiveIntegerField(_("Nombre d'inscriptions"), default=0)

    class Meta:
        verbose_name = _("site white label")
        verbose_name_plural = _("sites white label")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.ambassador.username})"

    def save(self, *args, **kwargs):
        # Vérifier que l'utilisateur est un ambassadeur
        if not hasattr(self, "ambassador") or not self.ambassador.is_ambassador:
            raise ValidationError(_("Seuls les ambassadeurs peuvent créer des sites white label"))

        # Vérifier la limite de 3 sites par ambassadeur
        if not self.pk:  # Seulement lors de la création
            existing_count = WhiteLabel.objects.filter(ambassador=self.ambassador).count()
            if existing_count >= 3:
                raise ValidationError(
                    _("Un ambassadeur ne peut pas avoir plus de 3 sites white label")
                )

        # Nettoyer le domaine
        if self.domain:
            self.domain = (
                self.domain.lower().replace("http://", "").replace("https://", "").rstrip("/")
            )

        if self.custom_domain:
            self.custom_domain = (
                self.custom_domain.lower()
                .replace("http://", "")
                .replace("https://", "")
                .rstrip("/")
            )

        # Générer un code de vérification DNS unique si nécessaire
        if not self.dns_verification_code:
            self.dns_verification_code = secrets.token_hex(16)

        super().save(*args, **kwargs)

        # Synchroniser avec Supabase après sauvegarde
        try:
            from .services import SupabaseService

            supabase = SupabaseService()
            supabase.sync_white_label(self)
        except Exception as e:
            logger.error(
                f"Erreur lors de la synchronisation Supabase du white label {self.id}: {str(e)}"
            )

    def verify_dns(self):
        """
        Vérifie que le domaine personnalisé pointe bien vers notre service
        via un enregistrement TXT
        """
        if not self.custom_domain:
            return False

        try:
            answers = dns.resolver.resolve(f"_escortdollars-verify.{self.custom_domain}", "TXT")
            for rdata in answers:
                for txt_string in rdata.strings:
                    if txt_string.decode() == self.dns_verification_code:
                        self.dns_verified = True
                        self.save(update_fields=["dns_verified"])
                        return True
        except Exception:
            pass

        return False

    def get_dns_instructions(self):
        """
        Retourne les instructions pour configurer le DNS
        """
        if not self.custom_domain or not self.dns_verification_code:
            return ""

        return _(
            """
            Pour vérifier votre domaine personnalisé, ajoutez l'enregistrement TXT suivant dans la configuration DNS de votre domaine :

            Nom : _escortdollars-verify.{domain}
            Type : TXT
            Valeur : {code}

            Une fois que vous avez ajouté cet enregistrement, cliquez sur le bouton "Vérifier le DNS" pour valider votre domaine.
        """
        ).format(domain=self.custom_domain, code=self.dns_verification_code)

    def get_absolute_url(self):
        """
        Retourne l'URL absolue du site white label
        """
        if self.dns_verified and self.custom_domain:
            return f"https://{self.custom_domain}"
        return f"https://{self.domain}"


class AffiliateLevel(models.Model):
    LEVEL_CHOICES = [
        ("bronze", "Bronze"),
        ("silver", "Argent"),
        ("gold", "Or"),
        ("platinum", "Platine"),
        ("diamond", "Diamant"),
    ]

    name = models.CharField(max_length=50, choices=LEVEL_CHOICES)
    min_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_referrals = models.IntegerField(default=0)
    min_conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    commission_bonus = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    benefits = models.JSONField(default=dict)
    icon = models.ImageField(upload_to="levels/icons/", null=True, blank=True)
    color = models.CharField(max_length=7, default="#000000")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["min_earnings"]
        verbose_name = _("niveau d'affiliation")
        verbose_name_plural = _("niveaux d'affiliation")

    def __str__(self):
        return self.get_name_display()

    def get_next_level(self):
        """Retourne le prochain niveau disponible."""
        return (
            AffiliateLevel.objects.filter(min_earnings__gt=self.min_earnings)
            .order_by("min_earnings")
            .first()
        )

    def get_previous_level(self):
        """Retourne le niveau précédent."""
        return (
            AffiliateLevel.objects.filter(min_earnings__lt=self.min_earnings)
            .order_by("-min_earnings")
            .first()
        )

    def calculate_progress(self, profile):
        """Calcule la progression vers ce niveau."""
        progress = {
            "earnings": (
                min(100, (profile.total_earnings / self.min_earnings) * 100)
                if self.min_earnings > 0
                else 100
            ),
            "referrals": (
                min(100, (profile.total_referrals / self.min_referrals) * 100)
                if self.min_referrals > 0
                else 100
            ),
            "conversion": (
                min(100, (profile.conversion_rate / self.min_conversion_rate) * 100)
                if self.min_conversion_rate > 0
                else 100
            ),
        }
        progress["total"] = sum(progress.values()) / len(progress)
        return progress


class AffiliateProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="affiliate_profile")
    level = models.ForeignKey(AffiliateLevel, on_delete=models.SET_NULL, null=True)
    points = models.IntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_referrals = models.IntegerField(default=0)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    badges = models.ManyToManyField("Badge", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("profil d'affilié")
        verbose_name_plural = _("profils d'affiliés")

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def update_level(self):
        """Met à jour le niveau de l'affilié en fonction de ses performances."""
        current_level = self.level
        new_level = (
            AffiliateLevel.objects.filter(
                min_earnings__lte=self.total_earnings,
                min_referrals__lte=self.total_referrals,
                min_conversion_rate__lte=self.conversion_rate,
            )
            .order_by("-min_earnings")
            .first()
        )

        if new_level and (not current_level or new_level.min_earnings > current_level.min_earnings):
            self.level = new_level
            self.save()

            # Créer une notification pour le changement de niveau
            Notification.objects.create(
                user=self.user,
                title=_("Nouveau niveau atteint !"),
                message=_("Félicitations ! Vous avez atteint le niveau {}.").format(
                    new_level.get_name_display()
                ),
                type="level_up",
            )

            return True
        return False

    def calculate_conversion_rate(self):
        """Calcule le taux de conversion actuel."""
        total_clicks = ReferralClick.objects.filter(user=self.user).count()
        if total_clicks > 0:
            self.conversion_rate = (self.total_referrals / total_clicks) * 100
            self.save()
        return self.conversion_rate

    def get_level_progress(self):
        """Retourne la progression vers le prochain niveau."""
        if not self.level:
            return None

        next_level = self.level.get_next_level()
        if not next_level:
            return {"total": 100, "earnings": 100, "referrals": 100, "conversion": 100}

        return next_level.calculate_progress(self)


class Badge(models.Model):
    CATEGORY_CHOICES = [
        ("referral", "Parrainage"),
        ("earning", "Gains"),
        ("engagement", "Engagement"),
        ("special", "Spécial"),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="referral")
    icon = models.CharField(max_length=50)  # Nom de l'icône FontAwesome
    points_value = models.IntegerField(default=0)
    requirements = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class Banner(models.Model):
    """
    Gestion des bannières pour les sites white label (max 3 bannières personnelles par site)
    """

    BANNER_TYPES = [
        ("personal", _("Bannière personnelle")),
        ("partner", _("Bannière partenaire")),
    ]

    white_label = models.ForeignKey(
        WhiteLabel,
        on_delete=models.CASCADE,
        related_name="banners",
        verbose_name=_("Site White Label"),
    )
    title = models.CharField(_("Titre"), max_length=100)
    type = models.CharField(_("Type"), max_length=10, choices=BANNER_TYPES, default="personal")

    # Pour les bannières personnelles (image)
    image = models.ImageField(_("Image"), upload_to="banners/", null=True, blank=True)

    # Pour les bannières partenaires (HTML)
    html_code = models.TextField(_("Code HTML"), null=True, blank=True)
    partner_email = models.EmailField(_("Email du partenaire"), null=True, blank=True)

    # URL de redirection
    link = models.URLField(_("Lien"), blank=True)

    # Statistiques
    views_count = models.PositiveIntegerField(_("Nombre de vues"), default=0)
    clicks_count = models.PositiveIntegerField(_("Nombre de clics"), default=0)

    # État et dates
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Bannière")
        verbose_name_plural = _("Bannières")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"

    def clean(self):
        """
        Validation des champs selon le type de bannière
        """
        if self.type == "personal":
            # Temporairement désactivé pour les tests
            # if not self.image:
            #     raise ValidationError(_('Une bannière personnelle doit avoir une image.'))

            # Vérifier la limite de 3 bannières personnelles par white label
            if not self.pk:  # Seulement lors de la création
                personal_banners_count = Banner.objects.filter(
                    white_label=self.white_label, type="personal"
                ).count()

                if personal_banners_count >= 3:
                    raise ValidationError(
                        _(
                            "Vous ne pouvez pas avoir plus de 3 bannières personnelles par site white label."
                        )
                    )

        elif self.type == "partner":
            # Une bannière partenaire doit avoir un code HTML et un email
            if not self.html_code:
                raise ValidationError(_("Une bannière partenaire doit avoir un code HTML."))

            if not self.partner_email:
                raise ValidationError(_("Une bannière partenaire doit avoir un email de contact."))

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

        # Synchroniser avec Supabase après sauvegarde
        try:
            from .services import SupabaseService

            supabase = SupabaseService()
            supabase.sync_banner(self)
        except Exception as e:
            import logging

            logging.error(
                f"Erreur lors de la synchronisation Supabase de la bannière {self.id}: {str(e)}"
            )

    def track_view(self):
        """
        Incrémente le compteur de vues de la bannière
        """
        self.views_count += 1
        self.save(update_fields=["views_count"])

    def track_click(self):
        """
        Incrémente le compteur de clics de la bannière
        """
        self.clicks_count += 1
        self.save(update_fields=["clicks_count"])

    @property
    def click_through_rate(self):
        """
        Calcule le taux de clics (CTR) de la bannière
        """
        if self.views_count == 0:
            return 0
        return (self.clicks_count / self.views_count) * 100


class MarketingMaterial(models.Model):
    """Modèle pour les matériels marketing."""

    title = models.CharField(max_length=200)
    description = models.TextField()
    file = models.FileField(upload_to="marketing_materials/")
    file_type = models.CharField(max_length=50)  # image, video, pdf, etc.
    is_active = models.BooleanField(default=True)
    download_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class PaymentMethod(models.Model):
    """Modèle pour les méthodes de paiement."""

    PAYMENT_TYPES = [
        ("bank", "Virement bancaire"),
        ("paypal", "PayPal"),
        ("crypto", "Cryptomonnaie"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    account_name = models.CharField(max_length=200)
    account_details = (
        models.JSONField()
    )  # Pour stocker les détails spécifiques à chaque type de paiement
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.get_payment_type_display()} - {self.account_name}"
