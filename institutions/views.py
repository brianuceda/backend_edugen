from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Institution, Term, GradeLevel
from .serializers import InstitutionSerializer, TermSerializer, GradeLevelSerializer


class InstitutionViewSet(viewsets.ModelViewSet):
    queryset = Institution.objects.all()
    serializer_class = InstitutionSerializer
    permission_classes = [IsAuthenticated]


class TermViewSet(viewsets.ModelViewSet):
    queryset = Term.objects.all()
    serializer_class = TermSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar períodos de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return Term.objects.filter(institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return Term.objects.filter(institution=self.request.user.institution)
        else:  # ALUMNO
            return Term.objects.filter(institution=self.request.user.institution)


class GradeLevelViewSet(viewsets.ModelViewSet):
    queryset = GradeLevel.objects.all()
    serializer_class = GradeLevelSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar grados de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return GradeLevel.objects.filter(institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return GradeLevel.objects.filter(institution=self.request.user.institution)
        else:  # ALUMNO
            return GradeLevel.objects.filter(institution=self.request.user.institution)