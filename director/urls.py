from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.DirectorUserViewSet, basename='director-users')
router.register(r'sections', views.DirectorSectionViewSet, basename='director-sections')

urlpatterns = [
    path('', include(router.urls)),
]
