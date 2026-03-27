from django.urls import path
from . import views

urlpatterns = [
    path('', views.character_list, name='character_list'),
    path('new/', views.character_create, name='character_create'),
    path('<int:pk>/edit/', views.character_edit, name='character_edit'),
    path('<int:pk>/copy/', views.character_copy, name='character_copy'),
    path('<int:pk>/move/', views.character_move, name='character_move'),
    path('<int:pk>/delete/', views.character_delete, name='character_delete'),
    path('<int:pk>/transfer/', views.character_transfer, name='character_transfer'),
]