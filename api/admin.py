from django.contrib import admin
from .models import Customer, ApiKey, Device, SensorData


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at")
    search_fields = ("name", "email")
    readonly_fields = ("created_at",)


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("customer", "read_key", "write_key", "created_at")
    search_fields = ("customer__name", "read_key", "write_key")
    readonly_fields = ("read_key", "write_key", "created_at")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "customer", "location", "created_at")
    search_fields = ("name", "customer__name")
    readonly_fields = ("created_at",)


@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ("device", "temperature", "pressure", "flow", "timestamp")
    search_fields = ("device__name", "device__customer__name")
    readonly_fields = ("timestamp",)
