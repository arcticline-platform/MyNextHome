# properties/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import (
    Property, PropertyImage, PropertyVideo, PropertyDocument,
    Address, Amenity, NeighborhoodFeature
)
from django.contrib.gis.geos import Point

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'street_address', 'apartment_suite', 'city', 
            'state', 'country', 'zip_code', 'latitude', 'longitude',
            'nearby_landmarks', 'neighborhood'
        ]
        widgets = {
            'street_address': forms.TextInput(attrs={'placeholder': '123 Main St'}),
            'apartment_suite': forms.TextInput(attrs={'placeholder': 'Apt 4B'}),
            'city': forms.TextInput(attrs={'placeholder': 'New York'}),
            'state': forms.TextInput(attrs={'placeholder': 'NY'}),
            'zip_code': forms.TextInput(attrs={'placeholder': '10001'}),
            'latitude': forms.NumberInput(attrs={'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'step': '0.000001'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if latitude and longitude:
            try:
                cleaned_data['location'] = Point(float(longitude), float(latitude))
            except (ValueError, TypeError):
                raise ValidationError("Invalid latitude or longitude values")
        
        return cleaned_data

class PropertyForm(forms.ModelForm):
    amenities = forms.ModelMultipleChoiceField(
        queryset=Amenity.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    neighborhood_features = forms.ModelMultipleChoiceField(
        queryset=NeighborhoodFeature.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Property
        fields = [
            'title', 'description', 'property_type', 'category',
            # Pricing information
            'price', 'price_currency', 'price_per_sqft', 'is_price_negotiable',
            'hourly_rate', 'nightly_rate', 'monthly_rate', 'yearly_rate',
            'tax_rate', 'hoa_fee', 'cleaning_fee', 'security_deposit',
            
            # Details
            'bedrooms', 'bathrooms', 'square_feet', 'lot_size',
            'year_built', 'floors', 'furnishing_status', 'available_from', 'last_refurbished',
            'amenities', 'neighborhood_features',
            'parking_spaces', 'internet_included', 'furnish_status',
            
            # Commercial & Hospitality
            'shop_size', 'warehouse_capacity', 'office_spaces', 'garage_slots', 'has_storefront',
            'maximum_occupancy', 'minimum_stay_nights', 'check_in_time', 'check_out_time',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'available_from': forms.DateInput(attrs={'type': 'date'}),
            'last_refurbished': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Group amenities by category
        amenities = Amenity.objects.select_related('category').order_by('category__name', 'name')
        amenity_choices = {}
        for amenity in amenities:
            category = amenity.category.name if amenity.category else 'Other'
            if category not in amenity_choices:
                amenity_choices[category] = []
            amenity_choices[category].append((amenity.id, amenity.name))

        self.fields['amenities'].choices = amenity_choices.items()

        # Group neighborhood features by category
        features = NeighborhoodFeature.objects.select_related('category').order_by('category__name', 'name')
        feature_choices = {}
        for feature in features:
            category = feature.category.name if feature.category else 'Other'
            if category not in feature_choices:
                feature_choices[category] = []
            feature_choices[category].append((feature.id, feature.name))

        self.fields['neighborhood_features'].choices = feature_choices.items()

class PropertyImageForm(forms.ModelForm):
    image = forms.ImageField(
        label='Add Image',
        widget=forms.ClearableFileInput(),
        required=False
    )
    
    class Meta:
        model = PropertyImage
        fields = ['image', 'caption', 'is_primary']

class PropertyVideoForm(forms.ModelForm):
    class Meta:
        model = PropertyVideo
        fields = ['video_url', 'caption', 'is_primary']

class PropertyDocumentForm(forms.ModelForm):
    class Meta:
        model = PropertyDocument
        fields = ['document', 'document_type', 'title', 'description']