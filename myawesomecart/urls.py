from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from accounts import views as account_views  # Import the views from your new accounts app

urlpatterns = [
                  path('admin/', admin.site.urls),

                  # Authentication Routes
                  path('signup/', account_views.signup_view, name='signup'),
                  path('login/', account_views.login_view, name='login'),
                  path('logout/', account_views.logout_view, name='logout'),
                  path('profile/', account_views.profile_view, name='profile'),

                  # Landing page should be the shop (My Awesome Cart)
                  path('', include('shop.urls')),

                  # Keep /shop/ working too (older links/bookmarks)
                  path('shop/', include('shop.urls')),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
