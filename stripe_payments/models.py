from os import environ

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.conf import settings
from django.db import models
from django.utils import timezone

from hashlib import sha512
from shortuuid import ShortUUID


class Invoice(models.Model):
    # username rather than FK; in case we delete the user later, we want to keep financial info
    username = models.CharField(max_length=255)
    invoice_id = models.CharField(max_length=255)
    amount = models.DecimalField(decimal_places=2, max_digits=8)
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True)
    # register date created so we can periodically delete any unpaid ones that were created by a user going to the
    # checkout and changing their mind
    date_created = models.DateTimeField(default=timezone.now)
    paid = models.BooleanField(default=False)
    date_paid = models.DateTimeField(null=True, blank=True)
    total_voucher_code = models.CharField(
        max_length=255, null=True, blank=True, help_text="Voucher applied to invoice total"
    )

    class Meta:
        ordering = ("-date_paid",)

    def __str__(self):
        return f"{self.invoice_id} - {self.username} - £{self.amount}{' (paid)' if self.paid else ''}"

    @classmethod
    def generate_invoice_id(cls):
        invoice_id = ShortUUID().random(length=22)
        while Invoice.objects.filter(invoice_id=invoice_id).exists():
            invoice_id = ShortUUID().random(length=22)
        return invoice_id

    def signature(self):
        return sha512((self.invoice_id + environ["INVOICE_KEY"]).encode("utf-8")).hexdigest()

    def items_dict(self):
        def _membership_cost_str(block):
            if block.voucher:
                return f"£{block.cost_with_voucher} (voucher applied: {block.voucher.code})"
            return f"£{block.block_config.cost}"
        memberships = {
            f"membership-{item.id}": {
                "name": item.membership.name, "cost": _membership_cost_str(item), "user": item.user
            } for item in self.memberships.all()
        }
        bookings = {
            f"subscription-{item.id}": {
                "name": item.event, "cost": f"£{item.event.cost}", "user": item.user
            } for item in self.bookings.all()
        }
        gift_vouchers = {
            f"gift_voucher-{gift_voucher.id}": {
                "name": gift_voucher.name, "cost": f"£{gift_voucher.gift_voucher_config.cost}"
            } for gift_voucher in self.gift_vouchers.all()
        }

        return {**memberships, **bookings, **gift_vouchers}

    def _item_counts(self):
        return {
            "memberships": self.memberships.count(),
            "bookings": self.bookings.count(),
            "gift_vouchers": self.gift_vouchers.count(),
        }

    def item_count(self):
        return sum(self._item_counts().values())

    def item_types(self):
        return [key for key, count in self._item_counts().items() if count > 0]

    def items_metadata(self):
        # This is used for the payment intent metadata, which is limited to 40 chars keys and string values
        items = self.items_dict()
        metadata = {}
        if self.total_voucher_code:
            metadata = {"Voucher code used on total invoice": self.total_voucher_code}
        items = {
            item["name"][:40]: f"{item['cost']} ({key})" for key, item in items.items()
        }
        return {**metadata, **items}

    def save(self, *args, **kwargs):
        if self.paid and not self.date_paid:
            self.date_paid = timezone.now()
        super().save()


class Seller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    site = models.OneToOneField(Site, on_delete=models.CASCADE, null=True, blank=True)
    stripe_user_id = models.CharField(max_length=255, blank=True)
    stripe_access_token = models.CharField(max_length=255, blank=True)
    stripe_refresh_token = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.user.email


class StripePaymentIntent(models.Model):
    payment_intent_id = models.CharField(max_length=255)
    amount = models.PositiveIntegerField()
    description = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True)
    seller = models.ForeignKey(Seller, on_delete=models.SET_NULL, null=True, blank=True)
    metadata = models.JSONField()
    client_secret = models.CharField(max_length=255)
    currency = models.CharField(max_length=3)

    @classmethod
    def update_or_create_payment_intent_instance(cls, payment_intent, invoice, seller=None):
        defaults = {
            "invoice": invoice,
            "amount": payment_intent.amount,
            "description": payment_intent.description,
            "status": payment_intent.status,
            "metadata": payment_intent.metadata,
            "client_secret": payment_intent.client_secret,
            "currency": payment_intent.currency
        }
        if seller is not None:
            defaults.update({"seller": seller})
        return cls.objects.update_or_create(payment_intent_id=payment_intent.id, defaults=defaults)

    def __str__(self):
        return f"{self.payment_intent_id} - invoice {self.invoice.invoice_id} - {self.invoice.username}"
