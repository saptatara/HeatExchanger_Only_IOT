from rest_framework import serializers
from .models import SensorData, Device, Customer

class SensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorData
        fields = ['id', 'device', 't1_in', 't1_out', 't2_in', 't2_out', 'created_at']
        read_only_fields = ['id', 'device', 'created_at']

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'name', 'location', 'write_api_key', 'read_api_key', 'created_at', 'user']
        read_only_fields = ['id', 'created_at', 'user']

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'user', 'company_name', 'contact_email', 'created_at']
        read_only_fields = ['id', 'created_at']
