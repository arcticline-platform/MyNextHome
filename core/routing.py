from django.urls import path, re_path
from .consumers import OnlineStatusConsumer, NotificationConsumer, UserNotificationConsumer, PaymentStatusConsumer, ChatConsumer, UnreadMessagesConsumer

websocket_urlpatterns = [ 
    path("ws/online_status/", OnlineStatusConsumer.as_asgi()),
    re_path(r"ws/notify/", NotificationConsumer.as_asgi()),
    re_path(r"ws/user_notification/", UserNotificationConsumer.as_asgi()),
    path("ws/payment-status/<int:payment_id>/", PaymentStatusConsumer.as_asgi()),
    path("ws/chat/<int:chat_id>/", ChatConsumer.as_asgi()),
    path("ws/unread-messages/", UnreadMessagesConsumer.as_asgi()),
]