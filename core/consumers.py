# your_project/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async

from accounts.models import User


class OnlineStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        # Handle when a user disconnects
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        user_id = data['user_id']
        is_online = data['is_online']
        await self.update_user_status(user_id, is_online)

    @database_sync_to_async
    def update_user_status(self, user_id, is_online):
        user = User.objects.get(pk=user_id)
        user.user_profile.is_online = is_online
        user.user_profile.save()

        # Notify all connected clients about the status change
        self.broadcast_user_status(user.id, is_online)

    async def broadcast_user_status(self, user_id, is_online):
        await self.send(text_data=json.dumps({
            'user_id': user_id,
            'is_online': is_online
        }))

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'public_room'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({ 'message': event['message'] }))


class UserNotificationConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.user_notification_id = None
        self.notification_group_id = None
        self.user = None

    async def connect(self):
        self.user = self.scope['user']
        print(self.user)
        self.user_notification_id = f'notification_inbox_{self.user.username}'
        await self.channel_layer.group_add(
            self.user_notification_id,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.user_notification_id,
            self.channel_name
        )

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({ 'message': event['message'] }))

class PaymentStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.payment_id = self.scope["url_route"]["kwargs"]["payment_id"]
        self.room_group_name = f"payment_{self.payment_id}"

        # Join the payment group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the payment group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def payment_status_update(self, event):
        # Send payment status update to WebSocket
        await self.send(text_data=json.dumps(event["data"]))