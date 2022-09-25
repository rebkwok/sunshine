from model_bakery import baker
import pytest

from django.contrib.auth.models import User

from ..models import GiftVoucher, MembershipType, GiftVoucherType
from .helpers import make_data_privacy_agreement, make_online_disclaimer, make_disclaimer_content

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
