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
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout

# Custom authentication function for device API keys
def customer_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            try:
                customer = Customer.objects.get(user=user)
                return redirect("customer_dashboard_ui", dashboard_uuid=customer.dashboard_url)
            except Customer.DoesNotExist:
                return render(request, "login.html", {"error": "No customer account linked to this user"})
        else:
            return render(request, "login.html", {"error": "Invalid username or password"})
    return render(request, "login.html")


def customer_logout(request):
    logout(request)
    return redirect("customer_login")
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

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import Device, SensorConfiguration, SensorType, SensorData


from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from .models import Device, SensorConfiguration, SensorType, SensorData

@api_view(['POST'])
@permission_classes([AllowAny])         # allow POST without Django login
@authentication_classes([])             # disable default TokenAuthentication
def write_data(request, device_id):
    """Write sensor data from IoT device using its write API key"""

    # --- Step 1: Validate API Key ---
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header:
        return Response({"error": "Authorization header required"}, status=status.HTTP_401_UNAUTHORIZED)

    if ' ' in auth_header:
        _, auth_key = auth_header.split(' ', 1)
    else:
        auth_key = auth_header

    try:
        device = Device.objects.get(
            id=device_id,
            write_api_key=auth_key,
            is_active=True
        )
    except Device.DoesNotExist:
        return Response({"error": "Invalid device or API key"}, status=status.HTTP_401_UNAUTHORIZED)

    # --- Step 2: Process sensor values ---
    data = request.data
    created_data = []

    for sensor_label, value in data.items():
        # Skip null / missing values
        if value in [None, "null", "None", ""]:
            continue

        try:
            # Get or create sensor config
            try:
                sensor_config = SensorConfiguration.objects.get(
                    device=device,
                    sensor_label=sensor_label
                )
            except SensorConfiguration.DoesNotExist:
                # Detect sensor type by prefix
                if sensor_label.upper().startswith('T'):
                    unit = '°C'; sensor_type_name = 'Temperature'
                elif sensor_label.upper().startswith('P'):
                    unit = 'kPa'; sensor_type_name = 'Pressure'
                elif sensor_label.upper().startswith('F'):
                    unit = 'L/min'; sensor_type_name = 'Flow'
                else:
                    unit = 'units'; sensor_type_name = 'Generic'

                sensor_type, _ = SensorType.objects.get_or_create(
                    name=sensor_type_name,
                    defaults={'unit': unit, 'description': f'Auto-created for {sensor_label}'}
                )

                sensor_config = SensorConfiguration.objects.create(
                    device=device,
                    sensor_type=sensor_type,
                    sensor_label=sensor_label
                )

            # Create sensor data row
            sensor_data = SensorData.objects.create(
                device=device,
                sensor_config=sensor_config,
                value=float(value)
            )
            created_data.append(sensor_data)

        except Exception as e:
            print(f"⚠️ Error saving data for {sensor_label}: {e}")
            continue

    # --- Step 3: Return response ---
    if created_data:
        response_data = [{
            'id': d.id,
            'device': d.device.id,
            'sensor_label': d.sensor_config.sensor_label,
            'value': d.value,
            'created_at': d.created_at.isoformat()
        } for d in created_data]

        return Response(response_data, status=status.HTTP_201_CREATED)
    else:
        return Response({"error": "No valid sensor data received"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@login_required
def customer_dashboard_data(request, dashboard_uuid):
    """
    Returns all devices + latest sensor values for a specific customer dashboard.
    Ensures only the logged-in customer's data is returned.
    """
    try:
        customer = Customer.objects.get(user=request.user, dashboard_url=dashboard_uuid)
    except Customer.DoesNotExist:
        return Response({"error": "Unauthorized or invalid dashboard"}, status=status.HTTP_403_FORBIDDEN)

    devices = Device.objects.filter(customer=customer, is_active=True)
    dashboard_data = []

    for device in devices:
        sensors_data = {}
        for config in SensorConfiguration.objects.filter(device=device):
            last_value = SensorData.objects.filter(device=device, sensor_config=config).order_by('-created_at').first()
            if last_value:
                sensors_data[config.sensor_label] = {
                    "value": last_value.value,
                    "created_at": last_value.created_at.isoformat()
                }

        dashboard_data.append({
            "device_id": device.id,
            "device_name": device.name,
            "sensors": sensors_data
        })

    return Response({
        "customer": customer.company_name,
        "dashboard_uuid": str(customer.dashboard_url),
        "devices": dashboard_data
    }, status=status.HTTP_200_OK)



@api_view(['GET'])
@authentication_classes([])  
@permission_classes([])     
def read_data(request, device_id):
    """Read latest sensor values for a device using its read API key"""
    # Get Authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')

    if not auth_header:
        return Response({"error": "Authorization header required"}, status=status.HTTP_401_UNAUTHORIZED)

    # Extract key
    if ' ' in auth_header:
        _, auth_key = auth_header.split(' ', 1)
    else:
        auth_key = auth_header

    # Validate device + read key
    try:
        device = Device.objects.get(
            id=device_id,
            read_api_key=auth_key,
            is_active=True
        )
    except Device.DoesNotExist:
        return Response({"error": "Invalid device or API key"}, status=status.HTTP_401_UNAUTHORIZED)

    # Collect latest sensor values per label
    latest_data = {}
    sensor_configs = SensorConfiguration.objects.filter(device=device)

    for config in sensor_configs:
        last_value = SensorData.objects.filter(device=device, sensor_config=config).order_by('-created_at').first()
        if last_value:
            latest_data[config.sensor_label] = {
                "value": last_value.value,
                "created_at": last_value.created_at.isoformat()
            }

    return Response({
        "device_id": device.id,
        "device_name": device.name,
        "sensors": latest_data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def get_sensor_data(request, device_id):
    """Get all sensor data for a device using read API key"""
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')

    if not auth_header:
        return Response({"error": "Authorization header required"}, status=status.HTTP_401_UNAUTHORIZED)

    if ' ' in auth_header:
        _, auth_key = auth_header.split(' ', 1)
    else:
        auth_key = auth_header

    try:
        device = Device.objects.get(
            id=device_id,
            read_api_key=auth_key,
            is_active=True
        )
    except Device.DoesNotExist:
        return Response({"error": "Invalid device or API key"}, status=status.HTTP_401_UNAUTHORIZED)

    # Group sensor data per label
    sensor_data = SensorData.objects.filter(device=device).order_by('-created_at')

    response_data = {}
    for data in sensor_data:
        label = data.sensor_config.sensor_label
        if label not in response_data:
            response_data[label] = []
        response_data[label].append({
            "id": data.id,
            "value": data.value,
            "created_at": data.created_at.isoformat()
        })

    return Response(response_data, status=status.HTTP_200_OK)

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
    """Manage specific device (API version) including latest sensor data"""
    try:
        # Ensure the device belongs to the logged-in customer
        device = Device.objects.get(id=device_id, customer__user=request.user)
    except Device.DoesNotExist:
        return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # Serialize the device
        device_serializer = DeviceSerializer(device)

        # Get the latest 50 sensor readings for this device
        sensor_readings = device.sensor_data.all()[:50]  # using related_name 'sensor_data'
        sensor_serializer = SensorDataSerializer(sensor_readings, many=True)

        # Combine device and sensor data in one response
        return Response({
            "device": device_serializer.data,
            "sensor_data": sensor_serializer.data
        })

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
        customer = Customer.objects.get(user=request.user,dashboard_url=dashboard_uuid)
        devices = Device.objects.filter(customer=customer)
        serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data)
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
def dashboard_view(request, dashboard_uuid):
    return render(request, 'dashboard.html', {'dashboard_uuid': dashboard_uuid})


@login_required
def device_detail(request, device_id):
    try:
        device = Device.objects.get(id=device_id, customer__user=request.user)
    except Device.DoesNotExist:
        return render(request, 'api/device_detail.html', {'error': 'Device not found'})

    # Get last 50 readings for each sensor for better performance
    readings = SensorData.objects.filter(device=device).order_by('-created_at')[:200]

    # Group readings by sensor label and sort by time ascending
    sensor_data = {}
    for r in readings:
        label = r.sensor_config.sensor_label
        if label not in sensor_data:
            sensor_data[label] = []
        sensor_data[label].append({
            'timestamp': r.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'value': r.value
        })

    # Sort each sensor data by timestamp ascending
    for label in sensor_data:
        sensor_data[label].sort(key=lambda x: x['timestamp'])

    context = {
        'device': device,
        'sensor_data': sensor_data,  # for Chart.js
        'sensor_readings': readings,  # for textual list if needed
    }
    return render(request, 'api/device_detail.html', context)

