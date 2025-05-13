import pytest
from django.contrib.auth import get_user_model
from apps.affiliate.models import WhiteLabel

User = get_user_model()


@pytest.mark.django_db
def test_whitelabel_creation():
    ambassador = User.objects.create_user(username="ambassador2", password="testpass")
    whitelabel = WhiteLabel.objects.create(
        ambassador=ambassador,
        name="Test WhiteLabel",
        domain="test-whitelabel.com",
        primary_color="#123456",
        secondary_color="#654321",
        logo="whitelabels/logos/test.png",
    )
    assert whitelabel.ambassador == ambassador
    assert whitelabel.name == "Test WhiteLabel"
    assert whitelabel.domain == "test-whitelabel.com"
