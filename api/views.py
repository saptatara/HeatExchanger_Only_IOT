from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import uuid
from .models import Customer, ApiKey, Device, SensorData

# -------------------------
# Create API key endpoint
# -------------------------
@csrf_exempt
def create_apikey(request):
    """Create an API key for an existing customer."""
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            customer_id = data.get("customer_id")
            customer = Customer.objects.get(id=customer_id)
            key = ApiKey.objects.create(customer=customer, key=str(uuid.uuid4()))
            return JsonResponse({"customer": customer.name, "api_key": key.key})
        except Customer.DoesNotExist:
            return JsonResponse({"error": "Customer not found"}, status=404)
    return JsonResponse({"error": "POST required"}, status=405)

# -------------------------
# Write sensor data
# -------------------------
@csrf_exempt
def write_data(request, device_id):
    """Write sensor data for a device."""
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            api_key = data.get("api_key")
            temperature = data.get("temperature")
            pressure = data.get("pressure")

            if not ApiKey.objects.filter(key=api_key).exists():
                return JsonResponse({"error": "Invalid API Key"}, status=403)

            device = Device.objects.get(id=device_id)
            SensorData.objects.create(device=device, temperature=temperature, pressure=pressure)

            return JsonResponse({"status": "success", "message": "Data saved"})
        except Device.DoesNotExist:
            return JsonResponse({"error": "Device not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "POST required"}, status=405)

# -------------------------
# Read sensor data
# -------------------------
def read_data(request, device_id):
    """Read sensor data for a device."""
    try:
        device = Device.objects.get(id=device_id)
        data = SensorData.objects.filter(device=device).order_by("-timestamp")[:20]

        readings = [
            {"timestamp": d.timestamp, "temperature": d.temperature, "pressure": d.pressure}
            for d in data
        ]

        return JsonResponse({"device": device.name, "readings": readings})
    except Device.DoesNotExist:
        return JsonResponse({"error": "Device not found"}, status=404)
