from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register),
    path('profile/', views.profile),
    path('follow/', views.follow),
    path('unfollow/', views.unfollow),
    path('<str:username>/posts/', views.user_posts),
    path('<str:username>/bookmarks/', views.user_bookmarks),
]