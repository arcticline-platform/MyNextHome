from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Property, PropertyImage, Favorites, Address

# Property List View
def property_list(request):
    properties = Property.objects.filter(is_published=True).order_by('-listed_date')
    return render(request, 'property_list.html', {'properties': properties})

# Property Detail View
def property_detail(request, slug):
    property_obj = get_object_or_404(Property, slug=slug, is_published=True)
    images = property_obj.images.all()
    google_maps_url = property_obj.address.google_maps_url() if property_obj.address else None

    context = {
        'property': property_obj,
        'images': images,
        'google_maps_url': google_maps_url,
    }
    return render(request, 'property_detail.html', context)

# Add to Favorites View
@login_required
def add_to_favorites(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id)
    favorite, created = Favorites.objects.get_or_create(user=request.user, property=property_obj)

    if created:
        messages.success(request, f"{property_obj.title} has been added to your favorites.")
    else:
        messages.info(request, f"{property_obj.title} is already in your favorites.")

    return redirect('property_detail', slug=property_obj.slug)

# Remove from Favorites View
@login_required
def remove_from_favorites(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id)
    Favorites.objects.filter(user=request.user, property=property_obj).delete()
    messages.success(request, f"{property_obj.title} has been removed from your favorites.")
    return redirect('property_detail', slug=property_obj.slug)

# Address Verification View
@login_required
def verify_address(request, address_id):
    address = get_object_or_404(Address, id=address_id)
    try:
        address.verify_address()
        messages.success(request, "Address successfully verified.")
    except Exception as e:
        messages.error(request, f"Address verification failed: {str(e)}")

    return redirect('property_detail', slug=address.property.slug)

# Search Properties View
def search_properties(request):
    query = request.GET.get('query', '')
    properties = Property.objects.filter(is_published=True)

    if query:
        properties = properties.filter(title__icontains=query)

    return render(request, 'property_list.html', {'properties': properties, 'query': query})