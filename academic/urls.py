from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# Agregar ViewSets cuando estén implementados
# router.register(r'courses', views.CourseViewSet)
# router.register(r'sections', views.SectionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]