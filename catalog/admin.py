from django.contrib import admin

from .models import (
    Category,
    ContactMessage,
    NewsletterSubscriber,
    Product,
    ProductImage,
    ProductReview,
    ProductVariant,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 2
    orderable = True
    fields = ('image', 'alt_text', 'display_order')


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('size', 'color', 'stock')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'order', 'product_count')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

    @admin.display(description='Products')
    def product_count(self, obj):
        return obj.products.count()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'discount_percent',
                    'discounted_price_display', 'stock', 'is_active',
                    'is_trending', 'sales_count')
    list_editable = ('price', 'discount_percent', 'stock', 'is_active', 'is_trending')
    list_filter = ('category', 'is_active', 'is_trending', 'is_seasonal', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]
    readonly_fields = ('sales_count', 'created_at', 'updated_at')
    fieldsets = (
        ('Product', {
            'fields': ('name', 'slug', 'category', 'description'),
        }),
        ('Pricing & stock', {
            'fields': ('price', 'discount_percent', 'stock'),
        }),
        ('Visibility', {
            'fields': ('is_active', 'is_trending', 'is_seasonal'),
        }),
        ('Stats', {
            'fields': ('sales_count', 'created_at', 'updated_at'),
        }),
    )

    @admin.display(description='Sale price')
    def discounted_price_display(self, obj):
        return obj.discounted_price


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user__phone', 'user__first_name', 'comment')
    readonly_fields = ('product', 'user', 'rating', 'comment', 'created_at', 'updated_at')


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at')
    search_fields = ('email',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'created_at')
    search_fields = ('subject', 'name', 'email', 'message')
    readonly_fields = ('name', 'email', 'subject', 'message', 'created_at')


admin.site.register(ProductImage)
admin.site.register(ProductVariant)
