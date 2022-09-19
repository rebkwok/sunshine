from decimal import Decimal

from delorean import Delorean


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


def start_of_day_in_utc(input_datetime):
    return Delorean(input_datetime, timezone="utc").start_of_day


def end_of_day_in_utc(input_datetime):
    return Delorean(input_datetime, timezone="utc").end_of_day


def end_of_day_in_local_time(input_datetime, local_timezone="Europe/London"):
    # Return localtime end of day in UTC
    end_of_day_utc = end_of_day_in_utc(input_datetime)
    utc_offset_at_input_datetime = Delorean(input_datetime, timezone="utc").shift(local_timezone).datetime.utcoffset()
    return end_of_day_utc - utc_offset_at_input_datetime