from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('product', 'variant', 'quantity', 'added_at')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'item_count_display', 'updated_at')
    search_fields = ('user__phone', 'user__first_name', 'user__username')
    inlines = [CartItemInline]

    @admin.display(description='Items')
    def item_count_display(self, obj):
        return obj.item_count
