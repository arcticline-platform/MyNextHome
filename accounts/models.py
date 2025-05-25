# import os
# import math
import uuid
import random
import string
import datetime
import requests
from datetime import date, datetime, timedelta

from django.db import models
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.core.cache import cache
# from django.dispatch import receiver
from django.utils.text import slugify
# from django.shortcuts import redirect
from django.utils.timezone import now
from django_countries.fields import CountryField
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from core.image_processor import CompressedImageField
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.db import models as gis_models
# from django.db.models.signals import pre_save, post_save
from django.core.validators import FileExtensionValidator, RegexValidator, MinValueValidator, MaxValueValidator

import django_filters
from .managers import CustomUserManager
from core.tasks import create_profile

from core.validators import post_file_extension, validate_image_with_face

from ckeditor.fields import RichTextField
from phonenumber_field.modelfields import PhoneNumberField

AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")


class User(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    is_owner = models.BooleanField(default=False, help_text=_('Designate the user as an owner'))
    is_realtor = models.BooleanField(default=False, help_text=_('Designate the user as a realtor'))
    is_banned = models.BooleanField(default=False, help_text=_('Ban accounts that breach user guidelines'))
    referral_code = models.UUIDField(null=True, blank=True, editable=False)
    REQUIRED_FIELDS = ['email']

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def get_absolute_url(self):
        return reverse('user_detail', args=[str(self.id)])
    
    def get_referral_url(self):
        return reverse('referred_signup', args=[self.referral_code])
    
    def save(self, *args, **kwargs):
        super(User, self).save(*args, **kwargs)

    def get_user_profile(self):
        profile = UserProfile.objects.get(user__id=self.id)
        if profile is not None:
            return profile
        else:
            return None

    @property
    def check_active_subscription(self):
        from finance.models import Subscription
        if Subscription.objects.filter(user__id=self.id, is_active=True).exists():
            return True
        else:
            return False
        
    @property
    def user_subscription(self, request):
        from finance.models import Subscription
        try:
            subscription = Subscription.objects.get(user__id=self.id, is_active=True)
            return subscription
        except Subscription.DoesNotExist:
            messages.error(request, 'You do not have active subscription!')
            return
        
    @property
    def get_user_names(self):
        if self.first_name and self.last_name:
            name = f'{self.first_name} {self.last_name}'
        elif self.first_name:
            name = f'{self.first_name}'
        elif self.last_name:
            name = f'{self.last_name}'
        elif self.username:
            name = f'{self.username}'
        else:
            name = 'User'
        return name


    def save(self, *args, **kwargs):
        # create_profile.apply_async(args=[self.pk,])
        # if UserProfile.objects.filter(user__id=self.id).exists():
        #     pass
        # else:
        #     UserProfile.objects.create(user=self, username=self.username, first_name=self.username, last_name="New User", email=self.email)
        super(User, self).save(*args, **kwargs)


GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )


class LoginAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    username = models.CharField(max_length=150, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField()

    def __str__(self):
        return f"{self.username or 'Unknown'} - {'Success' if self.success else 'Failed'}"


class UserProfile(models.Model):
    user = models.OneToOneField(AUTH_USER_MODEL, models.CASCADE, related_name="user_profile")
    username = models.CharField(max_length=75, unique=True)
    unique_id = models.CharField(max_length=9, help_text='User Unique ID', editable=False, default='000000001')
    first_name = models.CharField(max_length=75)
    last_name = models.CharField(max_length=75, null=True, blank=True)
    other_name = models.CharField(max_length=75, blank=True, null=True)
    photo = CompressedImageField(null=True, blank=True, quality=80, upload_to='users/%Y/%m/%d', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    cover_photo = CompressedImageField(null=True, quality=80, upload_to='users/%Y/%m/%d', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    email = models.EmailField()
    email_confirmed = models.BooleanField(default=False)
    phone = PhoneNumberField(null=True, blank=True, help_text='Follow syntax; start e.g +256')
    country = CountryField(blank_label='(Select Country)', verbose_name=_("Country"), help_text=_("Country of residence"), default='UG')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=75, default="Kampala")
    bio = models.TextField(blank=True, null=True, help_text=_("Hint: What inpires you, what's good about you"))
    interests = models.CharField(max_length=175, blank=True, null=True, help_text=_("e.g Sports, Travel, Vlogging, Engineering, Medicine"))
    user_likes = models.ManyToManyField(User, related_name='profile_likes')
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False, help_text=_("Ban User Profile"))
    is_online = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)


    # def __unicode__(self):
    #     return unicode(self.username)

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        return reverse('user_profile', args=[str(self.id)])

    def last_seen(self):
        return cache.get('last_seen_%s' % self.user.unique_id)

    def online(self):
        if self.last_seen():
            now = datetime.datetime.now()
            if now > (self.last_seen() + datetime.timedelta(seconds=settings.USER_ONLINE_TIMEOUT)):
                return False
            else:
                return True
        else:
            return False
        
    def number_of_likes(self):
        return self.user_likes.count()
    

    def age(self):
        age = (date.today() - self.date_of_birth).days / 365
        return round(age)

    def generate_unique_number(self):
        precede_numbers = '012'
        numbers = '3456789'
        alphanumeric = precede_numbers + numbers
        length = 9
        generate_unique_number = "".join(random.sample(alphanumeric, length))
        while UserProfile.objects.filter(unique_id=generate_unique_number).exists():
            generate_unique_number = "".join(random.sample(alphanumeric, length))
            # return generate_unique_number
        return generate_unique_number
    
    def get_user_currency(self):
        import pycountry
        country_name = self.country.name
        country = pycountry.countries.get(name=country_name)
        currency = pycountry.currencies.get(numeric=country.numeric)
        return currency.alpha_3

    def save(self, *args, **kwargs):
        if self.unique_id == '000000001':
            self.unique_id = self.generate_unique_number()
        super(UserProfile, self).save(*args, **kwargs)


class VerificationToken(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="verification_tokens")
    token = models.CharField(max_length=8, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.token:
            # Generate 8 character token using only digits
            while True:
                token = ''.join(random.choices(string.digits, k=6))
                if not VerificationToken.objects.filter(token=token).exists():
                    self.token = token
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Token for {self.user.username}"


class PortfolioType(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Business Type'
        verbose_name_plural = 'Business Types'

    def clean(self):
        # Ensure name doesn't contain special characters
        if not self.name.replace(' ', '').isalnum():
            raise ValidationError({'name': 'Business type name should only contain letters, numbers, and spaces.'})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Portfolio(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.SET_NULL, null=True, related_name='user_portfolio')
    kind_of_business = models.ForeignKey(PortfolioType, on_delete=models.SET_NULL, null=True)
    business_name = models.CharField(max_length=255)
    business_description = models.TextField(blank=True)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex], max_length=17)
    email = models.EmailField(max_length=254, blank=True)
    documents = models.FileField(upload_to='Portfolio_Documents/%Y/%m/%d', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verified_phone = models.BooleanField(default=False)
    verified_email = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    verification_code = models.CharField(max_length=6, blank=True)
    verification_attempts = models.PositiveIntegerField(default=0)
    last_verification_attempt = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']
        verbose_name = 'User Portfolio'
        verbose_name_plural = 'User Portfolios'

    def clean(self):
        if self.verification_attempts >= 3:
            if self.last_verification_attempt and \
               timezone.now() - self.last_verification_attempt < timezone.timedelta(hours=24):
                raise ValidationError('Maximum verification attempts reached. Please try again after 24 hours.')

    def generate_verification_code(self):
        """Generate a new 6-digit verification code"""
        import random
        return str(random.randint(100000, 999999))

    def verify_business(self, code):
        """Verify business with provided code"""
        if self.verification_code == code:
            self.is_verified = True
            self.verification_code = ''
            self.save()
            return True
        self.verification_attempts += 1
        self.last_verification_attempt = timezone.now()
        self.save()
        return False

    def has_active_payment_links(self):
        """Check if portfolio has any active payment links"""
        return self.payment_links.filter(status='active', expiry_date__gt=timezone.now()).exists()

    def __str__(self):
        return self.business_name


class Receipt(models.Model):
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    payer = models.CharField(max_length=255)
    payee = models.ForeignKey(User, on_delete=models.CASCADE)
    # pay_link = models.ForeignKey(PayLink, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed')
    ])

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['payee', 'status']),
            models.Index(fields=['transaction_id'])
        ]


class ReportUser(models.Model):
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_user')
    complaint = models.TextField()
    is_attended_to = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Reported User'
        verbose_name_plural = 'Reported Users'

    def __str__(self):
        return str(f'Reported User {self.reported_user}')
    

class ReportEvidence(models.Model):
    report = models.ForeignKey(ReportUser, on_delete=models.CASCADE, related_name='report_evidence')
    file = models.FileField(upload_to='ReportEvidence/%Y/%m/%d')
    timestamp = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(f'Report Evidence {self.id}')


def default_expiration_time():
    return now() + timedelta(minutes=10)


class OTPVerification(models.Model):
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    otp = models.CharField(max_length=6)
    expires_at = models.DateTimeField(default=default_expiration_time)
    verified = models.BooleanField(default=False)

    def is_valid(self):
        return now() < self.expires_at
 

class TimeStampedModel(models.Model):
    """Abstract base model for tracking creation and modification times."""
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PropertyType(models.Model):
    """Type of property (House, Apartment, Land, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True)  # For font-awesome or similar icons
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Property Type"
        verbose_name_plural = "Property Types"
        ordering = ['name']

    def __str__(self):
        return self.name


class AmenityCategory(models.Model):
    """Category for grouping amenities (Interior, Exterior, Community, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "Amenity Category"
        verbose_name_plural = "Amenity Categories"

    def __str__(self):
        return self.name


class Amenity(models.Model):
    """Feature or facility available in/around the property"""
    name = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(AmenityCategory, on_delete=models.SET_NULL, null=True, blank=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Amenity"
        verbose_name_plural = "Amenities"
        ordering = ['category__name', 'name']

    def __str__(self):
        return self.name


class NeighborhoodFeatureCategory(models.Model):
    """Category for nearby features (Education, Healthcare, Transportation, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "Neighborhood Feature Category"
        verbose_name_plural = "Neighborhood Feature Categories"

    def __str__(self):
        return self.name


class NeighborhoodFeature(models.Model):
    """Important locations or services near the property"""
    name = models.CharField(max_length=100)
    category = models.ForeignKey(NeighborhoodFeatureCategory, on_delete=models.SET_NULL, null=True, blank=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    is_essential = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Neighborhood Feature"
        verbose_name_plural = "Neighborhood Features"
        ordering = ['category__name', 'name']
        unique_together = ['name', 'category']

    def __str__(self):
        return f"{self.name} ({self.category.name if self.category else 'Uncategorized'})"


class Address(TimeStampedModel):
    """Physical location details with geospatial data using Mapbox"""
    street_address = models.CharField(max_length=255)
    apartment_suite = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    EAST_AFRICAN_COUNTRIES = [
        ('Uganda', 'Uganda'),
        ('Kenya', 'Kenya'),
        ('Tanzania', 'Tanzania'),
        ('Rwanda', 'Rwanda'),
        ('Burundi', 'Burundi'),
        ('South Sudan', 'South Sudan'),
        ('Ethiopia', 'Ethiopia'),
        ('Somalia', 'Somalia'),
        ('Eritrea', 'Eritrea'),
        ('Djibouti', 'Djibouti'),
        ('DR Congo', 'DR Congo'),
    ]
    country = models.CharField(
        max_length=100,
        choices=EAST_AFRICAN_COUNTRIES,
        default="Uganda",
        help_text="Country (East Africa only)"
    )
    zip_code = models.CharField(max_length=10)
    latitude = models.DecimalField(max_digits=13, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=13, decimal_places=6, blank=True, null=True)
    location = gis_models.PointField(geography=True, blank=True, null=True)
    nearby_landmarks = models.TextField(blank=True)
    map_url = models.URLField(blank=True)  
    address_verified = models.BooleanField(default=False)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    neighborhood = models.CharField(max_length=100, blank=True, null=True)
    place_name = models.CharField(max_length=255, blank=True, null=True)  # Full place name from Mapbox
    accuracy = models.CharField(max_length=50, blank=True, null=True)  # Accuracy of geocoding result

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        indexes = [
            models.Index(fields=['city', 'state']),
            models.Index(fields=['zip_code']),
            models.Index(fields=['location']),
        ]

    def __str__(self):
        return f"{self.street_address}, {self.city}, {self.state}, {self.country}"

    def clean(self):
        """Validate address data before saving"""
        if not any([self.street_address, self.city, self.state, self.zip_code]):
            raise ValidationError("At least one of street address, city, state, or zip code must be provided")

    def verify_address(self):
        """Verify address using Mapbox API and update geospatial fields."""
        if not settings.MAPBOX_ACCESS_TOKEN:
            raise ValueError("Mapbox access token is not configured")

        address_query = ", ".join(filter(None, [
            self.street_address,
            self.apartment_suite,
            self.city,
            self.state,
            self.zip_code,
            self.country
        ]))

        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address_query}.json"
        params = {
            'access_token': settings.MAPBOX_ACCESS_TOKEN,
            'country': 'us' if self.country.lower() == 'united states' else None,
            'limit': 1
        }

        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data.get('features'):
                feature = data['features'][0]
                self._update_from_mapbox_feature(feature)
                self._get_timezone_info()
                self.address_verified = True
                self.save()
                return True
            return False
        except requests.RequestException as e:
            raise Exception(f"Error verifying address with Mapbox: {str(e)}")

    def _update_from_mapbox_feature(self, feature):
        """Update address fields from Mapbox feature"""
        # Update coordinates
        longitude, latitude = feature['geometry']['coordinates']
        self.longitude = longitude
        self.latitude = latitude
        self.location = gis_models.Point(longitude, latitude, srid=4326)
        
        # Update address components from context
        context = {item['id'].split('.')[0]: item['text'] for item in feature.get('context', [])}
        
        self.neighborhood = feature.get('text', '') if 'poi' in feature.get('place_type', []) else None
        self.place_name = feature.get('place_name', '')
        self.accuracy = feature.get('relevance', None)
        
        # Update address components if not already set
        if not self.city and 'place' in context:
            self.city = context['place']
        if not self.state and 'region' in context:
            self.state = context['region']
        if not self.zip_code and 'postcode' in context:
            self.zip_code = context['postcode']
        if not self.country and 'country' in context:
            self.country = context['country']

    def _get_timezone_info(self):
        """Get timezone information for the current coordinates"""
        if not (self.latitude and self.longitude):
            return
            
        url = f"https://api.mapbox.com/v4/examples.4ze9z6tv/tilequery/{self.longitude},{self.latitude}.json"
        params = {
            'access_token': settings.MAPBOX_ACCESS_TOKEN,
            'layers': 'timezones'
        }

        try:
            response = requests.get(url, params=params, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get('features'):
                    self.timezone = data['features'][0]['properties']['TZID']
        except requests.RequestException:
            pass  # Timezone lookup is optional, so we ignore errors

    def reverse_geocode(self, latitude, longitude):
        """Populate address fields from coordinates using reverse geocoding"""
        if not settings.MAPBOX_ACCESS_TOKEN:
            raise ValueError("Mapbox access token is not configured")

        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{longitude},{latitude}.json"
        params = {
            'access_token': settings.MAPBOX_ACCESS_TOKEN,
            'types': 'address,poi,neighborhood,place,postcode,region,country'
        }

        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data.get('features'):
                self._update_from_mapbox_feature(data['features'][0])
                self.latitude = latitude
                self.longitude = longitude
                self.location = gis_models.Point(longitude, latitude, srid=4326)
                self._get_timezone_info()
                self.address_verified = True
                return True
            return False
        except requests.RequestException as e:
            raise Exception(f"Error reverse geocoding with Mapbox: {str(e)}")

    def mapbox_url(self):
        """Generate Mapbox URL for this address."""
        if self.latitude and self.longitude:
            return f"https://www.mapbox.com/?map={self.latitude},{self.longitude},15"
        return None

    def static_map_url(self, width=600, height=400, zoom=14):
        """Generate URL for a static map image"""
        if not (self.latitude and self.longitude):
            return None
            
        return (
            f"https://api.mapbox.com/styles/v1/mapbox/streets-v11/static/"
            f"pin-s+000({self.longitude},{self.latitude})/"
            f"{self.longitude},{self.latitude},{zoom}/{width}x{height}"
            f"?access_token={settings.MAPBOX_ACCESS_TOKEN}"
        )

    def get_formatted_address(self):
        """Return a standardized formatted address."""
        components = [
            self.street_address,
            f"Apt {self.apartment_suite}" if self.apartment_suite else None,
            f"{self.city}, {self.state} {self.zip_code}" if self.city else None,
            self.country
        ]
        return ", ".join(filter(None, components))

    def distance_to(self, other_address, unit='mi'):
        """
        Calculate distance to another address using geodjango.
        Returns distance in miles (mi) or kilometers (km)
        """
        if not (self.location and other_address.location):
            return None
            
        distance = self.location.distance(other_address.location)
        
        # Convert from degrees to desired unit
        if unit == 'mi':
            return distance * 69  # Approx miles per degree
        elif unit == 'km':
            return distance * 111.32  # Approx km per degree
        return distance


class Property(TimeStampedModel):
    """Main property listing model"""
    LISTING_STATUS = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('pending', 'Pending Approval'),
        ('sold', 'Sold/Rented'),
        ('hidden', 'Hidden')
    )

    LISTING_CATEGORY = (
        ('sale', 'For Sale'),
        ('rent', 'For Rent'),
        ('lease', 'For Lease'),
        ('short_term', 'Short Term Rental'),
        ('long_term', 'Long Term Rental')
    )

    FURNISHING_STATUS = (
        ('furnished', 'Furnished'),
        ('unfurnished', 'Unfurnished'),
        ('partially', 'Partially Furnished')
    )

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_properties')
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_properties')
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=300, blank=True)
    description = models.TextField()
    property_type = models.ForeignKey(PropertyType, on_delete=models.PROTECT)
    address = models.OneToOneField(Address, on_delete=models.CASCADE, related_name='property')
    
    # Pricing information
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    CURRENCY_CHOICES = [
        ('UGX', 'Ugandan Shilling'),
        ('KES', 'Kenyan Shilling'),
        ('TZS', 'Tanzanian Shilling'),
        ('RWF', 'Rwandan Franc'),
        ('BIF', 'Burundian Franc'),
        ('SSP', 'South Sudanese Pound'),
        ('ETB', 'Ethiopian Birr'),
        ('SOS', 'Somali Shilling'),
        ('ERN', 'Eritrean Nakfa'),
        ('DJF', 'Djiboutian Franc'),
        ('CDF', 'Congolese Franc'),
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('CNY', 'Chinese Yuan'),
    ]
    price_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='UGX',
        help_text="Currency for the property price"
    )
    price_per_sqft = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_price_negotiable = models.BooleanField(default=False)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    # Monthly/annual HOA (Homeowners Association) fee for the property, if applicable
    hoa_fee = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    
    # Property details
    bedrooms = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, validators=[MinValueValidator(0)])
    square_feet = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    lot_size = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    year_built = models.PositiveIntegerField(blank=True, null=True)
    floors = models.PositiveIntegerField(default=1)
    furnishing_status = models.CharField(max_length=20, choices=FURNISHING_STATUS, blank=True, null=True)
    
    # Features
    amenities = models.ManyToManyField(Amenity, blank=True, related_name='properties')
    neighborhood_features = models.ManyToManyField(NeighborhoodFeature, blank=True, related_name='properties')
    
    # Listing management
    status = models.CharField(max_length=20, choices=LISTING_STATUS, default='draft')
    category = models.CharField(max_length=20, choices=LISTING_CATEGORY, default='sale')
    is_featured = models.BooleanField(default=False)
    available_from = models.DateField(blank=True, null=True)
    last_refurbished = models.DateField(blank=True, null=True)

    listed_date = models.DateTimeField(auto_now_add=True)
    
    # Metrics
    view_count = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)], 
        default=0.0
    )
    favorite_count = models.PositiveIntegerField(default=0)

    is_published = models.BooleanField(default=False)
    listed_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='listed_properties')
    rating = models.DecimalField(max_digits=3, decimal_places=2, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)], default=0.0)
    parking_spaces = models.PositiveIntegerField(default=0)
    internet_included = models.BooleanField(default=False)
    PROPERTY_FURNISH_CHOICE = (
        ('furnished', 'Furnished'),
        ('semi-Furnished', 'Semi Furnished'),
        ('unfurnished', 'Unfurnished'),
    )
    furnish_status = models.CharField(max_length=20, choices=PROPERTY_FURNISH_CHOICE, default='unfurnished')
    PROPERTY_AVAILABILITY_CHOICE = (
        ('available','Available'),
        ('sold','Sold'),
        ('rented','Rented'),
        ('under_construction','Under Construction'),
    )
    availability_status = models.CharField(max_length=20, choices=PROPERTY_AVAILABILITY_CHOICE, default='available')

    def __str__(self):
        return f"{self.title} - {self.address.city}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Property.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        
        # Calculate price per sqft if needed
        if self.square_feet and self.price and not self.price_per_sqft:
            self.price_per_sqft = self.price / self.square_feet
        
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Property"
        verbose_name_plural = "Properties"
        ordering = ['-created']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['price']),
            models.Index(fields=['bedrooms']),
            models.Index(fields=['property_type']),
        ]

    def update_view_count(self):
        """Update the view count for the property."""
        self.view_count = self.views.count()
        self.save(update_fields=['view_count'])

    def update_favorite_count(self):
        """Update the favorite count for the property."""
        self.favorite_count = self.favorites.count()
        self.save(update_fields=['favorite_count'])

    def get_primary_image(self):
        """Get the primary image for the property."""
        return self.images.filter(is_primary=True).first() or self.images.first()


class PropertyImage(models.Model):
    """Images associated with a property listing"""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_images/%Y/%m/%d/')
    caption = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Property Image"
        verbose_name_plural = "Property Images"
        ordering = ['order', 'uploaded_at']

    def __str__(self):
        return f"Image for {self.property.title}"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per property
        if self.is_primary:
            PropertyImage.objects.filter(property=self.property).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class PropertyVideo(models.Model):
    """Videos associated with a property listing"""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='videos')
    video_url = models.URLField()
    caption = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Property Video"
        verbose_name_plural = "Property Videos"
        ordering = ['order', 'uploaded_at']

    def __str__(self):
        return f"Video for {self.property.title}"


class PropertyDocument(models.Model):
    """Documents associated with a property (floor plans, contracts, etc.)"""
    DOCUMENT_TYPES = (
        ('floor_plan', 'Floor Plan'),
        ('contract', 'Contract'),
        ('inspection', 'Inspection Report'),
        ('other', 'Other')
    )

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='property_documents/%Y/%m/%d/')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Property Document"
        verbose_name_plural = "Property Documents"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.document_type()} for {self.property.title}"


class NeighborhoodInfo(models.Model):
    """Detailed information about the neighborhood"""
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='neighborhood_info')
    description = models.TextField(blank=True)
    walk_score = models.PositiveIntegerField(blank=True, null=True, validators=[MaxValueValidator(100)])
    transit_score = models.PositiveIntegerField(blank=True, null=True, validators=[MaxValueValidator(100)])
    bike_score = models.PositiveIntegerField(blank=True, null=True, validators=[MaxValueValidator(100)])
    noise_level = models.CharField(max_length=50, blank=True, null=True)  # Quiet, Moderate, Loud
    safety_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        blank=True, 
        null=True, 
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)]
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Neighborhood Information"
        verbose_name_plural = "Neighborhood Information"

    def __str__(self):
        return f"Neighborhood info for {self.property.title}"


class PropertyView(TimeStampedModel):
    """Tracks property views by users"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='views')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    referrer = models.URLField(blank=True, null=True)

    class Meta:
        verbose_name = "Property View"
        verbose_name_plural = "Property Views"
        indexes = [
            models.Index(fields=['property', 'created']),
        ]

    def __str__(self):
        return f"View of {self.property.title} by {self.user or 'Anonymous'}"


class FavoriteProperty(TimeStampedModel):
    """Tracks user favorites for properties"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='favorites')
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Favorite Property"
        verbose_name_plural = "Favorite Properties"
        unique_together = ('user', 'property')
        ordering = ['-created']

    def __str__(self):
        return f"{self.user.username} favorited {self.property.title}"


class PropertyContact(TimeStampedModel):
    """Contact requests for a property"""
    CONTACT_METHOD = (
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('sms', 'Text Message'),
        ('whatsapp', 'WhatsApp')
    )

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='contacts')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    preferred_contact = models.CharField(max_length=20, choices=CONTACT_METHOD, default='email')
    message = models.TextField()
    is_contacted = models.BooleanField(default=False)
    contacted_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Property Contact"
        verbose_name_plural = "Property Contacts"
        ordering = ['-created']

    def __str__(self):
        return f"Contact request for {self.property.title} from {self.name}"
    

class PropertyPayment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    currency = models.CharField(max_length=3,default='USD',help_text="ISO 4217 currency code (e.g., USD, EUR, GBP)")
    usd_price = models.DecimalField(max_digits=12,decimal_places=2,validators=[MinValueValidator(0)],help_text="Price converted to USD")# All currencies are automatically converted to USD
    exchange_rate = models.DecimalField(max_digits=10,decimal_places=6,help_text="Exchange rate when price was converted to USD")
    # Exchange rate at the time of conversion
    conversion_date = models.DateTimeField(auto_now=True)# Conversion timestamp
    PAYMENT_TYPE_CHOICE = (
        ('cash', 'Cash'),
        ('installments', 'Installments'),
        ('rent_to_own', 'Rent-to-Own'),
    )
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICE, default='cash')
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    down_payment = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True)
