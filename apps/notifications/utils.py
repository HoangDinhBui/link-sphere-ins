from .models import Notification
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def create_notification(recipient, sender, notif_type, message):
    if recipient == sender:
        return
    Notification.objects.create(
        recipient=recipient,
        sender=sender,
        type=notif_type,
        message=message
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{recipient.id}',
        {
            'type': 'send_notification', # map to method in consumer
            'notification_type': notif_type,
            'message': message,
            'sender': sender.username
        }
    )