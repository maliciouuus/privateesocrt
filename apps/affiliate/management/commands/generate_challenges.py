from django.core.management.base import BaseCommand
from django.utils import timezone
from affiliate.models import Challenge
from datetime import timedelta


class Command(BaseCommand):
    help = "Génère automatiquement les défis quotidiens, hebdomadaires et mensuels"

    def handle(self, *args, **options):
        now = timezone.now()

        # Vérifier si c'est le début d'une nouvelle journée (00:00)
        if now.hour == 0 and now.minute < 5:
            self.generate_daily_challenges()

        # Vérifier si c'est le début d'une nouvelle semaine (lundi)
        if now.weekday() == 0 and now.hour == 0 and now.minute < 5:
            self.generate_weekly_challenges()

        # Vérifier si c'est le début d'un nouveau mois
        if now.day == 1 and now.hour == 0 and now.minute < 5:
            self.generate_monthly_challenges()

    def generate_daily_challenges(self):
        """Génère les défis quotidiens."""
        start_date = timezone.now()
        end_date = start_date + timedelta(days=1)

        # Défi de parrainage quotidien
        Challenge.objects.create(
            title="Parrainage du jour",
            description="Parrainez 3 nouveaux membres aujourd'hui",
            type="daily",
            category="referral",
            start_date=start_date,
            end_date=end_date,
            requirements={"target": 3, "type": "referrals"},
            rewards={"points": 50, "bonus": "5% de bonus sur les commissions"},
            color="#4CAF50",
        )

        # Défi de gains quotidiens
        Challenge.objects.create(
            title="Gains du jour",
            description="Gagnez 100€ en commissions aujourd'hui",
            type="daily",
            category="earning",
            start_date=start_date,
            end_date=end_date,
            requirements={"target": 100, "type": "earnings"},
            rewards={"points": 100, "bonus": "10% de bonus sur les commissions"},
            color="#2196F3",
        )

    def generate_weekly_challenges(self):
        """Génère les défis hebdomadaires."""
        start_date = timezone.now()
        end_date = start_date + timedelta(days=7)

        # Défi de parrainage hebdomadaire
        Challenge.objects.create(
            title="Parrainage de la semaine",
            description="Parrainez 10 nouveaux membres cette semaine",
            type="weekly",
            category="referral",
            start_date=start_date,
            end_date=end_date,
            requirements={"target": 10, "type": "referrals"},
            rewards={"points": 200, "bonus": "15% de bonus sur les commissions"},
            color="#9C27B0",
        )

        # Défi de gains hebdomadaires
        Challenge.objects.create(
            title="Gains de la semaine",
            description="Gagnez 500€ en commissions cette semaine",
            type="weekly",
            category="earning",
            start_date=start_date,
            end_date=end_date,
            requirements={"target": 500, "type": "earnings"},
            rewards={"points": 500, "bonus": "20% de bonus sur les commissions"},
            color="#FF9800",
        )

    def generate_monthly_challenges(self):
        """Génère les défis mensuels."""
        start_date = timezone.now()
        end_date = start_date + timedelta(days=30)

        # Défi de parrainage mensuel
        Challenge.objects.create(
            title="Parrainage du mois",
            description="Parrainez 50 nouveaux membres ce mois-ci",
            type="monthly",
            category="referral",
            start_date=start_date,
            end_date=end_date,
            requirements={"target": 50, "type": "referrals"},
            rewards={"points": 1000, "bonus": "25% de bonus sur les commissions"},
            color="#E91E63",
        )

        # Défi de gains mensuels
        Challenge.objects.create(
            title="Gains du mois",
            description="Gagnez 2000€ en commissions ce mois-ci",
            type="monthly",
            category="earning",
            start_date=start_date,
            end_date=end_date,
            requirements={"target": 2000, "type": "earnings"},
            rewards={"points": 2000, "bonus": "30% de bonus sur les commissions"},
            color="#F44336",
        )

        # Défi de conversion mensuel
        Challenge.objects.create(
            title="Conversion du mois",
            description="Atteignez un taux de conversion de 20% ce mois-ci",
            type="monthly",
            category="conversion",
            start_date=start_date,
            end_date=end_date,
            requirements={"target": 20, "type": "conversion_rate"},
            rewards={"points": 1500, "bonus": "Accès VIP"},
            color="#607D8B",
        )
