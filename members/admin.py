from django.contrib import admin
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    """
    Admin configuration for Member profiles.
    Replaced 'is_active' with 'status' to match the model definition.
    """
    
    # 1. Columns displayed in the list view
    # Using 'get_email' as a custom method to show user data
    list_display = (
        'member_number', 
        'get_full_name', 
        'get_email', 
        'national_id', 
        'status', 
        'date_joined'
    )

    # 2. Filters available in the right sidebar
    # Changed 'is_active' to 'status' to resolve admin.E116
    list_filter = ('status', 'gender', 'date_joined', 'county')

    # 3. Search functionality
    # Allows searching by member number, ID, or the linked user's details
    search_fields = (
        'member_number', 
        'national_id', 
        'user__username', 
        'user__email', 
        'user__first_name', 
        'user__last_name'
    )

    # 4. Organization of the edit form
    fieldsets = (
        ('Account Info', {
            'fields': ('user', 'member_number', 'status')
        }),
        ('Personal Details', {
            'fields': ('national_id', 'kra_pin', 'date_of_birth', 'gender')
        }),
        ('Contact Information', {
            'fields': ('address', 'town', 'county', 'alternative_phone')
        }),
        ('Next of Kin', {
            'fields': ('next_of_kin_name', 'next_of_kin_phone', 'next_of_kin_relationship')
        }),
    )

    # 5. Read-only fields
    readonly_fields = ('date_joined', 'created_at')

    # --- Custom methods to pull data from the User Model ---

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_full_name.short_description = 'Full Name'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email Address'

    # Optimization: Reduces database queries when loading the list
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')