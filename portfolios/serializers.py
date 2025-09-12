from rest_framework import serializers
from .models import Portfolio, Artifact


class ArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artifact
        fields = '__all__'


class PortfolioSerializer(serializers.ModelSerializer):
    artifacts = ArtifactSerializer(many=True, read_only=True)
    
    class Meta:
        model = Portfolio
        fields = '__all__'
