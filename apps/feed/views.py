from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.posts.models import Post
from apps.posts.serializers import PostSerializer
from apps.users.models import Follow
from utils.response import APIResponse


# Create your views here.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def feed(request):
    # Get the current user are following
    following = Follow.objects.filter(follower=request.user).values_list('following', flat=True)

    if not following:
        # return Response({
        #     'message': 'Follow someone to see their posts here',
        #     'results': []
        # })
        return APIResponse.error(
            message='Follow someone to see their posts here',
            error_code='NO_FOLLOWING',
            data={'results': []}
        )


    # Get posts from followed users
    posts = Post.objects.filter(author_id__in=following).select_related('author').order_by('-created_at')[:50]

    serializer = PostSerializer(posts, many=True, context={'request': request})

    # return Response({
    #     'count': len(serializer.data),
    #     'results': serializer.data
    # })
    return APIResponse.success(
        data={
            'count': len(serializer.data),
            'results': serializer.data
        }
    )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def explore(request):
    posts = Post.objects.select_related('author').order_by('-created_at')[:50]
    serializer = PostSerializer(posts, many=True, context={'request': request})
    # return Response({
    #     'count': len(serializer.data),
    #     'results': serializer.data
    # })
    return APIResponse.success(
        data={
            'count': len(serializer.data),
            'results': serializer.data
        }
    )