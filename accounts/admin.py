from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import (
    User, UserProfile, ReportUser, ReportEvidence, LoginAttempt, Portfolio, 
    PortfolioType, OTPVerification, PropertyType, AmenityCategory, Amenity, 
    NeighborhoodFeatureCategory, NeighborhoodFeature, Address, Property, 
    VerificationToken, Receipt, PropertyImage, PropertyVideo, PropertyDocument,
    NeighborhoodInfo, PropertyView, FavoriteProperty, PropertyContact, Chat, 
    Message, PropertyPayment
)


from import_export.admin import ExportActionMixin


class UserAdmin(ExportActionMixin, UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = UserAdmin
    list_display = (
        'email', 'username', 'first_name', 'last_name', 'is_staff', 'is_active',)
    list_filter = ('is_staff', 'is_active', 'date_joined', 'last_login',)
    filter_horizontal = ('groups', 'user_permissions',) 
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')
        }),
    )
    list_per_page = 50
    fieldsets = (
        (None, {'fields': ('email', 'first_name', 'last_name', 'password', 'date_joined', 'last_login')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups')}),
    )
    search_fields = ('email', 'first_name', 'last_name',)
    ordering = ('email',)


class UserProfileAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('user', 'email', 'username', 'first_name', 'last_name', 'is_online')
    list_per_page = 50
    search_fields = ('email', 'first_name', 'last_name',)
    list_filter = ('is_verified',)


class ReportEvidenceInline(admin.TabularInline):
    model = ReportEvidence
    raw_id_fields = ['report']

class ReportUserAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('reported_user', 'timestamp')
    list_per_page = 50
    search_fields = ('complaints',)
    list_filter = ('is_attended_to',)
    inlines = [ReportEvidenceInline]


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('username', 'ip_address', 'timestamp', 'success')
    list_filter = ('success', 'timestamp')
    search_fields = ('username', 'ip_address')

@admin.register(PropertyType)
class PropertyTypeAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('name', 'icon', 'is_commercial', 'is_residential', 'is_hospitality', 'default_pricing_model')
    list_filter = ('is_commercial', 'is_residential', 'is_hospitality', 'default_pricing_model')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('get_icon_class',)

@admin.register(AmenityCategory)
class AmenityCategoryAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)

@admin.register(Amenity)
class AmenityAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('name', 'category', 'icon', 'is_featured', 'is_premium', 'applies_to_residential', 'applies_to_commercial', 'applies_to_hospitality')
    list_filter = ('category', 'is_featured', 'is_premium', 'applies_to_residential', 'applies_to_commercial', 'applies_to_hospitality')
    search_fields = ('name',)
    readonly_fields = ('get_icon_class',)

@admin.register(NeighborhoodFeatureCategory)
class NeighborhoodFeatureCategoryAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)

@admin.register(NeighborhoodFeature)
class NeighborhoodFeatureAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('name', 'category', 'icon', 'is_essential', 'distance_km')
    list_filter = ('category', 'is_essential')
    search_fields = ('name',)
    readonly_fields = ('get_icon_class', 'get_distance_display')

@admin.register(Address)
class AddressAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('street_address', 'city', 'state', 'zip_code', 'country', 'address_verified')
    list_filter = ('country', 'state', 'address_verified')
    search_fields = ('street_address', 'city', 'state', 'zip_code')

@admin.register(Property)
class PropertyAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('title', 'owner', 'property_type', 'category', 'price', 'nightly_rate', 'status', 'is_featured')
    list_filter = ('status', 'category', 'property_type', 'is_featured', 'property_type__is_commercial', 'property_type__is_hospitality')
    search_fields = ('title', 'description', 'owner__username', 'owner__email')
    raw_id_fields = ('owner', 'agent', 'address', 'listed_by')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('amenities', 'neighborhood_features')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'agent', 'title', 'slug', 'description', 'property_type', 'address')
        }),
        ('Pricing', {
            'fields': ('price', 'price_currency', 'hourly_rate', 'nightly_rate', 'monthly_rate', 'yearly_rate', 
                      'price_per_sqft', 'is_price_negotiable', 'tax_rate', 'hoa_fee', 'cleaning_fee', 'security_deposit'),
            'classes': ('collapse',)
        }),
        ('Property Details', {
            'fields': ('bedrooms', 'bathrooms', 'square_feet', 'lot_size', 'year_built', 'floors', 
                      'furnishing_status', 'parking_spaces', 'internet_included')
        }),
        ('Commercial Fields', {
            'fields': ('shop_size', 'warehouse_capacity', 'office_spaces', 'garage_slots', 'has_storefront'),
            'classes': ('collapse',)
        }),
        ('Hospitality Fields', {
            'fields': ('maximum_occupancy', 'minimum_stay_nights', 'check_in_time', 'check_out_time'),
            'classes': ('collapse',)
        }),
        ('Features', {
            'fields': ('amenities', 'neighborhood_features')
        }),
        ('Listing Management', {
            'fields': ('status', 'category', 'is_featured', 'is_published', 'available_from', 'last_refurbished', 'availability_status')
        }),
        ('Metrics', {
            'fields': ('view_count', 'rating', 'favorite_count'),
            'classes': ('collapse',)
        }),
    )


admin.site.register(Portfolio)
admin.site.register(PortfolioType)
admin.site.register(OTPVerification)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(ReportUser, ReportUserAdmin)
admin.site.register(Receipt)
admin.site.register(PropertyImage)
admin.site.register(PropertyVideo)
admin.site.register(PropertyDocument)
admin.site.register(NeighborhoodInfo)
admin.site.register(PropertyView)
admin.site.register(FavoriteProperty)
admin.site.register(PropertyContact)
admin.site.register(Chat)
admin.site.register(Message)
admin.site.register(PropertyPayment)
admin.site.register(VerificationToken)
admin.site.register(ReportEvidence)

