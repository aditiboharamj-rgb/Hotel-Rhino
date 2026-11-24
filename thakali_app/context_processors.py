import os
from .models import PushNotification
from django.conf import settings

def restaurant_settings(request):
    active_notifications = PushNotification.objects.filter(is_active=True)
    pinned_notification = active_notifications.filter(is_pinned_banner=True).first()

    # Dynamic logo support: check uploaded media first, otherwise default static
    uploaded_logo_path = os.path.join(settings.MEDIA_ROOT, 'brand_logo.png')
    if os.path.exists(uploaded_logo_path):
        mtime = int(os.path.getmtime(uploaded_logo_path))
        restaurant_logo_url = f"{settings.MEDIA_URL}brand_logo.png?v={mtime}"
    else:
        static_logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'hotel_rhino_logo.png')
        mtime = int(os.path.getmtime(static_logo_path)) if os.path.exists(static_logo_path) else 1
        restaurant_logo_url = f"/static/images/hotel_rhino_logo.png?v={mtime}"

    return {
        'RESTAURANT_NAME': os.getenv('RESTAURANT_NAME', 'Hotel Raino - Authentic Thakali Kitchen'),
        'RESTAURANT_LOGO_URL': restaurant_logo_url,
        'RESTAURANT_LOCATION': os.getenv('RESTAURANT_LOCATION', 'Main Road, Dhangadhi, Sudurpaschim Province, Nepal'),
        'RESTAURANT_PHONE': os.getenv('RESTAURANT_PHONE', '+977-9715003003'),
        'RESTAURANT_WHATSAPP': os.getenv('RESTAURANT_WHATSAPP', '+977-9715003003'),
        'RESTAURANT_EMAIL': os.getenv('RESTAURANT_EMAIL', 'info@hotelrainothakali.com'),
        'CURRENCY': os.getenv('CURRENCY', 'NPR'),
        'VAT_PERCENTAGE': float(os.getenv('VAT_PERCENTAGE', 13.0)),
        'SERVICE_CHARGE_PERCENTAGE': float(os.getenv('SERVICE_CHARGE_PERCENTAGE', 10.0)),
        'VAPID_PUBLIC_KEY': os.getenv('VAPID_PUBLIC_KEY', ''),
        'STAFF_USER': request.user if request.user.is_authenticated else None,
        'STAFF_ROLE': getattr(getattr(request.user, 'staff_profile', None), 'role', None) if request.user.is_authenticated else None,
        'ACTIVE_NOTIFICATIONS': active_notifications,
        'PINNED_NOTIFICATION': pinned_notification,
    }

