# your_project/consumers.py

import json
from datetime import datetime

# from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from django.db.models import Q

from accounts.models import User, Chat, Message


class OnlineStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return
        await self.accept()

    async def disconnect(self, close_code):
        # Handle when a user disconnects
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            user_id = data.get('user_id')
            is_online = data.get('is_online')
            if user_id and is_online is not None:
                await self.update_user_status(user_id, is_online)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error processing online status update: {e}")

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
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
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
        super().__init__(*args, **kwargs)
        self.user_notification_id = None
        self.notification_group_id = None
        self.user = None

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
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


class UnreadMessagesConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time unread message count updates"""
    
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        self.user_group_name = f'unread_messages_{self.user.id}'
        
        # Join user's unread messages group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial unread count
        await self.send_initial_count()
    
    async def disconnect(self, close_code):
        # Leave user group
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )
    
    @database_sync_to_async
    def get_unread_count(self):
        """Get unread message count for the user"""
        from accounts.models import Chat
        chats = Chat.objects.filter(
            Q(property__owner=self.user) |
            Q(participant=self.user) |
            Q(property__agent=self.user)
        )
        
        total_unread = 0
        for chat in chats:
            total_unread += chat.get_unread_count(self.user)
        
        return total_unread
    
    async def send_initial_count(self):
        """Send initial unread count when connection is established"""
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': count
        }))
    
    async def unread_count_update(self, event):
        """Receive unread count update from channel layer"""
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': event['count']
        }))


class PaymentStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
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


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat messaging"""
    
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.room_group_name = f'chat_{self.chat_id}'
        
        # Verify user has access to this chat
        chat = await self.get_chat(self.chat_id)
        if not chat or not await self.user_has_access(chat):
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send chat history
        await self.send_chat_history(chat)
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'chat_message':
            content = data.get('content', '').strip()
            if content:
                await self.save_and_broadcast_message(content)
        elif message_type == 'typing':
            await self.broadcast_typing_status(data.get('is_typing', False))
        elif message_type == 'read_receipt':
            await self.mark_messages_as_read()
    
    @database_sync_to_async
    def get_chat(self, chat_id):
        try:
            return Chat.objects.select_related('property', 'participant', 'property__owner').get(id=chat_id)
        except Chat.DoesNotExist:
            return None
    
    @database_sync_to_async
    def user_has_access(self, chat):
        """Check if user has access to this chat"""
        if not self.user.is_authenticated:
            return False
        # User can access if they are the property owner, participant, or agent
        return (
            chat.property.owner == self.user or
            chat.participant == self.user or
            (chat.property.agent and chat.property.agent == self.user)
        )
    
    @database_sync_to_async
    def save_message(self, content):
        """Save message to database"""
        try:
            chat = Chat.objects.get(id=self.chat_id)
            message = Message.objects.create(
                chat=chat,
                sender=self.user,
                content=content,
                is_read=False
            )
            
            # Update chat's last_message_at
            from django.utils import timezone
            chat.last_message_at = timezone.now()
            chat.save()
            
            return {
                'id': message.id,
                'content': message.content,
                'sender': {
                    'id': self.user.id,
                    'username': self.user.username,
                    'name': self.user.get_full_name() or self.user.username,
                },
                'created': message.created.isoformat(),
                'is_read': message.is_read,
            }
        except Exception as e:
            print(f"Error saving message: {e}")
            return None
    
    async def save_and_broadcast_message(self, content):
        """Save message and broadcast to all users in the chat"""
        message_data = await self.save_message(content)
        if message_data:
            # Broadcast message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_data
                }
            )
            # Notify unread count update
            await self.notify_unread_count_update()
    
    async def notify_unread_count_update(self):
        """Notify users about unread count update"""
        chat = await self.get_chat(self.chat_id)
        if not chat:
            return
        
        # Get all users involved in this chat
        users_to_notify = set()
        if chat.property.owner:
            users_to_notify.add(chat.property.owner.id)
        if chat.participant:
            users_to_notify.add(chat.participant.id)
        if chat.property.agent:
            users_to_notify.add(chat.property.agent.id)
        
        # Send update to each user
        for user_id in users_to_notify:
            count = await self.get_unread_count_for_user(user_id)
            user_group = f'unread_messages_{user_id}'
            await self.channel_layer.group_send(
                user_group,
                {
                    'type': 'unread_count_update',
                    'count': count
                }
            )
    
    @database_sync_to_async
    def get_unread_count_for_user(self, user_id):
        """Get unread count for a specific user"""
        from accounts.models import User
        try:
            user = User.objects.get(id=user_id)
            chats = Chat.objects.filter(
                Q(property__owner_id=user_id) |
                Q(participant_id=user_id) |
                Q(property__agent_id=user_id)
            )
            total_unread = 0
            for chat in chats:
                total_unread += chat.get_unread_count(user)
            return total_unread
        except User.DoesNotExist:
            return 0
    
    async def chat_message(self, event):
        """Receive message from room group"""
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message
        }))
    
    async def broadcast_typing_status(self, is_typing):
        """Broadcast typing status to other users"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_status',
                'user': {
                    'id': self.user.id,
                    'username': self.user.username,
                },
                'is_typing': is_typing
            }
        )
    
    async def typing_status(self, event):
        """Receive typing status from room group"""
        if event['user']['id'] != self.user.id:  # Don't send to the user who is typing
            await self.send(text_data=json.dumps({
                'type': 'typing_status',
                'user': event['user'],
                'is_typing': event['is_typing']
            }))
    
    @database_sync_to_async
    def get_chat_messages(self, chat):
        """Get all messages for the chat"""
        messages = chat.messages.select_related('sender').all()[:50]  # Last 50 messages
        result = []
        for msg in messages:
            sender_data = None
            if msg.sender:
                sender_data = {
                    'id': msg.sender.id,
                    'username': msg.sender.username,
                    'name': msg.sender.get_full_name() or msg.sender.username,
                }
            result.append({
                'id': msg.id,
                'content': msg.content,
                'sender': sender_data,
                'created': msg.created.isoformat(),
                'is_read': msg.is_read,
            })
        return result
    
    async def send_chat_history(self, chat):
        """Send chat history to the connected user"""
        messages = await self.get_chat_messages(chat)
        await self.send(text_data=json.dumps({
            'type': 'chat_history',
            'messages': messages
        }))
    
    @database_sync_to_async
    def mark_messages_as_read_db(self):
        """Mark messages as read in database"""
        try:
            chat = Chat.objects.get(id=self.chat_id)
            chat.mark_as_read(self.user)
            return True
        except Exception as e:
            print(f"Error marking messages as read: {e}")
            return False
    
    async def mark_messages_as_read(self):
        """Mark messages as read and notify other users"""
        success = await self.mark_messages_as_read_db()
        if success:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_receipt',
                    'user': {
                        'id': self.user.id,
                        'username': self.user.username,
                    }
                }
            )
    
    async def read_receipt(self, event):
        """Receive read receipt from room group"""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'user': event['user']
        }))