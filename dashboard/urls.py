from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manage/reports/', views.manage_reports, name='manage_reports'),
    path('manage/claims/', views.manage_claims, name='manage_claims'),
    path('manage/users/', views.manage_users, name='manage_users'),
    path('manage/taxonomy/', views.manage_taxonomy, name='manage_taxonomy'),
]
