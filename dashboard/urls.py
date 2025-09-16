from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# Agregar ViewSets cuando estén implementados

urlpatterns = [
    path('', include(router.urls)),
    path('', views.dashboard_data, name='dashboard-data'),
]