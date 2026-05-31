from django.test import TestCase

# Create your tests here.
import pytest
from rest_framework.test import APIClient
from apps.users.models import User
from apps.chat.models import Conversation, ConversationParticipant, Message

@pytest.fixture
def client():
    return APIClient()

@pytest.fixture
def user1(db):
    return User.objects.create_user(
        username='user1',
        email='user1@gmail.com',
        password='password123'
    )

@pytest.fixture
def user2(db):
    return User.objects.create_user(
        username='user2',
        email='user2@gmail.com',
        password='password123'
    )

@pytest.fixture
def user3(db):
    return User.objects.create_user(
        username='user3',
        email='user3@gmail.com',
        password='password123'
    )

@pytest.fixture
def auth_client1(client, user1):
    response = client.post('/api/v1/auth/login/', {
        'username': 'user1',
        'password': 'password123'
    }, format='json')
    token = response.data['data']['access']
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client

@pytest.mark.django_db
class TestChatAPI:
    
    def test_create_direct_conversation_success(self, auth_client1, user1, user2):
        response = auth_client1.post('/api/v1/chat/conversations/', {
            'type': 'direct',
            'recipient_id': user2.id
        }, format='json')
        
        assert response.status_code == 201
        assert response.data['success'] is True
        assert response.data['data']['type'] == 'direct'
        assert response.data['data']['other_participant']['username'] == 'user2'

    def test_create_direct_conversation_with_self(self, auth_client1, user1):
        response = auth_client1.post('/api/v1/chat/conversations/', {
            'type': 'direct',
            'recipient_id': user1.id
        }, format='json')
        
        assert response.status_code == 400
        assert response.data['success'] is False
        assert response.data['errorCode'] == 'CANNOT_CHAT_SELF'

    def test_reuse_existing_direct_conversation(self, auth_client1, user1, user2):
        # Tạo cuộc hội thoại lần đầu
        res1 = auth_client1.post('/api/v1/chat/conversations/', {
            'type': 'direct',
            'recipient_id': user2.id
        }, format='json')
        assert res1.status_code == 201
        conv_id = res1.data['data']['id']
        
        # Thử tạo lại lần hai giữa 2 người này
        res2 = auth_client1.post('/api/v1/chat/conversations/', {
            'type': 'direct',
            'recipient_id': user2.id
        }, format='json')
        assert res2.status_code == 200
        assert res2.data['data']['id'] == conv_id
        assert "Tái sử dụng" in res2.data['message']

    def test_create_group_conversation_success(self, auth_client1, user1, user2, user3):
        response = auth_client1.post('/api/v1/chat/conversations/', {
            'type': 'group',
            'title': 'Nhóm Học Tập',
            'participants': [user2.id, user3.id]
        }, format='json')
        
        assert response.status_code == 201
        assert response.data['success'] is True
        assert response.data['data']['type'] == 'group'
        assert response.data['data']['title'] == 'Nhóm Học Tập'

    def test_get_conversation_list(self, auth_client1, user1, user2):
        # Khởi tạo trước một phòng chat
        Conversation.objects.create(type='direct')
        conv = Conversation.objects.create(type='direct')
        ConversationParticipant.objects.create(conversation=conv, user=user1)
        ConversationParticipant.objects.create(conversation=conv, user=user2)

        response = auth_client1.get('/api/v1/chat/conversations/')
        assert response.status_code == 200
        assert len(response.data['data']) == 1
        assert response.data['data'][0]['id'] == str(conv.id)

    def test_get_messages_cursor_paginated(self, auth_client1, user1, user2):
        # Tạo phòng chat
        conv = Conversation.objects.create(type='direct')
        participant1 = ConversationParticipant.objects.create(conversation=conv, user=user1)
        ConversationParticipant.objects.create(conversation=conv, user=user2)
        
        # Gửi trước một vài tin nhắn mẫu
        msg1 = Message.objects.create(conversation=conv, sender=user1, content="Hello")
        msg2 = Message.objects.create(conversation=conv, sender=user2, content="Hi there")

        response = auth_client1.get(f'/api/v1/chat/conversations/{conv.id}/messages/')
        assert response.status_code == 200
        assert len(response.data['data']) == 2
        # Tin nhắn mới nhất phải xếp đầu tiên (descending order)
        assert response.data['data'][0]['content'] == "Hi there"
        
        # Kiểm tra xem API có tự động đánh dấu đã đọc tin nhắn mới nhất không
        participant1.refresh_from_db()
        assert participant1.last_read_message_id == msg2.id
