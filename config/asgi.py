"""
ASGI config for LinkSphere project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from core.middleware import JWTAuthMiddleware
from apps.notifications.routing import websocket_urlpatterns as notifications_ws_urls
from apps.chat.routing import websocket_urlpatterns as chat_ws_urls

combined_websocket_urlpatterns = notifications_ws_urls + chat_ws_urls

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': JWTAuthMiddleware(
        URLRouter(combined_websocket_urlpatterns)
    ),
})
