import pytest
from rest_framework.test import APIClient
from apps.users.models import User
from apps.posts.models import Post

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
def auth_client(client, user):
    res = client.post('/api/v1/auth/login/', {
        'username': 'testuser',
        'password': '123456'
    }, format='json')
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {res.data["data"]["access"]}')
    return client

@pytest.mark.django_db
class TestSearch:
    def test_search_posts(self, auth_client, user):
        post1 = Post.objects.create(author=user, content="This is an incredible testing post for PostgreSQL")
        post2 = Post.objects.create(author=user, content="Another post with nothing relevant")
        
        # Cập nhật search_vector thủ công (do signal có thể mock)
        from django.contrib.postgres.search import SearchVector
        Post.objects.filter(pk=post1.pk).update(search_vector=SearchVector('content'))
        Post.objects.filter(pk=post2.pk).update(search_vector=SearchVector('content'))
        
        # Test full text search (sử dụng FTS)
        res = auth_client.get('/api/v1/search/posts/?q=incredible')
        assert res.status_code == 200
        assert res.data['data']['count'] == 1
        assert res.data['data']['results'][0]['content'] == "This is an incredible testing post for PostgreSQL"
