from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from .models import *

class CustomUserAdmin(UserAdmin):
    # The forms to add and change user instances
    model = CustomUser
    
    # Fields to display in the user list
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'role')
    
    # Fields to use in the user creation form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    
    # Fields to use in the user change form
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {
            'fields': ('is_active', 'is_on_duty', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Role', {'fields': ('role',)}),
    )
    
    # Search and ordering configuration
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    
    # Custom filter for role (Group)
    filter_horizontal = ('groups', 'user_permissions',)

# Register your models here
admin.site.register(CustomUser, CustomUserAdmin)

# Optional: Customize the Group admin if needed
class GroupAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    ordering = ('name',)
    filter_horizontal = ('permissions',)

# Unregister the default Group admin and register our custom one
admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
