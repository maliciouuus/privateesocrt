import pytest
from decimal import Decimal
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.affiliate.models import Referral, Commission, WhiteLabel


@pytest.fixture
def api_client():
    """Fixture pour créer un client API pour les tests."""
    return APIClient()


@pytest.fixture
def ambassador_user():
    """Fixture pour créer un utilisateur de type ambassadeur."""
    return User.objects.create_user(
        username="ambassador_fixture",
        email="ambassador_fixture@test.com",
        password="testpass123",
        user_type="ambassador",
    )


@pytest.fixture
def escort_user():
    """Fixture pour créer un utilisateur de type escort."""
    return User.objects.create_user(
        username="escort_fixture",
        email="escort_fixture@test.com",
        password="testpass123",
        user_type="escort",
    )


@pytest.fixture
def referral(ambassador_user, escort_user):
    """Fixture pour créer un parrainage."""
    return Referral.objects.create(
        ambassador=ambassador_user,
        referred=escort_user,
        referral_code="FIXTURE123",
        is_active=True,
    )


@pytest.fixture
def commission(referral):
    """Fixture pour créer une commission."""
    return Commission.objects.create(
        user=referral.ambassador,
        referral=referral,
        amount=Decimal("100.00"),
        status="pending",
    )


@pytest.fixture
def white_label(ambassador_user):
    """Fixture pour créer un site en marque blanche."""
    return WhiteLabel.objects.create(
        ambassador=ambassador_user,
        name="Test Site Fixture",
        domain="test-fixture.com",
        primary_color="#FF0000",
        secondary_color="#00FF00",
        is_active=True,
    )
