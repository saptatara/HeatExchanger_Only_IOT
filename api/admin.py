# api/admin.py
from django.contrib import admin
from .models import Customer, Device, DeviceType, SensorType, SensorConfiguration, SensorData, FoulingData

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'contact_email', 'phone_number', 'created_at']
    list_filter = ['created_at', 'receive_sms_alerts', 'receive_email_alerts']
    search_fields = ['company_name', 'contact_email']
    readonly_fields = ['dashboard_url']

@admin.register(DeviceType)
class DeviceTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'customer', 'device_type', 'location', 'is_active', 'created_at']
    list_filter = ['is_active', 'device_type', 'created_at', 'customer']
    search_fields = ['name', 'location', 'write_api_key']
    readonly_fields = ['write_api_key', 'read_api_key']

@admin.register(SensorType)
class SensorTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit', 'description']
    list_filter = ['name']
    search_fields = ['name', 'unit']

@admin.register(SensorConfiguration)
class SensorConfigurationAdmin(admin.ModelAdmin):
    list_display = ['sensor_label', 'device', 'sensor_type', 'expected_min', 'expected_max']
    list_filter = ['sensor_type', 'device']
    search_fields = ['sensor_label', 'device__name']

@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ['device', 'sensor_config', 'value', 'created_at']
    list_filter = ['device', 'sensor_config__sensor_type', 'created_at']
    search_fields = ['device__name', 'sensor_config__sensor_label']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

@admin.register(FoulingData)
class FoulingDataAdmin(admin.ModelAdmin):
    list_display = ['device', 'fouling_factor', 'thermal_efficiency', 'is_alert', 'created_at']
    list_filter = ['is_alert', 'device', 'created_at']
    search_fields = ['device__name', 'alert_message']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
