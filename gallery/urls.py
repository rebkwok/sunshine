from django.conf.urls import url

from gallery.views import gallery

urlpatterns = [
    url(r'^$', gallery, name='gallery'),
]
