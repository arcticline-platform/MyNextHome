from django.urls import path, include

from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('home/', views.home, name='home'),
    path('subscriptions/', views.subscriptions, name='subscriptions'),
    path('about/', views.about, name='about'),
    path('help_center/', views.help_center, name='help_center'),
    path('cookie_policy/', views.cookie_policy, name='cookie_policy'),
]
