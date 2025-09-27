from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication, BasicAuthentication
from rest_framework.response import Response
from rest_framework import status
from .models import Customer, Device, SensorConfiguration, SensorData, SensorType
from .serializers import DeviceSerializer, SensorDataSerializer
from .forms import SensorDataForm
from rest_framework.authtoken.models import Token

# ==================== CUSTOMER AUTH ====================

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

# ==================== CUSTOMER UI VIEWS ====================

@login_required
def customer_dashboard(request):
    customer = get_object_or_404(Customer, user=request.user)
    devices = Device.objects.filter(customer=customer, is_active=True)
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
def customer_dashboard_uuid(request, dashboard_uuid):
    customer = get_object_or_404(Customer, dashboard_url=dashboard_uuid, user=request.user)
    devices = Device.objects.filter(customer=customer, is_active=True)

    context = {
        'customer': customer,
        'devices': devices,
        'dashboard_uuid': dashboard_uuid
    }
    return render(request, 'api/customer_dashboard.html', context)

import json
from collections import defaultdict

def device_detail(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    sensor_readings = SensorData.objects.filter(device=device).order_by('-created_at')[:50]

    # Group readings by sensor_label
    sensor_data = defaultdict(list)
    for r in sensor_readings:
        sensor_data[r.sensor_config.sensor_label].append({
            "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "value": r.value
        })

    context = {
        "device": device,
        "sensor_readings": sensor_readings,
        "sensor_data_json": json.dumps(sensor_data)  # <-- pass as string
    }
    return render(request, 'api/device_detail.html', context)

@login_required
def device_detail_ui(request, device_id):
    """Alias for UI graph view"""
    return device_detail(request, device_id)

@login_required
def add_sensor_data(request):
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
    customer = get_object_or_404(Customer, user=request.user)
    devices = Device.objects.filter(customer=customer, is_active=True)
    configs = SensorConfiguration.objects.filter(device__in=devices)
    return render(request, 'api/sensor_configurations.html', {
        'configs': configs,
        'devices': devices
    })

# ==================== API ENDPOINTS ====================

@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def write_data(request, device_id):
    """Write sensor data from IoT device"""
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header:
        return Response({"error": "Authorization header required"}, status=status.HTTP_401_UNAUTHORIZED)
    auth_key = auth_header.split(' ')[-1]

    try:
        device = Device.objects.get(id=device_id, write_api_key=auth_key, is_active=True)
    except Device.DoesNotExist:
        return Response({"error": "Invalid device or API key"}, status=status.HTTP_401_UNAUTHORIZED)

    created_data = []
    for sensor_label, value in request.data.items():
        if value in [None, "null", "None", ""]:
            continue
        sensor_config, _ = SensorConfiguration.objects.get_or_create(
            device=device,
            sensor_label=sensor_label,
            defaults={
                'sensor_type': SensorType.objects.get_or_create(name='Generic', defaults={'unit':'units'})[0]
            }
        )
        d = SensorData.objects.create(device=device, sensor_config=sensor_config, value=float(value))
        created_data.append(d)

    return Response([{
        'id': d.id,
        'device': d.device.id,
        'sensor_label': d.sensor_config.sensor_label,
        'value': d.value,
        'created_at': d.created_at.isoformat()
    } for d in created_data], status=status.HTTP_201_CREATED if created_data else status.HTTP_400_BAD_REQUEST)

@login_required
def customer_dashboard_data(request, dashboard_uuid):
    """Return chart-ready time series for all devices in a dashboard"""
    customer = get_object_or_404(Customer, user=request.user, dashboard_url=dashboard_uuid)
    devices = Device.objects.filter(customer=customer, is_active=True)
    dashboard_data = []

    for device in devices:
        readings = SensorData.objects.filter(device=device).order_by('-created_at')[:200]
        sensor_data = {}
        for r in readings:
            label = r.sensor_config.sensor_label
            if label not in sensor_data:
                sensor_data[label] = []
            sensor_data[label].append({
                'timestamp': r.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'value': r.value
            })
        for label in sensor_data:
            sensor_data[label].sort(key=lambda x: x['timestamp'])

        dashboard_data.append({
            'device_id': device.id,
            'device_name': device.name,
            'sensor_data': sensor_data
        })

    return Response({
        'customer': customer.company_name,
        'dashboard_uuid': str(customer.dashboard_url),
        'devices': dashboard_data
    })

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def customer_devices_data(request, dashboard_uuid):
    customer = get_object_or_404(Customer, dashboard_url=dashboard_uuid, user=request.user)
    devices = Device.objects.filter(customer=customer, is_active=True)
    data = []
    for device in devices:
        latest_data = SensorData.objects.filter(device=device).order_by('-created_at')[:10]
        data.append({
            'id': device.id,
            'name': device.name,
            'latest_readings': SensorDataSerializer(latest_data, many=True).data,
        })
    return Response(data)

@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def get_sensor_data(request, device_id):
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header:
        return Response({"error": "Authorization header required"}, status=status.HTTP_401_UNAUTHORIZED)
    auth_key = auth_header.split(' ')[-1]
    try:
        device = Device.objects.get(id=device_id, read_api_key=auth_key, is_active=True)
    except Device.DoesNotExist:
        return Response({"error": "Invalid device or API key"}, status=status.HTTP_401_UNAUTHORIZED)

    sensor_data = {}
    readings = SensorData.objects.filter(device=device).order_by('-created_at')
    for r in readings:
        label = r.sensor_config.sensor_label
        if label not in sensor_data:
            sensor_data[label] = []
        sensor_data[label].append({
            'id': r.id,
            'value': r.value,
            'created_at': r.created_at.isoformat()
        })

    return Response(sensor_data)

# ==================== DEVICE MANAGEMENT API ====================

@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def device_list(request):
    if request.method == 'GET':
        devices = Device.objects.filter(customer__user=request.user)
        serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data)
    else:
        serializer = DeviceSerializer(data=request.data)
        if serializer.is_valid():
            customer = get_object_or_404(Customer, user=request.user)
            serializer.save(customer=customer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def device_detail_api(request, device_id):
    device = get_object_or_404(Device, id=device_id, customer__user=request.user)
    if request.method == 'GET':
        serializer = DeviceSerializer(device)
        readings = SensorData.objects.filter(device=device).order_by('-created_at')[:200]
        sensor_data = {}
        for r in readings:
            label = r.sensor_config.sensor_label
            if label not in sensor_data:
                sensor_data[label] = []
            sensor_data[label].append({
                'timestamp': r.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'value': r.value
            })
        for label in sensor_data:
            sensor_data[label].sort(key=lambda x: x['timestamp'])
        return Response({'device': serializer.data, 'sensor_data': sensor_data})
    elif request.method == 'PUT':
        serializer = DeviceSerializer(device, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        device.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# ==================== API KEY MANAGEMENT ====================

@api_view(['POST'])
@authentication_classes([TokenAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def create_apikey(request):
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
    try:
        token = Token.objects.get(user=request.user)
        return Response({'token': token.key, 'user': request.user.username})
    except Token.DoesNotExist:
        return Response({'error': 'No API token found', 'message': 'Use /api/create_apikey/ to create one'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_apikey(request):
    try:
        token = Token.objects.get(user=request.user)
        token.delete()
        return Response({'message': 'API token deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    except Token.DoesNotExist:
        return Response({'error': 'No API token found for user'}, status=status.HTTP_404_NOT_FOUND)

# ==================== CUSTOMER DEVICES API ====================

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def customer_devices(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id, user=request.user)
    devices = Device.objects.filter(customer=customer)
    serializer = DeviceSerializer(devices, many=True)
    return Response(serializer.data)

