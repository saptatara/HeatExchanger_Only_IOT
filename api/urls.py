from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

urlpatterns = [
    # Customer UI Views
    path('ui/dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('ui/device/<int:device_id>/', views.device_detail_ui, name='device_detail_ui'),
    path('ui/add-sensor-data/', views.add_sensor_data, name='add_sensor_data'),
    path('ui/sensor-configs/', views.sensor_configurations, name='sensor_configurations'),
    
    # API Endpoints (for IoT devices)
    path('write_data/<int:device_id>/', views.write_data, name='write_data'),
    path('read_data/<int:device_id>/', views.read_data, name='read_data'),
    path('sensor_data/<int:device_id>/', views.get_sensor_data, name='get_sensor_data'),
    
    # Device Management API
    path('devices/', views.device_list, name='device_list'),
    path('devices/<int:device_id>/', views.device_detail_api, name='device_detail_api'),
    
    # Authentication API
    path('create_apikey/', views.create_apikey, name='create_apikey'),
    path('get_apikey/', views.get_apikey, name='get_apikey'),
    path('delete_apikey/', views.delete_apikey, name='delete_apikey'),
    
    # Customer API
    path('customer/<int:customer_id>/devices/', views.customer_devices, name='customer_devices'),
    
    # Legacy URLs (keep for backward compatibility)
    path('dashboard/<uuid:dashboard_uuid>/', views.customer_dashboard_uuid, name='customer_dashboard_uuid'),
    path('api/dashboard/<uuid:dashboard_uuid>/data/', views.customer_devices_data, name='customer_dashboard_data'),
]
