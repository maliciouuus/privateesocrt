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


class AffiliateProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="affiliate_profile")
    points = models.IntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_referrals = models.IntegerField(default=0)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("profil d'affilié")
        verbose_name_plural = _("profils d'affiliés")

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def calculate_conversion_rate(self):
        """Calcule le taux de conversion des parrainages."""
        # TODO: implémenter le calcul du taux de conversion
        return 0.0


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
