from django.dispatch import receiver
from apps.posts.signals import post_liked
from .tasks import send_notification_task

@receiver(post_liked)
def handle_post_liked(sender, instance, user, **kwargs):
    """
    listen event 'post_liked' from app posts
    instance: post was liked
    user: user who liked post
    """
    send_notification_task.delay(
        recipient_id=instance.author.id,
        sender_id=user.id,
        notif_type='like',
        message=f'{user.username} liked your post',
        post_id=instance.id
    )
