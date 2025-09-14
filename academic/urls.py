from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'courses', views.CourseViewSet)
router.register(r'topics', views.TopicViewSet)
router.register(r'sections', views.SectionViewSet)
router.register(r'enrollments', views.EnrollmentViewSet)
router.register(r'assessments', views.AssessmentViewSet)
router.register(r'grades', views.GradeViewSet)
router.register(r'materials', views.MaterialViewSet)
router.register(r'material-sessions', views.MaterialViewingSessionViewSet)
router.register(r'material-interactions', views.MaterialInteractionViewSet)
router.register(r'material-analytics', views.MaterialAnalyticsViewSet)
router.register(r'material-tracking', views.MaterialTrackingViewSet, basename='material-tracking')

urlpatterns = [
    path('', include(router.urls)),
]