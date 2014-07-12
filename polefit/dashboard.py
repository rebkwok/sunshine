"""
This file was generated with the customdashboard management command and
contains the class for the main dashboard.

To activate your index dashboard add the following to your settings.py::
    GRAPPELLI_INDEX_DASHBOARD = 'polefit.dashboard.CustomIndexDashboard'
"""

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from grappelli.dashboard import modules, Dashboard
from grappelli.dashboard.utils import get_admin_site_name


class CustomIndexDashboard(Dashboard):
    """
    Custom index dashboard for www.
    """
    
    def init_with_context(self, context):
        site_name = get_admin_site_name(context)
        

        self.children.append(modules.ModelList(
            _('Timetable sessions'),
            collapsible=True,
            column=1,
            pre_content=('<h4>Enter scheduled classes, workshops and anything else that is to appear on the timetable '
                         'pages.</h4>'),
            css_classes=('collapse closed',),
            models=('timetable.models.Session',),
            exclude=('django.contrib.*',),
        ))



        self.children.append(modules.ModelList(
            _('Session types, Instructors and Venues'),
            collapsible=True,
            column=1,
            pre_content=('<h4>Enter session (class) types, instructors and venues.  Descriptive information entered and '
                         'photos uploaded here are used to populate the website pages.</h4>'),
            css_classes=('collapse closed',),
            models=('timetable.models.SessionType',
                    'timetable.models.Instructor',
                    'timetable.models.Venue',),
            exclude=('django.contrib.*',),
        ))

        self.children.append(modules.ModelList(
            _('Events'),
            collapsible=True,
            column=1,
            pre_content=('<h4>Shows, competitions and other events.</h4>'),
            css_classes=('collapse closed',),
            models=('timetable.models.Event',),
            exclude=('django.contrib.*',),
        ))

        self.children.append(modules.ModelList(
            _('Gallery'),
            collapsible=True,
            column=1,
            pre_content=('<h4>Upload images for the gallery pages.</h4>'),
            css_classes=('collapse closed',),
            models=('gallery.models.Category',),
            exclude=('django.contrib.*',),
        ))

        self.children.append(modules.ModelList(
            _('About page'),
            collapsible=True,
            column=1,
            pre_content=('<h4>Add content for the About page, including list of competitions and past achievements.</h4>'),
            css_classes=('collapse closed',),
            models=('polefit.website.models.AboutInfo',
                    'polefit.website.models.PastEvent',),
            exclude=('django.contrib.*',),
        ))

       # self.children.append(modules.AppList(
       #     _('Test applist to check all models are included in the real lists above'),
       #     pre_content=('<h4>To be deleted later.</h4>'),
       #     column=1,
       #     collapsible=True,
       #     css_classes=('collapse closed',),
       #     exclude=('django.contrib.*',),
       # ))
        
        # append another link list module for "support".
        self.children.append(modules.LinkList(
            _('Website links'),
            column=2,
            children=[
                {
                    'title': _('Homepage'),
                    'url': '/',
                    'external': False,
                },
                {
                    'title': _('Timetable'),
                    'url': '/timetable',
                    'external': False,
                },
            ]
        ))

        self.children.append(modules.ModelList(
            _('User Administration'),
            column=3,
            collapsible=False,
            models=('django.contrib.*',),
        ))
        
        # append a recent actions module
        self.children.append(modules.RecentActions(
            _('Recent Actions'),
            limit=5,
            collapsible=False,
            column=2,
        ))


