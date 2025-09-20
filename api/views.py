from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import SensorData, Device, Customer
from .serializers import SensorDataSerializer, DeviceSerializer, CustomerSerializer
from rest_framework.authtoken.models import Token
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

# Custom authentication function for device API keys
def authenticate_device_api_key(request, device_id, key_type='write'):
    """
    Authenticate using device API key
    key_type: 'write' for write_api_key, 'read' for read_api_key
    """
    try:
        device = Device.objects.get(id=device_id)
    except Device.DoesNotExist:
        return None, Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

    # Get the authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    
    if not auth_header:
        return None, Response({"error": "Authorization header required"}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Extract the key (remove any prefix like "Bearer" or "Token")
    if ' ' in auth_header:
        auth_key = auth_header.split(' ')[1]  # Get the part after the space
    else:
        auth_key = auth_header  # Use the whole header if no space

    # Validate the API key based on type
    if key_type == 'write' and auth_key == device.write_api_key:
        return device, None
    elif key_type == 'read' and auth_key == device.read_api_key:
        return device, None
    else:
        return None, Response({"error": "Invalid API key"}, status=status.HTTP_401_UNAUTHORIZED)

@login_required
def customer_dashboard(request, dashboard_uuid):
    # Verify customer owns this dashboard
    customer = get_object_or_404(Customer, dashboard_url=dashboard_uuid, user=request.user)
    devices = Device.objects.filter(customer=customer, is_active=True)

    context = {
        'customer': customer,
        'devices': devices,
        'dashboard_uuid': dashboard_uuid
    }

    return render(request, 'dashboard/customer_dashboard.html', context)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def customer_devices_data(request, dashboard_uuid):
    # API endpoint for dashboard data
    customer = get_object_or_404(Customer, dashboard_url=dashboard_uuid, user=request.user)
    devices = Device.objects.filter(customer=customer, is_active=True)
    data = []

    for device in devices:
        latest_data = SensorData.objects.filter(device=device).order_by('-created_at')[:10]
        device_data = {
            'id': device.id,
            'name': device.name,
            'latest_readings': SensorDataSerializer(latest_data, many=True).data,
        }
        data.append(device_data)

    return Response(data)

@api_view(['POST'])
def write_data(request, device_id):
    """Write sensor data using device write API key"""
    device, error_response = authenticate_device_api_key(request, device_id, 'write')
    if error_response:
        return error_response

    serializer = SensorDataSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(device=device)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def read_data(request, device_id):
    """Read sensor data using device read API key"""
    device, error_response = authenticate_device_api_key(request, device_id, 'read')
    if error_response:
        return error_response

    limit = request.GET.get('limit', 100)
    sensor_data = SensorData.objects.filter(device=device).order_by('-created_at')[:int(limit)]
    serializer = SensorDataSerializer(sensor_data, many=True)
    return Response(serializer.data)

# Keep the original get_sensor_data function for backward compatibility
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_sensor_data(request, device_id):
    """Get sensor data (requires user authentication) - Legacy function"""
    try:
        device = Device.objects.get(id=device_id, user=request.user)
    except Device.DoesNotExist:
        return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

    limit = request.GET.get('limit', 100)
    sensor_data = SensorData.objects.filter(device=device).order_by('-created_at')[:int(limit)]
    serializer = SensorDataSerializer(sensor_data, many=True)
    return Response(serializer.data)

@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def device_list(request):
    """Manage devices (requires user authentication)"""
    if request.method == 'GET':
        devices = Device.objects.filter(user=request.user)
        serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = DeviceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def device_detail(request, device_id):
    """Manage specific device (requires user authentication)"""
    try:
        device = Device.objects.get(id=device_id, user=request.user)
    except Device.DoesNotExist:
        return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = DeviceSerializer(device)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = DeviceSerializer(device, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        device.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_apikey(request):
    """Create or get API token for authenticated user"""
    token, created = Token.objects.get_or_create(user=request.user)
    return Response({
        'token': token.key,
        'created': created,
        'message': 'New token created' if created else 'Existing token retrieved'
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_apikey(request):
    """Get API token for authenticated user"""
    try:
        token = Token.objects.get(user=request.user)
        return Response({
            'token': token.key,
            'user': request.user.username
        })
    except Token.DoesNotExist:
        return Response({
            'error': 'No API token found for user',
            'message': 'Use /api/create_apikey/ to create one'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_apikey(request):
    """Delete API token for authenticated user"""
    try:
        token = Token.objects.get(user=request.user)
        token.delete()
        return Response({
            'message': 'API token deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)
    except Token.DoesNotExist:
        return Response({
            'error': 'No API token found for user'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def customer_devices(request, customer_id):
    """Get all devices for a specific customer"""
    try:
        customer = Customer.objects.get(id=customer_id, user=request.user)
        devices = Device.objects.filter(user=customer.user)
        serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data)
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
