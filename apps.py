from suit.apps import DjangoSuitConfig, SUIT_FORM_SIZE_FULL, SUIT_FORM_SIZE_SMALL, SUIT_FORM_SIZE_LARGE, SUIT_FORM_SIZE_X_LARGE
from suit.menu import ParentItem, ChildItem


class SuitConfig(DjangoSuitConfig):
    layout = 'horizontal'

    form_size = {
        'default': SUIT_FORM_SIZE_SMALL,
        # 'fields': {}
        'widgets': {
            'RelatedFieldWidgetWrapper': SUIT_FORM_SIZE_LARGE,
            'AdminTextInputWidget': SUIT_FORM_SIZE_FULL,
             'CheckboxInput': SUIT_FORM_SIZE_FULL,
             'AdminTextareaWidget':SUIT_FORM_SIZE_FULL,
             'Select': SUIT_FORM_SIZE_FULL,
             'FormBuilderWidget': SUIT_FORM_SIZE_FULL,
             'NumberInput': SUIT_FORM_SIZE_FULL,
        }
        # 'fieldsets': {}
    }

    # staff users cannot see anything at the moment
    superuser_permissions = ["add_event"]
    menu = (
        ParentItem('Accounts', children=[
            ChildItem(model='auth.user'),
            ChildItem(model='account.emailaddress'),
            ChildItem(model='accounts.signeddataprivacy'),
            ChildItem("Signed disclaimers", model='accounts.onlinedisclaimer'),
            ChildItem(model='accounts.archiveddisclaimer'),
        ], icon='fa fa-users', permissions=superuser_permissions),
        ParentItem('Policies', children=[
            ChildItem(model='accounts.cookiepolicy'),
            ChildItem(model='accounts.dataprivacypolicy'),
            ChildItem(model='accounts.disclaimercontent'),
        ], icon='fa fa-users', permissions=superuser_permissions),
        ParentItem('Timetable', children=[
            ChildItem(model='timetable.sessiontype'),
            ChildItem(model='timetable.venue'),
            ChildItem(model='timetable.category'),
            ChildItem(model='timetable.timetablesession'),
            ChildItem('Upload timetable', url='/site-admin/timetable/timetablesession/upload'),
        ], icon='fa fa-calendar', permissions=superuser_permissions),
        ParentItem('Classes/Workshops', children=[
            ChildItem(model='booking.event'),
            ChildItem(model='booking.regularclass'),
            ChildItem(model='booking.workshop'),
            ChildItem(model='booking.private'),
        ], icon='fa fa-calendar', permissions=superuser_permissions),
        ParentItem('Bookings', children=[
            ChildItem(model='booking.booking'),
            ChildItem(model='booking.waitinglistuser'),
        ], icon='fa fa-heart', permissions=superuser_permissions),
       ParentItem(
            'Memberships',
            children=[
                ChildItem(model='booking.membershiptype'),
                ChildItem(model='booking.membership')
            ],
            permissions=superuser_permissions
        ),
        ParentItem(
            'Vouchers',
            children=[
                ChildItem(model='booking.itemvoucher'),
                ChildItem(model='booking.totalvoucher')
            ],
            permissions=superuser_permissions
        ),
        ParentItem('Payments', children=[
            ChildItem(model='stripe_payments.invoice'),
            ChildItem(model='stripe_payments.seller'),
            ChildItem(model='stripe_payments.stripepaymentintent'),
        ], icon='fa fa-credit-card', permissions=superuser_permissions),
        ParentItem('Activity Log', children=[
           ChildItem("Activitylog", 'activitylog.activitylog'),
        ], permissions=superuser_permissions)
    )

    def ready(self):
        super(SuitConfig, self).ready()
