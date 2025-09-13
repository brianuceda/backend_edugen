from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.DirectorUserViewSet, basename='director-users')
router.register(r'sections', views.DirectorSectionViewSet, basename='director-sections')
router.register(r'grade-levels', views.DirectorGradeLevelViewSet, basename='director-grade-levels')
router.register(r'terms', views.DirectorTermViewSet, basename='director-terms')

urlpatterns = [
    path('sections/options/', views.DirectorSectionOptionsView.as_view(), name='director-section-options'),
    path('institution/', views.DirectorInstitutionView.as_view(), name='director-institution'),
    path('debug-user/', views.DirectorDebugUserView.as_view(), name='director-debug-user'),
    path('', include(router.urls)),
]
