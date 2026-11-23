from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import (
    StaffProfile, RestaurantTable, TableSession, KhanaSet,
    Customer, Order, OrderItem, Bill, Payment,
    CustomerServiceRequest, TableReservation, CustomerReview, PushNotification, AuditLog
)

@admin.register(StaffProfile)
class StaffProfileAdmin(ModelAdmin):
    list_display = ('user', 'role', 'phone', 'is_active_duty', 'created_at')
    list_filter = ('role', 'is_active_duty')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone')

@admin.register(RestaurantTable)
class RestaurantTableAdmin(ModelAdmin):
    list_display = ('table_number', 'name', 'capacity', 'status', 'qr_code_token')
    list_filter = ('status',)
    search_fields = ('table_number', 'name')

@admin.register(TableSession)
class TableSessionAdmin(ModelAdmin):
    list_display = ('id', 'table', 'customer_count', 'assigned_waiter', 'is_active', 'opened_at', 'closed_at')
    list_filter = ('is_active', 'table')
    search_fields = ('table__table_number', 'assigned_waiter__username')

@admin.register(KhanaSet)
class KhanaSetAdmin(ModelAdmin):
    list_display = ('name', 'category', 'price_npr', 'is_available', 'is_enabled_by_admin', 'is_featured', 'order_priority')
    list_filter = ('category', 'is_available', 'is_enabled_by_admin', 'is_featured')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ('order_number', 'table_session', 'source', 'status', 'final_amount', 'created_at')
    list_filter = ('status', 'source')
    search_fields = ('order_number', 'table_session__table__table_number')

@admin.register(Bill)
class BillAdmin(ModelAdmin):
    list_display = ('receipt_number', 'table_session', 'grand_total', 'paid_amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('receipt_number', 'table_session__table__table_number')

@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ('bill', 'amount', 'payment_method', 'status', 'is_verified', 'created_at')
    list_filter = ('payment_method', 'status', 'is_verified')
    search_fields = ('bill__receipt_number', 'transaction_reference')

@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ('name', 'phone', 'email', 'visit_count', 'total_spent_npr', 'last_visit')
    search_fields = ('name', 'phone', 'email')

@admin.register(TableReservation)
class TableReservationAdmin(ModelAdmin):
    list_display = ('name', 'phone', 'guest_count', 'reservation_date', 'reservation_time', 'table', 'status')
    list_filter = ('status', 'reservation_date')
    search_fields = ('name', 'phone')

@admin.register(PushNotification)
class PushNotificationAdmin(ModelAdmin):
    list_display = ('title', 'notification_type', 'badge_text', 'is_active', 'is_pinned_banner', 'created_at', 'expires_at')
    list_filter = ('is_active', 'notification_type', 'is_pinned_banner')
    search_fields = ('title', 'message', 'badge_text')
    actions = ['activate_notifications', 'deactivate_notifications']

    @admin.action(description="Push Live (Activate selected notifications)")
    def activate_notifications(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, "Selected push notifications are now active across the website!")

    @admin.action(description="Deactivate selected notifications")
    def deactivate_notifications(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, "Selected push notifications deactivated.")

@admin.register(CustomerReview)
class CustomerReviewAdmin(ModelAdmin):
    list_display = ('name', 'phone', 'rating', 'city', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_approved')
    search_fields = ('name', 'phone', 'comment')

@admin.register(CustomerServiceRequest)
class CustomerServiceRequestAdmin(ModelAdmin):
    list_display = ('table', 'request_type', 'status', 'created_at', 'attended_by')
    list_filter = ('status', 'request_type')

@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ('action', 'user', 'created_at', 'ip_address')
    list_filter = ('action',)
    search_fields = ('action', 'details')
