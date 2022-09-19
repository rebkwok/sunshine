from decimal import Decimal


def calculate_user_cart_total(
        unpaid_memberships=None,
        unpaid_bookings=None,
        unpaid_gift_vouchers=None,
        total_voucher=None
):
    def _membership_cost(unpaid_membership):
        # if unpaid_membership.voucher:
        #     return unpaid_membership.cost_with_voucher
        # else:
        #     return unpaid_membership.membership.cost
        return unpaid_membership.membership_type.cost
    
    def _booking_cost(unpaid_booking):
        # if unpaid_booking.voucher:
        #     return unpaid_booking.cost_with_voucher
        # else:
        #     return unpaid_booking.cost
        return unpaid_booking.event.cost

    membership_cost = sum(
        [_membership_cost(unpaid_membership) for unpaid_membership in unpaid_memberships]
    )
    booking_cost = sum(
        [_booking_cost(unpaid_booking) for unpaid_booking in unpaid_bookings]
    )
    gift_voucher_cost = sum(
        [gift_voucher.gift_voucher_config.cost for gift_voucher in unpaid_gift_vouchers]
    )

    cart_total = membership_cost + booking_cost + gift_voucher_cost
    if total_voucher:
        if total_voucher.discount:
            percentage_to_pay = Decimal((100 - total_voucher.discount) / 100)
            return (cart_total * percentage_to_pay).quantize(Decimal('.01'))
        else:
            if total_voucher.discount_amount > cart_total:
                cart_total = 0
            else:
                cart_total -= Decimal(total_voucher.discount_amount)
    return cart_total
