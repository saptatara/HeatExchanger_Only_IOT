from django.db import models

class Customer(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

class Device(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='devices')
    device_id = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.device_id} ({self.customer})"

class ApiKey(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='api_keys')
    key = models.CharField(max_length=128, unique=True)
    label = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.label or self.key[:8]}... ({self.customer})"

class SensorData(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='data')
    timestamp = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=['device','timestamp']),
        ]

    def __str__(self):
        return f"{self.device.device_id} @ {self.timestamp}"
