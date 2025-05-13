import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.affiliate.models import (
    WhiteLabel,
    Banner,
    Commission,
    CommissionRate,
    Referral,
    Transaction,
    Payout,
)
from faker import Faker

User = get_user_model()
fake = Faker()


class Command(BaseCommand):
    help = "Configure des données de démonstration pour le système d'affiliation"

    def handle(self, *args, **options):
        self.stdout.write("Configuration des données de démonstration...")

        # Créer un administrateur (si inexistant)
        self.create_admin()

        # Créer un manager d'affiliation (si inexistant)
        self.create_affiliate_manager()

        # Créer des ambassadeurs (si moins de 5)
        self.create_ambassadors(count=5)

        # Créer des sites white label pour chaque ambassadeur
        self.create_white_labels()

        # Créer des bannières pour chaque site white label
        self.create_banners()

        # Créer des taux de commission personnalisés
        self.create_commission_rates()

        # Créer des parrainages
        self.create_referrals()

        # Créer des transactions et des commissions
        self.create_transactions_and_commissions()

        # Créer des paiements
        self.create_payouts()

        self.stdout.write(self.style.SUCCESS("Données de démonstration configurées avec succès !"))

    def create_admin(self):
        """Créer un administrateur"""
        if not User.objects.filter(is_superuser=True).exists():
            admin = User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="adminpassword",
                user_type="administrator",
            )
            self.stdout.write(f"Administrateur créé: {admin.username}")

    def create_affiliate_manager(self):
        """Créer un manager d'affiliation"""
        if not User.objects.filter(user_type="administrator", is_superuser=False).exists():
            manager = User.objects.create_user(
                username="manager",
                email="manager@example.com",
                password="managerpassword",
                user_type="administrator",
                is_staff=True,
            )
            self.stdout.write(f"Manager d'affiliation créé: {manager.username}")

    def create_ambassadors(self, count=5):
        """Créer des ambassadeurs"""
        existing_count = User.objects.filter(user_type="ambassador").count()

        if existing_count < count:
            for i in range(existing_count, count):
                ambassador = User.objects.create_user(
                    username=f"ambassador{i+1}",
                    email=f"ambassador{i+1}@example.com",
                    password="password",
                    user_type="ambassador",
                    user_category="ambassador",
                    referral_code=f"REF{i+1}",
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    is_verified=True,
                )
                self.stdout.write(f"Ambassadeur créé: {ambassador.username}")

    def create_white_labels(self):
        """Créer des sites white label pour chaque ambassadeur"""
        ambassadors = User.objects.filter(user_type="ambassador")

        for ambassador in ambassadors:
            # Si l'ambassadeur a moins de 2 sites white label, en créer
            if WhiteLabel.objects.filter(ambassador=ambassador).count() < 2:
                for i in range(1, 3):
                    site_name = fake.company()
                    domain = (
                        f"{site_name.lower().replace(' ', '')}-{ambassador.id}.escortdollars.com"
                    )

                    white_label = WhiteLabel.objects.create(
                        name=site_name,
                        domain=domain,
                        ambassador=ambassador,
                        primary_color=f"#{fake.hex_color()[1:]}",
                        secondary_color=f"#{fake.hex_color()[1:]}",
                        is_active=True,
                    )
                    self.stdout.write(
                        f"Site white label créé: {white_label.name} pour {ambassador.username}"
                    )

    def create_banners(self):
        """Créer des bannières pour chaque site white label"""
        white_labels = WhiteLabel.objects.all()

        for white_label in white_labels:
            # Si le site white label a moins de 2 bannières, en créer
            if Banner.objects.filter(white_label=white_label).count() < 2:
                # Créer une bannière partenaire (pas besoin d'image)
                Banner.objects.create(
                    white_label=white_label,
                    title=f"Bannière partenaire pour {white_label.name}",
                    type="partner",
                    html_code=f'<a href="https://{white_label.domain}">Visitez {white_label.name}</a>',
                    partner_email=fake.email(),
                    is_active=True,
                )

                self.stdout.write(f"Bannière partenaire créée pour {white_label.name}")

    def create_commission_rates(self):
        """Créer des taux de commission personnalisés"""
        ambassadors = User.objects.filter(user_type="ambassador")

        for ambassador in ambassadors:
            # Si l'ambassadeur n'a pas de taux personnalisés, en créer
            if not CommissionRate.objects.filter(ambassador=ambassador).exists():
                CommissionRate.objects.create(
                    ambassador=ambassador,
                    target_type="escort",
                    rate=Decimal(random.randint(25, 35)),
                )

                CommissionRate.objects.create(
                    ambassador=ambassador,
                    target_type="ambassador",
                    rate=Decimal(random.randint(5, 15)),
                )

                self.stdout.write(f"Taux de commission créés pour {ambassador.username}")

    def create_referrals(self):
        """Créer des parrainages"""
        ambassadors = list(User.objects.filter(user_type="ambassador"))

        if len(ambassadors) >= 2:
            for i in range(len(ambassadors) - 1):
                referrer = ambassadors[i]
                referred = ambassadors[i + 1]

                # Si le parrainage n'existe pas déjà
                if not Referral.objects.filter(referrer=referrer, referred=referred).exists():
                    Referral.objects.create(
                        referrer=referrer,
                        referred=referred,
                        referral_code=referrer.referral_code,
                    )
                    self.stdout.write(
                        f"Parrainage créé: {referrer.username} -> {referred.username}"
                    )

    def create_transactions_and_commissions(self):
        """Créer des transactions et des commissions"""
        referrals = Referral.objects.all()

        for referral in referrals:
            # Créer entre 1 et 3 transactions et commissions
            for _ in range(random.randint(1, 3)):
                amount = Decimal(random.randint(50, 500))

                transaction = Transaction.objects.create(
                    escort=referral.referred,
                    amount=amount,
                    status="completed",
                    payment_method="credit_card",
                    payment_id=f"PAYMENT-{fake.uuid4()}",
                )

                commission_amount = amount * Decimal("0.3")  # 30%

                commission = Commission.objects.create(
                    user=referral.referrer,
                    referral=referral,
                    amount=commission_amount,
                    gross_amount=amount,
                    rate_applied=Decimal("30.00"),
                    commission_type="direct",
                    status="approved",
                    transaction_id=str(transaction.id),
                    description=f"Commission sur paiement de {referral.referred.username}",
                    approved_at=timezone.now(),
                )

                self.stdout.write(
                    f"Transaction et commission créées: {transaction.id} -> {commission.id}"
                )

    def create_payouts(self):
        """Créer des paiements"""
        ambassadors = User.objects.filter(user_type="ambassador")

        for ambassador in ambassadors:
            # Récupérer les commissions approuvées mais non payées
            commissions = Commission.objects.filter(user=ambassador, status="approved")

            if commissions.exists():
                total_amount = sum(commission.amount for commission in commissions)

                if total_amount > 0:
                    payout = Payout.objects.create(
                        ambassador=ambassador,
                        amount=total_amount,
                        payment_method="btc",
                        status="completed",
                        completed_at=timezone.now(),
                    )

                    # Ajouter les commissions au paiement
                    payout.commissions.set(commissions)

                    # Marquer les commissions comme payées
                    for commission in commissions:
                        commission.status = "paid"
                        commission.paid_at = timezone.now()
                        commission.save()

                    self.stdout.write(
                        f"Paiement créé pour {ambassador.username}: {payout.amount} €"
                    )
