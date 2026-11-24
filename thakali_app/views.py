import os
import json
import csv
from datetime import datetime, date, timedelta
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Sum, Count, Q, Avg
from django.db import models, transaction
from django.contrib import messages
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table as ReportTable, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from .models import (
    StaffProfile, RestaurantTable, TableSession, KhanaSet,
    Customer, Order, OrderItem, Bill, Payment,
    CustomerServiceRequest, TableReservation, CustomerReview, PushNotification, AuditLog
)

# Honeypot: Blocked /admin/ path
def blocked_admin_honeypot_view(request, subpath=None):
    ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
    AuditLog.objects.create(
        user=request.user if getattr(request.user, 'is_authenticated', False) else None,
        action='BLOCKED_ADMIN_PROBE',
        details=f"Unauthorized probe on /admin/{subpath or ''} from IP {ip}",
        ip_address=ip
    )
    from django.http import Http404
    raise Http404("Page not found. Admin has been relocated to secure credentials.")

# Helper: Log user audit actions
def log_audit(user, action, details, request=None):
    ip = None
    if request:
        ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
    AuditLog.objects.create(user=user if getattr(user, 'is_authenticated', False) else None, action=action, details=details, ip_address=ip)

# Helper: Check Staff Role Access
def get_user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'ADMIN'
    if hasattr(user, 'staff_profile'):
        return user.staff_profile.role
    return 'WAITER'

# ==========================================
# PUBLIC CUSTOMER PAGES
# ==========================================

def home_view(request):
    featured_sets = KhanaSet.objects.filter(is_enabled_by_admin=True, is_available=True, is_featured=True)[:6]
    hero_thakali_set = featured_sets.first() if featured_sets.exists() else None
    reviews = CustomerReview.objects.filter(is_approved=True)[:6]
    return render(request, 'public/home.html', {
        'featured_sets': featured_sets,
        'hero_thakali_set': hero_thakali_set,
        'reviews': reviews,
    })

def khana_sets_view(request):
    sets = KhanaSet.objects.filter(is_enabled_by_admin=True)
    return render(request, 'public/khana_sets.html', {
        'khana_sets': sets,
    })

def whats_inside_thali_view(request):
    thali_items = [
        {
            'name': 'Jimbu Mustang Black Dal',
            'nepali': 'मुस्ताङको कालो दाल (जिम्बु झानेको)',
            'description': 'Slow-cooked Himalayan organic black lentils hand-tempered in mountain Jimbu (allium hypsistum) and golden yak butter ghee.',
            'category': 'Essential Pulse',
            'icon': '🍲'
        },
        {
            'name': 'Steamed Fragrant Rice (Bhat)',
            'nepali': 'सुगन्धित बासमती / मार्सि भात',
            'description': 'Steaming hot, fluffy long-grain rice infused with subtle aroma, served piping hot with generous spoonfuls of molten ghee.',
            'category': 'Carbohydrate Staple',
            'icon': '🍚'
        },
        {
            'name': 'Organic Rayo ko Saag',
            'nepali': 'ताजा रायोको साग',
            'description': 'Fresh mountain broadleaf mustard greens sautéed lightly with fenugreek seeds, mustard oil, and dried whole red chilies.',
            'category': 'Greens',
            'icon': '🥬'
        },
        {
            'name': 'Himalayan Mixed Tarkari',
            'nepali': 'मौसमी हिमाली तरकारी',
            'description': 'Seasonal cauliflower, green peas, and local hill potatoes prepared in rich whole cumin, coriander, and freshly pounded turmeric.',
            'category': 'Vegetable Curry',
            'icon': '🥘'
        },
        {
            'name': 'Authentic Local Kukhura Curry',
            'nepali': 'लोकल कुखुराको झोल',
            'description': 'Free-range country chicken slow-simmered in rich Himalayan spiced bone broth with cloves, cardamom, ginger, and garlic.',
            'category': 'Non-Veg Highlight',
            'icon': '🍗'
        },
        {
            'name': 'Himalayan Mountain Khasi (Mutton)',
            'nepali': 'हिमाली खसीको मासु',
            'description': 'Tender mountain goat braised in traditional brass cookware with wild Timur peppercorns and aromatic Himalayan spices.',
            'category': 'Non-Veg Highlight',
            'icon': '🍖'
        },
        {
            'name': 'Timur & Tomato Chutney',
            'nepali': 'टिमुर र गोलभेडाको अचार',
            'description': 'Fire-roasted mountain tomatoes stone-ground with tingling Sichuan/Timur pepper, green chilies, and fresh coriander.',
            'category': 'Condiment',
            'icon': '🌶️'
        },
        {
            'name': 'Fermented Gundruk Sadeko',
            'nepali': 'गुन्द्रुक साधेको',
            'description': 'Traditional sun-dried sun-fermented leafy greens tossed with roasted mustard seeds, chopped shallots, and spicy mustard oil.',
            'category': 'Heritage Ferment',
            'icon': '🥗'
        },
        {
            'name': 'Crispy Papadam & Pure Ghee',
            'nepali': 'पापड र घ्यु',
            'description': 'Sun-crisped lentil papad roasted over charcoal, topped with authentic pure cow & mountain ghee (Shingati Chyangra ghee).',
            'category': 'Crunch & Aroma',
            'icon': '🫓'
        },
    ]
    return render(request, 'public/whats_inside.html', {'thali_items': thali_items})

def our_story_view(request):
    return render(request, 'public/our_story.html')

def gallery_view(request):
    return render(request, 'public/gallery.html')

def guest_experiences_view(request):
    reviews = CustomerReview.objects.filter(is_approved=True)
    if request.method == 'POST':
        name = (request.POST.get('guest_fullname') or request.POST.get('name') or '').strip()
        phone = (request.POST.get('guest_contact_phone') or request.POST.get('phone') or '').strip()
        rating = int(request.POST.get('rating', 3))
        comment = (request.POST.get('guest_comment') or request.POST.get('comment') or '').strip()
        city = (request.POST.get('city') or 'Dhangadhi').strip()
        if name and comment:
            CustomerReview.objects.create(
                name=name, 
                phone=phone,
                rating=rating, 
                comment=comment, 
                city=city, 
                is_approved=True
            )
            messages.success(request, "Dhanyabad! Thank you for sharing your feedback with Hotel Raino.")
            return redirect('guest_experiences')
    return render(request, 'public/guest_experiences.html', {'reviews': reviews})

def visit_us_view(request):
    if request.method == 'POST':
        name = (request.POST.get('guest_fullname') or request.POST.get('name') or '').strip()
        phone = (request.POST.get('guest_contact_phone') or request.POST.get('phone') or '').strip()
        email = (request.POST.get('guest_email_address') or request.POST.get('email') or '').strip()
        guests = int(request.POST.get('guests', 2))
        res_date = request.POST.get('date')
        res_time = request.POST.get('time')
        special = (request.POST.get('special_requests') or '').strip()

        if name and phone and res_date and res_time:
            TableReservation.objects.create(
                name=name,
                phone=phone,
                email=email,
                guest_count=guests,
                reservation_date=res_date,
                reservation_time=res_time,
                special_requests=special
            )
            messages.success(request, f"Namaste {name}! Your table reservation request for {guests} guests on {res_date} at {res_time} has been received. Our team will contact you shortly.")
            return redirect('visit_us')
        else:
            messages.error(request, "Please fill in all required fields.")
    return render(request, 'public/visit_us.html')

# ==========================================
# CUSTOMER QR ORDERING & SERVICE SYSTEM
# ==========================================

def qr_table_order_view(request, qr_token):
    # Lookup table by unique unguessable UUID token
    table = get_object_or_404(RestaurantTable, qr_code_token=qr_token)
    available_sets = KhanaSet.objects.filter(is_enabled_by_admin=True, is_available=True)
    active_session = table.current_session

    recent_orders = []
    if active_session:
        recent_orders = active_session.orders.all().prefetch_related('items__khana_set')

    return render(request, 'public/qr_order.html', {
        'table': table,
        'available_sets': available_sets,
        'active_session': active_session,
        'recent_orders': recent_orders,
    })

@require_POST
def submit_qr_order_api(request, qr_token):
    table = get_object_or_404(RestaurantTable, qr_code_token=qr_token)
    try:
        data = json.loads(request.body)
        items_data = data.get('items', [])
        special_instructions = data.get('special_instructions', '').strip()
        cust_name = data.get('customer_name', '').strip()
        cust_phone = data.get('customer_phone', '').strip()

        if not items_data:
            return JsonResponse({'status': 'error', 'message': 'Please select at least one Thakali Khana set.'}, status=400)

        with transaction.atomic():
            # Check or create active table session
            session = table.current_session
            if not session:
                session = TableSession.objects.create(table=table, customer_count=len(items_data) or 2)
                table.status = 'OCCUPIED'
                table.save()

            customer = None
            if cust_phone:
                customer, _ = Customer.objects.get_or_create(phone=cust_phone, defaults={'name': cust_name})
                if cust_name and customer.name != cust_name:
                    customer.name = cust_name
                    customer.save()

            # Create Order
            order_num = f"QR-{table.table_number}-{timezone.now().strftime('%H%M%S')}"
            order = Order.objects.create(
                order_number=order_num,
                table_session=session,
                customer=customer,
                source='QR_CUSTOMER',
                status='NEW',
                special_instructions=special_instructions
            )

            for item in items_data:
                khana_id = item.get('id')
                qty = int(item.get('quantity', 1))
                if qty > 0:
                    khana = KhanaSet.objects.get(id=khana_id, is_enabled_by_admin=True, is_available=True)
                    OrderItem.objects.create(
                        order=order,
                        khana_set=khana,
                        quantity=qty,
                        unit_price=khana.price_npr
                    )

            order.recalculate_totals()
            log_audit(None, 'CUSTOMER_QR_ORDER', f"Order {order.order_number} submitted via QR by Table {table.table_number}", request)

        return JsonResponse({
            'status': 'success',
            'order_number': order.order_number,
            'message': 'Order placed successfully and forwarded to the Kitchen!'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_POST
def submit_service_request_api(request, qr_token):
    table = get_object_or_404(RestaurantTable, qr_code_token=qr_token)
    try:
        data = json.loads(request.body)
        req_type = data.get('request_type', 'WAITER')
        details = data.get('details', '')

        valid_types = [c[0] for c in CustomerServiceRequest.REQUEST_TYPES]
        if req_type not in valid_types:
            req_type = 'WAITER'

        req_obj = CustomerServiceRequest.objects.create(
            table=table,
            request_type=req_type,
            details=details,
            status='PENDING'
        )

        if req_type == 'BILL':
            table.status = 'BILL_REQUESTED'
            table.save()

        log_audit(None, 'SERVICE_REQUEST', f"Table {table.table_number} requested {req_type}", request)
        return JsonResponse({'status': 'success', 'message': f'Your request ({req_obj.get_request_type_display()}) was sent to the waiter staff.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ==========================================
# STAFF AUTHENTICATION & PORTAL
# ==========================================

def staff_login_view(request):
    if request.user.is_authenticated:
        return redirect('staff_dashboard')

    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            log_audit(user, 'STAFF_LOGIN', f"User {user.username} logged in", request)
            return redirect('staff_dashboard')
        else:
            messages.error(request, 'Invalid username or password credentials.')
    return render(request, 'staff/login.html')

def staff_logout_view(request):
    if request.user.is_authenticated:
        log_audit(request.user, 'STAFF_LOGOUT', f"User {request.user.username} logged out", request)
    logout(request)
    return redirect('staff_login')


# ==========================================
# RESTAURANT UNIFIED ALL-IN-ONE DASHBOARD & RMS
# ==========================================

@login_required
def unified_dashboard_view(request):
    today = timezone.localdate()
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Real-time metrics
    today_orders = Order.objects.filter(created_at__gte=today_start).exclude(status='CANCELLED')
    today_revenue = Payment.objects.filter(created_at__gte=today_start, status='SUCCESS').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    total_lifetime_revenue = Payment.objects.filter(status='SUCCESS').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    
    total_tables = RestaurantTable.objects.count()
    active_tables = RestaurantTable.objects.filter(status='OCCUPIED').count()
    available_tables = RestaurantTable.objects.filter(status='AVAILABLE').count()
    pending_bills = Bill.objects.filter(status='PENDING').count()
    cancelled_orders = Order.objects.filter(created_at__gte=today_start, status='CANCELLED').count()

    # Active table sessions & floor tables
    tables = RestaurantTable.objects.all().order_by('table_number')
    active_sessions = TableSession.objects.filter(is_active=True).select_related('table', 'assigned_waiter')
    pending_requests = CustomerServiceRequest.objects.filter(status='PENDING')[:6]

    # Live Orders across all states
    recent_orders = Order.objects.all().select_related('table_session__table', 'customer', 'staff_member').prefetch_related('items__khana_set').order_by('-created_at')[:25]
    unserved_orders = Order.objects.exclude(status__in=['SERVED', 'CANCELLED']).count()

    # Khana Sets (all items with categories)
    khana_sets = KhanaSet.objects.all().order_by('order_priority', 'id')

    # Reservations
    reservations = TableReservation.objects.all().order_by('-reservation_date', '-reservation_time')[:20]

    # Customer Reviews
    reviews = CustomerReview.objects.all().order_by('-created_at')[:20]
    avg_rating = CustomerReview.objects.filter(is_approved=True).aggregate(avg=models.Avg('rating'))['avg'] or 5.0

    # Push Notifications
    notifications = PushNotification.objects.all().order_by('-created_at')[:15]

    # Recent Audit Activity
    audit_logs = AuditLog.objects.all().order_by('-created_at')[:10]

    # Daily revenue past 7 days for chart
    sales_chart_labels = []
    sales_chart_data = []
    order_chart_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_sales = Payment.objects.filter(
            created_at__date=day, status='SUCCESS'
        ).aggregate(s=Sum('amount'))['s'] or 0
        day_order_count = Order.objects.filter(
            created_at__date=day
        ).exclude(status='CANCELLED').count()
        sales_chart_labels.append(day.strftime('%b %d'))
        sales_chart_data.append(float(day_sales))
        order_chart_data.append(day_order_count)

    # Category popularity breakdown
    category_counts = {
        'VEG': OrderItem.objects.filter(khana_set__category='VEG').aggregate(s=Sum('quantity'))['s'] or 0,
        'CHICKEN': OrderItem.objects.filter(khana_set__category='CHICKEN').aggregate(s=Sum('quantity'))['s'] or 0,
        'MUTTON': OrderItem.objects.filter(khana_set__category='MUTTON').aggregate(s=Sum('quantity'))['s'] or 0,
        'FISH': OrderItem.objects.filter(khana_set__category='FISH').aggregate(s=Sum('quantity'))['s'] or 0,
    }

    return render(request, 'staff/dashboard.html', {
        'today_revenue': today_revenue,
        'total_lifetime_revenue': total_lifetime_revenue,
        'today_order_count': today_orders.count(),
        'unserved_orders': unserved_orders,
        'total_tables': total_tables,
        'active_tables': active_tables,
        'available_tables': available_tables,
        'pending_bills': pending_bills,
        'cancelled_orders': cancelled_orders,
        'tables': tables,
        'active_sessions': active_sessions,
        'pending_requests': pending_requests,
        'recent_orders': recent_orders,
        'khana_sets': khana_sets,
        'reservations': reservations,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'notifications': notifications,
        'audit_logs': audit_logs,
        'sales_chart_labels_json': json.dumps(sales_chart_labels),
        'sales_chart_data_json': json.dumps(sales_chart_data),
        'order_chart_data_json': json.dumps(order_chart_data),
        'category_chart_data_json': json.dumps([
            category_counts['VEG'],
            category_counts['CHICKEN'],
            category_counts['MUTTON'],
            category_counts['FISH'],
        ]),
    })

# Maintain staff_dashboard_view alias
staff_dashboard_view = unified_dashboard_view

# ==========================================
# IN-PLACE REAL-TIME QUICK UPDATE APIS (FOR DASHBOARD)
# ==========================================

@login_required
@require_POST
def dashboard_quick_update_api(request):
    try:
        data = json.loads(request.body)
        target = data.get('target')
        item_id = data.get('id')
        field = data.get('field')
        value = data.get('value')

        if target == 'khana_set':
            ks = get_object_or_404(KhanaSet, id=item_id)
            if field == 'price_npr':
                ks.price_npr = Decimal(str(value))
            elif field == 'is_available':
                ks.is_available = bool(value)
            elif field == 'is_featured':
                ks.is_featured = bool(value)
            elif field == 'is_enabled_by_admin':
                ks.is_enabled_by_admin = bool(value)
            elif field == 'name':
                ks.name = str(value).strip()
            ks.save()
            log_audit(request.user, 'DASHBOARD_MENU_UPDATE', f"Updated {field} on KhanaSet #{ks.id} ({ks.name})", request)
            return JsonResponse({'status': 'success', 'message': f'Updated {ks.name} {field}.'})

        elif target == 'order_status':
            order = get_object_or_404(Order, id=item_id)
            if value in dict(Order.STATUS_CHOICES):
                order.status = value
                if value == 'CANCELLED':
                    order.cancel_reason = data.get('cancel_reason', 'Cancelled via Dashboard')
                order.save()
                log_audit(request.user, 'DASHBOARD_ORDER_STATUS', f"Order #{order.order_number} status set to {value}", request)
                return JsonResponse({'status': 'success', 'message': f'Order status updated to {value}.'})

        elif target == 'table_status':
            table = get_object_or_404(RestaurantTable, id=item_id)
            if value in dict(RestaurantTable.STATUS_CHOICES):
                table.status = value
                table.save()
                log_audit(request.user, 'DASHBOARD_TABLE_STATUS', f"Table {table.table_number} status set to {value}", request)
                return JsonResponse({'status': 'success', 'message': f'Table {table.table_number} status updated to {value}.'})

        elif target == 'reservation_status':
            res = get_object_or_404(TableReservation, id=item_id)
            if value in dict(TableReservation.STATUS_CHOICES):
                res.status = value
                res.save()
                log_audit(request.user, 'DASHBOARD_RESERVATION_STATUS', f"Reservation #{res.id} for {res.name} set to {value}", request)
                return JsonResponse({'status': 'success', 'message': f'Reservation status set to {value}.'})

        elif target == 'review_toggle':
            rev = get_object_or_404(CustomerReview, id=item_id)
            rev.is_approved = not rev.is_approved
            rev.save()
            log_audit(request.user, 'DASHBOARD_REVIEW_TOGGLE', f"Review #{rev.id} is_approved={rev.is_approved}", request)
            return JsonResponse({'status': 'success', 'is_approved': rev.is_approved, 'message': 'Review visibility updated.'})

        elif target == 'notification_toggle':
            notif = get_object_or_404(PushNotification, id=item_id)
            if field == 'is_active':
                notif.is_active = not notif.is_active
            elif field == 'is_pinned_banner':
                notif.is_pinned_banner = not notif.is_pinned_banner
            notif.save()
            log_audit(request.user, 'DASHBOARD_NOTIFICATION_TOGGLE', f"PushNotification #{notif.id} {field} toggled", request)
            return JsonResponse({'status': 'success', 'message': 'Notification updated.'})

        return JsonResponse({'status': 'error', 'message': 'Invalid target or field'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@require_POST
def dashboard_save_khana_set_api(request):
    try:
        set_id = request.POST.get('id')
        name = request.POST.get('name', '').strip()
        category = request.POST.get('category', 'VEG')
        price_npr = Decimal(request.POST.get('price_npr', '0'))
        description = request.POST.get('description', '').strip()
        traditional_items = request.POST.get('traditional_items', '').strip()
        spice_level = request.POST.get('spice_level', 'Mild to Medium').strip()
        is_available = request.POST.get('is_available') == 'on'
        is_featured = request.POST.get('is_featured') == 'on'
        is_enabled = request.POST.get('is_enabled_by_admin') == 'on'
        image_file = request.FILES.get('image')

        from django.utils.text import slugify
        slug = slugify(name) or f"khana-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        if set_id:
            ks = get_object_or_404(KhanaSet, id=set_id)
            ks.name = name
            ks.category = category
            ks.price_npr = price_npr
            ks.description = description
            ks.traditional_items = traditional_items
            ks.spice_level = spice_level
            ks.is_available = is_available
            ks.is_featured = is_featured
            ks.is_enabled_by_admin = is_enabled
            if image_file:
                ks.image = image_file
            ks.save()
            msg = f"Updated {ks.name}."
        else:
            ks = KhanaSet.objects.create(
                name=name,
                slug=slug,
                category=category,
                price_npr=price_npr,
                description=description,
                traditional_items=traditional_items or "Jimbu Dal, Bhat, Tarkari, Saag, Gundruk, Achar, Ghee, Papad",
                spice_level=spice_level,
                is_available=is_available,
                is_featured=is_featured,
                is_enabled_by_admin=is_enabled,
                image=image_file
            )
            msg = f"Created new Khana Set: {ks.name}."

        log_audit(request.user, 'DASHBOARD_SAVE_KHANA', msg, request)
        return JsonResponse({'status': 'success', 'message': msg, 'id': ks.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@require_POST
def dashboard_save_notification_api(request):
    try:
        notif_id = request.POST.get('id')
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        notification_type = request.POST.get('notification_type', 'SPECIAL_OFFER')
        badge_text = request.POST.get('badge_text', 'Special Announcement').strip()
        action_url = request.POST.get('action_url', '/khana-sets/').strip()
        action_button_text = request.POST.get('action_button_text', 'View Details').strip()
        is_active = request.POST.get('is_active') == 'on'
        is_pinned_banner = request.POST.get('is_pinned_banner') == 'on'
        image_file = request.FILES.get('image')

        if notif_id:
            notif = get_object_or_404(PushNotification, id=notif_id)
            notif.title = title
            notif.message = message
            notif.notification_type = notification_type
            notif.badge_text = badge_text
            notif.action_url = action_url
            notif.action_button_text = action_button_text
            notif.is_active = is_active
            notif.is_pinned_banner = is_pinned_banner
            if image_file:
                notif.image = image_file
            notif.save()
            msg = f"Updated notification: {notif.title}."
        else:
            notif = PushNotification.objects.create(
                title=title,
                message=message,
                notification_type=notification_type,
                badge_text=badge_text,
                action_url=action_url,
                action_button_text=action_button_text,
                is_active=is_active,
                is_pinned_banner=is_pinned_banner,
                image=image_file
            )
            msg = f"Created live notification: {notif.title}."

        log_audit(request.user, 'DASHBOARD_SAVE_NOTIFICATION', msg, request)
        return JsonResponse({'status': 'success', 'message': msg, 'id': notif.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def table_management_view(request):
    tables = RestaurantTable.objects.all().order_by('table_number')
    staff_members = StaffProfile.objects.filter(is_active_duty=True).select_related('user')
    return render(request, 'staff/tables.html', {
        'tables': tables,
        'staff_members': staff_members,
    })

@login_required
@require_POST
def open_table_session_api(request, table_id):
    table = get_object_or_404(RestaurantTable, id=table_id)
    if table.status == 'OCCUPIED' and table.current_session:
        return JsonResponse({'status': 'error', 'message': 'Table already has an active session.'}, status=400)

    try:
        data = json.loads(request.body)
        guests = int(data.get('customer_count', 2))
        waiter_id = data.get('waiter_id')
        waiter = None
        if waiter_id:
            waiter = StaffProfile.objects.get(id=waiter_id).user

        session = TableSession.objects.create(
            table=table,
            customer_count=guests,
            assigned_waiter=waiter or request.user
        )
        table.status = 'OCCUPIED'
        table.save()
        log_audit(request.user, 'TABLE_OPENED', f"Opened Table {table.table_number} with {guests} guests", request)
        return JsonResponse({'status': 'success', 'session_id': session.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@require_POST
def update_table_status_api(request, table_id):
    table = get_object_or_404(RestaurantTable, id=table_id)
    data = json.loads(request.body)
    new_status = data.get('status')
    if new_status in dict(RestaurantTable.STATUS_CHOICES):
        table.status = new_status
        table.save()
        log_audit(request.user, 'TABLE_STATUS_CHANGE', f"Table {table.table_number} status set to {new_status}", request)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid status'}, status=400)

@login_required
@require_POST
def resolve_service_request_api(request, req_id):
    req_obj = get_object_or_404(CustomerServiceRequest, id=req_id)
    req_obj.status = 'ATTENDED'
    req_obj.attended_by = request.user
    req_obj.attended_at = timezone.now()
    req_obj.save()
    return JsonResponse({'status': 'success'})

# POS & ORDERING
@login_required
def pos_view(request):
    tables = RestaurantTable.objects.all().order_by('table_number')
    menu_items = KhanaSet.objects.filter(is_enabled_by_admin=True, is_available=True)
    return render(request, 'staff/pos.html', {
        'tables': tables,
        'menu_items': menu_items,
    })

@login_required
@require_POST
def submit_pos_order_api(request):
    try:
        data = json.loads(request.body)
        table_id = data.get('table_id')
        items_data = data.get('items', [])
        special_notes = data.get('special_instructions', '')

        table = get_object_or_404(RestaurantTable, id=table_id)
        session = table.current_session
        if not session:
            session = TableSession.objects.create(table=table, customer_count=len(items_data), assigned_waiter=request.user)
            table.status = 'OCCUPIED'
            table.save()

        with transaction.atomic():
            order_num = f"POS-{table.table_number}-{timezone.now().strftime('%H%M%S')}"
            order = Order.objects.create(
                order_number=order_num,
                table_session=session,
                staff_member=request.user,
                source='POS_WAITER',
                status='NEW',
                special_instructions=special_notes
            )
            for item in items_data:
                khana = KhanaSet.objects.get(id=item['id'])
                qty = int(item['quantity'])
                if qty > 0:
                    OrderItem.objects.create(
                        order=order,
                        khana_set=khana,
                        quantity=qty,
                        unit_price=khana.price_npr
                    )
            order.recalculate_totals()
            log_audit(request.user, 'POS_ORDER_CREATED', f"Created {order.order_number} on Table {table.table_number}", request)

        return JsonResponse({'status': 'success', 'order_number': order.order_number})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# KITCHEN DISPLAY SYSTEM (KDS)
@login_required
def kitchen_display_view(request):
    orders = Order.objects.exclude(status__in=['SERVED', 'CANCELLED']).prefetch_related('items__khana_set', 'table_session__table').order_by('created_at')
    return render(request, 'staff/kitchen.html', {
        'orders': orders,
    })

@login_required
@require_POST
def update_order_status_api(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    data = json.loads(request.body)
    new_status = data.get('status')
    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        if new_status == 'CANCELLED':
            order.cancel_reason = data.get('cancel_reason', 'Cancelled by kitchen/staff')
        order.save()
        log_audit(request.user, 'ORDER_STATUS_UPDATE', f"Order {order.order_number} status -> {new_status}", request)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Invalid status'}, status=400)

# BILLING & PAYMENTS
@login_required
def billing_view(request):
    occupied_sessions = TableSession.objects.filter(is_active=True).select_related('table')
    recent_bills = Bill.objects.all().order_by('-created_at')[:20]
    return render(request, 'staff/billing.html', {
        'sessions': occupied_sessions,
        'recent_bills': recent_bills,
    })

@login_required
def generate_table_bill_api(request, session_id):
    session = get_object_or_404(TableSession, id=session_id, is_active=True)
    orders = session.orders.exclude(status='CANCELLED')
    
    subtotal = sum(order.subtotal_npr for order in orders)
    sc = round(float(subtotal) * (float(settings.SERVICE_CHARGE_PERCENTAGE) / 100.0), 2) if hasattr(settings, 'SERVICE_CHARGE_PERCENTAGE') else 0.0
    vat = round((float(subtotal) + sc) * (13.0 / 100.0), 2)
    grand_total = float(subtotal) + sc + vat

    # Existing pending bill or generate new receipt
    bill = session.bills.filter(status='PENDING').first()
    if not bill:
        receipt_num = f"RHINO-{session.table.table_number}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        bill = Bill.objects.create(
            receipt_number=receipt_num,
            table_session=session,
            cashier=request.user,
            subtotal=Decimal(str(subtotal)),
            service_charge=Decimal(str(sc)),
            vat_amount=Decimal(str(vat)),
            grand_total=Decimal(str(grand_total)),
            paid_amount=Decimal('0.00'),
            status='PENDING'
        )
    return JsonResponse({
        'status': 'success',
        'bill_id': bill.id,
        'receipt_number': bill.receipt_number,
        'table_number': session.table.table_number,
        'subtotal': float(bill.subtotal),
        'service_charge': float(bill.service_charge),
        'vat_amount': float(bill.vat_amount),
        'grand_total': float(bill.grand_total),
        'balance': float(bill.balance_remaining),
        'paid_amount': float(bill.paid_amount),
    })

@login_required
@require_POST
def process_payment_api(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)
    if bill.status == 'PAID':
        return JsonResponse({'status': 'error', 'message': 'Bill is already paid and completed.'}, status=400)

    try:
        data = json.loads(request.body)
        amount = Decimal(str(data.get('amount', bill.balance_remaining)))
        method = data.get('method', 'CASH')
        notes = data.get('notes', '')
        ref = data.get('reference', '')

        with transaction.atomic():
            payment = Payment.objects.create(
                bill=bill,
                amount=amount,
                payment_method=method,
                status='SUCCESS',
                transaction_reference=ref,
                cashier=request.user,
                is_verified=True,
                notes=notes
            )
            bill.paid_amount += amount
            if bill.paid_amount >= bill.grand_total:
                bill.status = 'PAID'
                bill.closed_at = timezone.now()
                # Close table session and free the table
                session = bill.table_session
                session.is_active = False
                session.closed_at = timezone.now()
                session.save()
                table = session.table
                table.status = 'CLEANING_REQUIRED'
                table.save()

            bill.save()
            log_audit(request.user, 'PAYMENT_RECEIVED', f"Received {amount} NPR ({method}) for Bill {bill.receipt_number}", request)

        return JsonResponse({'status': 'success', 'paid': float(bill.paid_amount), 'bill_status': bill.status})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# PDF Thermal Receipt Generator
@login_required
def receipt_pdf_view(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Receipt_{bill.receipt_number}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=(226, 600), leftMargin=10, rightMargin=10, topMargin=10, bottomMargin=10)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Normal'], fontSize=12, alignment=1, spaceAfter=4, fontName='Helvetica-Bold')
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=8, alignment=1, spaceAfter=2)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=8)
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold')

    elements = []
    elements.append(Paragraph("HOTEL RAINO", title_style))
    elements.append(Paragraph("Authentic Himalayan Thakali Kitchen", sub_style))
    elements.append(Paragraph("Sauraha, Chitwan / Kathmandu, Nepal", sub_style))
    elements.append(Paragraph("Tel: +977-9715003003 | PAN: 601234589", sub_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"Receipt: {bill.receipt_number}", bold_style))
    elements.append(Paragraph(f"Date: {bill.created_at.strftime('%Y-%m-%d %H:%M')}", body_style))
    elements.append(Paragraph(f"Table: {bill.table_session.table.table_number} | Cashier: {bill.cashier.username if bill.cashier else 'Staff'}", body_style))
    elements.append(Spacer(1, 6))

    # Items table
    table_data = [["Item", "Qty", "Price", "Total"]]
    for order in bill.table_session.orders.exclude(status='CANCELLED'):
        for it in order.items.all():
            table_data.append([it.khana_set.name[:14], str(it.quantity), str(int(it.unit_price)), str(int(it.total_price))])

    t = ReportTable(table_data, colWidths=[80, 25, 45, 55])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('LINEBELOW', (0,0), (-1,0), 0.5, colors.black),
        ('LINEBELOW', (0,-1), (-1,-1), 0.5, colors.black),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 6))

    elements.append(Paragraph(f"Subtotal: NPR {bill.subtotal:.2f}", body_style))
    elements.append(Paragraph(f"Service Charge (10%): NPR {bill.service_charge:.2f}", body_style))
    elements.append(Paragraph(f"VAT (13%): NPR {bill.vat_amount:.2f}", body_style))
    elements.append(Paragraph(f"GRAND TOTAL: NPR {bill.grand_total:.2f}", bold_style))
    elements.append(Paragraph(f"PAID: NPR {bill.paid_amount:.2f}", bold_style))
    elements.append(Paragraph(f"Status: {bill.get_status_display()}", body_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Thank you for dining with us! Namaste!", sub_style))

    doc.build(elements)
    return response

# KHANA SET MANAGEMENT
@login_required
def khana_set_management_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle_availability':
            set_id = request.POST.get('set_id')
            ks = get_object_or_404(KhanaSet, id=set_id)
            ks.is_available = not ks.is_available
            ks.save()
            messages.success(request, f"{ks.name} availability updated to {ks.is_available}.")
            return redirect('staff_khana_sets')
        elif action == 'update_price':
            set_id = request.POST.get('set_id')
            price = request.POST.get('price')
            ks = get_object_or_404(KhanaSet, id=set_id)
            ks.price_npr = Decimal(price)
            ks.save()
            messages.success(request, f"Price updated for {ks.name}.")
            return redirect('staff_khana_sets')
        elif action == 'create_single':
            name = request.POST.get('name', '').strip()
            category = request.POST.get('category', 'VEG')
            price = request.POST.get('price_npr', 0)
            portion_info = request.POST.get('portion_info', '').strip()
            description = request.POST.get('description', '').strip()
            traditional_items = request.POST.get('traditional_items', '').strip()
            spice_level = request.POST.get('spice_level', 'Mild to Medium')
            image_file = request.FILES.get('image')

            if name and price:
                base_slug = slugify(name) or f"khana-set-{int(timezone.now().timestamp())}"
                slug = base_slug
                counter = 1
                while KhanaSet.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                ks = KhanaSet.objects.create(
                    name=name,
                    slug=slug,
                    category=category,
                    price_npr=Decimal(price),
                    portion_info=portion_info or "Complete Himalayan Thali with Unlimited Rice, Dal & Tarkari Refills",
                    description=description or f"Authentic Thakali set: {name}",
                    traditional_items=traditional_items or "Jimbu-tempered Mustang Dal, Steamed Rice, Himalayan Tarkari, Rayo ko Saag, Gundruk Sadeko, Timur Achar, Crispy Papad, Pure Mountain Ghee",
                    spice_level=spice_level,
                    is_available=True,
                    is_featured=True,
                    is_enabled_by_admin=True
                )
                if image_file:
                    ks.image = image_file
                    ks.save()
                messages.success(request, f"Successfully created new item: {ks.name}!")
            else:
                messages.error(request, "Name and Price are required.")
            return redirect('staff_khana_sets')

        elif action == 'batch_create':
            raw_text = request.POST.get('batch_items', '').strip()
            category_default = request.POST.get('default_category', 'VEG')
            created_count = 0

            # Each line: Name | Price | Category (optional) | Portion Info (optional)
            lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
            for line in lines:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    item_name = parts[0]
                    try:
                        item_price = Decimal(parts[1].replace('NPR', '').replace(',', '').strip())
                    except Exception:
                        continue

                    item_category = parts[2].upper() if len(parts) > 2 and parts[2].upper() in ['VEG', 'CHICKEN', 'MUTTON', 'FISH'] else category_default
                    item_portion = parts[3] if len(parts) > 3 else "Complete Himalayan Thali with Unlimited Rice, Dal & Tarkari Refills"

                    base_slug = slugify(item_name) or f"item-{int(timezone.now().timestamp())}-{created_count}"
                    slug = base_slug
                    counter = 1
                    while KhanaSet.objects.filter(slug=slug).exists():
                        slug = f"{base_slug}-{counter}"
                        counter += 1

                    KhanaSet.objects.create(
                        name=item_name,
                        slug=slug,
                        category=item_category,
                        price_npr=item_price,
                        portion_info=item_portion,
                        description=f"Authentic Himalayan Thakali {item_name}",
                        traditional_items="Mustang Dal, Steamed Rice, Seasonal Tarkari, Rayo ko Saag, Gundruk Sadeko, Timur Achar, Crispy Papad, Pure Mountain Ghee",
                        is_available=True,
                        is_featured=True,
                        is_enabled_by_admin=True
                    )
                    created_count += 1

            if created_count > 0:
                messages.success(request, f"Successfully added {created_count} items in bulk!")
            else:
                messages.error(request, "No valid items could be parsed. Format each line as: Name | Price")
            return redirect('staff_khana_sets')

        elif action == 'delete_set':
            set_id = request.POST.get('set_id')
            ks = get_object_or_404(KhanaSet, id=set_id)
            set_name = ks.name
            ks.delete()
            messages.success(request, f"Item '{set_name}' deleted successfully.")
            return redirect('staff_khana_sets')

    sets = KhanaSet.objects.all().order_by('order_priority', 'id')
    return render(request, 'staff/khana_sets_manage.html', {'khana_sets': sets})

# SALES & REPORTS
@login_required
def sales_reports_view(request):
    today = timezone.localdate()
    # Summaries
    today_revenue = Payment.objects.filter(created_at__date=today, status='SUCCESS').aggregate(s=Sum('amount'))['s'] or 0
    total_revenue = Payment.objects.filter(status='SUCCESS').aggregate(s=Sum('amount'))['s'] or 0
    total_orders = Order.objects.exclude(status='CANCELLED').count()
    cancelled_orders = Order.objects.filter(status='CANCELLED').count()

    # Category breakdown (Veg vs Non-Veg Thakali Sets)
    veg_count = OrderItem.objects.filter(khana_set__category='VEG').aggregate(s=Sum('quantity'))['s'] or 0
    non_veg_count = OrderItem.objects.filter(khana_set__category__in=['CHICKEN', 'MUTTON', 'FISH']).aggregate(s=Sum('quantity'))['s'] or 0

    # Payment method breakdown
    payment_methods = Payment.objects.filter(status='SUCCESS').values('payment_method').annotate(total=Sum('amount'), cnt=Count('id'))

    # Export requests
    export_format = request.GET.get('export')
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="Hotel_Rhino_Sales_{today}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Receipt No', 'Date', 'Amount (NPR)', 'Payment Method', 'Cashier', 'Status'])
        for p in Payment.objects.filter(status='SUCCESS').select_related('bill', 'cashier'):
            writer.writerow([p.bill.receipt_number, p.created_at.strftime('%Y-%m-%d %H:%M'), p.amount, p.get_payment_method_display(), p.cashier.username if p.cashier else 'N/A', p.status])
        return response

    return render(request, 'staff/reports.html', {
        'today_revenue': today_revenue,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'cancelled_orders': cancelled_orders,
        'veg_count': veg_count,
        'non_veg_count': non_veg_count,
        'payment_methods': payment_methods,
    })

# STAFF MANAGEMENT & RESERVATIONS
@login_required
def staff_management_view(request):
    profiles = StaffProfile.objects.all().select_related('user')
    return render(request, 'staff/staff_members.html', {'profiles': profiles})

@login_required
def reservations_view(request):
    reservations = TableReservation.objects.all().order_by('-reservation_date', '-reservation_time')
    return render(request, 'staff/reservations.html', {'reservations': reservations})

@login_required
def customers_view(request):
    customers = Customer.objects.all().order_by('-last_visit')
    return render(request, 'staff/customers.html', {'customers': customers})

@login_required
def settings_view(request):
    return render(request, 'staff/settings.html')

# REAL-TIME LIVE SYNC API FOR DASHBOARD, KDS & POS
@login_required
def live_sync_api(request):
    unserved_orders = Order.objects.exclude(status__in=['SERVED', 'CANCELLED']).count()
    pending_bills = Bill.objects.filter(status='PENDING').count()
    service_requests = CustomerServiceRequest.objects.filter(status='PENDING').count()
    return JsonResponse({
        'unserved_orders': unserved_orders,
        'pending_bills': pending_bills,
        'service_requests': service_requests,
        'timestamp': timezone.now().isoformat()
    })

# LOGO MANAGEMENT UPLOAD API FOR DASHBOARD
@login_required
@require_POST
def dashboard_upload_logo_api(request):
    """
    Secure endpoint allowing dashboard managers to upload a new brand logo.
    Saves to media/brand_logo.png and also syncs static/images/hotel_rhino_logo.png
    so that both static and dynamic rendering resolve smoothly without breaking admin routes.
    """
    logo_file = request.FILES.get('logo')
    if not logo_file:
        return JsonResponse({'status': 'error', 'message': 'No file provided.'}, status=400)

    # Validate file extension
    ext = os.path.splitext(logo_file.name)[1].lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.webp', '.svg']:
        return JsonResponse({'status': 'error', 'message': 'Invalid format. Please upload PNG, JPG, WEBP, or SVG.'}, status=400)

    # Size check (max 5MB)
    if logo_file.size > 5 * 1024 * 1024:
        return JsonResponse({'status': 'error', 'message': 'File too large. Maximum allowed size is 5MB.'}, status=400)

    try:
        # Read content
        content = logo_file.read()

        # Destination paths
        media_logo = os.path.join(settings.MEDIA_ROOT, 'brand_logo.png')
        static_logo = os.path.join(settings.BASE_DIR, 'static', 'images', 'hotel_rhino_logo.png')
        raino_logo = os.path.join(settings.BASE_DIR, 'static', 'images', 'hotel_raino_logo.png')

        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        os.makedirs(os.path.dirname(static_logo), exist_ok=True)

        # Write to media root
        with open(media_logo, 'wb') as f:
            f.write(content)

        # Also write to static directories
        with open(static_logo, 'wb') as f:
            f.write(content)
        with open(raino_logo, 'wb') as f:
            f.write(content)

        # Audit log
        log_audit(request.user, 'LOGO_UPLOAD', 'Updated brand logo from dashboard', request)

        logo_url = f"/media/brand_logo.png?v={int(timezone.now().timestamp())}"
        return JsonResponse({
            'status': 'success',
            'message': 'Brand logo updated successfully!',
            'logo_url': logo_url
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Failed to save logo: {str(e)}'}, status=500)

