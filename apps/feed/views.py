from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.posts.models import Post
from apps.posts.serializers import PostSerializer
from apps.users.models import Follow

# Create your views here.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def feed(request):
    # Get the current user are following
    following = Follow.objects.filter(follower=request.user).values_list('following', flat=True)

    # Get posts from followed users
    posts = Post.objects.filter(author_id__in=following).select_related('author').order_by('-created_at')

    serializer = PostSerializer(posts, many=True, context={'request': request})
    return Response(serializer.data)