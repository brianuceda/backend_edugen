from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'institutions', views.InstitutionViewSet)
router.register(r'terms', views.TermViewSet)
router.register(r'grade-levels', views.GradeLevelViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
