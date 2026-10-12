from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Address, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'created_at')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('phone', 'first_name', 'last_name', 'email', 'username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Veloura', {'fields': ('phone', 'created_at')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Veloura', {'fields': ('phone',)}),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'city', 'state', 'pincode', 'is_default')
    list_filter = ('is_default', 'state')
    search_fields = ('full_name', 'phone', 'user__phone', 'city', 'pincode')
