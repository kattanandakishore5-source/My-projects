from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),

    # Optimized: Delegated authentication routes to the accounts app's urls.py
    path('', include('accounts.urls')),

    # Landing page should be the shop (My Awesome Cart)
    path('', include('shop.urls')),

    # Keep /shop/ working too (older links/bookmarks)
    path('shop/', include('shop.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)