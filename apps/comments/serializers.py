from rest_framework import serializers
from .models import Comment
from apps.users.serializers import UserSerializer

class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    post = serializers.PrimaryKeyRelatedField(read_only=True)
    parentId = serializers.PrimaryKeyRelatedField(
        queryset=Comment.objects.all(), source='parent', required=False, allow_null=True
    )
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'author', 'post', 'parentId', 'content', 'created_at', 'reply_count']

    def get_reply_count(self, obj):
        return obj.replies.count()