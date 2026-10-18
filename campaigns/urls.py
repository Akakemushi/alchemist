from django.urls import path
from . import views

urlpatterns = [
    path('', views.campaign_list, name='campaign_list'),
    path('new/', views.campaign_create, name='campaign_create'),
    path('search/', views.campaign_search, name='campaign_search'),
    path('<slug:slug>/join/', views.campaign_join, name='campaign_join'),
    path('<slug:slug>/manage/', views.campaign_manage, name='campaign_manage'),
    path('<slug:slug>/enter/', views.campaign_enter, name='campaign_enter'),
    path('<slug:slug>/play/<int:character_id>/', views.campaign_play, name='campaign_play'),
    path('<slug:slug>/play/<int:character_id>/expedition/<int:expedition_id>/', views.expedition_detail, name='expedition_detail'),
    path('<slug:slug>/gm/', views.campaign_gm, name='campaign_gm'),
    path('<slug:slug>/gm/expedition/<int:expedition_id>/', views.gm_expedition_detail, name='gm_expedition_detail'),
]
