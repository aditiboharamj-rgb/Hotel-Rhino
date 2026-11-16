import os

def restaurant_settings(request):
    return {
        'RESTAURANT_NAME': os.getenv('RESTAURANT_NAME', 'Hotel Rhino - Authentic Thakali Kitchen'),
        'RESTAURANT_LOCATION': os.getenv('RESTAURANT_LOCATION', 'Main Road, Dhangadhi, Sudurpaschim Province, Nepal'),
        'RESTAURANT_PHONE': os.getenv('RESTAURANT_PHONE', '+977-9801234567'),
        'RESTAURANT_WHATSAPP': os.getenv('RESTAURANT_WHATSAPP', '+977-9801234567'),
        'RESTAURANT_EMAIL': os.getenv('RESTAURANT_EMAIL', 'info@hotelrhinothakali.com'),
        'CURRENCY': os.getenv('CURRENCY', 'NPR'),
        'VAT_PERCENTAGE': float(os.getenv('VAT_PERCENTAGE', 13.0)),
        'SERVICE_CHARGE_PERCENTAGE': float(os.getenv('SERVICE_CHARGE_PERCENTAGE', 10.0)),
        'VAPID_PUBLIC_KEY': os.getenv('VAPID_PUBLIC_KEY', ''),
        'STAFF_USER': request.user if request.user.is_authenticated else None,
        'STAFF_ROLE': getattr(getattr(request.user, 'staff_profile', None), 'role', None) if request.user.is_authenticated else None,
    }

