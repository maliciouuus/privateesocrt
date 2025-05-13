from django.core.management.base import BaseCommand
from apps.accounts.models import User
from apps.affiliate.models import Referral
from decimal import Decimal


class Command(BaseCommand):
    help = "Définit une relation d'affiliation entre deux utilisateurs"

    def add_arguments(self, parser):
        parser.add_argument("ambassador", type=str, help="Nom d'utilisateur de l'ambassadeur")
        parser.add_argument("referred", type=str, help="Nom d'utilisateur de l'utilisateur référé")

    def handle(self, *args, **options):
        ambassador_username = options["ambassador"]
        referred_username = options["referred"]

        try:
            ambassador = User.objects.get(username=ambassador_username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"L'ambassadeur {ambassador_username} n'existe pas!")
            )
            return

        try:
            referred_user = User.objects.get(username=referred_username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"L'utilisateur {referred_username} n'existe pas!"))
            return

        # Définir la relation d'affiliation
        referred_user.referred_by = ambassador
        referred_user.save(update_fields=["referred_by"])

        # Créer ou mettre à jour l'entrée Referral
        referral, created = Referral.objects.get_or_create(
            ambassador=ambassador,
            referred_user=referred_user,
            defaults={"is_active": True, "total_earnings": Decimal("0.00")},
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Relation d'affiliation créée: {referred_username} est parrainé par {ambassador_username}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Relation d'affiliation mise à jour: {referred_username} est parrainé par {ambassador_username}"
                )
            )
