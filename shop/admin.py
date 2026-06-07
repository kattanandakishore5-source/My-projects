from django.contrib import admin
from .models import Product, Contact, Orders, OrderUpdate, Coupon, ProductReview
from django.utils.html import format_html

# Basic Model Registrations
admin.site.register(Contact)
admin.site.register(Orders)
admin.site.register(OrderUpdate)

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'valid_from', 'valid_to', 'discount_type', 'discount_value', 'active')
    list_filter = ('active', 'discount_type', 'valid_from', 'valid_to')
    search_fields = ('code',)

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    readonly_fields = ('product', 'user', 'review_text', 'rating', 'image', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

# Fixed: Properly registered the custom ProductAdmin to the Product model
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Image Preview", {
            'fields': ('image', 'img_preview'),
        }),
        ("Product Details", {
            'fields': ('product_name', 'category', 'subcategory', 'price', 'desc', 'pub_date', 'stock',
                       'low_stock_threshold')
        }),
    )

    readonly_fields = ('img_preview',)

    def img_preview(self, obj):
        if obj.image:
            return format_html(
                '<div style="text-align: left;">'
                '<img src="{}" style="width: 7cm; height: 7cm; object-fit: cover; border-radius: 8px; border: 1px solid #ccc; display: block;"/>'
                '</div>',
                obj.image.url
            )
        return "No Image Uploaded"

    img_preview.short_description = ""