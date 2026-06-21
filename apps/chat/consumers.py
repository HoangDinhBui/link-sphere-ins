import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache
from django.utils import timezone
from apps.chat.models import Conversation, ConversationParticipant, Message
from apps.users.models import User

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close(code=4001)
            return

        # Mỗi user khi kết nối sẽ tham gia vào nhóm cá nhân (user_specific group)
        # Việc này giúp họ nhận tin nhắn thời gian thực từ bất kỳ cuộc hội thoại nào họ tham gia
        self.user_group = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        
        # Đánh dấu user đang online trên Redis (TTL: 60s)
        await cache.aset(f"user:online:{self.user.id}", timezone.now().isoformat(), timeout=60)
        
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
        if hasattr(self, 'user') and not self.user.is_anonymous:
            # Gỡ trạng thái online ngay khi ngắt kết nối
            await cache.adelete(f"user:online:{self.user.id}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            conversation_id = data.get('conversation_id')

            if not conversation_id:
                await self.send(text_data=json.dumps({'error': 'conversation_id is required'}))
                return

            # Kiểm tra quyền truy cập cuộc hội thoại
            is_member = await self.is_conversation_member(conversation_id)
            if not is_member:
                await self.send(text_data=json.dumps({'error': 'You are not a participant of this conversation'}))
                return

            handlers = {
                'send_message': self.handle_send_message,
                'typing': self.handle_typing,
                'read_messages': self.handle_read_messages,
                'ping': self.handle_ping,
                'webrtc_offer': self.handle_webrtc_signaling,
                'webrtc_answer': self.handle_webrtc_signaling,
                'webrtc_ice_candidate': self.handle_webrtc_signaling,
                'webrtc_reject': self.handle_webrtc_signaling,
                'webrtc_end': self.handle_webrtc_signaling,
            }

            handler = handlers.get(action)
            if handler:
                await handler(data)
            else:
                await self.send(text_data=json.dumps({'error': 'Invalid action'}))
        except Exception as e:
            await self.send(text_data=json.dumps({'error': str(e)}))

    async def handle_send_message(self, data):
        conversation_id = data.get('conversation_id')
        content = data.get('content', '')
        message_type = data.get('message_type', 'text')
        file_url = data.get('file_url')

        # Lưu tin nhắn vào cơ sở dữ liệu bất đồng bộ
        msg = await self.save_message(conversation_id, self.user, content, message_type, file_url)
        participants = await self.get_conversation_participants(conversation_id)

        payload = {
            'type': 'chat_message',
            'event': 'message_received',
            'data': {
                'id': msg.id,
                'conversation_id': conversation_id,
                'sender': {
                    'id': self.user.id,
                    'username': self.user.username,
                    'avatar': self.user.avatar.url if self.user.avatar else None
                },
                'content': msg.content,
                'message_type': msg.message_type,
                'file_url': msg.file_url,
                'created_at': msg.created_at.isoformat()
            }
        }

        # Phát tin nhắn tới tất cả thành viên trong nhóm đang online
        for user_id in participants:
            await self.channel_layer.group_send(f"user_{user_id}", payload)

    async def chat_message(self, event):
        # Trả payload sự kiện về cho client qua kết nối WebSocket
        await self.send(text_data=json.dumps({
            'event': event['event'],
            'data': event['data']
        }))

    async def handle_typing(self, data):
        conversation_id = data.get('conversation_id')
        is_typing = data.get('is_typing', False)
        participants = await self.get_conversation_participants(conversation_id)

        payload = {
            'type': 'chat_message',
            'event': 'typing',
            'data': {
                'conversation_id': conversation_id,
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing
            }
        }

        # Phát trạng thái typing cho tất cả người dùng khác trong cuộc hội thoại
        for user_id in participants:
            if user_id != self.user.id:
                await self.channel_layer.group_send(f"user_{user_id}", payload)

    async def handle_read_messages(self, data):
        conversation_id = data.get('conversation_id')
        message_id = data.get('message_id')

        if not message_id:
            return

        # cập nhật mốc tin nhắn đã đọc cuối cùng của user hiện tại
        await self.update_last_read(conversation_id, self.user, message_id)
        participants = await self.get_conversation_participants(conversation_id)

        payload = {
            'type': 'chat_message',
            'event': 'messages_read',
            'data': {
                'conversation_id': conversation_id,
                'user_id': self.user.id,
                'message_id': message_id
            }
        }

        for user_id in participants:
            await self.channel_layer.group_send(f"user_{user_id}", payload)

    async def handle_ping(self, data):
        # Gia hạn trạng thái online thêm 60 giây
        await cache.aset(f"user:online:{self.user.id}", timezone.now().isoformat(), timeout=60)
        await self.send(text_data=json.dumps({
            'event': 'pong',
            'data': {'status': 'ok'}
        }))

    async def handle_webrtc_signaling(self, data):
        conversation_id = data.get('conversation_id')
        target_user_id = data.get('target_user_id') # Tùy chọn: Gửi đích danh cho 1 user (như người gọi)
        participants = await self.get_conversation_participants(conversation_id)

        payload = {
            'type': 'chat_message',
            'event': data.get('action'),
            'data': {
                'conversation_id': conversation_id,
                'sender_id': self.user.id,
                'payload': data.get('payload') # Chứa SDP hoặc ICE Candidate
            }
        }

        # Phát tín hiệu tới người khác trong phòng (hoặc người được chỉ định)
        for user_id in participants:
            if user_id != self.user.id:
                if target_user_id and user_id != target_user_id:
                    continue
                await self.channel_layer.group_send(f"user_{user_id}", payload)

    @database_sync_to_async
    def is_conversation_member(self, conversation_id):
        return ConversationParticipant.objects.filter(conversation_id=conversation_id, user=self.user).exists()

    @database_sync_to_async
    def get_conversation_participants(self, conversation_id):
        return list(ConversationParticipant.objects.filter(conversation_id=conversation_id).values_list('user_id', flat=True))

    @database_sync_to_async
    def save_message(self, conversation_id, sender, content, message_type, file_url):
        conv = Conversation.objects.get(id=conversation_id)
        msg = Message.objects.create(
            conversation=conv,
            sender=sender,
            content=content,
            message_type=message_type,
            file_url=file_url
        )
        # Cập nhật trường updated_at của Conversation để đưa phòng lên đầu danh sách chat
        conv.save()
        return msg

    @database_sync_to_async
    def update_last_read(self, conversation_id, user, message_id):
        ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            user=user
        ).update(last_read_message_id=message_id)