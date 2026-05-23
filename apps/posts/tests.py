import pytest
from rest_framework.test import APIClient
from apps.users.models import User
from apps.posts.models import Post, Like

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
    res = client.post('/api/v1/auth/login/', {
        'username': 'testuser',
        'password': '123456'
    }, format='json')
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {res.data["data"]["access"]}')
    return client

@pytest.fixture
def post(db, user):
    return Post.objects.create(author=user, content='Test post')


@pytest.mark.django_db
class TestPosts:
    def test_create_post(self, auth_client):
        res = auth_client.post('/api/v1/posts/', {
            'content': 'Hello world!'
        }, format='json')
        assert res.status_code == 201
        assert res.data['data']['content'] == 'Hello world!'

    def test_create_post_unauthenticated(self, client):
        res = client.post('/api/v1/posts/', {
            'content': 'Hello!'
        }, format='json')
        assert res.status_code == 401

    def test_list_posts(self, auth_client, post):
        res = auth_client.get('/api/v1/posts/')
        assert res.status_code == 200
        assert len(res.data['data']) >= 1

    def test_like_post(self, auth_client, post):
        res = auth_client.post(f'/api/v1/posts/{post.id}/like/')
        assert res.status_code == 201
        assert res.data['message'] == 'Post liked'

    def test_unlike_post(self, auth_client, user, post):
        Like.objects.create(user=user, post=post)
        res = auth_client.post(f'/api/v1/posts/{post.id}/like/')
        assert res.status_code == 200
        assert res.data['message'] == 'Post unliked'

    def test_like_nonexistent_post(self, auth_client):
        res = auth_client.post('/api/v1/posts/9999/like/')
        assert res.status_code == 404


@pytest.mark.django_db
class TestComments:
    def test_create_comment(self, auth_client, post):
        res = auth_client.post(f'/api/v1/posts/{post.id}/comments/', {
            'content': 'Nice post!'
        }, format='json')
        assert res.status_code == 201
        assert res.data['data']['content'] == 'Nice post!'

    def test_list_comments(self, auth_client, post):
        res = auth_client.get(f'/api/v1/posts/{post.id}/comments/')
        assert res.status_code == 200

    def test_comment_nonexistent_post(self, auth_client):
        res = auth_client.post('/api/v1/posts/9999/comments/', {
            'content': 'Nice!'
        }, format='json')
        assert res.status_code == 404
