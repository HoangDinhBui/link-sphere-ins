from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer
from utils.response import APIResponse

# Create your views here.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications(request):
    notifications = Notification.objects.filter(recipient=request.user).select_related('sender')
    serializer = NotificationSerializer(notifications, many=True)
    # return Response(serializer.data)
    return APIResponse.success(data=serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    # return Response({'message': 'All notifications marked as read'})
    return APIResponse.success(message='All notifications marked as read')