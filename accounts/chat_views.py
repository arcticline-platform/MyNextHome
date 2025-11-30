"""
Chat views for messaging functionality
"""
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Max, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.urls import reverse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Chat, Message, Property, PropertyContact


@login_required
def chat_list(request):
    """Display unified chat page with list and detail view"""
    # Get all chats where user is property owner, participant, or agent
    chats = Chat.objects.filter(
        Q(property__owner=request.user) |
        Q(participant=request.user) |
        Q(property__agent=request.user)
    ).select_related(
        'property', 'participant', 'property__owner', 'property__agent'
    ).annotate(
        unread_count=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user))
    ).order_by('-last_message_at', '-created')
    
    # Get unread counts for each chat
    for chat in chats:
        chat.unread_count = chat.get_unread_count(request.user)
    
    # Check if a specific chat is requested
    chat_id = request.GET.get('chat')
    chat = None
    messages_page = None
    other_participant = None
    other_participant_name = None
    property_obj = None
    
    if chat_id:
        try:
            chat = get_object_or_404(
                Chat.objects.select_related('property', 'participant', 'property__owner', 'property__agent'),
                id=chat_id
            )
            
            # Check if user has access to this chat
            if (chat.property.owner == request.user or 
                chat.participant == request.user or 
                (chat.property.agent and chat.property.agent == request.user)):
                
                # Mark messages as read
                chat.mark_as_read(request.user)
                
                # Get messages (paginated)
                messages = chat.messages.select_related('sender').all().order_by('created')
                paginator = Paginator(messages, 50)
                page = request.GET.get('page', 1)
                messages_page = paginator.get_page(page)
                
                # Get other participant info
                other_participant = chat.get_other_participant(request.user)
                other_participant_name = chat.get_other_participant_name(request.user)
                property_obj = chat.property
        except:
            pass
    
    context = {
        'chats': chats,
        'chat': chat,
        'messages': messages_page,
        'other_participant': other_participant,
        'other_participant_name': other_participant_name,
        'property': property_obj,
    }
    return render(request, 'accounts/chat.html', context)


@login_required
def chat_detail(request, chat_id):
    """Redirect to unified chat view with chat parameter"""
    # Redirect to unified chat view
    return redirect(f"{reverse('chat_list')}?chat={chat_id}")


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def send_message(request, chat_id):
    """Send a message via AJAX (fallback when WebSocket is not available)"""
    try:
        chat = Chat.objects.select_related('property', 'participant', 'property__owner', 'property__agent').get(id=chat_id)
        
        # Check if user has access
        if not (chat.property.owner == request.user or 
                chat.participant == request.user or 
                (chat.property.agent and chat.property.agent == request.user)):
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'error': 'Message content is required'}, status=400)
        
        # Create message
        message = Message.objects.create(
            chat=chat,
            sender=request.user,
            content=content,
            is_read=False
        )
        
        # Update chat's last_message_at
        chat.last_message_at = timezone.now()
        chat.save()
        
        # Notify users about unread count update via WebSocket
        notify_unread_count_update(chat)
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'sender': {
                    'id': request.user.id,
                    'username': request.user.username,
                    'name': request.user.get_full_name() or request.user.username,
                },
                'created': message.created.isoformat(),
                'is_read': message.is_read,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def notify_unread_count_update(chat):
    """Notify users about unread count update via WebSocket"""
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
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
            # Get unread count for this user
            user = chat.property.owner.__class__.objects.get(id=user_id) if hasattr(chat.property.owner, '__class__') else None
            if not user:
                continue
                
            user_chats = Chat.objects.filter(
                Q(property__owner_id=user_id) |
                Q(participant_id=user_id) |
                Q(property__agent_id=user_id)
            )
            total_unread = 0
            for user_chat in user_chats:
                total_unread += user_chat.get_unread_count(user)
            
            user_group = f'unread_messages_{user_id}'
            async_to_sync(channel_layer.group_send)(
                user_group,
                {
                    'type': 'unread_count_update',
                    'count': total_unread
                }
            )
    except Exception as e:
        print(f"Error notifying unread count update: {e}")
    except Chat.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Chat not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_messages(request, chat_id):
    """Get messages for a chat via AJAX (for polling)"""
    try:
        chat = Chat.objects.get(id=chat_id)
        
        # Check if user has access
        if not (chat.property.owner == request.user or 
                chat.participant == request.user or 
                (chat.property.agent and chat.property.agent == request.user)):
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        # Get last message ID from request (for incremental updates)
        last_message_id = request.GET.get('last_message_id', None)
        
        if last_message_id:
            messages = chat.messages.filter(id__gt=last_message_id).select_related('sender').order_by('created')
        else:
            messages = chat.messages.select_related('sender').all().order_by('-created')[:50]
            messages = list(reversed(messages))
        
        messages_data = []
        for msg in messages:
            sender_data = None
            if msg.sender:
                sender_data = {
                    'id': msg.sender.id,
                    'username': msg.sender.username,
                    'name': msg.sender.get_full_name() or msg.sender.username,
                }
            messages_data.append({
                'id': msg.id,
                'content': msg.content,
                'sender': sender_data,
                'created': msg.created.isoformat(),
                'is_read': msg.is_read,
            })
        
        # Mark messages as read
        chat.mark_as_read(request.user)
        
        return JsonResponse({
            'success': True,
            'messages': messages_data,
            'chat_id': chat.id,
        })
    except Chat.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Chat not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def create_chat_from_contact(request, contact_id):
    """Create a chat from a property contact request"""
    try:
        contact = PropertyContact.objects.select_related('property', 'user', 'property__owner', 'property__agent').get(id=contact_id)
        
        # Check if user has access (must be property owner or agent)
        if not (contact.property.owner == request.user or 
                (contact.property.agent and contact.property.agent == request.user)):
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        # Create or get chat
        chat = contact.create_chat()
        
        return JsonResponse({
            'success': True,
            'chat_id': chat.id,
            'redirect_url': f'/accounts/chat/{chat.id}/'
        })
    except PropertyContact.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Contact not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_unread_count(request):
    """Get total unread message count for the current user"""
    try:
        # Get all chats where user is property owner, participant, or agent
        chats = Chat.objects.filter(
            Q(property__owner=request.user) |
            Q(participant=request.user) |
            Q(property__agent=request.user)
        )
        
        # Count unread messages across all chats
        total_unread = 0
        for chat in chats:
            unread = chat.get_unread_count(request.user)
            total_unread += unread
        
        return JsonResponse({
            'success': True,
            'unread_count': total_unread
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

