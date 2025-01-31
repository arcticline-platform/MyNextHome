from django.urls import path

from . import views
# from . import admin

urlpatterns = [
    path('checkout/<plan_id>/', views.checkout, name='checkout'),
    path('initiate_payment/', views.initiate_payment, name='initiate_payment'),
    path('get_payment_update/<id>/', views.get_payment_update, name='get_payment_update'),
    path('user_wallet/<id>/<username>', views.user_wallet, name='user_wallet'),
]