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
from django.db.models import Sum, Count, Q
from django.db import transaction
from django.contrib import messages
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table as ReportTable, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from .models import (
    StaffProfile, RestaurantTable, TableSession, KhanaSet,
    Customer, Order, OrderItem, Bill, Payment,
    CustomerServiceRequest, TableReservation, CustomerReview, AuditLog
)

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
    featured_sets = KhanaSet.objects.filter(is_enabled_by_admin=True, is_available=True, is_featured=True)[:4]
    reviews = CustomerReview.objects.filter(is_approved=True)[:6]
    return render(request, 'public/home.html', {
        'featured_sets': featured_sets,
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
        name = request.POST.get('name', '').strip()
        rating = int(request.POST.get('rating', 5))
        comment = request.POST.get('comment', '').strip()
        city = request.POST.get('city', 'Kathmandu').strip()
        if name and comment:
            CustomerReview.objects.create(name=name, rating=rating, comment=comment, city=city, is_approved=True)
            messages.success(request, "Dhanyabad! Thank you for sharing your experience at Hotel Rhino.")
            return redirect('guest_experiences')
    return render(request, 'public/guest_experiences.html', {'reviews': reviews})

def visit_us_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        guests = int(request.POST.get('guests', 2))
        res_date = request.POST.get('date')
        res_time = request.POST.get('time')
        special = request.POST.get('special_requests', '').strip()

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
# RESTAURANT ADMIN DASHBOARD & RMS
# ==========================================

@login_required
def staff_dashboard_view(request):
    today = timezone.localdate()
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Real-time metrics
    today_orders = Order.objects.filter(created_at__gte=today_start).exclude(status='CANCELLED')
    today_revenue = Payment.objects.filter(created_at__gte=today_start, status='SUCCESS').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    
    total_tables = RestaurantTable.objects.count()
    active_tables = RestaurantTable.objects.filter(status='OCCUPIED').count()
    available_tables = RestaurantTable.objects.filter(status='AVAILABLE').count()
    pending_bills = Bill.objects.filter(status='PENDING').count()
    cancelled_orders = Order.objects.filter(created_at__gte=today_start, status='CANCELLED').count()

    # Active table sessions
    active_sessions = TableSession.objects.filter(is_active=True).select_related('table', 'assigned_waiter')
    pending_requests = CustomerServiceRequest.objects.filter(status='PENDING')[:5]

    # Daily revenue past 7 days for chart
    sales_chart_labels = []
    sales_chart_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_sales = Payment.objects.filter(
            created_at__date=day, status='SUCCESS'
        ).aggregate(s=Sum('amount'))['s'] or 0
        sales_chart_labels.append(day.strftime('%b %d'))
        sales_chart_data.append(float(day_sales))

    return render(request, 'staff/dashboard.html', {
        'today_revenue': today_revenue,
        'today_order_count': today_orders.count(),
        'total_tables': total_tables,
        'active_tables': active_tables,
        'available_tables': available_tables,
        'pending_bills': pending_bills,
        'cancelled_orders': cancelled_orders,
        'active_sessions': active_sessions,
        'pending_requests': pending_requests,
        'sales_chart_labels_json': json.dumps(sales_chart_labels),
        'sales_chart_data_json': json.dumps(sales_chart_data),
    })

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
    elements.append(Paragraph("HOTEL RHINO", title_style))
    elements.append(Paragraph("Authentic Himalayan Thakali Kitchen", sub_style))
    elements.append(Paragraph("Sauraha, Chitwan / Kathmandu, Nepal", sub_style))
    elements.append(Paragraph("Tel: +977-9801234567 | PAN: 601234589", sub_style))
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

    sets = KhanaSet.objects.all().order_by('order_priority')
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
