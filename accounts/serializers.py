from django.utils.timezone import now
from django.contrib.auth import get_user_model

from rest_framework import serializers

from .models import  VerificationToken
from accounts.models import UserProfile

User = get_user_model()


class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['email', 'phone', 'password']

    def validate_email(self, value):
        """Ensure the email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists. Log in instead.")
        return value

    def generate_username(self, email):
        """Generate a unique username with a max length of 15 characters."""
        if email:
            base_username = email.split('@')[0]  # Extract part before '@'
        else:
            base_username = "user"  # Default if no email

        date_suffix = now().strftime("%d%m%y")  # Shortened format: DDMMYY

        # Ensure base + date suffix leaves space for counter (max 2 digits)
        max_base_length = 15 - len(date_suffix) - 2  # Reserve 2 chars for counter
        base_username = base_username[:max_base_length]  # Truncate if needed

        # Find a unique counter
        count = 1
        while User.objects.filter(username=f"{base_username}{date_suffix}{count:02d}").exists():
            count += 1
            if count > 99:  # Fallback in case of extreme collisions
                base_username = "usr"  # Force a short base name
                break

        return f"{base_username}{date_suffix}{count:02d}"

    def create(self, validated_data):
        password = validated_data.pop('password')
        email = validated_data.get('email', "")  # Get email if provided
        phone = validated_data.get('phone')
        validated_data['username'] = self.generate_username(email)  # Auto-generate username

        user = User(**validated_data)
        user.set_password(password)
        user.is_active = False  # Inactive until verified
        user.phone = phone if phone else None
        user.save()

        # Create user profile
        user_profile = UserProfile.objects.create(user=user)
        user_profile.username = user.username
        user_profile.email = email
        user_profile.phone = phone
        user_profile.save()

        return user
    

class LoginSerializer(serializers.Serializer):
    username_or_email_or_phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
