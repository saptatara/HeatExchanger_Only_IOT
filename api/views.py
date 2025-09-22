from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from .models import SensorData, Device, Customer, SensorConfiguration
from .serializers import SensorDataSerializer, DeviceSerializer, CustomerSerializer
from rest_framework.authtoken.models import Token
from django.http import JsonResponse
from .forms import SensorDataForm
from .authentication import DeviceAuthentication

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
        auth_type, auth_key = auth_header.split(' ', 1)
    else:
        auth_key = auth_header
        
    # Validate the API key based on type
    if key_type == 'write' and auth_key == device.write_api_key:
        return device, None
    elif key_type == 'read' and auth_key == device.read_api_key:
        return device, None
    else:
        return None, Response({"error": "Invalid API key"}, status=status.HTTP_401_UNAUTHORIZED)

# ==================== CUSTOMER UI VIEWS ====================

@login_required
def customer_dashboard(request):
    """Dashboard for customer to see their devices and data"""
    # Get customer for this user
    customer = get_object_or_404(Customer, user=request.user)
    devices = Device.objects.filter(customer=customer, is_active=True)
    
    # Get recent sensor data
    recent_data = []
    for device in devices:
        data = SensorData.objects.filter(device=device).order_by('-created_at')[:5]
        recent_data.extend(data)
    
    return render(request, 'api/customer_dashboard.html', {
        'customer': customer,
        'devices': devices,
        'recent_data': recent_data
    })

@login_required
def device_detail_ui(request, device_id):
    """Detailed view for a specific device (UI version)"""
    customer = get_object_or_404(Customer, user=request.user)
    device = get_object_or_404(Device, id=device_id, customer=customer)
    
    # Get sensor data with config details
    sensor_data = SensorData.objects.filter(device=device).select_related(
        'sensor_config', 'sensor_config__sensor_type'
    ).order_by('-created_at')[:100]
    
    return render(request, 'api/device_detail.html', {
        'device': device,
        'sensor_data': sensor_data
    })

@login_required
def add_sensor_data(request):
    """Form to manually add sensor data (customer-specific)"""
    customer = get_object_or_404(Customer, user=request.user)
    
    if request.method == 'POST':
        form = SensorDataForm(customer, request.POST)
        if form.is_valid():
            form.save()
            return redirect('customer_dashboard')
    else:
        form = SensorDataForm(customer)
    
    return render(request, 'api/add_sensor_data.html', {'form': form})

@login_required
def sensor_configurations(request):
    """Manage sensor configurations for customer's devices"""
    customer = get_object_or_404(Customer, user=request.user)
    devices = Device.objects.filter(customer=customer, is_active=True)
    configs = SensorConfiguration.objects.filter(device__in=devices)
    
    return render(request, 'api/sensor_configurations.html', {
        'configs': configs,
        'devices': devices
    })

@login_required
def customer_dashboard_uuid(request, dashboard_uuid):
    """Legacy dashboard view with UUID"""
    customer = get_object_or_404(Customer, dashboard_url=dashboard_uuid, user=request.user)
    devices = Device.objects.filter(customer=customer, is_active=True)
    
    context = {
        'customer': customer,
        'devices': devices,
        'dashboard_uuid': dashboard_uuid
    }
    return render(request, 'dashboard/customer_dashboard.html', context)

# ==================== API ENDPOINTS ====================

@api_view(['POST'])
def write_data(request, device_id):
    """Write sensor data using device write API key"""
    # Get the authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    
    if not auth_header:
        return Response({"error": "Authorization header required"}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Extract the key (remove any prefix like "Bearer" or "Token")
    if ' ' in auth_header:
        auth_type, auth_key = auth_header.split(' ', 1)
    else:
        auth_key = auth_header
    
    # Try to find the device with this API key
    try:
        device = Device.objects.get(
            id=device_id,
            write_api_key=auth_key,
            is_active=True
        )
    except Device.DoesNotExist:
        return Response({"error": "Invalid device or API key"}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Handle the request data
    data = request.data
    
    # Create sensor data for each field
    created_data = []
    for sensor_label, value in data.items():
        try:
            # Try to get existing sensor configuration
            sensor_config = SensorConfiguration.objects.get(
                device=device,
                sensor_label=sensor_label
            )
        except SensorConfiguration.DoesNotExist:
            # Create a new sensor configuration if it doesn't exist
            try:
                # Try to determine sensor type from label
                if sensor_label.startswith('T'):
                    unit = '°C'
                    sensor_type_name = 'Temperature'
                elif sensor_label.startswith('P'):
                    unit = 'kPa'
                    sensor_type_name = 'Pressure'
                elif sensor_label.startswith('F'):
                    unit = 'L/min'
                    sensor_type_name = 'Flow'
                else:
                    unit = 'units'
                    sensor_type_name = 'Generic'
                
                sensor_type, created = SensorType.objects.get_or_create(
                    name=sensor_type_name,
                    defaults={'unit': unit, 'description': f'Auto-created for {sensor_label}'}
                )
                
                sensor_config = SensorConfiguration.objects.create(
                    device=device,
                    sensor_type=sensor_type,
                    sensor_label=sensor_label
                )
            except Exception as e:
                print(f"Error creating sensor config for {sensor_label}: {e}")
                continue
        
        # Create the sensor data entry
        try:
            sensor_data = SensorData.objects.create(
                device=device,
                sensor_config=sensor_config,
                value=float(value)
            )
            created_data.append(sensor_data)
        except Exception as e:
            print(f"Error creating sensor data for {sensor_label}: {e}")
            continue

    if created_data:
        # Use a simple serializer or just return basic info
        response_data = [{
            'id': data.id,
            'device': data.device.id,
            'sensor_label': data.sensor_config.sensor_label,
            'value': data.value,
            'created_at': data.created_at.isoformat()
        } for data in created_data]
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    else:
        return Response({"error": "No valid sensor data received"}, status=status.HTTP_400_BAD_REQUEST)

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

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_sensor_data(request, device_id):
    """Get sensor data (requires user authentication)"""
    try:
        device = Device.objects.get(id=device_id, customer__user=request.user)
    except Device.DoesNotExist:
        return Response({"error": "Device not found or you don't have permission"}, status=status.HTTP_404_NOT_FOUND)

    limit = request.GET.get('limit', 100)
    sensor_data = SensorData.objects.filter(device=device).order_by('-created_at')[:int(limit)]
    serializer = SensorDataSerializer(sensor_data, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def customer_devices_data(request, dashboard_uuid):
    """API endpoint for dashboard data"""
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

# ==================== DEVICE MANAGEMENT API ====================

@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def device_list(request):
    """Manage devices (requires user authentication)"""
    if request.method == 'GET':
        devices = Device.objects.filter(customer__user=request.user)
        serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = DeviceSerializer(data=request.data)
        if serializer.is_valid():
            # Automatically assign to customer
            customer = get_object_or_404(Customer, user=request.user)
            serializer.save(customer=customer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def device_detail_api(request, device_id):
    """Manage specific device (API version)"""
    try:
        device = Device.objects.get(id=device_id, customer__user=request.user)
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

# ==================== AUTHENTICATION API ====================

@api_view(['POST'])
@authentication_classes([TokenAuthentication, BasicAuthentication])
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
        devices = Device.objects.filter(customer=customer)
        serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data)
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
