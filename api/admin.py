from django.contrib import admin
from .models import Customer, Device, ApiKey, SensorData

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id','customer')

@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ('key','customer','label')

@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ('device','timestamp')
    readonly_fields = ('timestamp','data')
