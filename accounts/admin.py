from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import User, UserProfile, ReportUser, ReportEvidence, LoginAttempt, Portfolio, PortfolioType, OTPVerification, PropertyType, AmenityCategory, Amenity, NeighborhoodFeatureCategory, NeighborhoodFeature, Address, Property


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
    list_display = ('name', 'icon')
    search_fields = ('name',)

@admin.register(AmenityCategory)
class AmenityCategoryAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)

@admin.register(Amenity)
class AmenityAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('name', 'category', 'icon', 'is_featured')
    list_filter = ('category', 'is_featured')
    search_fields = ('name',)

@admin.register(NeighborhoodFeatureCategory)
class NeighborhoodFeatureCategoryAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)

@admin.register(NeighborhoodFeature)
class NeighborhoodFeatureAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('name', 'category', 'icon', 'is_essential')
    list_filter = ('category', 'is_essential')
    search_fields = ('name',)

@admin.register(Address)
class AddressAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('street_address', 'city', 'state', 'zip_code', 'country', 'address_verified')
    list_filter = ('country', 'state', 'address_verified')
    search_fields = ('street_address', 'city', 'state', 'zip_code')

@admin.register(Property)
class PropertyAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('title', 'owner', 'property_type', 'price', 'status', 'category', 'is_featured')
    list_filter = ('status', 'category', 'property_type', 'is_featured')
    search_fields = ('title', 'description', 'owner__username')
    raw_id_fields = ('owner', 'agent', 'address')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('amenities', 'neighborhood_features')


admin.site.register(Portfolio)
admin.site.register(PortfolioType)
admin.site.register(OTPVerification)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(ReportUser, ReportUserAdmin)
