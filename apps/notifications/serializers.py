from rest_framework import serializers
from .models import Notification
from apps.users.serializers import UserSerializer

class NotificationSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'sender', 'type', 'message', 'is_read', 'post_id', 'created_at']