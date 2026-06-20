from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from utils.response import APIResponse, swagger_response
from .models import User, Follow
from .serializers import RegisterSerializer, UserSerializer
from apps.notifications.utils import create_notification
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from apps.posts.models import Post
from apps.posts.serializers import PostSerializer

class CustomLoginView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return APIResponse.success(
            message='Login successful',
            data=serializer.validated_data,
            status_code=status.HTTP_200_OK
        )



# Create your views here.
@extend_schema(
    request=RegisterSerializer,
    responses={201: swagger_response(UserSerializer, name_prefix='Register')},
    description="Đăng ký tài khoản mới"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    # Đẩy việc gửi email ra background để API trả về ngay, không block request.
    if user.email:
        from apps.users.tasks import send_welcome_email
        send_welcome_email.delay(user.email, user.username)

    return APIResponse.success(
        message='User registered successfully',
        data=UserSerializer(user).data,
        status_code=status.HTTP_201_CREATED
    )
    # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    request=UserSerializer,
    responses={200: swagger_response(UserSerializer, name_prefix='Profile')},
    description="Lấy hoặc cập nhật thông tin profile cá nhân"
)
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile(request):
    if request.method == 'GET':
        serializer = UserSerializer(request.user)
        return APIResponse.success(
            message='User profile retrieved successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    
    # PATCH logic
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return APIResponse.success(
            message='User profile updated successfully',
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    return APIResponse.error(
        message='Failed to update profile',
        error_code='UPDATE_PROFILE_FAILED',
        data=serializer.errors,
        status_code=status.HTTP_400_BAD_REQUEST
    )


@extend_schema(
    request={'application/json': {'type': 'object', 'properties': {'username': {'type': 'string'}}}},
    responses={200: swagger_response(name_prefix='Follow')},
    description="Follow một người dùng khác bằng username"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow(request):
    username = request.data.get('username')
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        # return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return APIResponse.error(
            message='User not found',
            error_code='USER_NOT_FOUND',
            status_code=status.HTTP_404_NOT_FOUND
        )

    if target_user == request.user:
        # return Response({'error': 'You cannot follow yourself'}, status=status.HTTP_400_BAD_REQUEST)
        return APIResponse.error(
            message='You cannot follow yourself',
            error_code='CANNOT_FOLLOW_SELF',
            status_code=status.HTTP_400_BAD_REQUEST
        )

    follow, created = Follow.objects.get_or_create(follower=request.user, following=target_user)

    if not created:
        # return Response({'error': 'You are already following this user'}, status=status.HTTP_400_BAD_REQUEST)
        return APIResponse.error(
            message='You are already following this user',
            error_code='ALREADY_FOLLOWING',
            status_code=status.HTTP_400_BAD_REQUEST
        )

    create_notification(
        recipient=target_user,
        sender=request.user,
        notif_type='follow',
        message=f'{request.user.username} started following you'
    )

    # return Response({'message': f'You are now following {target_user.username}'}, status=status.HTTP_200_OK)
    return APIResponse.success(
        message=f'You are now following {target_user.username}',
        data={'username': target_user.username},
        status_code=status.HTTP_200_OK
    )

@extend_schema(
    request={'application/json': {'type': 'object', 'properties': {'username': {'type': 'string'}}}},
    responses={200: swagger_response(name_prefix='Unfollow')},
    description="Bỏ follow một người dùng bằng username"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unfollow(request):
    username = request.data.get('username')
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        # return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return APIResponse.error(
            message='User not found',
            error_code='USER_NOT_FOUND',
            status_code=status.HTTP_404_NOT_FOUND
        )

    if target_user == request.user:
        # return Response({'error': 'You cannot unfollow yourself'}, status=status.HTTP_400_BAD_REQUEST)
        return APIResponse.error(
            message='You cannot unfollow yourself',
            error_code='CANNOT_UNFOLLOW_SELF',
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        follow = Follow.objects.get(follower=request.user, following=target_user)
        follow.delete()
        # return Response({'message': f'You have unfollowed {target_user.username}'}, status=status.HTTP_200_OK)
        return APIResponse.success(
            message=f'You have unfollowed {target_user.username}',
            data={'username': target_user.username},
            status_code=status.HTTP_200_OK
        )
    except Follow.DoesNotExist:
        #return Response({'error': 'You are not following this user'}, status=status.HTTP_400_BAD_REQUEST)
        return APIResponse.error(
            message='You are not following this user',
            error_code='NOT_FOLLOWING',
            status_code=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(
    responses={200: swagger_response(PostSerializer, many=True, name_prefix='UserPosts')},
    description="Lấy danh sách bài viết của một user theo username"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_posts(request, username):
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return APIResponse.error(
            message='User not found',
            error_code='USER_NOT_FOUND',
            status_code=status.HTTP_404_NOT_FOUND
        )

    posts = Post.objects.filter(author=target_user).select_related('author').prefetch_related('likes', 'comments').order_by('-created_at')
    serializer = PostSerializer(posts, many=True, context={'request': request})
    
    return APIResponse.success(
        message=f'Retrieved posts for {username}',
        data=serializer.data,
        status_code=status.HTTP_200_OK
    )

from apps.posts.models import Bookmark

@extend_schema(
    responses={200: swagger_response(PostSerializer, many=True, name_prefix='UserBookmarks')},
    description="Lấy danh sách bài viết đã lưu (bookmark) của một user theo username"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_bookmarks(request, username):
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return APIResponse.error(
            message='User not found',
            error_code='USER_NOT_FOUND',
            status_code=status.HTTP_404_NOT_FOUND
        )

    # Chỉ cho phép xem bookmark của chính mình
    if target_user != request.user:
        return APIResponse.error(
            message='You do not have permission to view these bookmarks',
            error_code='PERMISSION_DENIED',
            status_code=status.HTTP_403_FORBIDDEN
        )

    bookmarks = Bookmark.objects.filter(user=target_user, post__is_delete=False).select_related('post', 'post__author').order_by('-created_at')
    bookmarked_posts = [bookmark.post for bookmark in bookmarks]
    
    serializer = PostSerializer(bookmarked_posts, many=True, context={'request': request})
    
    return APIResponse.success(
        message='Retrieved bookmarked posts successfully',
        data=serializer.data,
        status_code=status.HTTP_200_OK
    )

