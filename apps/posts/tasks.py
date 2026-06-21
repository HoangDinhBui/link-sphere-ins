from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from apps.posts.models import Post, Hashtag
from django.db.models import Count
from django.core.cache import cache
import json

@shared_task
def calculate_trending_hashtags():
    time_threshold = timezone.now() - timedelta(hours=24)
    
    trending = Hashtag.objects.filter(
        post__created_at__gte=time_threshold
    ).annotate(
        post_count=Count('post')
    ).order_by('-post_count')[:10]
    
    result = [
        {'id': tag.id, 'name': tag.name, 'post_count': tag.post_count}
        for tag in trending
    ]
    
    cache.set('trending_hashtags', json.dumps(result), timeout=60 * 90)
    return result
