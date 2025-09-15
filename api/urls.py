from django.urls import path
from . import views

urlpatterns = [
    path('write/', views.write_data, name='write_data'),
    path('read/', views.read_data, name='read_data'),
    path('create_apikey/', views.create_apikey, name='create_apikey'),
]
