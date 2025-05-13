from django.core.management.base import BaseCommand
from apps.accounts.models import User
from apps.affiliate.models import Referral
from decimal import Decimal


class Command(BaseCommand):
    help = "Crée les entrées Referral manquantes pour les utilisateurs qui ont referred_by mais pas d'entrée dans la table Referral"

    def handle(self, *args, **options):
        # Trouver tous les utilisateurs qui ont un referred_by
        referred_users = User.objects.filter(referred_by__isnull=False)
        count = 0

        for user in referred_users:
            ambassador = user.referred_by

            # Vérifier si une entrée Referral existe déjà
            existing_referral = Referral.objects.filter(
                ambassador=ambassador, referred_user=user
            ).first()

            if not existing_referral:
                # Créer une nouvelle entrée Referral
                Referral.objects.create(
                    ambassador=ambassador,
                    referred_user=user,
                    is_active=True,
                    total_earnings=Decimal("0.00"),
                )
                count += 1
                self.stdout.write(
                    f"Entrée Referral créée pour {user.username} parrainé par {ambassador.username}"
                )

        if count == 0:
            self.stdout.write(self.style.SUCCESS("Aucune entrée Referral manquante trouvée."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{count} entrées Referral créées avec succès!"))
