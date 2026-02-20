# properties/urls.py
from django.urls import path
from .properties_views import (AddPropertyView, EditPropertyView,
    UploadPropertyImageView, property_detail, delete_property_image, add_property, set_primary_image, delete_image, delete_property, contact_property_owner, toggle_property_availability
)

urlpatterns = [
    # path('add/', add_property, name='add_property'),
    path('add/', AddPropertyView.as_view(), name='add_property'),
    path('property/<int:id>/', property_detail, name='property_detail'),
    path('<int:pk>/edit/', EditPropertyView.as_view(), name='edit_property'),
    path('<int:pk>/upload-images/', UploadPropertyImageView.as_view(), name='upload_property_image'),
    path('<int:pk>/images/<int:image_id>/delete/', delete_property_image, name='delete_property_image'),
    path('delete/<int:property_id>/', delete_property, name='delete_property'),
    path('images/<int:image_id>/set-primary/', set_primary_image, name='set_primary_image'),
    path('images/<int:image_id>/delete/', delete_image, name='delete_image'),
    path('property/<int:property_id>/contact/', contact_property_owner, name='contact_property_owner'),
    path('<int:property_id>/toggle-availability/', toggle_property_availability, name='toggle_property_availability'),
]
