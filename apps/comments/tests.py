from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from apps.users.models import User
from apps.posts.models import Post
from apps.comments.models import Comment

class CommentLazyLoadingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='user1', email='user1@test.com', password='password123')
        self.user2 = User.objects.create_user(username='user2', email='user2@test.com', password='password123')
        
        self.post = Post.objects.create(author=self.user1, content="Test Post")
        
        # Authenticate
        self.client.force_authenticate(user=self.user1)

    @patch('apps.comments.views.create_notification')
    def test_create_and_fetch_nested_comments(self, mock_create_notification):
        # 1. Create a top level comment
        response = self.client.post(f'/api/v1/posts/{self.post.id}/comments/', {'content': 'First comment'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        comment_id = response.data['data']['id']

        # 2. Create a reply
        self.client.force_authenticate(user=self.user2)
        response_reply = self.client.post(f'/api/v1/posts/{self.post.id}/comments/', {
            'content': 'Reply to first comment',
            'parentId': comment_id
        })
        self.assertEqual(response_reply.status_code, status.HTTP_201_CREATED)

        # 3. Fetch top level comments (should be 1, with reply_count = 1)
        response_get = self.client.get(f'/api/v1/posts/{self.post.id}/comments/')
        self.assertEqual(response_get.status_code, status.HTTP_200_OK)
        comments = response_get.data['data']
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]['id'], comment_id)
        self.assertEqual(comments[0]['reply_count'], 1)

        # 4. Fetch replies
        response_replies = self.client.get(f'/api/v1/posts/{self.post.id}/comments/{comment_id}/replies/')
        self.assertEqual(response_replies.status_code, status.HTTP_200_OK)
        replies = response_replies.data['data']
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]['content'], 'Reply to first comment')
