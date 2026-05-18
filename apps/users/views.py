from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import User, Follow
from .serializers import RegisterSerializer, UserSerializer

# Create your views here.
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow(request):
    username = request.data.get('username')
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if target_user == request.user:
        return Response({'error': 'You cannot follow yourself'}, status=status.HTTP_400_BAD_REQUEST)

    follow, created = Follow.objects.get_or_create(follower=request.user, following=target_user)

    if not created:
        return Response({'error': 'You are already following this user'}, status=status.HTTP_400_BAD_REQUEST)

    create_notification(
        recipient=post.author,
        sender=request.user,
        notif_type='like',
        message=f'{request.user.username} liked your post'
    )

    return Response({'message': f'You are now following {target_user.username}'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unfollow(request):
    username = request.data.get('username')
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if target_user == request.user:
        return Response({'error': 'You cannot unfollow yourself'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        follow = Follow.objects.get(follower=request.user, following=target_user)
        follow.delete()
        return Response({'message': f'You have unfollowed {target_user.username}'}, status=status.HTTP_200_OK)
    except Follow.DoesNotExist:
        return Response({'error': 'You are not following this user'}, status=status.HTTP_400_BAD_REQUEST)


