from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from academic.models import Section
from accounts.serializers import UserSerializer
from academic.serializers import SectionSerializer

User = get_user_model()


class DirectorUserViewSet(viewsets.ModelViewSet):
    """
    Vista para que el director gestione usuarios de su institución
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo usuarios de la misma institución del director
        if self.request.user.role == 'DIRECTOR':
            return User.objects.filter(institution=self.request.user.institution)
        return User.objects.none()
    
    def perform_create(self, serializer):
        # Asignar automáticamente la institución del director
        serializer.save(institution=self.request.user.institution)


class DirectorSectionViewSet(viewsets.ModelViewSet):
    """
    Vista para que el director gestione secciones de su institución
    """
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo secciones de la institución del director
        if self.request.user.role == 'DIRECTOR':
            return Section.objects.filter(course__institution=self.request.user.institution)
        return Section.objects.none()
    
    def perform_create(self, serializer):
        # Verificar que el curso pertenece a la institución del director
        course = serializer.validated_data.get('course')
        if course.institution != self.request.user.institution:
            return Response(
                {'error': 'No puedes crear secciones para cursos de otras instituciones'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        serializer.save()
