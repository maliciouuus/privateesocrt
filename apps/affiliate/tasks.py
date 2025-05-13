from django.utils import timezone
from affiliate.models import Challenge
from django.core.management import call_command


def cleanup_expired_challenges():
    """Nettoie les défis expirés."""
    # Désactiver les défis expirés
    expired_challenges = Challenge.objects.filter(is_active=True, end_date__lt=timezone.now())

    for challenge in expired_challenges:
        challenge.is_active = False
        challenge.save()


def generate_challenges():
    """Génère les défis quotidiens, hebdomadaires et mensuels."""
    call_command("generate_challenges")
