from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class WhiteLabel(models.Model):
    """
    Modèle pour gérer les sites white label
    """

    name = models.CharField(_("Site Name"), max_length=100)
    domain = models.CharField(_("Domain"), max_length=255, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="whitelabel_sites",
        verbose_name=_("Propriétaire"),
    )
    logo = models.ImageField(_("Logo"), upload_to="whitelabel/logos/", null=True, blank=True)
    favicon = models.ImageField(
        _("Favicon"), upload_to="whitelabel/favicons/", null=True, blank=True
    )
    primary_color = models.CharField(_("Primary Color"), max_length=7, default="#7C4DFF")
    secondary_color = models.CharField(_("Secondary Color"), max_length=7, default="#FF4D94")
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("White Label Site")
        verbose_name_plural = _("White Label Sites")
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f"https://{self.domain}"

    def save(self, *args, **kwargs):
        # Ensure domain is clean (no http:// or trailing slashes)
        if self.domain:
            self.domain = self.domain.replace("http://", "").replace("https://", "").rstrip("/")
        super().save(*args, **kwargs)
