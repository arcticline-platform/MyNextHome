from django.urls import path #,include

from . import views

urlpatterns = [
    # path('', views.landing_page, name='landing_page'),
    path('', views.home, name='home'),
    path('search/', views.property_search, name='property_search'),
    path('api/properties/', views.properties_api, name='properties_api'),
    path('api/filter-options/', views.filter_options_api, name='filter_options_api'),
    path('subscriptions/', views.subscriptions, name='subscriptions'),
    path('about/', views.about, name='about'),
    path('help_center/', views.help_center, name='help_center'),
    path('cookie_policy/', views.cookie_policy, name='cookie_policy'),
]
