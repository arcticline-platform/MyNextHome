# from django.db.models import Q
from django.shortcuts import render
# from django.contrib import messages
# from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
# from django.http import HttpResponse, HttpRequest, JsonResponse
from django.shortcuts import render, redirect #,get_object_or_404,

# from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import SystemUtility
from finance.models import Subscription
from tracking_analyzer.models import Tracker
# from accounts.models import User, UserProfile, ProfileFilter, SearchFilter

channel_layer = get_channel_layer()

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('profile',request.user.id, request.user.username)
    try:
        utility = SystemUtility.objects.get(id=1)
        Tracker.objects.create_from_request(request, utility)
    except SystemUtility.DoesNotExist:
        utility = None  
    return render(request, 'paylink.html', {})


@login_required
def home(request):
    return redirect('discover') 

@login_required
def settings(request):
    return render(request, 'settings.html', {})


def check_subscription(request, user_id):
    if Subscription.objects.filter(user_id=user_id, is_active=True).exists():
        return True
    else:
        return False
    
def subscriptions(request):
    return render(request, 'finance/subscriptions.html', {})


def about(request):
    return render(request, 'core/aboutPage.html', {})

def help_center(request):
    return render(request, 'core/help_center.html', {})

def cookie_policy(request):
    title = 'Cookie Policy'
    page_title = 'Cookie Policy'
    page_content = "When it comes to dating apps, you’ve got options out there no doubt. It doesn’t matter if you want to find love, a date, or just have a casual chat, you want an app that’s the right match for you. We understand that in the vast world of online dating, authenticity is key that is why at Flirt, we believe that genuine connections are the heart of any meaningful relationship.And so we've created a platform that goes beyond the swipe, offering you access to real user dating profiles to connect with people who have like minds like you!"
    return render(request, 'core/info.html', {'title':title, 'page_title':page_title, 'page_content':page_content})