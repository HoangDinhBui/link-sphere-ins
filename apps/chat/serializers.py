from rest_framework import serializers
from apps.users.models import User
from apps.chat.models import Conversation, ConversationParticipant, Message

class UserChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'avatar']

class ConversationCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[('direct', 'Direct'), ('group', 'Group')], default='direct')
    recipient_id = serializers.IntegerField(required=False, help_text="Bắt buộc nếu type=direct. ID của người nhận tin nhắn.")
    title = serializers.CharField(required=False, max_length=255, help_text="Bắt buộc nếu type=group. Tiêu đề của nhóm chat.")
    participants = serializers.ListField(
        child=serializers.IntegerField(), 
        required=False, 
        help_text="Danh sách ID thành viên khác (chỉ dành cho group chat)."
    )

class MessageSerializer(serializers.ModelSerializer):
    sender = UserChatSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 
            'conversation', 
            'sender', 
            'content', 
            'message_type', 
            'file_url', 
            'created_at', 
            'updated_at', 
            'is_deleted'
        ]
        read_only_fields = ['id', 'sender', 'created_at', 'updated_at']

class ConversationSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 
            'title', 
            'type', 
            'avatar', 
            'created_at', 
            'updated_at', 
            'last_message', 
            'unread_count', 
            'other_participant'
        ]

    def get_other_participant_obj(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        # Cache kết quả truy vấn đối phương tham gia chat trên chính instance serializer để tránh N+1 query
        if not hasattr(self, '_other_participants'):
            self._other_participants = {}
        
        if obj.id not in self._other_participants:
            participant = obj.participants.exclude(user=request.user).select_related('user').first()
            self._other_participants[obj.id] = participant.user if participant else None
            
        return self._other_participants[obj.id]

    def get_title(self, obj):
        if obj.type == 'direct':
            other_user = self.get_other_participant_obj(obj)
            return other_user.username if other_user else obj.title
        return obj.title

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.type == 'direct':
            other_user = self.get_other_participant_obj(obj)
            if other_user and other_user.avatar:
                return request.build_absolute_uri(other_user.avatar.url) if request else other_user.avatar.url
            return None
        
        if obj.avatar:
            return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url
        return None

    def get_other_participant(self, obj):
        if obj.type == 'direct':
            other_user = self.get_other_participant_obj(obj)
            if other_user:
                return UserChatSerializer(other_user, context=self.context).data
        return None

    def get_last_message(self, obj):
        # Lấy tin nhắn mới nhất chưa bị xóa của cuộc hội thoại
        last_msg = obj.messages.filter(is_deleted=False).order_by('-created_at').first()
        if last_msg:
            return MessageSerializer(last_msg, context=self.context).data
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        
        try:
            participant = obj.participants.get(user=request.user)
            last_read_id = participant.last_read_message_id
            
            messages_query = obj.messages.all()
            if last_read_id is not None:
                messages_query = messages_query.filter(id__gt=last_read_id)
            
            return messages_query.count()
        except ConversationParticipant.DoesNotExist:
            return 0
