from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    # Frontend Shop URLs
    path("", views.index, name="ShopHome"),
    path("about/", views.about, name="AboutUs"),
    path("contact/", views.contact, name="ContactUs"),
    path("search/", views.search, name="Search"),
    path("products/<int:myid>", views.productView, name="ProductView"),
    path("checkout/", views.checkout, name="Checkout"),
    path("payment-success/", views.payment_success, name="PaymentSuccess"),

    # Backend Cart URLs
    path("add-to-cart/<int:product_id>/", views.add_to_cart, name="AddToCart"),
    path("cart/", views.cart_detail, name="CartDetail"),
    path("update-cart/<int:product_id>/<str:action>/", views.update_cart_item, name="UpdateCartItem"),
    path("remove-cart/<int:product_id>/", views.remove_from_cart, name="RemoveFromCart"),
    path('apply/', views.coupon_apply, name='apply'),
    path("my-orders/", views.my_orders, name="MyOrders"),

    # Wishlist URLs
    path("wishlist/", views.wishlist_view, name="Wishlist"),
    path("toggle-wishlist/<int:product_id>/", views.toggle_wishlist, name="ToggleWishlist"),

    # API URLs
    path('api/products/', api_views.api_get_products, name='api_get_products'),
    path('api/products/<int:pk>/', api_views.api_get_product_detail, name='ApiGetProductDetail'),
]