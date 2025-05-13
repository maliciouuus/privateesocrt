import pytest
from django.contrib.auth import get_user_model
from apps.affiliate.models import Payout
from decimal import Decimal

User = get_user_model()


@pytest.mark.django_db
def test_payout_creation():
    ambassador = User.objects.create_user(username="ambassador3", password="testpass")
    payout = Payout.objects.create(
        ambassador=ambassador,
        amount=Decimal("100.00"),
        payment_method="btc",
        wallet_address="1BitcoinAddress",
        status="pending",
    )
    assert payout.ambassador == ambassador
    assert payout.amount == Decimal("100.00")
    assert payout.payment_method == "btc"
    assert payout.status == "pending"
