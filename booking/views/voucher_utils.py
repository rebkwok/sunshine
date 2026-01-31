import logging

from stripe_payments.models import Invoice
from ..models import ItemVoucher, Membership, TotalVoucher

logger = logging.getLogger(__name__)


class VoucherValidationError(Exception):
    pass


def validate_voucher_max_total_uses(
    voucher, paid_only=True, user=None, item_to_exclude=()
):
    assert isinstance(voucher, ItemVoucher)
    if voucher.max_vouchers is not None:
        # find all items that have used the voucher
        # This is PAID items only
        all_used_items = voucher.used_items()

        if not paid_only:
            # We're counting unpaid uses for THIS USER too
            # Find all unpaid voucher items for this user
            user_unpaid_items = {
                k: v.filter(user=user, paid=False)
                for k, v in voucher.paid_and_unpaid_items().items()
            }
            # we count used items plus user unpaid
            used_items_to_count = {
                k: all_used_items[k] | user_unpaid_items[k]
                for k, v in all_used_items.items()
            }
        else:
            used_items_to_count = all_used_items

        # exclude the current item if necessary
        if item_to_exclude:
            item_type, item_id = item_to_exclude
            used_items_to_count[item_type] = used_items_to_count[item_type].exclude(
                id=item_id
            )

        used_voucher_count = sum(
            [item.count() for item in used_items_to_count.values()]
        )
        if used_voucher_count >= voucher.max_vouchers:
            raise VoucherValidationError(
                f"Voucher code {voucher.code} has limited number of total uses and expired before it could be used for all applicable items"
            )


def validate_total_voucher_max_total(voucher):
    assert isinstance(voucher, TotalVoucher)
    if voucher.max_vouchers is not None:
        used_voucher_invoices = Invoice.objects.filter(
            total_voucher_code=voucher.code, paid=True
        )
        # exclude any uses associated with unpaid invoices
        if used_voucher_invoices.count() >= voucher.max_vouchers:
            raise VoucherValidationError(
                f"Voucher code {voucher.code} has limited number of total uses and has expired"
            )


def validate_voucher_properties(voucher):
    """Validate voucher properties that are not specific to number of uses"""
    if voucher.has_expired:
        raise VoucherValidationError("Voucher has expired")
    elif not voucher.activated:
        raise VoucherValidationError("Voucher has not been activated yet")
    elif not voucher.has_started:
        raise VoucherValidationError(
            f"Voucher code is not valid until {voucher.start_date.strftime('%d %b %y')}"
        )
    elif voucher.max_vouchers is not None:
        # validate max vouchers by checking paid blocks/invoices only
        if isinstance(voucher, ItemVoucher):
            validate_voucher_max_total_uses(voucher, paid_only=True)
        else:
            validate_total_voucher_max_total(voucher)


def validate_unpaid_voucher_max_total_uses(user, voucher, item_to_exclude=None):
    if voucher.max_vouchers is not None:
        validate_voucher_max_total_uses(
            voucher, user=user, paid_only=False, item_to_exclude=item_to_exclude
        )


def validate_voucher_for_user(voucher, user, check_voucher_properties=True):
    # Only check items that haven't already had this code applied
    if check_voucher_properties:
        validate_voucher_properties(voucher)
    if (
        voucher.max_per_user is not None
        and voucher.uses(user=user) >= voucher.max_per_user
    ):
        raise VoucherValidationError(
            f"You have already used voucher code {voucher.code} the maximum number of times ({voucher.max_per_user})"
        )


def validate_total_voucher_for_checkout_user(voucher, user):
    validate_voucher_properties(voucher)
    if (
        voucher.max_per_user is not None
        and Invoice.objects.filter(
            username=user.email, paid=True, total_voucher_code=voucher.code
        ).count()
        >= voucher.max_per_user
    ):
        raise VoucherValidationError(
            f"You have already used voucher code {voucher.code} the maximum number of times ({voucher.max_per_user})"
        )


def validate_voucher_for_items_in_cart(
    voucher, cart_unpaid_memberships, cart_unpaid_bookings
):
    valid_bookings_in_cart = any(
        [
            voucher.check_event_type(booking.event.event_type)
            for booking in cart_unpaid_bookings
        ]
    )
    if not valid_bookings_in_cart:
        valid_memberships_in_cart = any(
            [
                voucher.check_membership_type(membership.membership_type)
                for membership in cart_unpaid_memberships
            ]
        )
        if not valid_memberships_in_cart:
            raise VoucherValidationError(
                f"Code '{voucher.code}' is not valid for any items in your cart"
            )


def validate_voucher_for_unpaid_item(
    item_type, item, voucher=None, check_voucher_properties=True
):
    voucher = voucher or item.voucher
    if check_voucher_properties:
        # raise exceptions for all the voucher-related things
        validate_voucher_properties(voucher)
    validate_unpaid_voucher_max_total_uses(
        item.user, voucher, item_to_exclude=(item_type, item.id)
    )
    # raise exception if voucher not valid specifically for this user
    if voucher.max_per_user is not None:
        user_items = voucher.paid_and_unpaid_items(user=item.user)
        users_used_vouchers_excluding_this_one = 0
        for voucher_item_type, voucher_items in user_items.items():
            if voucher_item_type != item_type:
                users_used_vouchers_excluding_this_one += voucher_items.count()
            else:
                users_used_vouchers_excluding_this_one += voucher_items.exclude(
                    id=item.id
                ).count()

        if users_used_vouchers_excluding_this_one >= voucher.max_per_user:
            raise VoucherValidationError(
                f"Voucher code {voucher.code} already used max number of times (limited to {voucher.max_per_user} per user)"
            )


def get_valid_applied_voucher_info(item):
    """
    Validate codes already applied to unpaid items and return info
    """
    if isinstance(item, Membership):
        item_type = "membership"
    else:
        item_type = "booking"

    if item.voucher:
        try:
            validate_voucher_for_unpaid_item(item_type, item)
            return {
                "code": item.voucher.code,
                "discounted_cost": item.cost_with_voucher,
            }
        except VoucherValidationError as voucher_error:
            logger.error(
                "Previously applied voucher (code %s) for %s id %s, user %s is now invalid and removed: %s",
                item.voucher.code,
                item_type,
                item.id,
                item.user.username,
                voucher_error,
            )
            item.voucher = None
            item.save()
    return {"code": None, "discounted_cost": None}


def _verify_item_vouchers(unpaid_memberships, unpaid_bookings):
    # verify any existing vouchers on items
    for item_type, item_set in [
        ("membership", unpaid_memberships),
        ("booking", unpaid_bookings),
    ]:
        for item in item_set:
            if item.voucher:
                try:
                    validate_voucher_properties(item.voucher)
                    # check the voucher is valid for this item type (returns bool)
                    if not item.voucher.check_item(item):
                        raise VoucherValidationError(
                            f"voucher on {item_type} not valid"
                        )
                    validate_voucher_for_user(
                        item.voucher, item.user, check_voucher_properties=False
                    )
                    validate_voucher_for_unpaid_item(
                        item_type, item, item.voucher, check_voucher_properties=False
                    )
                except VoucherValidationError:
                    item.voucher = None
                    item.save()


def _get_and_verify_total_vouchers(request):
    total_voucher_code = request.session.get("total_voucher_code")
    if total_voucher_code:
        total_voucher = TotalVoucher.objects.get(code=total_voucher_code)
        try:
            validate_total_voucher_for_checkout_user(total_voucher, request.user)
            return total_voucher
        except VoucherValidationError:
            del request.session["total_voucher_code"]
