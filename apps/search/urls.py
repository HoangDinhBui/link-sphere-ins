from django.urls import path
from . import views

urlpatterns = [
    path('posts/', views.search_posts),
    path('users/', views.search_users),
]