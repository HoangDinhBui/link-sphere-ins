from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task
def send_notification_task(recipient_id, sender_id, notif_type, message, post_id=None):
    if recipient_id == sender_id:
        return
        
    Notification.objects.create(
        recipient_id=recipient_id,
        sender_id=sender_id,
        type=notif_type,
        message=message,
        post_id=post_id
    )

    # get sender username for the real-time event
    try:
        sender = User.objects.get(id=sender_id)
        sender_username = sender.username
    except User.DoesNotExist:
        sender_username = 'Unknown'

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{recipient_id}',
        {
            'type': 'send_notification', # map to method in consumer
            'notification_type': notif_type,
            'message': message,
            'sender': sender_username,
            'post_id': post_id
        }
    )
