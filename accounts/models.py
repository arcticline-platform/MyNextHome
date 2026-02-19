import os
import io
# import math
import uuid
import random
import string
import datetime
import requests
from datetime import date, datetime, timedelta

# import django_filters
from django.db import models
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.core.cache import cache
from django.dispatch import receiver
from django.db.models.signals import pre_delete, post_delete
from django.utils.text import slugify
# from django.shortcuts import redirect
from django.utils.timezone import now
from django.core.files.base import ContentFile
from django_countries.fields import CountryField
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from core.image_processor import CompressedImageField
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.db import models as gis_models
from django.db.models.signals import pre_save, post_save
from django.core.validators import FileExtensionValidator, RegexValidator, MinValueValidator, MaxValueValidator


from moviepy import VideoFileClip
from PIL import Image

from .managers import CustomUserManager
# from core.tasks import create_profile
# from core.validators import post_file_extension, validate_image_with_face

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
        if self.pk:
            try:
                old_profile = UserProfile.objects.get(pk=self.pk)
                if old_profile.photo and self.photo != old_profile.photo:
                    if os.path.isfile(old_profile.photo.path):
                        os.remove(old_profile.photo.path)
            except UserProfile.DoesNotExist:
                pass
            except Exception:
                pass

        if self.unique_id == '000000001':
            self.unique_id = self.generate_unique_number()
        super(UserProfile, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.photo:
            if os.path.isfile(self.photo.path):
                os.remove(self.photo.path)
        super(UserProfile, self).delete(*args, **kwargs)


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
    """Type of property (House, Apartment, Land, Hotel, Shop, etc.)"""
    
    # Predefined property type choices with icons
    PROPERTY_TYPE_CHOICES = [
        # Residential
        ('house', 'House'),
        ('apartment', 'Apartment'),
        ('condo', 'Condominium'),
        ('townhouse', 'Townhouse'),
        ('villa', 'Villa'),
        ('studio', 'Studio'),
        ('duplex', 'Duplex'),
        ('penthouse', 'Penthouse'),
        ('land', 'Land/Plot'),
        
        # Hospitality
        ('hotel_room', 'Hotel Room'),
        ('airbnb', 'Airbnb/Vacation Rental'),
        ('hostel', 'Hostel'),
        ('guest_house', 'Guest House'),
        
        # Commercial
        ('shop', 'Shop/Retail Space'),
        ('office', 'Office Space'),
        ('warehouse', 'Warehouse'),
        ('garage', 'Garage/Parking'),
        ('restaurant', 'Restaurant'),
        ('mall_space', 'Mall Space'),
        ('showroom', 'Showroom'),
        ('factory', 'Factory'),
        ('storage', 'Storage Unit'),
        
        # Mixed/Other
        ('commercial_building', 'Commercial Building'),
        ('mixed_use', 'Mixed Use'),
        ('other', 'Other'),
    ]
    
    # Icon mapping for property types (Font Awesome classes)
    ICON_CHOICES = {
        'house': 'fa-home',
        'apartment': 'fa-building',
        'condo': 'fa-building-columns',
        'townhouse': 'fa-house-chimney',
        'villa': 'fa-house-flag',
        'studio': 'fa-door-open',
        'duplex': 'fa-house-laptop',
        'penthouse': 'fa-crown',
        'land': 'fa-mountain-sun',
        'hotel_room': 'fa-hotel',
        'airbnb': 'fa-house-user',
        'hostel': 'fa-bed',
        'guest_house': 'fa-house-circle-check',
        'shop': 'fa-shop',
        'office': 'fa-briefcase',
        'warehouse': 'fa-warehouse',
        'garage': 'fa-car',
        'restaurant': 'fa-utensils',
        'mall_space': 'fa-store',
        'showroom': 'fa-spray-can-sparkles',
        'factory': 'fa-industry',
        'storage': 'fa-box-archive',
        'commercial_building': 'fa-building-shield',
        'mixed_use': 'fa-city',
        'other': 'fa-question-circle',
    }
    
    PRICING_MODEL_CHOICES = [
        ('fixed', 'Fixed Price'),
        ('per_night', 'Per Night'),
        ('per_hour', 'Per Hour'),
        ('per_month', 'Per Month'),
        ('per_year', 'Per Year'),
        ('per_sqft', 'Per Square Foot'),
    ]
    
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text='Font Awesome icon class (e.g., fa-home)')
    description = models.TextField(blank=True)
    is_commercial = models.BooleanField(default=False, help_text='Is this a commercial property type?')
    is_residential = models.BooleanField(default=True, help_text='Is this a residential property type?')
    is_hospitality = models.BooleanField(default=False, help_text='Is this a hospitality property type?')
    default_pricing_model = models.CharField(
        max_length=20, 
        choices=PRICING_MODEL_CHOICES, 
        default='fixed',
        help_text='Default pricing model for this property type'
    )
    
    # Feature flags for conditional UI
    has_bedrooms = models.BooleanField(default=True, help_text='Does this property type usually have bedrooms?')
    has_bathrooms = models.BooleanField(default=True, help_text='Does this property type usually have bathrooms?')
    has_floors = models.BooleanField(default=True, help_text='Does this property type have floors?')
    has_furnishing = models.BooleanField(default=True, help_text='Can this property type be furnished?')

    class Meta:
        verbose_name = "Property Type"
        verbose_name_plural = "Property Types"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        
        # Ensure slug is unique even if database constraint is removed
        original_slug = self.slug
        counter = 1
        while PropertyType.objects.filter(slug=self.slug).exclude(id=self.id).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1

        # Auto-set icon if name matches predefined types
        if not self.icon:
            for key, label in self.PROPERTY_TYPE_CHOICES:
                if self.name.lower() == label.lower():
                    self.icon = self.ICON_CHOICES.get(key, 'fa-home')
                    break
        super().save(*args, **kwargs)
    
    def get_icon_class(self):
        """Returns the Font Awesome icon class"""
        return self.icon or 'fa-home'



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
    
    # Predefined common amenities
    AMENITY_CHOICES = [
        # Residential Interior
        ('wifi', 'WiFi/Internet'),
        ('ac', 'Air Conditioning'),
        ('heating', 'Heating'),
        ('furnished', 'Furnished'),
        ('kitchen', 'Full Kitchen'),
        ('dishwasher', 'Dishwasher'),
        ('washer_dryer', 'Washer & Dryer'),
        ('fireplace', 'Fireplace'),
        ('hardwood_floors', 'Hardwood Floors'),
        
        # Residential Exterior
        ('pool', 'Swimming Pool'),
        ('gym', 'Gym/Fitness Center'),
        ('parking', 'Parking Space'),
        ('garage', 'Private Garage'),
        ('garden', 'Garden/Yard'),
        ('balcony', 'Balcony/Terrace'),
        ('elevator', 'Elevator'),
        ('security', 'Security System'),
        ('gated', 'Gated Community'),
        ('playground', 'Playground'),
        
        # Commercial Specific
        ('loading_dock', 'Loading Dock'),
        ('office_space', 'Office Space'),
        ('display_windows', 'Display Windows'),
        ('storage_room', 'Storage Room'),
        ('climate_control', 'Climate Control'),
        ('high_ceiling', 'High Ceilings'),
        ('conference_room', 'Conference Room'),
        ('reception', 'Reception Area'),
        ('kitchenette', 'Kitchenette'),
        
        # Hospitality Specific
        ('room_service', 'Room Service'),
        ('concierge', 'Concierge'),
        ('spa', 'Spa'),
        ('restaurant', 'Restaurant'),
        ('breakfast', 'Breakfast Included'),
        ('laundry_service', 'Laundry Service'),
        
        # General
        ('pet_friendly', 'Pet Friendly'),
        ('wheelchair_accessible', 'Wheelchair Accessible'),
        ('solar_panels', 'Solar Panels'),
        ('backup_generator', 'Backup Generator'),
    ]
    
    # Icon mapping for amenities
    ICON_CHOICES = {
        'wifi': 'fa-wifi',
        'ac': 'fa-snowflake',
        'heating': 'fa-temperature-high',
        'furnished': 'fa-couch',
        'kitchen': 'fa-kitchen-set',
        'dishwasher': 'fa-sink',
        'washer_dryer': 'fa-jug-detergent',
        'fireplace': 'fa-fire',
        'hardwood_floors': 'fa-layer-group',
        'pool': 'fa-swimming-pool',
        'gym': 'fa-dumbbell',
        'parking': 'fa-square-parking',
        'garage': 'fa-warehouse',
        'garden': 'fa-tree',
        'balcony': 'fa-house-chimney-window',
        'elevator': 'fa-elevator',
        'security': 'fa-shield-halved',
        'gated': 'fa-lock',
        'playground': 'fa-child',
        'loading_dock': 'fa-truck-ramp-box',
        'office_space': 'fa-building-user',
        'display_windows': 'fa-window-restore',
        'storage_room': 'fa-boxes-stacked',
        'climate_control': 'fa-temperature-half',
        'high_ceiling': 'fa-up-long',
        'conference_room': 'fa-people-roof',
        'reception': 'fa-bell-concierge',
        'kitchenette': 'fa-mug-hot',
        'room_service': 'fa-bell',
        'concierge': 'fa-user-tie',
        'spa': 'fa-spa',
        'restaurant': 'fa-utensils',
        'breakfast': 'fa-bread-slice',
        'laundry_service': 'fa-shirt',
        'pet_friendly': 'fa-paw',
        'wheelchair_accessible': 'fa-wheelchair',
        'solar_panels': 'fa-solar-panel',
        'backup_generator': 'fa-plug',
    }
    
    name = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(AmenityCategory, on_delete=models.SET_NULL, null=True, blank=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text='Font Awesome icon class')
    is_featured = models.BooleanField(default=False, help_text='Show as featured amenity')
    is_premium = models.BooleanField(default=False, help_text='Premium/Luxury amenity')
    applies_to_residential = models.BooleanField(default=True, help_text='Available for residential properties')
    applies_to_commercial = models.BooleanField(default=False, help_text='Available for commercial properties')
    applies_to_hospitality = models.BooleanField(default=False, help_text='Available for hospitality properties')

    class Meta:
        verbose_name = "Amenity"
        verbose_name_plural = "Amenities"
        ordering = ['category__name', 'name']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Auto-set icon if name matches predefined amenities
        if not self.icon:
            for key, label in self.AMENITY_CHOICES:
                if self.name.lower() == label.lower():
                    self.icon = self.ICON_CHOICES.get(key, 'fa-check-circle')
                    break
        super().save(*args, **kwargs)
    
    def get_icon_class(self):
        """Returns the Font Awesome icon class"""
        return self.icon or 'fa-check-circle'



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
    
    # Predefined common features
    FEATURE_CHOICES = [
        # Education
        ('school', 'School'),
        ('college', 'College/University'),
        ('library', 'Library'),
        
        # Healthcare
        ('hospital', 'Hospital'),
        ('clinic', 'Clinic'),
        ('pharmacy', 'Pharmacy'),
        
        # Shopping
        ('mall', 'Shopping Mall'),
        ('supermarket', 'Supermarket'),
        ('market', 'Local Market'),
        
        # Transportation
        ('bus_stop', 'Bus Stop'),
        ('train_station', 'Train Station'),
        ('airport', 'Airport'),
        ('taxi_stand', 'Taxi Stand'),
        
        # Recreation
        ('park', 'Park'),
        ('gym', 'Gym'),
        ('cinema', 'Cinema'),
        ('restaurant', 'Restaurants'),
        ('cafe', 'Cafes'),
        
        # Worship
        ('mosque', 'Mosque'),
        ('church', 'Church'),
        ('temple', 'Temple'),
        
        # Services
        ('bank', 'Bank/ATM'),
        ('post_office', 'Post Office'),
        ('police_station', 'Police Station'),
        ('fire_station', 'Fire Station'),
        
        # Other
        ('beach', 'Beach'),
        ('gas_station', 'Gas Station'),
    ]
    
    # Icon mapping for features
    ICON_CHOICES = {
        'school': 'fa-school',
        'college': 'fa-graduation-cap',
        'library': 'fa-book',
        'hospital': 'fa-hospital',
        'clinic': 'fa-clinic-medical',
        'pharmacy': 'fa-prescription-bottle-medical',
        'mall': 'fa-shopping-bag',
        'supermarket': 'fa-cart-shopping',
        'market': 'fa-store',
        'bus_stop': 'fa-bus',
        'train_station': 'fa-train',
        'airport': 'fa-plane',
        'taxi_stand': 'fa-taxi',
        'park': 'fa-tree',
        'gym': 'fa-dumbbell',
        'cinema': 'fa-film',
        'restaurant': 'fa-utensils',
        'cafe': 'fa-mug-saucer',
        'mosque': 'fa-mosque',
        'church': 'fa-church',
        'temple': 'fa-place-of-worship',
        'bank': 'fa-building-columns',
        'post_office': 'fa-envelope',
        'police_station': 'fa-shield-halved',
        'fire_station': 'fa-fire-extinguisher',
        'beach': 'fa-umbrella-beach',
        'gas_station': 'fa-gas-pump',
    }
    
    name = models.CharField(max_length=100)
    category = models.ForeignKey(NeighborhoodFeatureCategory, on_delete=models.SET_NULL, null=True, blank=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text='Font Awesome icon class')
    is_essential = models.BooleanField(default=False, help_text='Essential service/feature')
    distance_km = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True,
        help_text='Distance from property in kilometers'
    )

    class Meta:
        verbose_name = "Neighborhood Feature"
        verbose_name_plural = "Neighborhood Features"
        ordering = ['category__name', 'name']
        unique_together = ['name', 'category']

    def __str__(self):
        return f"{self.name} ({self.category.name if self.category else 'Uncategorized'})"
    
    def save(self, *args, **kwargs):
        # Auto-set icon if name matches predefined features
        if not self.icon:
            for key, label in self.FEATURE_CHOICES:
                if self.name.lower() == label.lower():
                    self.icon = self.ICON_CHOICES.get(key, 'fa-location-dot')
                    break
        super().save(*args, **kwargs)
    
    def get_icon_class(self):
        """Returns the Font Awesome icon class"""
        return self.icon or 'fa-location-dot'
    
    def get_distance_display(self):
        """Returns formatted distance"""
        if self.distance_km:
            if self.distance_km < 1:
                return f"{int(self.distance_km * 1000)}m"
            return f"{self.distance_km}km"
        return "N/A"



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
        ('long_term', 'Long Term Rental'),
        ('hourly', 'Hourly Rental'),
        ('nightly', 'Nightly Rental'),
        ('monthly', 'Monthly Rental'),
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
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], null=True, blank=True)
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
    
    # Flexible pricing for different property types
    hourly_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(0)],
        help_text='Hourly rental rate (for parking, meeting rooms, etc.)'
    )
    nightly_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(0)],
        help_text='Nightly rate (for hotels, Airbnb, etc.)'
    )
    monthly_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(0)],
        help_text='Monthly rental rate'
    )
    yearly_rate = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(0)],
        help_text='Yearly rental/lease rate'
    )
    
    # Property details
    bedrooms = models.PositiveIntegerField(validators=[MinValueValidator(0)], blank=True, null=True, help_text='Number of bedrooms (0 for studio)')
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, validators=[MinValueValidator(0)], blank=True, null=True)
    square_feet = models.PositiveIntegerField(validators=[MinValueValidator(0)], blank=True, null=True)
    lot_size = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    year_built = models.PositiveIntegerField(blank=True, null=True)
    floors = models.PositiveIntegerField(default=1, blank=True, null=True)
    furnishing_status = models.CharField(max_length=20, choices=FURNISHING_STATUS, blank=True, null=True)
    
    # Commercial property specific fields
    shop_size = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        help_text='Shop/retail space size in sq ft'
    )
    warehouse_capacity = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        blank=True, 
        null=True,
        help_text='Warehouse storage capacity in cubic feet or tons'
    )
    office_spaces = models.PositiveIntegerField(
        blank=True, 
        null=True,
        help_text='Number of individual office spaces/rooms'
    )
    garage_slots = models.PositiveIntegerField(
        blank=True, 
        null=True,
        help_text='Number of parking/garage slots'
    )
    has_storefront = models.BooleanField(
        default=False,
        help_text='Has street-facing storefront (for shops)'
    )
    
    # Hospitality property specific fields
    maximum_occupancy = models.PositiveIntegerField(
        blank=True, 
        null=True,
        help_text='Maximum number of guests (for hotels/Airbnb)'
    )
    minimum_stay_nights = models.PositiveIntegerField(
        blank=True, 
        null=True,
        help_text='Minimum stay requirement in nights'
    )
    check_in_time = models.TimeField(
        blank=True, 
        null=True,
        help_text='Standard check-in time'
    )
    check_out_time = models.TimeField(
        blank=True, 
        null=True,
        help_text='Standard check-out time'
    )
    cleaning_fee = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(0)],
        help_text='One-time cleaning fee'
    )
    security_deposit = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        validators=[MinValueValidator(0)],
        help_text='Refundable security deposit'
    )
    
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
    compressed_image = models.ImageField(upload_to='property_images/compressed/%Y/%m/%d/', blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    processed = models.BooleanField(default=False)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # In bytes
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Property Image"
        verbose_name_plural = "Property Images"
        ordering = ['order', 'uploaded_at']

    def __str__(self):
        return f"Image for {self.property.title}"

    def compress_image(self):
        """Compress the image while maintaining quality"""
        if self.image and not self.processed:
            img = None
            try:
                # Open image
                img = Image.open(self.image)
                
                # Get original dimensions
                self.width = img.width 
                self.height = img.height
                self.file_size = self.image.size

                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # Calculate new dimensions while maintaining aspect ratio
                max_size = (1920, 1080)  # Full HD
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

                # Save compressed version
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                output.seek(0)

                # Save compressed file
                self.compressed_image.save(
                    f"{self.image.name.split('/')[-1]}_compressed.jpg",
                    ContentFile(output.getvalue()),
                    save=False
                )

                self.processed = True

            except Exception as e:
                print(f"Error processing image: {e}")
            finally:
                if img is not None:
                    img.close()

    def save(self, *args, **kwargs):
        # Ensure only one primary image per property
        if self.is_primary:
            PropertyImage.objects.filter(property=self.property).exclude(pk=self.pk).update(is_primary=False)
        
        # Compress image if not already processed
        if not self.processed:
            self.compress_image()
            
        super().save(*args, **kwargs)

    def get_image_url(self):
        """Returns the URL of the compressed image if available, otherwise original"""
        return self.compressed_image.url if self.compressed_image else self.image.url


class PropertyVideo(models.Model):
    """Videos associated with a property listing"""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='videos')
    video = models.FileField(
        upload_to='property_videos/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['mp4', 'mov', 'avi', 'mkv']
            )
        ],
        null=True,
        blank=True
    )
    video_url = models.URLField(blank=True, null=True)  # For processed/compressed version
    thumbnail = models.ImageField(
        upload_to='property_video_thumbnails/%Y/%m/%d/',
        blank=True,
        null=True
    )
    caption = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    duration = models.DurationField(null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)  # In bytes
    processed = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Property Video"
        verbose_name_plural = "Property Videos"
        ordering = ['order', 'uploaded_at']

    def __str__(self):
        return f"Video for {self.property.title}"

    def save(self, *args, **kwargs):
        if not self.processed and self.video:
            try:

                # Load video
                video = VideoFileClip(self.video.path)
                
                # Get video info
                self.duration = timedelta(seconds=video.duration)
                self.file_size = self.video.size

                # Create thumbnail from first frame
                frame = video.get_frame(0)
                img = Image.fromarray(frame)
                thumb_io = io.BytesIO()
                img.save(thumb_io, format='JPEG', quality=85)
                
                # Save thumbnail
                self.thumbnail.save(
                    f"{self.video.name.split('/')[-1]}_thumb.jpg",
                    ContentFile(thumb_io.getvalue()),
                    save=False
                )

                # Compress video if needed (over 100MB)
                if self.file_size > 100 * 1024 * 1024:  # 100MB
                    output_path = f"{self.video.path}_compressed.mp4"
                    video.write_videofile(
                        output_path,
                        codec='libx264',
                        audio_codec='aac',
                        preset='medium',
                        fps=24,
                        bitrate="2000k"
                    )
                    
                    # Update video file
                    with open(output_path, 'rb') as f:
                        self.video.save(
                            f"{self.video.name.split('/')[-1]}_compressed.mp4",
                            ContentFile(f.read()),
                            save=False
                        )
                    
                    os.remove(output_path)

                video.close()
                self.processed = True

            except Exception as e:
                print(f"Error processing video: {e}")

        super().save(*args, **kwargs)

    def get_video_url(self):
        """Returns the URL of the video (processed version if available)"""
        return self.video_url or self.video.url if self.video else None


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
    
    def create_chat(self):
        """Create a chat conversation from this contact request"""
        from .models import Chat
        chat, created = Chat.objects.get_or_create(
            property=self.property,
            participant=self.user if self.user else None,
            defaults={
                'property_contact': self,
                'other_participant_name': self.name,
                'other_participant_email': self.email,
            }
        )
        if created and self.message:
            # Create initial message from contact request
            Message.objects.create(
                chat=chat,
                sender=None,  # External user
                content=self.message,
                is_read=False
            )
        return chat


class Chat(TimeStampedModel):
    """Chat conversation between users about a property"""
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='chats')
    participant = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='chats')
    property_contact = models.OneToOneField(PropertyContact, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat')
    
    # For non-authenticated users
    other_participant_name = models.CharField(max_length=100, blank=True, null=True)
    other_participant_email = models.EmailField(blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Chat"
        verbose_name_plural = "Chats"
        ordering = ['-last_message_at', '-created']
        unique_together = [['property', 'participant']]
    
    def __str__(self):
        if self.participant:
            return f"Chat: {self.property.title} - {self.participant.username}"
        return f"Chat: {self.property.title} - {self.other_participant_name or 'Guest'}"
    
    def get_other_participant(self, current_user):
        """Get the other participant in the chat"""
        if self.property.owner == current_user:
            return self.participant if self.participant else None
        return self.property.owner
    
    def get_other_participant_name(self, current_user):
        """Get the name of the other participant"""
        if self.property.owner == current_user:
            if self.participant:
                return self.participant.get_full_name() or self.participant.username
            return self.other_participant_name or 'Guest'
        return self.property.owner.get_full_name() or self.property.owner.username
    
    def get_unread_count(self, user):
        """Get unread message count for a user"""
        return self.messages.filter(is_read=False).exclude(sender=user).count()
    
    def mark_as_read(self, user):
        """Mark all messages as read for a user"""
        self.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)


class Message(TimeStampedModel):
    """Individual message in a chat"""
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_messages')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # For file attachments (future enhancement)
    attachment = models.FileField(upload_to='chat_attachments/%Y/%m/%d/', blank=True, null=True)
    attachment_type = models.CharField(max_length=50, blank=True, null=True)  # image, document, etc.
    
    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ['created']
    
    def __str__(self):
        sender_name = self.sender.username if self.sender else 'Guest'
        return f"Message from {sender_name} in {self.chat}"
    
    def mark_as_read(self):
        """Mark this message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


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


@receiver(pre_delete, sender=UserProfile)
def delete_user_profile_photo(sender, instance, **kwargs):
    if instance.photo:
        try:
            if os.path.isfile(instance.photo.path):
                os.remove(instance.photo.path)
        except Exception:
            pass


@receiver(pre_delete, sender=PropertyImage)
def delete_property_image_files(sender, instance, **kwargs):
    # Delete original image
    if instance.image:
        try:
            if os.path.isfile(instance.image.path):
                os.remove(instance.image.path)
        except Exception:
            pass
    # Delete compressed image
    if instance.compressed_image:
        try:
            if os.path.isfile(instance.compressed_image.path):
                os.remove(instance.compressed_image.path)
        except Exception:
            pass


@receiver(pre_delete, sender=PropertyVideo)
def delete_property_video_files(sender, instance, **kwargs):
    if instance.video:
        try:
            if os.path.isfile(instance.video.path):
                os.remove(instance.video.path)
        except Exception:
            pass
    if instance.thumbnail:
        try:
            if os.path.isfile(instance.thumbnail.path):
                os.remove(instance.thumbnail.path)
        except Exception:
            pass
