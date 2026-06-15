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
        all_comments = Comment.objects.filter(post=post).select_related('author')
        serializer = CommentSerializer(all_comments, many=True)
        # return Response(serializer.data, status=status.HTTP_200_OK)
        return APIResponse.success(data=serializer.data)

    serializer = CommentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(author=request.user, post=post)

    create_notification(
        recipient=post.author,
        sender=request.user,
        notif_type='comment',
        message=f'{request.user.username} commented on your post',
        post=post
    )

    # return Response(serializer.data, status=status.HTTP_201_CREATED)
    return APIResponse.success(
        message='Comment created successfully',
        data=serializer.data,
        status_code=status.HTTP_201_CREATED
    )