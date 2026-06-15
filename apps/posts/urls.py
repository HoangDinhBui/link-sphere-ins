from django.urls import path
from . import views

urlpatterns = [
    path('', views.posts),
    path('<int:post_id>/like/', views.like_post),
    path('<int:post_id>/', views.delete_post),
    path('<int:post_id>/bookmark/', views.toggle_bookmark),
]