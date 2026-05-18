import pytest
from rest_framework.test import APIClient
from apps.users.models import User, Follow
from apps.posts.models import Post

# Create your tests here.
@pytest.fixture
def client():
    return APIClient()

@pytest.fixture
def user(db):
    return User.objects.create_user(username='user1', email='u1@gmail.com', password='123456')

@pytest.fixture
def user2(db):
    return User.objects.create_user(username='user2', email='u2@gmail.com', password='123456')

@pytest.fixture
def auth_client(client, user):
    res = client.post('/api/v1/auth/login/', {
        'username': 'user1', 'password': '123456'
    }, format='json')
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {res.data["access"]}')
    return client


@pytest.mark.django_db
class TestFeed:
    def test_feed_empty(self, auth_client):
        res = auth_client.get('/api/v1/feed/')
        assert res.status_code == 200

    def test_feed_shows_followed_posts(self, auth_client, user, user2):
        Follow.objects.create(follower=user, following=user2)
        Post.objects.create(author=user2, content='Post from user2')
        res = auth_client.get('/api/v1/feed/')
        assert res.status_code == 200
        assert res.data['count'] == 1

    def test_explore(self, auth_client, user2):
        Post.objects.create(author=user2, content='Explore post')
        res = auth_client.get('/api/v1/feed/explore/')
        assert res.status_code == 200
        assert res.data['count'] >= 1