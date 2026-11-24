from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from thakali_app import views as app_views

urlpatterns = [
    # Blocked /admin/ honeypot - returning 404 and logging probe
    path('admin/', app_views.blocked_admin_honeypot_view, name='blocked_admin'),
    path('admin/<path:subpath>', app_views.blocked_admin_honeypot_view),
    # Secret underlying database admin route
    path(settings.SECRET_ADMIN_VAULT_URL, admin.site.urls),
    path('', include('thakali_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
