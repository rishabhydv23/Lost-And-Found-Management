from django.urls import path

from . import views

urlpatterns = [
    path('browse/', views.browse, name='browse'),
    path('lost/new/', views.report_item, {'report_type': 'lost'}, name='report_lost'),
    path('found/new/', views.report_item, {'report_type': 'found'}, name='report_found'),
    path('<int:pk>/', views.item_detail, name='item_detail'),
    path('<int:pk>/found/', views.report_found_for_lost_item, name='report_found_for_item'),
    path('<int:pk>/edit/', views.edit_report, name='edit_report'),
    path('mine/', views.my_reports, name='my_reports'),
    path('matches/', views.matches, name='potential_matches'),
]
