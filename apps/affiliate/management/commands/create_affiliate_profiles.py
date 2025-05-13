from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from affiliate.models import AffiliateProfile

User = get_user_model()


class Command(BaseCommand):
    help = "Creates affiliate profiles for all users who don't have one"

    def handle(self, *args, **options):
        users_without_profile = User.objects.filter(affiliate_profile__isnull=True)
        profiles_created = 0

        for user in users_without_profile:
            AffiliateProfile.objects.create(user=user)
            profiles_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created affiliate profiles for {profiles_created} users"
            )
        )
