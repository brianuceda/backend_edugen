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

urlpatterns = [
    path('', include(router.urls)),
]