from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Referral, Commission, ReferralClick
from django.db import models


@receiver(post_save, sender=Commission)
def update_affiliate_stats(sender, instance, created, **kwargs):
    """Met à jour les statistiques de l'affilié lorsqu'une commission est créée."""
    if created:
        affiliate = instance.referral.referrer
        profile = affiliate.affiliate_profile

        # Mettre à jour les gains totaux
        profile.total_earnings = (
            Commission.objects.filter(
                referral__referrer=affiliate, status__in=["approved", "paid"]
            ).aggregate(total=models.Sum("amount"))["total"]
            or 0
        )

        # Mettre à jour le taux de conversion
        total_clicks = ReferralClick.objects.filter(user=affiliate).count()
        total_referrals = Referral.objects.filter(referrer=affiliate).count()
        if total_clicks > 0:
            profile.conversion_rate = (total_referrals / total_clicks) * 100

        profile.save()


@receiver(post_save, sender=Referral)
def update_referral_stats(sender, instance, created, **kwargs):
    """Met à jour les statistiques de parrainage lorsqu'un nouveau parrainage est créé."""
    if created:
        affiliate = instance.referrer
        profile = affiliate.affiliate_profile

        # Mettre à jour le nombre total de parrainages
        profile.total_referrals = Referral.objects.filter(referrer=affiliate).count()

        # Mettre à jour le taux de conversion
        total_clicks = ReferralClick.objects.filter(user=affiliate).count()
        if total_clicks > 0:
            profile.conversion_rate = (profile.total_referrals / total_clicks) * 100

        profile.save()


@receiver(post_save, sender=ReferralClick)
def update_click_stats(sender, instance, created, **kwargs):
    """Met à jour les statistiques de clics lorsqu'un nouveau clic est enregistré."""
    if created:
        affiliate = instance.user
        profile = affiliate.affiliate_profile

        # Mettre à jour le taux de conversion
        total_clicks = ReferralClick.objects.filter(user=affiliate).count()
        total_referrals = Referral.objects.filter(referrer=affiliate).count()
        if total_clicks > 0:
            profile.conversion_rate = (total_referrals / total_clicks) * 100

        profile.save()
