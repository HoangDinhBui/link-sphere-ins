from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Comment
from .serializers import CommentSerializer
from apps.posts.models import Post
from apps.notifications.utils import create_notification

# Create your views here.
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def comments(request, post_id):
    try:
        post = Post.objects.get(id = post_id)
    except:
        return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        all_comments = Comment.objects.filter(post=post).select_related('author')
        serializer = CommentSerializer(all_comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    serializer = CommentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(author=request.user, post=post)

        create_notification(
            recipient=post.author,
            sender=request.user,
            notif_type='comment',
            message=f'{request.user.username} commented on your post'
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)