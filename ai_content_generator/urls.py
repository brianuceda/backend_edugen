from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'conversations', views.AIContentGeneratorViewSet, basename='conversations')
router.register(r'templates', views.ContentTemplateViewSet, basename='templates')
router.register(r'generated-content', views.GeneratedContentViewSet, basename='generated-content')

urlpatterns = [
    path('', include(router.urls)),
]