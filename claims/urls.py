from django.urls import path

from . import views

urlpatterns = [
    path('item/<int:pk>/create/', views.create_claim, name='create_claim'),
    path('mine/', views.my_claims, name='my_claims'),
]
