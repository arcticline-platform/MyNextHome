from django.urls import include, path, re_path

from . import views, utils, apis
from django.contrib.auth import views as auth_views

from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'users', apis.UserViewSet)
router.register(r'profiles', apis.UserProfileViewSet)
router.register(r'portfolios', apis.PortfolioViewSet)
router.register(r'paylinks', apis.PayLinkViewSet)
router.register(r'receipts', apis.ReceiptViewSet)


urlpatterns = [
    path('api/', include(router.urls)),
	# Logins
	path('auth/', include('django.contrib.auth.urls')),
    path('login/', views.LogInView.as_view(), name='login'),
	path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signUp/', views.user_signup, name='signup'),
	path('check_username/', views.check_username, name='check_username'),
	re_path(r'^check_user_email/$', views.check_user_email, name='check_email'),
	# activation
    path('activate/<uidb64>/<token>', views.activate, name='activate'),
    path('account_activation_sent/', views.account_activation_sent, name='account_activation_sent'),
    path('resend-activation-email/', views.resend_activation_email, name='resend_activation_email'),
	path('account_page/', views.account_page, name='account_page'),
	path('profile/<id>/<username>/',  views.profile, name='profile'),
    path('<id>/upload_photo', views.upload_photo, name='upload_photo'),
    path('<id>/upload_cover_photo', views.upload_cover_photo, name='upload_cover_photo'),
    path('<id>/user_bio/', views.user_bio, name='user_bio'),
    path('account_settings/', views.account_settings, name='account_settings'),
	path('int:<id>/update_profile/', views.update_profile, name='update_profile'),
    path('int:<id>/create_or_update_portfolio/', views.create_or_update_portfolio, name='create_or_update_portfolio'),
    path('notifications/', views.notifications, name='notifications'),
	# Account Delete
	path('int:<id>/delete_account/', views.delete_user_account, name='delete_buyer_account'),
    # PayLink update
	path('create-pay-link/', views.create_pay_link, name='create_pay_link'),
    path('pay/<uuid:link_id>/', views.pay_view, name='pay_view'),
    path('edit-pay_link/', views.edit_pay_link, name='edit_pay_link'),
    path('delete-pay_link/', views.delete_pay_link, name='delete_pay_link'),

    path('send-otp/', utils.send_otp, name='send_otp'),
    path('verify-otp/', utils.verify_otp, name='verify_otp'),

    path('report_user/<id>/<link_id>', views.report_user, name='report_user'),
]