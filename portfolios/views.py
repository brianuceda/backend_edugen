from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Portfolio, Artifact
from .serializers import PortfolioSerializer, ArtifactSerializer


class PortfolioViewSet(viewsets.ModelViewSet):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]


class ArtifactViewSet(viewsets.ModelViewSet):
    queryset = Artifact.objects.all()
    serializer_class = ArtifactSerializer
    permission_classes = [IsAuthenticated]