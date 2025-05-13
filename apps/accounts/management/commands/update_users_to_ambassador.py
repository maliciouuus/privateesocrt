from django.core.management.base import BaseCommand
from apps.accounts.models import User


class Command(BaseCommand):
    help = "Met à jour tous les utilisateurs standard existants en ambassadeurs"

    def handle(self, *args, **options):
        # Trouver tous les utilisateurs standard
        standard_users = User.objects.filter(user_type="standard")
        count = standard_users.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS("Aucun utilisateur standard trouvé. Rien à faire.")
            )
            return

        # Mettre à jour les utilisateurs
        for user in standard_users:
            # Générer un code de référence s'il n'en a pas
            if not user.referral_code:
                import uuid

                user.referral_code = f"AFF{str(uuid.uuid4())[:8].upper()}"

            user.user_type = "ambassador"
            user.save()

            self.stdout.write(f"Utilisateur {user.username} mis à jour en ambassadeur")

        self.stdout.write(
            self.style.SUCCESS(
                f"{count} utilisateurs mis à jour avec succès de standard à ambassador!"
            )
        )
