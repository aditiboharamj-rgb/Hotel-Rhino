from django.urls import path
from . import views

urlpatterns = [
    # Public Pages
    path('', views.home_view, name='home'),
    path('khana-sets/', views.khana_sets_view, name='khana_sets'),
    path('whats-inside-your-thali/', views.whats_inside_thali_view, name='whats_inside_thali'),
    path('our-story/', views.our_story_view, name='our_story'),
    path('gallery/', views.gallery_view, name='gallery'),
    path('guest-experiences/', views.guest_experiences_view, name='guest_experiences'),
    path('visit-us/', views.visit_us_view, name='visit_us'),

    # QR Customer Self-Service & Ordering
    path('table-qr/<uuid:qr_token>/', views.qr_table_order_view, name='qr_table_order'),
    path('api/qr/<uuid:qr_token>/order/', views.submit_qr_order_api, name='submit_qr_order_api'),
    path('api/qr/<uuid:qr_token>/service-request/', views.submit_service_request_api, name='submit_service_request_api'),

    # Staff Auth
    path('staff/login/', views.staff_login_view, name='staff_login'),
    path('staff/logout/', views.staff_logout_view, name='staff_logout'),

    # Staff RMS & POS
    path('staff/dashboard/', views.staff_dashboard_view, name='staff_dashboard'),
    path('staff/tables/', views.table_management_view, name='staff_tables'),
    path('staff/pos/', views.pos_view, name='staff_pos'),
    path('staff/kitchen/', views.kitchen_display_view, name='staff_kitchen'),
    path('staff/billing/', views.billing_view, name='staff_billing'),
    path('staff/reports/', views.sales_reports_view, name='staff_reports'),
    path('staff/khana-sets/', views.khana_set_management_view, name='staff_khana_sets'),
    path('staff/members/', views.staff_management_view, name='staff_members'),
    path('staff/reservations/', views.reservations_view, name='staff_reservations'),
    path('staff/customers/', views.customers_view, name='staff_customers'),
    path('staff/settings/', views.settings_view, name='staff_settings'),

    # APIs & POS Actions
    path('api/table/<int:table_id>/open-session/', views.open_table_session_api, name='open_table_session_api'),
    path('api/table/<int:table_id>/update-status/', views.update_table_status_api, name='update_table_status_api'),
    path('api/pos/order/', views.submit_pos_order_api, name='submit_pos_order_api'),
    path('api/order/<int:order_id>/status/', views.update_order_status_api, name='update_order_status_api'),
    path('api/billing/generate/<int:session_id>/', views.generate_table_bill_api, name='generate_table_bill_api'),
    path('api/billing/pay/<int:bill_id>/', views.process_payment_api, name='process_payment_api'),
    path('staff/billing/receipt/<int:bill_id>/pdf/', views.receipt_pdf_view, name='receipt_pdf'),
    path('api/service-request/<int:req_id>/resolve/', views.resolve_service_request_api, name='resolve_service_request_api'),
    path('api/live-sync/', views.live_sync_api, name='live_sync_api'),
]

