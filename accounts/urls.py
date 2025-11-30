from django.urls import include, path, re_path

from . import views, utils, apis
from django.contrib.auth import views as auth_views

from rest_framework.routers import DefaultRouter


router = DefaultRouter()


urlpatterns = [
    path('api/', include(router.urls)),

    path('api/login/', views.LoginView.as_view(), name='login_api'),
    path('api/signup/', views.SignupView.as_view(), name='signup_api'),
    path('api/verify/', views.VerifyUserView.as_view(), name='verify_user'),

    # Template renders
    path('signup/',views.signup, name='signup'),
    path('login/',views.login_user, name='login'),
    path('logout/',views.logout_view, name='logout'),

    path("update_user_profile/", views.update_user_profile, name="update_user_profile"),
    path('contact-support/', views.contact_support, name='contact_support'),
    path('notification-preferences/', views.notification_preferences, name='notification_preferences'),
    path('accounts_password_change/', views.accounts_password_change, name='accounts_password_change'),
    path("delete-account/", views.delete_account, name="delete_account"),


    path('properties/', include('accounts.property_urls')),

	# Logins
	# path('auth/', include('django.contrib.auth.urls')),
	path('check_username/', views.check_username, name='check_username'),
	re_path(r'^check_user_email/$', views.check_user_email, name='check_email'),
	# activation
	path('profile/',  views.profile, name='profile'),
    path('<id>/upload_photo', views.upload_photo, name='upload_photo'),
    path('<id>/upload_cover_photo', views.upload_cover_photo, name='upload_cover_photo'),
    path('<id>/user_bio/', views.user_bio, name='user_bio'),
    path('account_settings/', views.account_settings, name='settings'),
	path('int:<id>/update_profile/', views.update_profile, name='update_profile'),
    path('notifications/', views.notifications, name='notifications'),

    path('send-otp/', utils.send_otp, name='send_otp'),
    path('verify-otp/', utils.verify_otp, name='verify_otp'),

    path('report_user/<id>/<link_id>', views.report_user, name='report_user'),
    
    # Saved Properties URLs
    path('saved-properties/', views.saved_properties_list, name='saved_properties_list'),
    path('saved-properties/<int:property_id>/toggle/', views.toggle_save_property, name='toggle_save_property'),
    path('saved-properties/<int:property_id>/check/', views.check_property_saved, name='check_property_saved'),
    path('saved-properties/<int:property_id>/remove/', views.remove_saved_property, name='remove_saved_property'),
]