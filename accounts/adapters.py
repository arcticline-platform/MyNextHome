from django.shortcuts import render, redirect

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import UserProfile

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        UserProfile.objects.get_or_create(user=user, username=user.username, email=user.email, first_name=user.first_name, last_name=user.last_name, is_active=True)
        return user