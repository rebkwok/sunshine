# Generated by Django 4.0.6 on 2022-09-28 07:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stripe_payments', '0002_stripe_refund_and_more'),
        ('booking', '0006_basevoucher_totalvoucher_itemvoucher_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='GiftVoucherType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(blank=True, choices=[('regular_session', 'Class'), ('private', 'Private Lesson'), ('workshop', 'Workshop')], help_text='Create gift vouchers valid for one event type (class, workshop, private)', max_length=255, null=True, unique=True)),
                ('discount_amount', models.DecimalField(blank=True, decimal_places=2, help_text='Create gift vouchers for a fixed amount; used as a discount against the total shopping basket value for any purchases.', max_digits=6, null=True, unique=True, verbose_name='Exact amount (£)')),
                ('active', models.BooleanField(default=True, help_text='Display on site; set to False instead of deleting unused gift voucher types')),
                ('duration', models.PositiveIntegerField(default=6, help_text='How many months will this gift voucher last?')),
                ('override_cost', models.DecimalField(blank=True, decimal_places=2, help_text='Use this to override the default cost to purchase this gift voucher. (Default cost is the current cost of the item the voucher is for (i.e. the discount amount, or for memberships, the current cost to purchase that membership, and for classes/privates/workshops, the cost of the last event of that type that was created.', max_digits=8, null=True)),
                ('membership_type', models.OneToOneField(blank=True, help_text='Create gift vouchers valid for one membership', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gift_voucher_types', to='booking.membershiptype')),
            ],
            options={
                'ordering': ('event_type', 'membership_type', 'discount_amount'),
            },
        ),
        migrations.CreateModel(
            name='GiftVoucher',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('paid', models.BooleanField(default=False)),
                ('slug', models.SlugField(blank=True, max_length=40, null=True)),
                ('gift_voucher_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.giftvouchertype')),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gift_vouchers', to='stripe_payments.invoice')),
                ('item_voucher', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gift_voucher', to='booking.itemvoucher')),
                ('total_voucher', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gift_voucher', to='booking.totalvoucher')),
            ],
        ),
    ]