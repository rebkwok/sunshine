import logging

from django.contrib.auth.models import Group, User,  Permission
from django.views.generic import CreateView, ListView, UpdateView

from braces.views import LoginRequiredMixin


logger = logging.getLogger(__name__)


NAME_FILTERS = (
    'All', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
)


def _get_name_filter_available(queryset):
    names_list = queryset.distinct().values_list('first_name', flat=True)
    letter_set = set([name[0].lower() for name in names_list if name])

    name_filter_options = []
    for option in NAME_FILTERS:
        if option == "All":
            name_filter_options.append({'value': 'All',  'available': True})
        else:
            name_filter_options.append(
                {
                    'value': option,
                    'available': option.lower() in letter_set
                }
            )
    return name_filter_options


class UserListView(LoginRequiredMixin,  ListView):

    model = User
    template_name = 'studioadmin/user_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        queryset = User.objects.all().order_by('first_name')
        filter = self.request.GET.get('filter')

        if filter and filter != 'All':
            queryset = queryset.filter(first_name__istartswith=filter)

        return queryset

    def get_context_data(self):
        queryset = self.get_queryset()
        context = super().get_context_data()
        context['students_menu_class'] = 'active'
        filter = self.request.GET.get('filter')
        context["filter_submitted"] = filter is not None
        context['filter_options'] = _get_name_filter_available(queryset)

        num_results = queryset.count()
        total_users = User.objects.count()

        context['num_results'] = num_results
        context['total_users'] = total_users
        return context
