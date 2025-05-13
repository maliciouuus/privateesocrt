import pytest
from django.contrib.auth import get_user_model
from apps.affiliate.models import CommissionRate
from decimal import Decimal

User = get_user_model()


@pytest.mark.django_db
def test_commissionrate_creation():
    ambassador = User.objects.create_user(username="ambassador", password="testpass")
    rate = CommissionRate.objects.create(
        ambassador=ambassador, target_type="escort", rate=Decimal("0.30")
    )
    assert rate.ambassador == ambassador
    assert rate.target_type == "escort"
    assert rate.rate == Decimal("0.30")
