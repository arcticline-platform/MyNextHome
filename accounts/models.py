# import os
# import math
import uuid
import random
# import string
import datetime
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
from django.contrib.auth.models import AbstractUser
from core.image_processor import CompressedImageField
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
# from django.db.models.signals import pre_save, post_save
from django.core.validators import FileExtensionValidator, RegexValidator, MinValueValidator

import django_filters
from .managers import CustomUserManager
from core.tasks import create_profile

from core.validators import post_file_extension, validate_image_with_face

from ckeditor.fields import RichTextField
from phonenumber_field.modelfields import PhoneNumberField

AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")


class User(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    is_subscribed = models.BooleanField(default=False, help_text=_('Designate the user as a buyer'))
    is_creator = models.BooleanField(default=False, help_text=_('Designate the user as a creator'))
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


class ProfileFilter(django_filters.FilterSet):
    class Meta:
        model = UserProfile
        fields = ['country', ]#'is_verified'
   

class SearchFilter(django_filters.FilterSet):
    class Meta:
        model = UserProfile
        fields = ['country', 'city']


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