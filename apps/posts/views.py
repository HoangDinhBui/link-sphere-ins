from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Post, Like, User
from .serializers import PostSerializer
from apps.notifications.utils import create_notification
from apps.users.models import Follow
from utils.response import APIResponse, swagger_response
from .signals import post_liked
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

# Create your views here.
@extend_schema(
    request=PostSerializer,
    responses={200: swagger_response(PostSerializer, many=True, name_prefix='PostList'), 201: swagger_response(PostSerializer, name_prefix='PostCreate')},
    description="Lấy danh sách post hoặc tạo post mới"
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def posts(request):
    if request.method == 'GET':
        all_post = Post.objects.select_related('author').prefetch_related('likes', 'comments').filter(is_delete=False)
        serializer = PostSerializer(all_post, many=True, context={'request': request})
        # return Response(serializer.data, status=status.HTTP_200_OK)
        return APIResponse.success(data=serializer.data)

    serializer = PostSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        post = serializer.save(author=request.user)
        follower_ids = Follow.objects.filter(following=request.user).values_list('follower', flat=True)
        from apps.users.models import User as AppUser
        for follower in AppUser.objects.filter(id__in=follower_ids):
            create_notification(
                recipient=follower,
                sender=request.user,
                notif_type='new_post',
                message=f'{request.user.username} has posted a new update',
                post=post
            )

        # return Response(serializer.data, status=status.HTTP_201_CREATED)
        return APIResponse.success(
            message='Post created successfully',
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )
    # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return APIResponse.error(
        message='Failed to create post',
        error_code='POST_CREATION_FAILED',
        data=serializer.errors,
        status_code=status.HTTP_400_BAD_REQUEST
    )

@extend_schema(
    request=PostSerializer,
    responses={200: swagger_response(PostSerializer, many=True, name_prefix='PostDelete'), 201: swagger_response(PostSerializer, name_prefix='PostDelete')},
    description="Xoá 1 bài post"
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_post(request, post_id):
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return APIResponse.error(
            message="Post not found",
            error_code="POST_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )

    if post.author != request.user:
        return APIResponse.error(
            message="You do not have permission to delete this post",
            error_code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN
        )

    if post.is_delete:
        return APIResponse.error(
            message="Post has already been deleted",
            error_code="POST_ALREADY_DELETED",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    post.is_delete=True
    post.save()

    return APIResponse.success(
        message="Delete post success",
        status_code=status.HTTP_200_OK
    )

@extend_schema(
    request=None,
    responses={200: swagger_response(name_prefix='Unlike'), 201: swagger_response(name_prefix='Like')},
    description="Thích hoặc bỏ thích bài viết"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_post(request, post_id):
    try:
        post = Post.objects.get(id=post_id, is_delete=False)
    except Post.DoesNotExist:
        # return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
        return APIResponse.error(
            message='Post not found',
            error_code='POST_NOT_FOUND',
            status_code=status.HTTP_404_NOT_FOUND
        )

    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
        # return Response({'message': 'Post unliked'}, status=status.HTTP_200_OK)
        return APIResponse.success(
            message='Post unliked',
            status_code=status.HTTP_200_OK
        )

    post_liked.send(sender=post.__class__, instance=post, user=request.user)

    # return Response({'message': 'Post liked'}, status=status.HTTP_201_CREATED)
    return APIResponse.success(
        message='Post liked',
        status_code=status.HTTP_201_CREATED
    )

from .models import Bookmark

@extend_schema(
    request=None,
    responses={200: swagger_response(name_prefix='Unbookmark'), 201: swagger_response(name_prefix='Bookmark')},
    description="Lưu hoặc bỏ lưu bài viết (Bookmark)"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_bookmark(request, post_id):
    try:
        post = Post.objects.get(id=post_id, is_delete=False)
    except Post.DoesNotExist:
        return APIResponse.error(
            message='Post not found',
            error_code='POST_NOT_FOUND',
            status_code=status.HTTP_404_NOT_FOUND
        )

    bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)
    if not created:
        bookmark.delete()
        return APIResponse.success(
            message='Post removed from bookmarks',
            status_code=status.HTTP_200_OK
        )

    return APIResponse.success(
        message='Post bookmarked successfully',
        status_code=status.HTTP_201_CREATED
    )
