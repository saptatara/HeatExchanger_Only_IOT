import json
import secrets
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from .models import Customer, Device, ApiKey, SensorData

def _validate_apikey(apikey):
    try:
        return ApiKey.objects.get(key=apikey)
    except ApiKey.DoesNotExist:
        return None

@csrf_exempt
def write_data(request):
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')
    try:
        payload = json.loads(request.body)
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')
    apikey = payload.get('apikey') or request.headers.get('X-API-KEY')
    if not apikey:
        return HttpResponseForbidden('API key required')
    key_obj = _validate_apikey(apikey)
    if not key_obj:
        return HttpResponseForbidden('Invalid API key')

    device_id = payload.get('device_id')
    if not device_id:
        return HttpResponseBadRequest('device_id required')
    data = payload.get('data')
    if data is None:
        return HttpResponseBadRequest('data payload required')

    device, _ = Device.objects.get_or_create(device_id=device_id, defaults={'customer': key_obj.customer})

    sd = SensorData.objects.create(device=device, data=data)
    return JsonResponse({'status':'ok','id': sd.id, 'timestamp': sd.timestamp.isoformat()})

def read_data(request):
    device_id = request.GET.get('device')
    if not device_id:
        return HttpResponseBadRequest('device param required')
    try:
        device = Device.objects.get(device_id=device_id)
    except Device.DoesNotExist:
        return HttpResponseBadRequest('device not found')
    limit = int(request.GET.get('limit', 100))
    qs = SensorData.objects.filter(device=device).order_by('-timestamp')[:limit]
    results = [ {'timestamp': s.timestamp.isoformat(), 'data': s.data} for s in qs ]
    return JsonResponse({'device': device_id, 'count': len(results), 'results': results})

def create_apikey(request):
    customer_slug = request.GET.get('customer')
    if not customer_slug:
        return HttpResponseBadRequest('customer slug required, e.g. ?customer=acme')
    customer, _ = Customer.objects.get_or_create(slug=customer_slug, defaults={'name': customer_slug})
    key = secrets.token_hex(16)
    ak = ApiKey.objects.create(customer=customer, key=key, label=f'key-{customer_slug}')
    return JsonResponse({'key': ak.key, 'customer': customer.slug})
