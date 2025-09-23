from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# Agregar ViewSets cuando estén implementados

urlpatterns = [
    path('', include(router.urls)),
    path('export/', views.export_content_as_scorm, name='export-scorm'),
    path('preview/<int:content_id>/', views.preview_scorm_content, name='preview-scorm'),
]