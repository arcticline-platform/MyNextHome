from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Action, Notification


@receiver(post_save, sender=Action)
def action_created(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'notification_inbox_{instance.user.username}',
            {
                "type": "send_notification",
                "message": instance.verb
            }
        )


@receiver(post_save, sender=Notification)
def notification_created(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'public_room',
            {
                "type": "send_notification",
                "message": instance.message
            }
        )
