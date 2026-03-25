from django.contrib import admin
from .models import Product, Contact, Orders, OrderUpdate, Cart, CartItem, Coupon, ProductReview
from django.utils.html import format_html

# Basic Model Registrations
admin.site.register(Product)
admin.site.register(Contact)
admin.site.register(Orders)
admin.site.register(OrderUpdate)
admin.site.register(Cart)
admin.site.register(CartItem)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'valid_from', 'valid_to', 'discount_type', 'discount_value', 'active')
    list_filter = ('active', 'discount_type', 'valid_from', 'valid_to')
    search_fields = ('code',)


# Custom Admin for Product Reviews
@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')

    # Makes the review read-only so admin can't fake/edit user reviews
    readonly_fields = ('product', 'user', 'review_text', 'rating', 'image')

    # Prevents the admin from writing their own reviews via the dashboard
    def has_add_permission(self, request):
        return False


class ProductAdmin(admin.ModelAdmin):
    # Organizes fields into a main section and a sidebar-style preview section
    fieldsets = (
        ("Product Details", {
            'fields': ('product_name', 'category', 'subcategory', 'price', 'desc', 'pub_date', 'stock',
                       'low_stock_threshold')
        }),
        ("Image Preview", {
            'fields': ('image', 'img_preview'),
            'classes': ('img-right-column',),
        }),
    )

    readonly_fields = ('img_preview',)

    def img_preview(self, obj):
        if obj.image:
            return format_html(
                '<div style="text-align: center;">'
                '<img src="{}" style="width: 100%; max-width: 250px; height: auto; border-radius: 8px; border: 1px solid #ccc;"/>'
                '<p style="margin-top: 10px; color: #666; font-weight: bold;">Current Image View</p>'
                '</div>',
                obj.image.url
            )
        return "No Image Uploaded"

    img_preview.short_description = ""

    class Media:
        # This tells Django to load your custom CSS file for this admin page
        css = {
            'all': ('shop/css/admin_custom.css',)
        }