from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('_nested_admin/', include('nested_admin.urls')), # تأكيد مسار الـ nested admin
    path('api/', include('product.urls')), # المسار اللي هنعمله للـ APIs دلوقتي
]

# السطر ده بيخلي دجانجو يخدم صور الـ media في مرحلة الـ Development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)