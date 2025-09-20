from django.urls import path
from . import views

urlpatterns = [
    path('write_data/<int:device_id>/', views.write_data, name='write_data'),
    path('dashboard/<uuid:dashboard_uuid>/', views.customer_dashboard, name='customer_dashboard'),
    path('api/dashboard/<uuid:dashboard_uuid>/data/', views.customer_devices_data, name='customer_dashboard_data'),
    path('write_data/<int:device_id>/', views.write_data, name='write_data'),
    path('sensor_data/<int:device_id>/', views.get_sensor_data, name='get_sensor_data'),
    path('devices/', views.device_list, name='device_list'),
    path('devices/<int:device_id>/', views.device_detail, name='device_detail'),
    path('create_apikey/', views.create_apikey, name='create_apikey'),
    path('get_apikey/', views.get_apikey, name='get_apikey'),
    path('delete_apikey/', views.delete_apikey, name='delete_apikey'),
    path('customer/<int:customer_id>/devices/', views.customer_devices, name='customer_devices'),
]
