from suit.apps import DjangoSuitConfig, SUIT_FORM_SIZE_LARGE, SUIT_FORM_SIZE_X_LARGE
from suit.menu import ParentItem, ChildItem


class SuitConfig(DjangoSuitConfig):
    layout = 'horizontal'

    form_size = {
        'default': SUIT_FORM_SIZE_LARGE,
        # 'fields': {}
        'widgets': {
            'RelatedFieldWidgetWrapper': SUIT_FORM_SIZE_X_LARGE
        }
        # 'fieldsets': {}
    }

    # instructor users can only view registers; all other menu items require this permission
    superuser_permissions = ["add_event"]
    menu = (
        ParentItem('Website', children=[
            ChildItem(model='website.aboutinfo'),
            ChildItem(model='timetable.sessiontype'),
            ChildItem(model='timetable.instructor'),
        ], icon='fa fa-globe', permissions=superuser_permissions),
        ParentItem('Gallery', app="gallery", icon='fa fa-camera'),
        ParentItem('Accounts', children=[
            ChildItem(model='auth.user'),
            ChildItem(model='account.emailaddress'),
            ChildItem(model='accounts.cookiepolicy'),
            ChildItem(model='accounts.dataprivacypolicy'),
            ChildItem(model='accounts.signeddataprivacy'),
        ], icon='fa fa-users', permissions=superuser_permissions),
        ParentItem('Timetable', children=[
            ChildItem(model='timetable.timetablesession'),
            ChildItem('Upload timetable', url='/pf_admin/timetable/timetablesession/upload'),
        ], icon='fa fa-calendar', permissions=superuser_permissions),
        ParentItem('Classes/Workshops', children=[
            ChildItem(model='booking.event'),
            ChildItem(model='booking.regularclass'),
            ChildItem(model='booking.workshop'),
        ], icon='fa fa-calendar', permissions=superuser_permissions),
        ParentItem('Registers', children=[
            ChildItem(model='booking.register'),
        ], icon='fa fa-star'),
        ParentItem('Bookings', children=[
            ChildItem(model='booking.booking'),
            ChildItem(model='booking.waitinglistuser'),
        ], icon='fa fa-heart', permissions=superuser_permissions),
        ParentItem('Payments', children=[
            ChildItem(model='payments.paypalbookingtransaction'),
            ChildItem(model='ipn.paypalipn'),
            ChildItem("Test paypal email", url='/payments/test-paypal-email')
        ], icon='fa fa-credit-card', permissions=superuser_permissions),
        ParentItem('Activity Log', children=[
            ChildItem("Activitylog", 'activitylog.activitylog'),
        ], permissions=superuser_permissions)
    )

    def ready(self):
        super(SuitConfig, self).ready()
