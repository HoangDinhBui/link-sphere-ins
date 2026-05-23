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
    token = response.data['access']
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client

@pytest.mark.django_db
class TestRegister:
    def test_register_success(self, client):
        res = client.post('/api/v1/users/register/', {
            'username': 'newuser',
            'email': 'new@gmail.com',
            'password': '123456'
        }, format='json')
        assert res.status_code == 201
        assert res.data['data']['username'] == 'newuser'

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
        assert 'access' in res.data
        assert 'refresh' in res.data

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