from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Comment
from .serializers import CommentSerializer
from apps.posts.models import Post
from apps.notifications.utils import create_notification
from utils.response import APIResponse, swagger_response
from drf_spectacular.utils import extend_schema

# Create your views here.
@extend_schema(
    request=CommentSerializer,
    responses={200: swagger_response(CommentSerializer, many=True, name_prefix='CommentList'), 201: swagger_response(CommentSerializer, name_prefix='CommentCreate')},
    description="Xem danh sách comment hoặc tạo comment mới cho bài viết"
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def comments(request, post_id):
    try:
        post = Post.objects.get(id = post_id)
    except:
        # return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
        return APIResponse.error(
            message='Post not found',
            error_code='POST_NOT_FOUND',
            status_code=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'GET':
        all_comments = Comment.objects.filter(post=post, parent=None).select_related('author')
        serializer = CommentSerializer(all_comments, many=True)
        return APIResponse.success(data=serializer.data)

    serializer = CommentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    parent = serializer.validated_data.get('parent')
    if parent and parent.post != post:
        return APIResponse.error(
            message='Parent comment does not belong to this post',
            error_code='INVALID_PARENT_COMMENT',
            status_code=status.HTTP_400_BAD_REQUEST
        )

    comment = serializer.save(author=request.user, post=post)

    if parent and parent.author != request.user:
        create_notification(
            recipient=parent.author,
            sender=request.user,
            notif_type='comment',
            message=f'{request.user.username} replied to your comment',
            post=post
        )
    elif post.author != request.user:
        create_notification(
            recipient=post.author,
            sender=request.user,
            notif_type='comment',
            message=f'{request.user.username} commented on your post',
            post=post
        )

    return APIResponse.success(
        message='Comment created successfully',
        data=serializer.data,
        status_code=status.HTTP_201_CREATED
    )

@extend_schema(
    responses={200: swagger_response(CommentSerializer, many=True, name_prefix='CommentReplies')},
    description="Xem danh sách câu trả lời (replies) của một comment"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def replies(request, post_id, comment_id):
    try:
        parent_comment = Comment.objects.get(id=comment_id, post_id=post_id)
    except Comment.DoesNotExist:
        return APIResponse.error(
            message='Comment not found',
            error_code='COMMENT_NOT_FOUND',
            status_code=status.HTTP_404_NOT_FOUND
        )

    all_replies = Comment.objects.filter(parent=parent_comment).select_related('author')
    serializer = CommentSerializer(all_replies, many=True)
    return APIResponse.success(data=serializer.data)