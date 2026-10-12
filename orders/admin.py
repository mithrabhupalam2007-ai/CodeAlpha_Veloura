from django.contrib import admin

from .models import Coupon, Order, OrderItem, Payment


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'value', 'min_order_amount',
                    'valid_from', 'valid_to', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('discount_type', 'is_active')
    search_fields = ('code', 'description')
    readonly_fields = ('created_at',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'variant', 'product_name', 'size', 'color',
                       'unit_price', 'quantity')
    can_delete = False


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    max_num = 1
    readonly_fields = ('amount', 'method', 'reference', 'is_demo', 'created_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'full_name', 'total', 'payment_method',
                    'status', 'created_at')
    list_editable = ('status',)
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order_number', 'full_name', 'phone', 'user__phone')
    readonly_fields = ('order_number', 'user', 'subtotal', 'discount_amount',
                       'shipping_amount', 'total', 'coupon', 'created_at', 'updated_at')
    inlines = [OrderItemInline, PaymentInline]
    fieldsets = (
        ('Order', {
            'fields': ('order_number', 'user', 'status', 'customer_note'),
        }),
        ('Customer', {
            'fields': ('full_name', 'phone', 'address_line1', 'address_line2',
                       'city', 'state', 'pincode'),
        }),
        ('Money', {
            'fields': ('subtotal', 'discount_amount', 'shipping_amount',
                       'total', 'coupon', 'payment_method'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'method', 'status', 'is_demo', 'created_at')
    list_filter = ('method', 'status', 'is_demo')
    search_fields = ('order__order_number', 'reference')
    readonly_fields = ('order', 'amount', 'method', 'reference', 'is_demo',
                       'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False  # payments are created by the checkout flow only
