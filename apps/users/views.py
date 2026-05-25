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

    try:
        import resend
        from django.conf import settings
        resend.api_key = settings.RESEND_API_KEY
        
        if user.email:
            # The onboarding@resend.dev domain only sends to the verified email address on the free tier
            
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px; background-color: #f9f9f9;">
                <div style="text-align: center; padding-bottom: 20px;">
                    <h2 style="color: #4A90E2; margin: 0; font-size: 28px;">LinkSphere 🌐</h2>
                </div>
                <div style="background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <h3 style="color: #333333; margin-top: 0;">Xin chào {user.username},</h3>
                    <p style="color: #555555; line-height: 1.6; font-size: 16px;">Cảm ơn bạn đã gia nhập mạng xã hội <strong>LinkSphere</strong>. Chúng tôi rất vui mừng được chào đón bạn đến với cộng đồng của chúng tôi!</p>
                    <p style="color: #555555; line-height: 1.6; font-size: 16px;">Hãy bắt đầu khám phá, kết nối với bạn bè và chia sẻ những khoảnh khắc tuyệt vời của bạn ngay hôm nay.</p>
                    
                    <div style="text-align: center; margin: 35px 0;">
                        <a href="https://github.com/HoangDinhBui/link-sphere-ins" style="background-color: #4A90E2; color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 6px; font-weight: bold; font-size: 16px; display: inline-block;">Khám phá ngay</a>
                    </div>
                    
                    <p style="color: #555555; line-height: 1.6; font-size: 16px;">Thân mến,<br/><strong>LinkSphere Team</strong></p>
                </div>
                <div style="text-align: center; margin-top: 25px; font-size: 13px; color: #999999;">
                    <p style="margin: 5px 0;">Bạn nhận được email này vì đã đăng ký tài khoản tại LinkSphere.</p>
                    <p style="margin: 5px 0;">
                        <a href="https://github.com/HoangDinhBui/link-sphere-ins/blob/main/README.md" style="color: #4A90E2; text-decoration: none;">Điều khoản dịch vụ</a> &nbsp;|&nbsp; 
                        <a href="https://github.com/HoangDinhBui/link-sphere-ins/blob/main/README.md" style="color: #4A90E2; text-decoration: none;">Chính sách bảo mật</a>
                    </p>
                </div>
            </div>
            """

            resend.Emails.send({
                "from": "LinkSphere <onboarding@resend.dev>",
                "to": user.email,
                "subject": "Chào mừng bạn đến với LinkSphere! 🚀",
                "html": html_content
            })
    except Exception as e:
        print(f"Lỗi gửi email chào mừng: {e}")

    return APIResponse.success(
        message='User registered successfully',
        data=UserSerializer(user).data,
        status_code=status.HTTP_201_CREATED
    )
    # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    responses={200: swagger_response(UserSerializer, name_prefix='Profile')},
    description="Lấy thông tin profile cá nhân"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    serializer = UserSerializer(request.user)
    # return Response(serializer.data)
    return APIResponse.success(
        message='User profile retrieved successfully',
        data=serializer.data,
        status_code=status.HTTP_200_OK
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


