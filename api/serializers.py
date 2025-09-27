from rest_framework import serializers
from .models import Customer, Device, SensorData, SensorConfiguration, SensorType


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "email", "created_at"]


class SensorTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorType
        fields = ["id", "name", "unit"]


class SensorConfigurationSerializer(serializers.ModelSerializer):
    sensor_type = SensorTypeSerializer()

    class Meta:
        model = SensorConfiguration
        fields = ["id", "sensor_label", "sensor_type"]


class SensorDataSerializer(serializers.ModelSerializer):
    sensor_label = serializers.CharField(source="sensor_config.sensor_label", read_only=True)
    unit = serializers.CharField(source="sensor_config.sensor_type.unit", read_only=True)
    timestamp = serializers.DateTimeField(source="created_at", format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = SensorData
        fields = ["id", "value", "timestamp", "sensor_label", "unit"]


class DeviceSerializer(serializers.ModelSerializer):
    sensor_data = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = ["id", "name", "description", "created_at", "sensor_data"]

    def get_sensor_data(self, obj):
        readings = obj.sensor_data.all().select_related(
            "sensor_config", "sensor_config__sensor_type"
        ).order_by("-created_at")[:50]

        grouped = {}
        for r in readings:
            label = r.sensor_config.sensor_label
            if label not in grouped:
                grouped[label] = []
            grouped[label].append({
                "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "value": r.value,
                "unit": r.sensor_config.sensor_type.unit,
            })

        # Sort each group by time ascending
        for label in grouped:
            grouped[label].sort(key=lambda x: x["timestamp"])

        return grouped

