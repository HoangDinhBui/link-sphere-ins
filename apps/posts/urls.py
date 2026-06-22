from django.urls import path
from . import views

urlpatterns = [
    path('', views.posts),
    path('trending-hashtags/', views.trending_hashtags),
    path('<int:post_id>/like/', views.like_post),
    path('<int:post_id>/', views.post_detail),
    path('<int:post_id>/bookmark/', views.toggle_bookmark),
]
