import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.users.models import User, Follow

# Create your tests here.
@pytest.fixture
def client():
    return APIClient()

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@gmail.com',
        password='123456'
    )

@pytest.fixture
def user2(db):
    return User.objects.create_user(
        username='testuser2',
        email='test2@gmail.com',
        password='123456'
    )

@pytest.fixture
def auth_client(client, user):
    response = client.post('/api/v1/auth/login/', {
        'username': 'testuser',
        'password': '123456'
    }, format='json')
    token = response.data['data']['access']
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client

@pytest.mark.django_db
class TestRegister:
    def test_register_success(self, client):
        from unittest.mock import patch
        with patch('apps.users.tasks.send_welcome_email.delay') as mock_delay:
            res = client.post('/api/v1/users/register/', {
                'username': 'newuser',
                'email': 'new@gmail.com',
                'password': '123456'
            }, format='json')
            assert res.status_code == 201
            assert res.data['data']['username'] == 'newuser'
            mock_delay.assert_called_once()

    def test_register_duplicate_username(self, client, user):
        res = client.post('/api/v1/users/register/', {
            'username': 'testuser',
            'email': 'other@gmail.com',
            'password': '123456'
        }, format='json')
        assert res.status_code == 400

    def test_register_missing_fields(self, client):
        res = client.post('/api/v1/users/register/', {
            'username': 'newuser'
        }, format='json')
        assert res.status_code == 400

@pytest.mark.django_db
class TestAuth:
    def test_login_success(self, client, user):
        res = client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': '123456'
        }, format='json')
        assert res.status_code == 200
        assert 'access' in res.data['data']
        assert 'refresh' in res.data['data']

    def test_login_wrong_password(self, client, user):
        res = client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpass'
        }, format='json')
        assert res.status_code == 401

    def test_profile_unauthenticated(self, client):
        res = client.get('/api/v1/users/profile/')
        assert res.status_code == 401

    def test_profile_authenticated(self, auth_client):
        res = auth_client.get('/api/v1/users/profile/')
        assert res.status_code == 200
        assert res.data['data']['username'] == 'testuser'

@pytest.mark.django_db
class TestFollow:
    def test_follow_user(self, auth_client, user2):
        res = auth_client.post('/api/v1/users/follow/', {
            'username': 'testuser2'
        }, format='json')
        assert res.status_code == 200

    def test_follow_self(self, auth_client, user):
        res = auth_client.post('/api/v1/users/follow/', {
            'username': 'testuser'
        }, format='json')
        assert res.status_code == 400

    def test_unfollow_user(self, auth_client, user, user2):
        Follow.objects.create(follower=user, following=user2)
        res = auth_client.post('/api/v1/users/unfollow/', {
            'username': 'testuser2'
        }, format='json')
        assert res.status_code == 200

@pytest.mark.django_db
class TestProfileUpdate:
    def test_update_profile_display_name(self, auth_client):
        res = auth_client.patch('/api/v1/users/profile/', {
            'display_name': 'New Display Name',
            'bio': 'New Bio'
        }, format='json')
        assert res.status_code == 200
        assert res.data['data']['display_name'] == 'New Display Name'
        assert res.data['data']['bio'] == 'New Bio'

@pytest.mark.django_db
class TestUserBookmarks:
    def test_get_user_bookmarks(self, auth_client, user):
        from apps.posts.models import Post, Bookmark
        post = Post.objects.create(author=user, content='Test post')
        Bookmark.objects.create(user=user, post=post)
        
        res = auth_client.get(f'/api/v1/users/{user.username}/bookmarks/')
        assert res.status_code == 200
        assert len(res.data['data']) == 1
        assert res.data['data'][0]['id'] == post.id

    def test_get_other_user_bookmarks_forbidden(self, auth_client, user2):
        res = auth_client.get(f'/api/v1/users/{user2.username}/bookmarks/')
        assert res.status_code == 403

@pytest.mark.django_db
class TestPresenceAPI:
    def test_presence_missing_user_ids(self, auth_client):
        res = auth_client.get('/api/v1/users/presence/')
        assert res.status_code == 400
        assert res.data['errorCode'] == 'MISSING_USER_IDS'

    def test_presence_invalid_user_ids(self, auth_client):
        res = auth_client.get('/api/v1/users/presence/?user_ids=abc,123')
        assert res.status_code == 400
        assert res.data['errorCode'] == 'INVALID_USER_IDS'

    def test_presence_success(self, auth_client, user):
        from unittest.mock import patch
        from django.utils import timezone
        
        now = timezone.now().isoformat()
        
        # Mock cache.get so we don't need real Redis running
        with patch('apps.users.views.cache.get') as mock_get:
            def side_effect(key):
                if key == f"user:online:{user.id}":
                    return now
                return None
            mock_get.side_effect = side_effect
            
            res = auth_client.get(f'/api/v1/users/presence/?user_ids={user.id},999')
            assert res.status_code == 200
            
            data = res.data['data']
            assert user.id in data
            assert data[user.id]['status'] == 'online'
            assert data[user.id]['last_seen'] == now
            assert data[999]['status'] == 'offline'