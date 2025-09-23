from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, ai_views

router = DefaultRouter()
router.register(r'conversations', views.AIContentGeneratorViewSet, basename='conversations')
router.register(r'templates', views.ContentTemplateViewSet, basename='templates')
router.register(r'generated-content', views.GeneratedContentViewSet, basename='generated-content')

urlpatterns = [
    path('', include(router.urls)),
    # Nuevas rutas para el editor Gamma
    path('gamma/generate-blocks/', ai_views.generate_gamma_blocks, name='generate-gamma-blocks'),
    path('gamma/improve-block/', ai_views.improve_gamma_block, name='improve-gamma-block'),
    path('gamma/generate-image/', ai_views.generate_educational_image, name='generate-educational-image'),
    path('gamma/generate-quiz/', ai_views.generate_quiz_questions, name='generate-quiz-questions'),
    path('gamma/translate-blocks/', ai_views.translate_gamma_blocks, name='translate-gamma-blocks'),
    path('gamma/confirm-and-generate/', ai_views.confirm_and_generate_content, name='confirm-and-generate-content'),
]