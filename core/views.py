from django.db.models import Q
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
# from django.contrib import messages
from django.middleware.csrf import get_token
from decimal import Decimal, InvalidOperation
from django.urls import reverse, reverse_lazy
# from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect #,get_object_or_404,

# from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import SystemUtility
from finance.models import Subscription
from tracking_analyzer.models import Tracker
from accounts.models import Property, PropertyType, Amenity, AmenityCategory
# from accounts.models import User, UserProfile, ProfileFilter, SearchFilter

channel_layer = get_channel_layer()

MAPBOX_ACCESS_TOKEN = settings.MAPBOX_ACCESS_TOKEN

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
    property_list = [format_property_data(prop) for prop in properties]
    
    # Get filter options for the search form
    property_types = PropertyType.objects.all().order_by('name')
    categories = [choice[0] for choice in Property.LISTING_CATEGORY]
    featured_amenities = Amenity.objects.filter(is_featured=True)[:10]

    # Map context for JS
    map_context = {
        'isAuthenticated': request.user.is_authenticated,
        'loginUrl': reverse('login'),
        'signupUrl': reverse('signup'),
        'csrfToken': get_token(request),
    }

    return render(request, 'map.html', {
        'properties': property_list,
        'property_types': property_types,
        'categories': categories,
        'featured_amenities': featured_amenities,
        'map_context': map_context,
        'MAPBOX_ACCESS_TOKEN': MAPBOX_ACCESS_TOKEN,
    })


def property_search(request):
    query = request.GET.get('q', '')
    property_type = request.GET.get('property_type')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    bedrooms = request.GET.get('bedrooms')
    bathrooms = request.GET.get('bathrooms')
    amenities = request.GET.getlist('amenities')
    sort_by = request.GET.get('sort_by', '-listed_date')

    properties = Property.objects.filter(status='published').select_related('address', 'property_type').prefetch_related('amenities__category', 'images')

    if query:
        properties = properties.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(address__city__icontains=query) |
            Q(address__state__icontains=query) |
            Q(address__country__icontains=query) |
            Q(address__street_address__icontains=query) |
            Q(address__place_name__icontains=query) |
            Q(address__neighborhood__icontains=query)
        ).distinct()

    if property_type and property_type != 'All Types':
        properties = properties.filter(property_type__name=property_type)

    if min_price:
        try:
            properties = properties.filter(price__gte=Decimal(min_price))
        except (ValueError, InvalidOperation):
            pass
    
    if max_price:
        try:
            properties = properties.filter(price__lte=Decimal(max_price))
        except (ValueError, InvalidOperation):
            pass

    if bedrooms and bedrooms != 'Any':
        try:
            val = int(bedrooms.replace('+', ''))
            properties = properties.filter(bedrooms__gte=val)
        except (ValueError, TypeError):
            pass

    if bathrooms and bathrooms != 'Any':
        try:
            val = int(bathrooms.replace('+', ''))
            properties = properties.filter(bathrooms__gte=val)
        except (ValueError, TypeError):
            pass

    if amenities:
        properties = properties.filter(amenities__id__in=amenities).distinct()

    # Apply sorting
    if sort_by == 'price_low':
        properties = properties.order_by('price')
    elif sort_by == 'price_high':
        properties = properties.order_by('-price')
    elif sort_by == 'popular':
        properties = properties.order_by('-view_count')
    else:
        properties = properties.order_by('-listed_date')

    property_list = [format_property_data(prop) for prop in properties]
    
    # Context for filters
    property_types = PropertyType.objects.all().order_by('name')
    categories = [choice[0] for choice in Property.LISTING_CATEGORY]
    featured_amenities = Amenity.objects.filter(is_featured=True)[:10]

    # Map context for JS
    map_context = {
        'isAuthenticated': request.user.is_authenticated,
        'loginUrl': reverse('login'),
        'signupUrl': reverse('signup'),
        'csrfToken': get_token(request),
    }

    return render(request, 'map.html', {
        'properties': property_list,
        'query': query,
        'property_types': property_types,
        'categories': categories,
        'featured_amenities': featured_amenities,
        'current_filters': request.GET,
        'map_context': map_context,
        'MAPBOX_ACCESS_TOKEN': settings.MAPBOX_ACCESS_TOKEN,
    })

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
    page_content = "When it comes to dating apps, you've got options out there no doubt. It doesn't matter if you want to find love, a date, or just have a casual chat, you want an app that's the right match for you. We understand that in the vast world of online dating, authenticity is key that is why at Flirt, we believe that genuine connections are the heart of any meaningful relationship.And so we've created a platform that goes beyond the swipe, offering you access to real user dating profiles to connect with people who have like minds like you!"
    return render(request, 'core/info.html', {'title':title, 'page_title':page_title, 'page_content':page_content})


def format_property_data(property):
    """Helper function to format property data consistently"""
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
    return {
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
            'has_bedrooms': property.property_type.has_bedrooms,
            'has_bathrooms': property.property_type.has_bathrooms,
            'has_floors': property.property_type.has_floors,
            'has_furnishing': property.property_type.has_furnishing,
        } if property.property_type else None,
        'description': property.description.replace('\n', '\\u000A') if property.description else "",
        'amenities': amenities,
        'neighborhood_features': neighborhood_features,
        'date_listed': property.listed_date.strftime('%Y-%m-%d') if property.listed_date else "",
        'image_url': primary_image.image.url if primary_image and primary_image.image else "",
        'images': [img.image.url for img in property.images.all() if img.image],
        'coordinates': [str(address.longitude), str(address.latitude)] if address and address.longitude is not None and address.latitude is not None else None,
        'is_featured': "Yes" if property.is_featured is not None else "No",
        'view_count': str(property.view_count) if property.view_count is not None else "",
        'rating': str(property.rating) if property.rating is not None else "",
        'favorite_count': str(property.favorite_count) if property.favorite_count is not None else "",
        'available_from': property.available_from.strftime('%Y-%m-%d') if property.available_from else "",
        'last_refurbished': property.last_refurbished.strftime('%Y-%m-%d') if property.last_refurbished else "",
        'video_url': [video.video_url for video in property.videos.all()] if property.videos.all().first() else "",
    }


def properties_api(request):
    """API endpoint for fetching paginated and filtered properties"""
    try:
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 15))
        offset = (page - 1) * per_page
        
        # Start with base queryset
        properties = Property.objects.filter(status='published').select_related('address', 'property_type').prefetch_related('amenities__category', 'images', 'neighborhood_features__category')
        
        # Apply keyword search
        query = request.GET.get('q')
        if query:
            properties = properties.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(address__city__icontains=query) |
                Q(address__state__icontains=query) |
                Q(address__country__icontains=query) |
                Q(address__street_address__icontains=query) |
                Q(address__place_name__icontains=query) |
                Q(address__neighborhood__icontains=query)
            ).distinct()

        # Apply filters
        # Property Type
        property_type = request.GET.get('property_type')
        if property_type:
            try:
                property_type_id = int(property_type)
                properties = properties.filter(property_type_id=property_type_id)
            except (ValueError, TypeError):
                pass
        
        # Category (listing type)
        category = request.GET.get('category')
        if category:
            properties = properties.filter(category=category)
        
        # Price range
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        if min_price:
            try:
                min_price_decimal = Decimal(min_price)
                properties = properties.filter(price__gte=min_price_decimal)
            except (ValueError, InvalidOperation, TypeError):
                pass
        if max_price:
            try:
                max_price_decimal = Decimal(max_price)
                properties = properties.filter(price__lte=max_price_decimal)
            except (ValueError, InvalidOperation, TypeError):
                pass
        
        # Currency
        currency = request.GET.get('currency')
        if currency:
            properties = properties.filter(price_currency=currency)
        
        # Bedrooms
        min_bedrooms = request.GET.get('min_bedrooms')
        max_bedrooms = request.GET.get('max_bedrooms')
        if min_bedrooms:
            try:
                properties = properties.filter(bedrooms__gte=int(min_bedrooms))
            except (ValueError, TypeError):
                pass
        if max_bedrooms:
            try:
                properties = properties.filter(bedrooms__lte=int(max_bedrooms))
            except (ValueError, TypeError):
                pass
        
        # Bathrooms
        min_bathrooms = request.GET.get('min_bathrooms')
        max_bathrooms = request.GET.get('max_bathrooms')
        if min_bathrooms:
            try:
                properties = properties.filter(bathrooms__gte=Decimal(min_bathrooms))
            except (ValueError, InvalidOperation, TypeError):
                pass
        if max_bathrooms:
            try:
                properties = properties.filter(bathrooms__lte=Decimal(max_bathrooms))
            except (ValueError, InvalidOperation, TypeError):
                pass
        
        # Square feet
        min_sqft = request.GET.get('min_sqft')
        max_sqft = request.GET.get('max_sqft')
        if min_sqft:
            try:
                properties = properties.filter(square_feet__gte=int(min_sqft))
            except (ValueError, TypeError):
                pass
        if max_sqft:
            try:
                properties = properties.filter(square_feet__lte=int(max_sqft))
            except (ValueError, TypeError):
                pass
        
        # Furnishing status
        furnishing = request.GET.get('furnishing')
        if furnishing:
            properties = properties.filter(Q(furnishing_status=furnishing) | Q(furnish_status=furnishing))
        
        # Availability status
        availability = request.GET.get('availability')
        if availability:
            properties = properties.filter(availability_status=availability)
        
        # Amenities (multiple)
        amenities = request.GET.getlist('amenities')
        if amenities:
            try:
                amenity_ids = [int(aid) for aid in amenities]
                properties = properties.filter(amenities__id__in=amenity_ids).distinct()
            except (ValueError, TypeError):
                pass
        
        # Location filters
        city = request.GET.get('city')
        if city:
            properties = properties.filter(address__city__icontains=city)
        
        state = request.GET.get('state')
        if state:
            properties = properties.filter(address__state__icontains=state)
        
        country = request.GET.get('country')
        if country:
            properties = properties.filter(address__country=country)
        
        # Features
        parking_spaces = request.GET.get('parking_spaces')
        if parking_spaces:
            try:
                properties = properties.filter(parking_spaces__gte=int(parking_spaces))
            except (ValueError, TypeError):
                pass
        
        internet_included = request.GET.get('internet_included')
        if internet_included == 'true':
            properties = properties.filter(internet_included=True)
        elif internet_included == 'false':
            properties = properties.filter(internet_included=False)
        
        # Price negotiable
        price_negotiable = request.GET.get('price_negotiable')
        if price_negotiable == 'true':
            properties = properties.filter(is_price_negotiable=True)
        
        # Featured properties
        featured = request.GET.get('featured')
        if featured == 'true':
            properties = properties.filter(is_featured=True)
        
        # Get total count before pagination
        total_count = properties.count()
        
        # Apply ordering and pagination
        order_by = request.GET.get('order_by', '-listed_date')
        properties = properties.order_by(order_by)[offset:offset + per_page]
        
        property_list = [format_property_data(property) for property in properties]
        
        has_more = offset + len(property_list) < total_count
        
        return JsonResponse({
            'success': True,
            'properties': property_list,
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'has_more': has_more
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def filter_options_api(request):
    """API endpoint for getting filter options (property types, amenities, etc.)"""
    try:
        # Get all property types
        property_types = [
            {
                'id': pt.id,
                'name': pt.name,
                'icon': pt.icon or '',
                'description': pt.description or ''
            }
            for pt in PropertyType.objects.all().order_by('name')
        ]
        
        # Get all amenities grouped by category
        amenities_by_category = {}
        for category in AmenityCategory.objects.all().order_by('name'):
            amenities = Amenity.objects.filter(category=category).order_by('name')
            amenities_by_category[category.name] = [
                {
                    'id': a.id,
                    'name': a.name,
                    'icon': a.icon or '',
                    'is_featured': a.is_featured
                }
                for a in amenities
            ]
        
        # Get amenities without category
        uncategorized_amenities = Amenity.objects.filter(category__isnull=True).order_by('name')
        if uncategorized_amenities.exists():
            amenities_by_category['Other'] = [
                {
                    'id': a.id,
                    'name': a.name,
                    'icon': a.icon or '',
                    'is_featured': a.is_featured
                }
                for a in uncategorized_amenities
            ]
        
        # Get unique cities, states, and countries from addresses
        from accounts.models import Address
        cities = list(Address.objects.values_list('city', flat=True).distinct().exclude(city='').order_by('city'))
        states = list(Address.objects.values_list('state', flat=True).distinct().exclude(state='').order_by('state'))
        countries = list(Address.objects.values_list('country', flat=True).distinct().exclude(country='').order_by('country'))
        
        # Get price range
        from django.db.models import Min, Max
        price_range = Property.objects.filter(status='published').aggregate(
            min_price=Min('price'),
            max_price=Max('price')
        )
        
        # Get bedroom/bathroom/square feet ranges
        bedroom_range = Property.objects.filter(status='published').aggregate(
            min_bedrooms=Min('bedrooms'),
            max_bedrooms=Max('bedrooms')
        )
        
        bathroom_range = Property.objects.filter(status='published').aggregate(
            min_bathrooms=Min('bathrooms'),
            max_bathrooms=Max('bathrooms')
        )
        
        sqft_range = Property.objects.filter(status='published').aggregate(
            min_sqft=Min('square_feet'),
            max_sqft=Max('square_feet')
        )
        
        return JsonResponse({
            'success': True,
            'property_types': property_types,
            'amenities_by_category': amenities_by_category,
            'locations': {
                'cities': cities,
                'states': states,
                'countries': countries
            },
            'ranges': {
                'price': {
                    'min': float(price_range['min_price']) if price_range['min_price'] else 0,
                    'max': float(price_range['max_price']) if price_range['max_price'] else 0
                },
                'bedrooms': {
                    'min': bedroom_range['min_bedrooms'] or 0,
                    'max': bedroom_range['max_bedrooms'] or 0
                },
                'bathrooms': {
                    'min': float(bathroom_range['min_bathrooms']) if bathroom_range['min_bathrooms'] else 0,
                    'max': float(bathroom_range['max_bathrooms']) if bathroom_range['max_bathrooms'] else 0
                },
                'square_feet': {
                    'min': sqft_range['min_sqft'] or 0,
                    'max': sqft_range['max_sqft'] or 0
                }
            },
            'categories': [choice[0] for choice in Property.LISTING_CATEGORY],
            'furnishing_statuses': [choice[0] for choice in Property.FURNISHING_STATUS],
            'availability_statuses': [choice[0] for choice in Property.PROPERTY_AVAILABILITY_CHOICE],
            'currencies': [choice[0] for choice in Property.CURRENCY_CHOICES]
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)