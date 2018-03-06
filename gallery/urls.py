from django.urls import path

from gallery.views import gallery


app_name = 'gallery'


urlpatterns = [
    path('', gallery, name='gallery'),
]
