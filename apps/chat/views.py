from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.pagination import CursorPagination
from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from utils.response import APIResponse
from apps.chat.models import Conversation, ConversationParticipant, Message
from apps.users.models import User
from apps.chat.serializers import ConversationSerializer, MessageSerializer, ConversationCreateSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

class ChatMessageCursorPagination(CursorPagination):
    page_size = 50
    ordering = '-created_at' # xếp tin nhắn mới nhất lên đầu
    cursor_query_param = 'cursor'

    def get_paginated_response(self, data):
        return Response({
            "success": True,
            "message": "Get message history successfully.",
            "data": data,
            "pagination": {
                "next": self.get_next_link(),
                "previous": self.get_previous_link()
            }
        })

class ConversationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: ConversationSerializer(many=True)},
        description="Get list of conversations that user participates in"
    )
    def list(self, request):
        conversations = Conversation.objects.filter(
            participants__user=request.user
        ).order_by('-updated_at')
        
        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return APIResponse.success(data=serializer.data)

    @extend_schema(
        request=ConversationCreateSerializer,
        responses={201: ConversationSerializer},
        description="Initiate a new conversation (direct chat or group chat)"
    )
    def create(self, request):
        chat_type = request.data.get('type', 'direct')
        
        if chat_type not in ['direct', 'group']:
            return APIResponse.error(
                message="Invalid chat type. Only 'direct' or 'group' are allowed.",
                error_code="INVALID_CHAT_TYPE",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if chat_type == 'direct':
            recipient_id = request.data.get('recipient_id')
            if not recipient_id:
                return APIResponse.error(
                    message="Recipient ID is required for direct chat.",
                    error_code="RECIPIENT_ID_REQUIRED",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                recipient = User.objects.get(id=recipient_id)
            except User.DoesNotExist:
                return APIResponse.error(
                    message="Recipient not found.",
                    error_code="RECIPIENT_NOT_FOUND",
                    status_code=status.HTTP_404_NOT_FOUND
                )

            if recipient == request.user:
                return APIResponse.error(
                    message="Cannot chat with yourself.",
                    error_code="CANNOT_CHAT_SELF",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # check xem đã tồn tại cuộc hội thoại direct chat giữa hai người dùng chưa
            existing_chat = Conversation.objects.filter(
                type='direct',
                participants__user=request.user
            ).filter(
                participants__user=recipient
            ).first()

            if existing_chat:
                serializer = ConversationSerializer(existing_chat, context={'request': request})
                return APIResponse.success(
                    data=serializer.data,
                    message="Reuse existing conversation.",
                    status_code=status.HTTP_200_OK
                )

            # tạo direct chat mới sử dụng transaction bảo đảm toàn vẹn dữ liệu
            with transaction.atomic():
                conversation = Conversation.objects.create(type='direct')
                ConversationParticipant.objects.create(
                    conversation=conversation,
                    user=request.user,
                    role='member'
                )
                ConversationParticipant.objects.create(
                    conversation=conversation,
                    user=recipient,
                    role='member'
                )

            serializer = ConversationSerializer(conversation, context={'request': request})
            return APIResponse.success(
                data=serializer.data,
                message="Create direct chat successfully.",
                status_code=status.HTTP_201_CREATED
            )

        elif chat_type == 'group':
            title = request.data.get('title')
            participant_ids = request.data.get('participants', [])

            if not title:
                return APIResponse.error(
                    message="Group title is required.",
                    error_code="GROUP_TITLE_REQUIRED",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Tạo group chat sử dụng transaction
            with transaction.atomic():
                conversation = Conversation.objects.create(
                    type='group',
                    title=title,
                    avatar=request.FILES.get('avatar')
                )
                # thêm người tạo làm admin
                ConversationParticipant.objects.create(
                    conversation=conversation,
                    user=request.user,
                    role='admin'
                )
                
                # thêm các thành viên khác
                if participant_ids:
                    valid_participants = User.objects.filter(id__in=participant_ids).exclude(id=request.user.id)
                    for user in valid_participants:
                        ConversationParticipant.objects.create(
                            conversation=conversation,
                            user=user,
                            role='member'
                        )

            serializer = ConversationSerializer(conversation, context={'request': request})
            return APIResponse.success(
                data=serializer.data,
                message="Create group chat successfully.",
                status_code=status.HTTP_201_CREATED
            )

    @extend_schema(
        parameters=[OpenApiParameter("cursor", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Cursor phân trang")],
        responses={200: MessageSerializer(many=True)},
        description="Get message history of the conversation (Pagination based on Cursor)"
    )
    @action(detail=True, methods=['GET'], url_path='messages')
    def messages(self, request, pk=None):
        # check xem cuộc hội thoại có tồn tại không
        try:
            conversation = Conversation.objects.get(id=pk)
        except (Conversation.DoesNotExist, ValueError):
            return APIResponse.error(
                message="Conversation not found.",
                error_code="CONVERSATION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # check xem người dùng hiện tại có quyền truy cập cuộc hội thoại này không
        try:
            participant = ConversationParticipant.objects.get(conversation=conversation, user=request.user)
        except ConversationParticipant.DoesNotExist:
            return APIResponse.error(
                message="You are not a participant of this conversation.",
                error_code="ACCESS_DENIED",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # lấy các tin nhắn chưa bị xóa
        queryset = Message.objects.filter(conversation=conversation, is_deleted=False).order_by('-created_at')

        # phân trang Cursor
        paginator = ChatMessageCursorPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        
        # tự động cập nhật trạng thái "đã đọc" toàn bộ tin nhắn mới nhất trong phòng
        latest_message = queryset.first()
        if latest_message:
            participant.last_read_message_id = latest_message.id
            participant.save(update_fields=['last_read_message_id'])

        if page is not None:
            serializer = MessageSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = MessageSerializer(queryset, many=True, context={'request': request})
        return APIResponse.success(data=serializer.data)

class ChatMediaUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {
                        'type': 'string',
                        'format': 'binary'
                    }
                }
            }
        },
        responses={200: OpenApiTypes.OBJECT},
        description="Upload images/videos/files to Cloudinary for WebSocket transmission"
    )
    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return APIResponse.error(
                message="No file uploaded.",
                error_code="NO_FILE_UPLOADED",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Lưu file bằng Django default_storage (tự động đẩy lên Cloudinary)
        try:
            file_name = default_storage.save(f"chat_media/{file_obj.name}", file_obj)
            file_url = default_storage.url(file_name)
            
            return APIResponse.success(
                data={"file_url": file_url},
                message="Upload file successfully."
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Upload file failed: {str(e)}",
                error_code="UPLOAD_FAILED",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
