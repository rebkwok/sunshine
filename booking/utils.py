from decimal import Decimal

from delorean import Delorean


def calculate_user_cart_total(
        unpaid_memberships=None,
        unpaid_bookings=None,
        unpaid_gift_vouchers=None,
        total_voucher=None
):

    membership_cost = sum(
        [unpaid_membership.cost_with_voucher for unpaid_membership in unpaid_memberships]
    )
    booking_cost = sum(
        [unpaid_booking.cost_with_voucher for unpaid_booking in unpaid_bookings]
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


def full_name(user):
    return f"{user.first_name} {user.last_name}"


def start_of_day_in_utc(input_datetime):
    return Delorean(input_datetime, timezone="utc").start_of_day


def end_of_day_in_utc(input_datetime):
    return Delorean(input_datetime, timezone="utc").end_of_day


def date_in_local_time_as_utc(input_datetime, local_timezone="Europe/London"):
    return Delorean(input_datetime, timezone="utc").shift(local_timezone).datetime


def end_of_day_in_local_time(input_datetime, local_timezone="Europe/London"):
    # Return localtime end of day in UTC
    end_of_day_utc = end_of_day_in_utc(input_datetime)
    utc_offset_at_input_datetime = date_in_local_time_as_utc(input_datetime).utcoffset()
    return end_of_day_utc - utc_offset_at_input_datetime


def start_of_day_in_local_time(input_datetime, local_timezone="Europe/London"):
    # Return localtime end of day in UTC
    start_of_day_utc = start_of_day_in_utc(input_datetime)
    utc_offset_at_input_datetime = date_in_local_time_as_utc(input_datetime).utcoffset()
    return start_of_day_utc - utc_offset_at_input_datetime


def host_from_request(request):
    return f"http://{request.META.get('HTTP_HOST')}"
