import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.affiliate.models import Referral, Commission
from decimal import Decimal


@pytest.mark.django_db
def test_export_commission_csv():
    user = User.objects.create_user(username="csvuser", password="testpass")
    referrer = User.objects.create_user(username="csvreferrer", password="testpass")
    referral = Referral.objects.create(referrer=referrer, referred=user, referral_code="CSV123")
    Commission.objects.create(
        user=user, referral=referral, amount=Decimal("20.00"), status="pending"
    )
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("commission-export-csv")
    response = client.get(url)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    content = response.content.decode()
    assert "csvuser" in content
    assert "20.00" in content


@pytest.mark.django_db
def test_create_commission_api():
    user = User.objects.create_user(username="apiuser", password="testpass")
    referrer = User.objects.create_user(username="apireferrer", password="testpass")
    referral = Referral.objects.create(referrer=referrer, referred=user, referral_code="API123")
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("commission-list")
    data = {
        "user": user.id,
        "referral": referral.id,
        "amount": "15.00",
        "status": "pending",
    }
    response = client.post(url, data)
    assert response.status_code == 201
    assert Commission.objects.filter(user=user, referral=referral, amount=Decimal("15.00")).exists()


@pytest.mark.django_db
def test_export_commission_csv_unauthorized():
    url = reverse("commission-export-csv")
    client = APIClient()
    response = client.get(url)
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_mark_paid_action():
    user = User.objects.create_user(username="payuser", password="testpass")
    referrer = User.objects.create_user(username="payreferrer", password="testpass")
    referral = Referral.objects.create(referrer=referrer, referred=user, referral_code="PAY123")
    commission = Commission.objects.create(
        user=user, referral=referral, amount=Decimal("30.00"), status="pending"
    )
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("commission-mark-paid", args=[commission.id])
    response = client.post(url)
    assert response.status_code == 200
    commission.refresh_from_db()
    assert commission.status == "paid"
    assert commission.paid_at is not None


@pytest.mark.django_db
def test_mark_paid_action_unauthorized():
    user = User.objects.create_user(username="payuser2", password="testpass")
    referrer = User.objects.create_user(username="payreferrer2", password="testpass")
    referral = Referral.objects.create(referrer=referrer, referred=user, referral_code="PAY124")
    commission = Commission.objects.create(
        user=user, referral=referral, amount=Decimal("40.00"), status="pending"
    )
    client = APIClient()
    url = reverse("commission-mark-paid", args=[commission.id])
    response = client.post(url)
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_list_commissions():
    user = User.objects.create_user(username="listuser", password="testpass")
    referrer = User.objects.create_user(username="listreferrer", password="testpass")
    referral = Referral.objects.create(referrer=referrer, referred=user, referral_code="LIST123")
    Commission.objects.create(
        user=user, referral=referral, amount=Decimal("50.00"), status="pending"
    )
    Commission.objects.create(
        user=user, referral=referral, amount=Decimal("60.00"), status="pending"
    )
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("commission-list")
    response = client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    amounts = [Decimal(str(c["amount"])) for c in data]
    assert Decimal("50.00") in amounts and Decimal("60.00") in amounts


@pytest.mark.django_db
def test_retrieve_commission():
    user = User.objects.create_user(username="retrieveuser", password="testpass")
    referrer = User.objects.create_user(username="retrieveref", password="testpass")
    referral = Referral.objects.create(referrer=referrer, referred=user, referral_code="RET123")
    commission = Commission.objects.create(
        user=user, referral=referral, amount=Decimal("70.00"), status="pending"
    )
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("commission-detail", args=[commission.id])
    response = client.get(url)
    assert response.status_code == 200
    assert response.json()["amount"] == "70.00"


@pytest.mark.django_db
def test_update_commission():
    user = User.objects.create_user(username="updateuser", password="testpass")
    referrer = User.objects.create_user(username="updateref", password="testpass")
    referral = Referral.objects.create(referrer=referrer, referred=user, referral_code="UPD123")
    commission = Commission.objects.create(
        user=user, referral=referral, amount=Decimal("80.00"), status="pending"
    )
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("commission-detail", args=[commission.id])
    response = client.patch(url, {"amount": "85.00"})
    assert response.status_code == 200
    commission.refresh_from_db()
    assert commission.amount == Decimal("85.00")


@pytest.mark.django_db
def test_delete_commission():
    user = User.objects.create_user(username="deleteuser", password="testpass")
    referrer = User.objects.create_user(username="deleteref", password="testpass")
    referral = Referral.objects.create(referrer=referrer, referred=user, referral_code="DEL123")
    commission = Commission.objects.create(
        user=user, referral=referral, amount=Decimal("90.00"), status="pending"
    )
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse("commission-detail", args=[commission.id])
    response = client.delete(url)
    assert response.status_code == 204
    assert not Commission.objects.filter(id=commission.id).exists()


@pytest.mark.django_db
def test_list_commissions_unauthorized():
    url = reverse("commission-list")
    client = APIClient()
    response = client.get(url)
    assert response.status_code in (401, 403)
