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

from accounts.models import Property
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
    return render(request, 'landing.html', {})


def home(request):
    properties = Property.objects.filter(status='published').select_related('address').prefetch_related('amenities', 'images')
    property_list = []
    for property in properties:
        primary_image = property.images.filter(is_primary=True).first()
        property_list.append({
            'id': property.id,
            'title': property.title,
            'price': float(property.price),
            'address': str(property.address),
            'bedrooms': property.bedrooms,
            'bathrooms': float(property.bathrooms),
            'area': property.square_feet,
            'listing_type': property.category,
            'description': property.description.replace('\n', '\\u000A'),
            'amenities': [f'"{amenity.name}"' for amenity in property.amenities.all()],
            'date_listed': property.listed_date.strftime('%Y-%m-%d') if property.listed_date else '',
            'image_url': primary_image.image.url if primary_image else '',
            'coordinates': [float(property.address.longitude), float(property.address.latitude)] if property.address else None
        })

    return render(request, 'map.html', {'properties': property_list})

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