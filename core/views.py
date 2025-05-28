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

try:
    from django.db import connection
    if connection.settings_dict and 'core_systemutility' in connection.introspection.table_names():
        try:
            utility = SystemUtility.objects.get(id=1)
        except SystemUtility.DoesNotExist:
            utility = None
    else:
        utility = None
except Exception as e:
    utility = None


def landing_page(request):
    if utility is not None:
        Tracker.objects.create_from_request(request, utility)
    return render(request, 'landing.html', {})


def home(request):
    properties = (
        Property.objects.filter(status='published')
        .select_related('address', 'property_type')
        .prefetch_related('amenities__category', 'images', 'neighborhood_features__category')
        .order_by('-listed_date')[:15]
    )
    property_list = []
    for property in properties:
        primary_image = property.get_primary_image()
        amenities = [
            {
                'id': amenity.id,
                'name': amenity.name,
                'category': amenity.category.name if amenity.category else None,
                'icon': amenity.icon,
                'is_featured': "Yes" if amenity.is_featured else "No",
            }
            for amenity in property.amenities.all()
        ]
        neighborhood_features = [
            {
                'id': nf.id,
                'name': nf.name,
                'category': nf.category.name if nf.category else None,
                'icon': nf.icon,
                'is_essential': "Yes" if nf.is_essential else "No",
            }
            for nf in property.neighborhood_features.all()
        ]
        address = property.address
        property_list.append({
            'id': property.id if property.id is not None else "",
            'title': property.title or "",
            'slug': property.slug or "",
            'price': str(property.price) if property.price is not None else "",
            'price_currency': property.price_currency or "",
            'is_price_negotiable': "Yes" if property.is_price_negotiable else "No",
            'address': address.get_formatted_address() if address else "",
            'city': address.city if address and address.city else "",
            'state': address.state if address and address.state else "",
            'country': address.country if address and address.country else "",
            'latitude': str(address.latitude) if address and address.latitude is not None else "",
            'longitude': str(address.longitude) if address and address.longitude is not None else "",
            'bedrooms': str(property.bedrooms) if property.bedrooms is not None else "",
            'bathrooms': str(property.bathrooms) if property.bathrooms is not None else "",
            'area': str(property.square_feet) if property.square_feet is not None else "",
            'lot_size': str(property.lot_size) if property.lot_size is not None else "",
            'year_built': str(property.year_built) if property.year_built is not None else "",
            'floors': str(property.floors) if property.floors is not None else "",
            'furnishing_status': property.furnishing_status or "",
            'furnish_status': property.furnish_status or "",
            'parking_spaces': str(property.parking_spaces) if property.parking_spaces is not None else "",
            'internet_included': str(property.internet_included) if property.internet_included is not None else "",
            'listing_type': property.category or "",
            'availability_status': property.availability_status or "",
            'property_type': {
                'id': str(property.property_type.id) if property.property_type and property.property_type.id is not None else "",
                'name': property.property_type.name if property.property_type and property.property_type.name else "",
                'icon': property.property_type.icon if property.property_type and property.property_type.icon else "",
                'description': property.property_type.description if property.property_type and property.property_type.description else "",
            } if property.property_type else None,
            'description': property.description.replace('\n', '\\u000A') if property.description else "",
            'amenities': amenities,
            'neighborhood_features': neighborhood_features,
            'date_listed': property.listed_date.strftime('%Y-%m-%d') if property.listed_date else "",
            'image_url': primary_image.image.url if primary_image and primary_image.image else "",
            'images': [img.image.url for img in property.images.all() if img.image],
            'coordinates': [str(address.longitude), str(address.latitude) ] if address and address.longitude is not None and address.latitude is not None else None,
            'is_featured': "Yes" if property.is_featured is not None else "No",
            'view_count': str(property.view_count) if property.view_count is not None else "",
            'rating': str(property.rating) if property.rating is not None else "",
            'favorite_count': str(property.favorite_count) if property.favorite_count is not None else "",
            'available_from': property.available_from.strftime('%Y-%m-%d') if property.available_from else "",
            'last_refurbished': property.last_refurbished.strftime('%Y-%m-%d') if property.last_refurbished else "",
            'video_url' : [video.video_url for video in property.videos.all()] if property.videos.all().first() else "",
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