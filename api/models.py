import uuid
import secrets
from django.db import models
from django.utils import timezone


class Customer(models.Model):
    """
    Represents a customer who owns devices and API keys.
    """
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.name


class ApiKey(models.Model):
    """
    Each customer has one Read Key and one Write Key.
    These keys are auto-generated if not provided.
    """
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="api_key")
    read_key = models.CharField(max_length=64, unique=True, editable=False, blank=True)
    write_key = models.CharField(max_length=64, unique=True, editable=False, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Auto-generate keys if not set
        if not self.read_key:
            self.read_key = secrets.token_hex(16)
        if not self.write_key:
            self.write_key = secrets.token_hex(16)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.name} Keys"


class Device(models.Model):
    """
    Each customer can have multiple IoT devices.
    """
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="devices")
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        unique_together = ("customer", "name")

    def __str__(self):
        return f"{self.name} ({self.customer.name})"


class SensorData(models.Model):
    """
    Stores sensor readings from devices.
    For simplicity we keep separate columns for common fields (temperature, pressure, flow).
    """
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="sensor_data")
    temperature = models.FloatField(blank=True, null=True)
    pressure = models.FloatField(blank=True, null=True)
    flow = models.FloatField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["device", "timestamp"]),
        ]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.device.name} @ {self.timestamp}"
