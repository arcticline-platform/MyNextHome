import os
import uuid

# properties/views.py
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from django.shortcuts import render
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.core.files.base import ContentFile
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Property, Address, PropertyImage
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, UpdateView, TemplateView
from .property_forms import PropertyForm, AddressForm, PropertyImageForm


# @csrf_exempt
# @require_http_methods(["GET", "POST"])
def add_property(request):
    template_name = 'accounts/add_property.html'
    # success_url = reverse_lazy('profile')
    context = {}
    print(f"Request method: {request.method}")
    print("Data in request.POST:", request.POST)
    print("Files in request.FILES:", request.FILES)

    if request.method == 'POST':
        property_form = PropertyForm(request.POST, user=request.user)
        # Limit latitude and longitude precision to 8 decimal places if present
        post_data = request.POST.copy()
        if 'latitude' in post_data and post_data['latitude']:
            print(f"Original latitude: {post_data['latitude']}")
            try:
                post_data['latitude'] = str(round(float(post_data['latitude']), 8))
            except Exception:
                pass
        if 'longitude' in post_data and post_data['longitude']:
            print(f"Original longitude: {post_data['longitude']}")
            try:
                post_data['longitude'] = str(round(float(post_data['longitude']), 8))
            except Exception:
                pass

        address_form = AddressForm(post_data)
        image_form = PropertyImageForm(request.POST, request.FILES)

        if property_form.is_valid() and address_form.is_valid():
            with transaction.atomic():
                address = address_form.save()
                property = property_form.save(commit=False)
                property.address = address
                property.owner = request.user
                property.listed_by = request.user
                property.status = 'published'  # Ensure status is set to published
                property.save()
                property_form.save_m2m()

                # Handle AJAX vs regular form submission
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'propertyId': property.pk,
                        'redirectUrl': reverse('edit_property', kwargs={'pk': property.pk})
                    })

                # Handle regular form submission with images
                if image_form.is_valid() and 'image' in request.FILES:
                    for i, image_file in enumerate(request.FILES.getlist('image')):
                        PropertyImage.objects.create(
                            property=property,
                            image=image_file,
                            caption=image_form.cleaned_data.get('caption', ''),
                            is_primary=i == 0  # First image is primary
                        )

                messages.success(request, 'Property added successfully!')
                return redirect('edit_property', pk=property.pk)
        else:
            print("Property form errors:", property_form.errors)
            print("Address form errors:", address_form.errors)
            messages.error(request, 'There was an error saving the property. Please correct the errors below.')

        # If forms are invalid
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = {
                'property_errors': property_form.errors,
                'address_errors': address_form.errors
            }
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        # Regular form submission with errors
        context['property_form'] = property_form
        context['address_form'] = address_form
        context['image_form'] = image_form
    else:
        context['property_form'] = PropertyForm(user=request.user)
        context['address_form'] = AddressForm()
        context['image_form'] = PropertyImageForm()
        context['MAPBOX_ACCESS_TOKEN'] = os.getenv('MAPBOX_ACCESS_TOKEN', '')

    return render(request, template_name, context)


class AddPropertyView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/add_property.html'
    success_url = reverse_lazy('profile')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['property_form'] = PropertyForm(self.request.POST, user=self.request.user)
            context['address_form'] = AddressForm(self.request.POST)
            context['image_form'] = PropertyImageForm(self.request.POST, self.request.FILES)
        else:
            context['property_form'] = PropertyForm(user=self.request.user)
            context['address_form'] = AddressForm()
            context['image_form'] = PropertyImageForm()
            context['MAPBOX_ACCESS_TOKEN'] = os.getenv('MAPBOX_ACCESS_TOKEN', '')
        return context
    
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # Copy POST data and round latitude/longitude if present
        post_data = request.POST.copy()
        if 'latitude' in post_data and post_data['latitude']:
            try:
                post_data['latitude'] = str(round(float(post_data['latitude']), 8))
            except Exception:
                pass
        if 'longitude' in post_data and post_data['longitude']:
            try:
                post_data['longitude'] = str(round(float(post_data['longitude']), 8))
            except Exception:
                pass

        property_form = PropertyForm(request.POST, user=request.user)
        address_form = AddressForm(post_data)
        
        if property_form.is_valid() and address_form.is_valid():
            # Save address first
            address = address_form.save()
            
            # Save property with address and owner
            property = property_form.save(commit=False)
            property.address = address
            property.owner = request.user
            property.listed_by = request.user
            property.status = 'published'  # Ensure status is set to published
            property.save()
            
            # Save many-to-many relationships
            property_form.save_m2m()
            
            # Handle AJAX vs regular form submission
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                messages.success(request, 'Property added successfully!')
                return JsonResponse({
                    'success': True,
                    'propertyId': property.pk,
                    'redirectUrl': reverse('profile')
                })
            
            # Handle regular form submission with images
            image_form = PropertyImageForm(request.POST, request.FILES)
            if image_form.is_valid() and 'image' in request.FILES:
                for i, image_file in enumerate(request.FILES.getlist('image')):
                    PropertyImage.objects.create(
                        property=property,
                        image=image_file,
                        caption=image_form.cleaned_data.get('caption', ''),
                        is_primary=i == 0  # First image is primary
                    )
            
            messages.success(request, 'Property added successfully!')
            return redirect('profile')
        
        # If forms are invalid
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = {
                'property_errors': property_form.errors,
                'address_errors': address_form.errors
            }
            return JsonResponse({'success': False, 'errors': errors}, status=400)
        
        # Regular form submission with errors
        context = self.get_context_data()
        context['property_form'] = property_form
        context['address_form'] = address_form
        context['image_form'] = PropertyImageForm(request.POST, request.FILES)
        return self.render_to_response(context)


class EditPropertyView(LoginRequiredMixin, UpdateView):
    model = Property
    form_class = PropertyForm
    template_name = 'accounts/edit_property.html'
    
    def get_success_url(self):
        return reverse_lazy('edit_property', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['property_form'] = self.get_form()
        context['address_form'] = AddressForm(instance=self.object.address)
        context['image_form'] = PropertyImageForm()
        context['images'] = self.object.images.all().order_by('order')
        context['MAPBOX_ACCESS_TOKEN'] = os.getenv('MAPBOX_ACCESS_TOKEN', '')
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        property_form = self.get_form()
        address_form = AddressForm(request.POST, instance=self.object.address)
        image_form = PropertyImageForm(request.POST, request.FILES)
        
        if property_form.is_valid() and address_form.is_valid():
            # Save address first
            address = address_form.save()
            
            # Save property with address
            property = property_form.save(commit=False)
            property.status = 'published'  # Ensure status is set to published
            property.address = address
            property.save()
            
            # Save many-to-many relationships
            property_form.save_m2m()
            
            # Handle image uploads
            if 'image' in request.FILES:
                for image_file in request.FILES.getlist('image'):
                    PropertyImage.objects.create(
                        property=property,
                        image=image_file,
                        caption=image_form.cleaned_data.get('caption', ''),
                        is_primary=image_form.cleaned_data.get('is_primary', False)
                    )
            
            messages.success(request, 'Property updated successfully!')
            return redirect('edit_property', pk=property.pk)
        
        # If forms are invalid, return with errors
        context = self.get_context_data()
        context['property_form'] = property_form
        context['address_form'] = address_form
        context['image_form'] = image_form
        return self.render_to_response(context)


@method_decorator(csrf_exempt, name='dispatch')
class UploadPropertyImageView(LoginRequiredMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        print(f"UploadPropertyImageView POST request: {request.POST}")
        print(f"Files in request.FILES: {request.FILES}")
        property_id = kwargs.get('pk')
        try:
            property = Property.objects.get(pk=property_id, owner=request.user)
        except Property.DoesNotExist:
            print(f"Property with ID {property_id} not found or permission denied for user {request.user}")
            return JsonResponse({'error': 'Property not found or permission denied'}, status=404)
        
        if 'image' not in request.FILES and 'images' not in request.FILES:
            return JsonResponse({'error': 'No image provided'}, status=400)

        # Support both 'image' (single) and 'images' (multiple)
        image_files = []
        if 'images' in request.FILES:
            image_files = request.FILES.getlist('images')
        elif 'image' in request.FILES:
            image_files = request.FILES.getlist('image')

        if not image_files:
            return JsonResponse({'error': 'No image provided'}, status=400)

        images_data = []
        for i, image_file in enumerate(image_files):
            ext = os.path.splitext(image_file.name)[1]
            filename = f"property_{property_id}_{uuid.uuid4().hex}{ext}"
            file_path = default_storage.save(f'property_images/{filename}', ContentFile(image_file.read()))
            image = PropertyImage.objects.create(
            property=property,
            image=file_path,
            caption=request.POST.get('caption', ''),
            is_primary=(i == 0 and not property.images.exists())  # Set as primary if first and no images yet
            )
            images_data.append({
            'image_id': image.id,
            'image_url': image.image.url,
            'caption': image.caption
            })

        return JsonResponse({
            'success': True,
            'images': images_data
        })


def property_detail(request, id):
    try:
        property = Property.objects.get(id=id)
        images = property.images.all().order_by('order')
        
        # Build image data
        image_data = [{
            'id': img.id,
            'url': img.image.url,
            'caption': img.caption,
            'is_primary': img.is_primary,
            'order': img.order
        } for img in images]

        # Build amenities and features data
        amenities_data = [{'id': a.id, 'name': a.name} for a in property.amenities.all()]
        features_data = [{'id': f.id, 'name': f.name} for f in property.neighborhood_features.all()]

        # Construct property data
        property_data = {
            'id': property.pk,
            'title': property.title,
            'description': property.description,
            'property_type': property.property_type.name,
            'price': float(property.price),
            'currency': property.price_currency,
            'bedrooms': property.bedrooms,
            'bathrooms': float(property.bathrooms),
            'square_feet': property.square_feet,
            'status': property.status,
            'category': property.category,
            'address': {
                'street': property.address.street_address,
                'city': property.address.city,
                'state': property.address.state,
                'country': property.address.country,
                'postal_code': property.address.zip_code,
                'latitude': float(property.address.latitude) if property.address.latitude else None,
                'longitude': float(property.address.longitude) if property.address.longitude else None,
            },
            'amenities': amenities_data,
            'neighborhood_features': features_data,
            'images': image_data,
            'furnishing_status': property.furnishing_status,
            'parking_spaces': property.parking_spaces,
            'internet_included': property.internet_included,
            'availability_status': property.availability_status,
            'created': property.created.isoformat(),
            'modified': property.updated.isoformat(),
        }

        return JsonResponse(property_data)
    except Property.DoesNotExist:
        return JsonResponse({'error': 'Property not found'}, status=404)


@require_http_methods(["DELETE"])
@csrf_exempt
def delete_property_image(request, pk, image_id):
    try:
        image = PropertyImage.objects.get(pk=image_id, property__pk=pk, property__owner=request.user)
        image.delete()
        return JsonResponse({'success': True})
    except PropertyImage.DoesNotExist:
        return JsonResponse({'error': 'Image not found or permission denied'}, status=404)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def set_primary_image(request, image_id):
    try:
        image = PropertyImage.objects.select_related('property').get(pk=image_id)
        if image.property.owner != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Set all images for this property as not primary
        PropertyImage.objects.filter(property=image.property).update(is_primary=False)
        
        # Set this image as primary
        image.is_primary = True
        image.save()
        
        return JsonResponse({'success': True})
    except PropertyImage.DoesNotExist:
        return JsonResponse({'error': 'Image not found'}, status=404)

@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def delete_image(request, image_id):
    try:
        image = PropertyImage.objects.select_related('property').get(pk=image_id)
        if image.property.owner != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Delete the image file
        image.image.delete()
        # Delete the database record
        image.delete()
        
        return JsonResponse({'success': True})
    except PropertyImage.DoesNotExist:
        return JsonResponse({'error': 'Image not found'}, status=404)
    

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def delete_property(request, property_id):
    try:
        property = Property.objects.get(id=property_id)
        if property.owner != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Delete all associated images first
        for image in property.images.all():
            image.image.delete()  # Delete the image file
        
        # Delete the property (this will cascade delete address and other related objects)
        property.delete()
        
        return JsonResponse({'success': True})
    except Property.DoesNotExist:
        return JsonResponse({'error': 'Property not found'}, status=404)