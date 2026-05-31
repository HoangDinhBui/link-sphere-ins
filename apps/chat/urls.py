from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import ConversationViewSet, ChatMediaUploadView

router = SimpleRouter()
router.register('conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    path('media/upload/', ChatMediaUploadView.as_view(), name='chat-media-upload'),
    path('', include(router.urls)),
]
