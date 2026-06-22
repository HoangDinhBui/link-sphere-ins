from django.urls import path
from . import views

urlpatterns = [
    path('<int:post_id>/comments/', views.comments),
    path('<int:post_id>/comments/<int:comment_id>/replies/', views.replies),
]