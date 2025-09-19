from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('dashboard.urls')),
    path('projects/', include('projects.urls')),
    path('users/', include('users.urls')),
    path('leaves/', include('leaves.urls')),
]

admin.site.site_header = "ManageHub Admin"
admin.site.site_title = "ManageHub Admin Portal"
admin.site.index_title = "Welcome to ManageHub Admin Portal"

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom error handlers
handler400 = 'managehub.views.bad_request'
handler403 = 'managehub.views.permission_denied'
handler404 = 'managehub.views.page_not_found'
handler500 = 'managehub.views.server_error'