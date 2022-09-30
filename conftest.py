from unittest.mock import Mock

from model_bakery import baker
import pytest

from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from booking.models import GiftVoucher, MembershipType, GiftVoucherType
from booking.tests.helpers import make_data_privacy_agreement, make_online_disclaimer, make_disclaimer_content
from stripe_payments.models import Seller

@pytest.fixture(autouse=True)
def use_dummy_cache_backend(settings):
    settings.SKIP_NEW_ACCOUNT_EMAIL = True


@pytest.fixture
def configured_user():
    user = User.objects.create_user(
            username='test', 
            first_name="Test", 
            last_name="User", 
            email='test@test.com', 
            password='test'
        )
    make_disclaimer_content()
    make_online_disclaimer(user=user)
    make_data_privacy_agreement(user)
    yield user


@pytest.fixture
def superuser():
    yield User.objects.create_superuser(
        username='test_superuser', 
        first_name="Super", 
        last_name="User", 
        email='super@test.com', 
        password='test'
    )


@pytest.fixture
def seller():
    yield baker.make(Seller, site=Site.objects.get_current())


@pytest.fixture
def membership_type():
    yield baker.make(MembershipType, name="test", cost=20, number_of_classes=2)


@pytest.fixture
def membership_type_4():
    yield baker.make(MembershipType, name="test4", cost=40, number_of_classes=4)


@pytest.fixture
def gift_voucher_types(membership_type, membership_type_4):
    # make sure we've got a regular_session and private to fetch costs from
    baker.make_recipe("booking.future_PC")
    baker.make_recipe("booking.future_PV")
    yield {
        "total": baker.make(GiftVoucherType, discount_amount=10, active=True),
        "regular_session": baker.make(GiftVoucherType, event_type="regular_session", active=True),
        "private": baker.make(GiftVoucherType, event_type="private", active=True),
        "membership_2": baker.make(GiftVoucherType, membership_type=membership_type, active=True),
        "membership_4": baker.make(GiftVoucherType, membership_type=membership_type_4, active=True),
    }


@pytest.fixture
def membership_gift_voucher(configured_user, gift_voucher_types):
    gv = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["membership_2"])
    gv.voucher.purchaser_email = configured_user.email
    gv.voucher.save()
    yield gv


@pytest.fixture
def event_gift_voucher(configured_user, gift_voucher_types):
    gv = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["regular_session"])
    gv.voucher.purchaser_email = configured_user.email
    gv.voucher.save()
    yield gv


@pytest.fixture
def total_gift_voucher(configured_user, gift_voucher_types):
    gv = baker.make(GiftVoucher, gift_voucher_type=gift_voucher_types["total"])
    gv.voucher.purchaser_email = configured_user.email
    gv.voucher.save()
    yield gv


@pytest.fixture
def get_mock_payment_intent():
    def payment_intent(webhook_event_type=None, **params):
        defaults = {
            "id": "mock-intent-id",
            "amount": 1000,
            "description": "",
            "status": "succeeded",
            "metadata": {},
            "currency": "gbp",
            "client_secret": "secret",
            "charges": Mock(data=[{"billing_details": {"email": "stripe-payer@test.com"}}])
        }
        options = {**defaults, **params}
        if webhook_event_type == "payment_intent.payment_failed":
            options["last_payment_error"] = {'error': 'an error'}
        return Mock(**options)
    return payment_intent


@pytest.fixture
def get_mock_refund():
    def refund(**params):
        defaults = {
            "id": "mock-refund-id",
            "amount": 800,
            "status": "succeeded",
            "metadata": {},
            "currency": "gbp",
            "reason": "",
        }
        options = {**defaults, **params}
        return Mock(**options)
    return refund


@pytest.fixture
def get_mock_webhook_event(get_mock_payment_intent):
    def mock_webhook_event(**params):
        webhook_event_type = params.pop("webhook_event_type", "payment_intent.succeeded")
        mock_event = Mock(
            data=Mock(object=get_mock_payment_intent(webhook_event_type, **params)), type=webhook_event_type
        )
        return mock_event
    return mock_webhook_event
