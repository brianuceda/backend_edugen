from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'portfolios', views.PortfolioViewSet)
router.register(r'artifacts', views.ArtifactViewSet)

urlpatterns = [
    path('', include(router.urls)),
]