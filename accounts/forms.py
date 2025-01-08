import uuid
import random
from datetime import date

from django import forms
from django.conf import settings
from django.db import transaction
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from accounts.models import User, UserProfile, ReportUser, ReportEvidence, PayLink, Portfolio

from django_countries.widgets import CountrySelectWidget
from dobwidget import DateOfBirthWidget

# User = getattr(settings, "AUTH_USER_MODEL", "auth.User")

# General User Signup
class CustomUserCreationForm(UserCreationForm):
	class Meta(UserCreationForm):
		model = User
		fields = ('username', 'email', 'first_name', 'last_name',)


# General User Change Form
class CustomUserChangeForm(UserChangeForm):
	class Meta:
		model = User
		fields = ('username','email')


class CreateUserForm(UserCreationForm):
	password1 = forms.CharField(widget=forms.PasswordInput(), label='Create a Password', help_text='Create a minimum 8 characters of letters, symbols and numbers')
	password2 = forms.CharField(widget=forms.PasswordInput(), label='Confirm your password', help_text='Enter password as before')


class UserSignUpForm(CreateUserForm):
	# username = forms.CharField(max_length=15, widget=forms.TextInput(
	# 	attrs={
	# 		'placeholder': 'e.g Sonia'
	# 	}),   help_text='Must be unique.', label='Create a username for your account')
	class Meta(UserCreationForm.Meta):
		model = User
		fields = ('username', 'email',)
		widgets = {
			'email': forms.EmailInput(attrs={'placeholder': 'e.g example@shukrani.shop'}),
			# 'password1': forms.PasswordInput(attrs={'placeholder': '**************'}),
		}

	@transaction.atomic
	def save(self):
		user = super().save(commit=False)
		user.is_active = False
		user.is_staff = False
		user.referral_code = uuid.uuid4()
		user.save()
		profile = UserProfile.objects.create(user=user)
		profile.username = self.cleaned_data.get('username')
		profile.email = self.cleaned_data.get('email')
		profile.save()
		return user

	# Validating the username to ensure it's unique
	def clean_username(self):
		username = self.cleaned_data['username']
		if UserProfile.objects.filter(username=username).exists():
			raise ValidationError('Username already taken. Please choose another one.')
		return username
	
	def clean_email(self):
		email = self.cleaned_data['email']
		if User.objects.filter(email=email).exists():
			raise ValidationError('Email not available')
		return email

 

#Profile Edit Form
class ProfileChangeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['last_name'].required = True
        self.fields['gender'].required = True
        self.fields['date_of_birth'].required = True

    def clean_date_of_birth(self):
        dob = self.cleaned_data['date_of_birth']
        age = (date.today() - dob).days / 365
        if age < 18:
            raise forms.ValidationError('You must be at least 18 years old.')
        elif age > 100:
            raise forms.ValidationError('Come on 😐, you cannot be over 100 years old and still be in the game!')
        return dob

    class Meta:
        model = UserProfile
        fields = (
            'first_name', 'last_name', 'other_name', 'gender', 'date_of_birth',
            'phone', 'country', 'city', 'bio',
        )
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'e.g., Julia', 'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'e.g., Octavia', 'class': 'form-control'}),
            'other_name': forms.TextInput(attrs={'placeholder': 'e.g., Javier', 'class': 'form-control'}),
            'date_of_birth': DateOfBirthWidget(attrs={'class': 'form-control'}),
            'country': CountrySelectWidget(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'placeholder': '+256700112233', 'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'placeholder': 'Write your bio...', 'class': 'form-control', 'rows': 4}),
        }


class AboutMeForm(forms.ModelForm):
	class Meta:
		model = UserProfile
		fields = ('bio',)
		widgets = {
			'bio': forms.Textarea(attrs={'placeholder': 'Write your bio you...'}),
		}


class ImageForm(forms.ModelForm):
	class Meta:
		model = UserProfile
		fields = ('photo',)
		# widgets = {
			
		# }

class CoverPhotoForm(forms.ModelForm):
	class Meta:
		model = UserProfile
		fields = ('cover_photo',)
		# widgets = {
			
		# }


class ReportUserForm(forms.ModelForm):
	class Meta:
		model = ReportUser
		fields = ('complaint',)
		widgets = {
			'complaint': forms.Textarea(attrs={'placeholder': 'Write a text...'}),
		}


class ReportEvidenceForm(forms.ModelForm):
	class Meta:
		model = ReportEvidence
		fields = ('file',)

class PayLinkForm(forms.ModelForm):
    class Meta:
        model = PayLink
        fields = ['name', 'link_type', 'image', 'description', 'amount']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': "Enter link name e.g. Alesi's Welcome Party Contribution",
                'required': True
            }),
            'link_type': forms.Select(attrs={
                'placeholder': "Select link type",
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': "Describe your link e.g. Contribute UGX 5,000 for Alesi's Welcome Party or You are paying UGX 20,000 for designer heels from Cynthia's Closets"
            }),
            'amount': forms.NumberInput(attrs={
                'step': '0.01',
                'placeholder': "Enter product/service amount",
                'required': True
            }),
            'image': forms.ClearableFileInput(attrs={
                'placeholder': "Provide a product/service image or graphics"
            }),
        }


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = [
            'business_name',
            'business_description',
            'phone',
            'email',
            'documents',
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'placeholder': "Enter your venture's name", 'required': True}),
            'business_description': forms.Textarea(attrs={'placeholder': 'Describe what you or your venture does', 'rows': 3, 'cols': 40, 'required': True}),
            'phone': forms.TextInput(attrs={'placeholder': 'Enter your phone number', 'required': True}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter your email address', 'required': True}),
            'documents': forms.ClearableFileInput(attrs={'multiple': False, 'required': True}),
        }
    # Custom field validation
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # You can add custom validation logic for phone number if necessary
        return phone

    # def clean_email(self):
    #     email = self.cleaned_data.get('email')
    #     if email and not email.endswith('@example.com'):  # Example custom logic
    #         raise ValidationError("Email must end with @example.com")
    #     return email

    def save(self, commit=True):
        portfolio = super().save(commit=False)
        # You can add any custom save logic if needed here
        if commit:
            portfolio.save()
        return portfolio


class EmailVerificationForm(forms.Form):
    otp = forms.CharField(max_length=6, required=True, widget=forms.TextInput(attrs={'placeholder': 'Enter OTP'}))


class PhoneVerificationForm(forms.Form):
    otp = forms.CharField(max_length=6, required=True, widget=forms.TextInput(attrs={'placeholder': 'Enter OTP'}))
