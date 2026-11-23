from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator
from PIL import Image
import os
import uuid

# User Profile / Staff Roles
class StaffProfile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Owner / Admin'),
        ('CASHIER', 'Cashier'),
        ('WAITER', 'Waiter'),
        ('KITCHEN', 'Kitchen Staff'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='WAITER')
    phone = models.CharField(max_length=20, blank=True)
    is_active_duty = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


# Restaurant Table Management
class RestaurantTable(models.Model):
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('BILL_REQUESTED', 'Bill Requested'),
        ('PAYMENT_PENDING', 'Payment Pending'),
        ('CLEANING_REQUIRED', 'Cleaning Required'),
    ]
    table_number = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50, blank=True, help_text="e.g. Table 1, Heritage Courtyard 4")
    capacity = models.PositiveIntegerField(default=4)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='AVAILABLE')
    qr_code_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['table_number']

    def __str__(self):
        return f"Table {self.table_number} ({self.get_status_display()})"

    @property
    def current_session(self):
        return self.sessions.filter(is_active=True).first()


# Table Session: Prevents overlapping and tracks occupancy
class TableSession(models.Model):
    table = models.ForeignKey(RestaurantTable, on_delete=models.CASCADE, related_name='sessions')
    customer_count = models.PositiveIntegerField(default=2)
    assigned_waiter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='served_sessions')
    is_active = models.BooleanField(default=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-opened_at']

    def __str__(self):
        return f"Session #{self.id} on Table {self.table.table_number}"

    @property
    def total_bill_amount(self):
        total = 0
        for order in self.orders.exclude(status='CANCELLED'):
            total += order.final_amount
        return total


# Khana Set Menu Items (Exclusively Authentic Thakali Khana Sets)
class KhanaSet(models.Model):
    CATEGORY_CHOICES = [
        ('VEG', 'Vegetarian Thakali Khana Set'),
        ('CHICKEN', 'Chicken Thakali Khana Set (Local Kukhura)'),
        ('MUTTON', 'Mutton Thakali Khana Set (Himalayan Khasi)'),
        ('FISH', 'Fish Thakali Khana Set (Fresh Himalayan River Fish)'),
    ]
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='VEG')
    description = models.TextField(help_text="Detailed description of ingredients and preparation")
    traditional_items = models.TextField(
        default="Jimbu-tempered Mustang Dal, Aromatic Steamed Rice (Bhat), Seasonal Himalayan Tarkari, Rayo ko Saag, Gundruk Sadeko, Timur Achar, Crispy Papad, Pure Shingati Chyangra Ghee",
        help_text="Items included in this Thali"
    )
    price_npr = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    portion_info = models.CharField(max_length=100, default="Complete Himalayan Thali with Unlimited Rice, Dal & Tarkari Refills")
    image = models.ImageField(upload_to='khana_sets/', blank=True, null=True)
    image_url = models.URLField(blank=True, help_text="Direct CDN / Unsplash fallback URL")
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=True)
    is_enabled_by_admin = models.BooleanField(default=True)
    spice_level = models.CharField(max_length=20, default='Mild to Medium', blank=True)
    calories = models.CharField(max_length=50, blank=True, default="~850 kcal")
    order_priority = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order_priority', 'id']

    def __str__(self):
        return f"{self.name} - NPR {self.price_npr}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Fast image optimization to prevent jitter and excessive storage
        if self.image and os.path.exists(self.image.path):
            try:
                img = Image.open(self.image.path)
                if img.height > 1200 or img.width > 1200:
                    output_size = (1200, 1200)
                    img.thumbnail(output_size)
                    img.save(self.image.path, quality=85, optimize=True)
            except Exception:
                pass


# Customer Master Record (Optional voluntary store)
class Customer(models.Model):
    name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=30, unique=True, blank=True, null=True)
    email = models.EmailField(blank=True)
    visit_count = models.PositiveIntegerField(default=1)
    total_spent_npr = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    last_visit = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name or 'Guest'} ({self.phone or 'No phone'})"


# Orders (POS or Customer QR)
class Order(models.Model):
    STATUS_CHOICES = [
        ('NEW', 'New Order'),
        ('PREPARING', 'Preparing in Kitchen'),
        ('READY', 'Ready to Serve'),
        ('SERVED', 'Served'),
        ('CANCELLED', 'Cancelled'),
    ]
    ORDER_SOURCE = [
        ('POS_WAITER', 'POS (Waiter/Staff)'),
        ('QR_CUSTOMER', 'Customer QR Order'),
    ]
    order_number = models.CharField(max_length=30, unique=True)
    table_session = models.ForeignKey(TableSession, on_delete=models.CASCADE, related_name='orders')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    staff_member = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_orders')
    source = models.CharField(max_length=20, choices=ORDER_SOURCE, default='POS_WAITER')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    special_instructions = models.TextField(blank=True)
    cancel_reason = models.TextField(blank=True)
    subtotal_npr = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    service_charge_npr = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    vat_npr = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_npr = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number} - {self.table_session.table.table_number}"

    def recalculate_totals(self, vat_percent=13.0, service_percent=10.0, discount=0.00):
        subtotal = sum(item.total_price for item in self.items.all())
        self.subtotal_npr = subtotal
        self.discount_npr = discount
        after_discount = max(0, float(subtotal) - float(discount))
        sc = round(after_discount * (service_percent / 100.0), 2)
        vat = round((after_discount + sc) * (vat_percent / 100.0), 2)
        self.service_charge_npr = sc
        self.vat_npr = vat
        self.final_amount = round(after_discount + sc + vat, 2)
        self.save()


# Order Line Items
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    khana_set = models.ForeignKey(KhanaSet, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.CharField(max_length=200, blank=True)

    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.khana_set.name} (NPR {self.total_price})"


# Bill & Invoicing
class Bill(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Payment'),
        ('PAID', 'Paid & Completed'),
        ('SPLIT', 'Split Payment in Progress'),
        ('CANCELLED', 'Cancelled / Voided'),
    ]
    receipt_number = models.CharField(max_length=40, unique=True)
    table_session = models.ForeignKey(TableSession, on_delete=models.CASCADE, related_name='bills')
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='billed_invoices')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Bill {self.receipt_number} - NPR {self.grand_total}"

    @property
    def balance_remaining(self):
        return max(0, float(self.grand_total) - float(self.paid_amount))


# Payment Transactions
class Payment(models.Model):
    METHOD_CHOICES = [
        ('CASH', 'Cash Payment'),
        ('FONEPAY_QR', 'Fonepay / Bank QR'),
        ('CARD', 'Debit / Credit Card'),
        ('ESEWA', 'eSewa Mobile Wallet'),
        ('KHALTI', 'Khalti Mobile Wallet'),
    ]
    STATUS_CHOICES = [
        ('SUCCESS', 'Successful / Verified'),
        ('PENDING', 'Pending Verification'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='CASH')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUCCESS')
    transaction_reference = models.CharField(max_length=100, blank=True)
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_verified = models.BooleanField(default=True, help_text="Cashier confirmation or API webhook verified")
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment NPR {self.amount} ({self.get_payment_method_display()}) - {self.bill.receipt_number}"


# Service & Call Requests (From Customer QR)
class CustomerServiceRequest(models.Model):
    REQUEST_TYPES = [
        ('WAITER', 'Call Waiter'),
        ('WATER', 'Water Refill Request'),
        ('BILL', 'Request Bill Checkout'),
        ('ASSISTANCE', 'Need Assistance / Special Diet'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ATTENDED', 'Attended / Resolved'),
    ]
    table = models.ForeignKey(RestaurantTable, on_delete=models.CASCADE, related_name='service_requests')
    request_type = models.CharField(max_length=30, choices=REQUEST_TYPES)
    details = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    attended_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    attended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Table {self.table.table_number}: {self.get_request_type_display()}"


# Table Reservation
class TableReservation(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Confirmation'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed / Arrived'),
    ]
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    guest_count = models.PositiveIntegerField(default=2)
    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    table = models.ForeignKey(RestaurantTable, on_delete=models.SET_NULL, null=True, blank=True)
    special_requests = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['reservation_date', 'reservation_time']

    def __str__(self):
        return f"Reservation {self.name} ({self.guest_count} guests) on {self.reservation_date} {self.reservation_time}"


# Customer Review & Testimonials
class CustomerReview(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, help_text="Guest contact phone number")
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField()
    city = models.CharField(max_length=100, default="Kathmandu / Chitwan", blank=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.rating} stars)"


# Push Announcement / Notification System
class PushNotification(models.Model):
    TYPE_CHOICES = [
        ('SPECIAL_OFFER', 'Special Thakali Offer / Festive Discount'),
        ('NEW_DISH', 'New Himalayan Dish / Seasonal Arrival'),
        ('EVENT', 'Cultural Event / Deuda Evening'),
        ('ANNOUNCEMENT', 'General Hotel Announcement'),
        ('URGENT', 'Important / Holiday Notice'),
    ]

    title = models.CharField(max_length=150, help_text="e.g. Fresh Himalayan Chyang & Jimbu Feast Today!")
    message = models.TextField(help_text="Detailed notification announcement for website visitors & diners.")
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='SPECIAL_OFFER')
    badge_text = models.CharField(max_length=50, default="Special Announcement", help_text="Pill tag shown on notification banner")
    image = models.ImageField(upload_to='notifications/', blank=True, null=True, help_text="Upload notification photo")
    image_url = models.URLField(blank=True, help_text="Or external image URL")
    action_url = models.CharField(max_length=200, default="/khana-sets/", blank=True, help_text="Where clicking notification navigates")
    action_button_text = models.CharField(max_length=50, default="View Details", blank=True)
    is_active = models.BooleanField(default=True, help_text="Toggle ON to push live across the website")
    is_pinned_banner = models.BooleanField(default=True, help_text="Show as a top floating announcement banner")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True, help_text="Optional expiry date/time")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Push Notification"
        verbose_name_plural = "Push Notifications"

    def __str__(self):
        status = "🟢 ACTIVE" if self.is_active else "⚪ INACTIVE"
        return f"[{status}] {self.title} ({self.get_notification_type_display()})"


# Audit Logs
class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    details = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {self.user}: {self.action}"
