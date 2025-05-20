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
    return render(request, 'landing.html', {})


def home(request):
    properties = [
        {
            'id': 1,
            'title': "Modern Downtown Apartment",
            'price': 450000,
            'address': "Plot 15, Kampala Road, Kampala",
            'bedrooms': 2,
            'bathrooms': 2,
            'area': 1200,
            'listing_type': "For Sale",
            'description': "Contemporary apartment with city views and modern amenities",
            'amenities': ["Balcony", "Security", "Parking", "Pool"],
            'date_listed': "2023-05-15",
            'image_url': "https://images.unsplash.com/photo-1493809842364-78817add7ffb?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
            'coordinates': [32.5825, 0.3476]
        },
        {
            'id': 2,
            'title': "Luxury Villa with Pool", 
            'price': 1200000,
            'address': "Plot 23, Mbale Road, Jinja",
            'bedrooms': 4,
            'bathrooms': 3.5,
            'area': 3200,
            'listing_type': "For Sale",
            'description': "Stunning villa with lake views and private pool",
            'amenities': ["Pool", "Garden", "Security", "Servants Quarter"],
            'date_listed': "2023-05-10",
            'image_url': "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
            'coordinates': [33.2067, 0.4478]
        },
        {
            'id': 3,
            'title': "Cozy Suburban Home",
            'price': 325000,
            'address': "Plot 45, Masaka Road, Entebbe",
            'bedrooms': 3,
            'bathrooms': 2,
            'area': 1800,
            'listing_type': "For Sale",
            'description': "Family home in quiet suburban area near airport",
            'amenities': ["Garden", "Garage", "Security", "Play Area"],
            'date_listed': "2023-05-05",
            'image_url': "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
            'coordinates': [32.4420, 0.0512]
        },
        {
            'id': 4,
            'title': "Stylish Condo Near Downtown",
            'price': 750000,
            'address': "Plot 78, Republic Street, Gulu",
            'bedrooms': 1,
            'bathrooms': 1,
            'area': 850,
            'listing_type': "For Sale",
            'description': "Modern condo with great city access",
            'amenities': ["Balcony", "Security", "Parking"],
            'date_listed': "2023-05-01",
            'image_url': "https://images.unsplash.com/photo-1484154218962-a197022b5858?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
            'coordinates': [32.2990, 2.7747]
        },
        {
            'id': 5,
            'title': "Spacious Family Home",
            'price': 575000,
            'address': "Plot 12, Main Street, Mbarara",
            'bedrooms': 4,
            'bathrooms': 3,
            'area': 2800,
            'listing_type': "For Sale",
            'description': "Large family home with beautiful mountain views",
            'amenities': ["Garden", "Garage", "Security", "Play Area"],
            'date_listed': "2023-04-28",
            'image_url': "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
            'coordinates': [30.6545, -0.6066]
        },
        {
            'id': 6,
            'title': "Charming Bungalow",
            'price': 395000,
            'address': "Plot 34, Cathedral Road, Arua",
            'bedrooms': 2,
            'bathrooms': 1,
            'area': 1100,
            'listing_type': "For Sale",
            'description': "Traditional bungalow with modern updates",
            'amenities': ["Garden", "Parking", "Security"],
            'date_listed': "2023-04-25",
            'image_url': "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80",
            'coordinates': [30.9110, 3.0220]
        }
    ]
    return render(request, 'map.html', {'properties': properties})

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