from django.urls import path
from . import views

urlpatterns = [
    path('create_apikey/', views.create_apikey, name='create_apikey'),
    path('write_data/<int:device_id>/', views.write_data, name='write_data'),
    path('read_data/<int:device_id>/', views.read_data, name='read_data'),
]
