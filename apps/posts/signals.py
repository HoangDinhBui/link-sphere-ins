from django.dispatch import Signal
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.posts.models import Post, Hashtag
import re

post_liked = Signal()

@receiver(post_save, sender=Post)
def extract_hashtags_from_post(sender, instance, created, **kwargs):
    hashtags = re.findall(r'#(\w+)', instance.content)
    
    if hashtags:
        hashtags = list(set([h.lower() for h in hashtags]))
        
        hashtag_objs = []
        for tag in hashtags:
            obj, _ = Hashtag.objects.get_or_create(name=tag)
            hashtag_objs.append(obj)
        
        instance.hashtags.set(hashtag_objs)
    else:
        instance.hashtags.clear()