from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.posts.models import Post
from apps.posts.serializers import PostSerializer
from apps.users.models import Follow
from utils.response import APIResponse, swagger_response
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
# Create your views here.
FeedDataSchema = inline_serializer(
    name='FeedData',
    fields={
        'count': serializers.IntegerField(),
        'results': PostSerializer(many=True)
    }
)

@extend_schema(
    responses={200: swagger_response(FeedDataSchema, name_prefix='Feed')},
    description="Lấy danh sách bài viết trên News Feed (từ những người đang follow)"
)
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
        return APIResponse.success(
            message='Follow someone to see their posts here',
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

@extend_schema(
    responses={200: swagger_response(FeedDataSchema, name_prefix='Explore')},
    description="Khám phá các bài viết nổi bật"
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