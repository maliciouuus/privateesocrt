import pytest
from django.contrib.auth import get_user_model
from apps.affiliate.models import Commission, Referral
from decimal import Decimal

User = get_user_model()


@pytest.mark.django_db
def test_commission_creation():
    user = User.objects.create_user(username="testuser", password="testpass")
    referrer = User.objects.create_user(username="referrer", password="testpass")
    referral = Referral.objects.create(referrer=referrer, referred=user, referral_code="ABC123")
    commission = Commission.objects.create(user=user, referral=referral, amount=Decimal("10.00"))
    assert commission.amount == Decimal("10.00")
    assert commission.user == user
    assert commission.referral == referral
