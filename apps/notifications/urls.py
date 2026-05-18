from django.urls import path
from . import views

urlpatterns = [
    path('', views.notifications),
    path('read/', views.mark_all_read),
]