import pytest
from apps.users.models import User
from apps.posts.models import Post
from apps.notifications.models import Notification
from apps.notifications.utils import create_notification

@pytest.fixture
def user1(db):
    return User.objects.create_user(username='user1', password='password123')

@pytest.fixture
def user2(db):
    return User.objects.create_user(username='user2', password='password123')

@pytest.fixture
def post(db, user1):
    return Post.objects.create(author=user1, content='Test Post')

@pytest.mark.django_db
class TestNotifications:
    def test_create_notification_with_post_id(self, user1, user2, post):
        create_notification(
            recipient=user1,
            sender=user2,
            notif_type='like',
            message='User2 liked your post',
            post=post
        )
        
        notif = Notification.objects.get(recipient=user1)
        assert notif.post_id == post.id
        assert notif.type == 'like'
