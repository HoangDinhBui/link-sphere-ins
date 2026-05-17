from django.urls import path
from . import views

urlpatterns = [
    path('', views.posts),
    path('<int:pk>/like/', views.like_post),
]