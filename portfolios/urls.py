from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PortfolioViewSet, ActivityViewSet, ActivityAssignmentViewSet, ArtifactViewSet

router = DefaultRouter()
router.register(r'portfolios', PortfolioViewSet)
router.register(r'activities', ActivityViewSet)
router.register(r'assignments', ActivityAssignmentViewSet)
router.register(r'artifacts', ArtifactViewSet)

urlpatterns = [
    path('', include(router.urls)),
]