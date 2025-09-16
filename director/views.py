from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from academic.models import Section
from institutions.models import GradeLevel, Term, Institution
from accounts.serializers import UserSerializer
from institutions.serializers import InstitutionSerializer
from .serializers import DirectorTermSerializer, DirectorGradeLevelSerializer, DirectorSectionSerializer, DirectorUserSerializer

User = get_user_model()


class DirectorUserViewSet(viewsets.ModelViewSet):
    """
    Vista para que el director gestione usuarios de su institución
    """
    serializer_class = DirectorUserSerializer
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
    serializer_class = DirectorSectionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo secciones de la institución del director
        if self.request.user.role == 'DIRECTOR':
            return Section.objects.filter(
                term__institution=self.request.user.institution,
                grade_level__institution=self.request.user.institution
            )
        return Section.objects.none()
    
    def perform_create(self, serializer):
        # Verificar que el período y grado pertenecen a la institución del director
        term = serializer.validated_data.get('term')
        grade_level = serializer.validated_data.get('grade_level')
        
        if (term.institution != self.request.user.institution or
            grade_level.institution != self.request.user.institution):
            return Response(
                {'error': 'No puedes crear secciones con datos de otras instituciones'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        serializer.save()


class DirectorGradeLevelViewSet(viewsets.ModelViewSet):
    """
    Vista para que el director gestione grados de su institución
    """
    serializer_class = DirectorGradeLevelSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo grados de la institución del director
        if self.request.user.role == 'DIRECTOR':
            return GradeLevel.objects.filter(institution=self.request.user.institution)
        return GradeLevel.objects.none()
    
    def perform_create(self, serializer):
        # Asignar automáticamente la institución del director
        serializer.save(institution=self.request.user.institution)


class DirectorTermViewSet(viewsets.ModelViewSet):
    """
    Vista para que el director gestione períodos académicos de su institución
    """
    serializer_class = DirectorTermSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo períodos de la institución del director
        if self.request.user.role == 'DIRECTOR':
            return Term.objects.filter(institution=self.request.user.institution)
        return Term.objects.none()
    
    def perform_create(self, serializer):
        # Asignar automáticamente la institución del director
        serializer.save(institution=self.request.user.institution)


class DirectorInstitutionView(APIView):
    """
    Vista para que el director vea y actualice la información de su institución
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Obtener información de la institución del director"""
        if request.user.role != 'DIRECTOR':
            return Response(
                {'error': 'Solo los directores pueden acceder a esta información'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not request.user.institution:
            return Response(
                {'error': 'No tienes una institución asignada'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = InstitutionSerializer(request.user.institution)
        return Response(serializer.data)
    
    def patch(self, request):
        """Actualizar información de la institución del director"""
        if request.user.role != 'DIRECTOR':
            return Response(
                {'error': 'Solo los directores pueden actualizar esta información'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not request.user.institution:
            return Response(
                {'error': 'No tienes una institución asignada'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = InstitutionSerializer(
            request.user.institution, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DirectorSectionOptionsView(APIView):
    """
    Vista para obtener opciones para crear secciones (cursos, profesores, períodos)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Obtener opciones para crear secciones"""
        if request.user.role != 'DIRECTOR':
            return Response(
                {'error': 'Solo los directores pueden acceder a esta información'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not request.user.institution:
            return Response(
                {'error': 'No tienes una institución asignada'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Obtener profesores de la institución
        professors = User.objects.filter(
            institution=request.user.institution, 
            role='PROFESOR'
        ).values('id', 'first_name', 'last_name', 'username')
        
        # Obtener períodos de la institución
        terms = Term.objects.filter(institution=request.user.institution).values('id', 'name', 'is_active')
        
        # Obtener grados de la institución
        grade_levels = GradeLevel.objects.filter(institution=request.user.institution).values('id', 'name', 'level')
        
        return Response({
            'professors': list(professors),
            'terms': list(terms),
            'grade_levels': list(grade_levels)
        })
    


class DirectorDebugUserView(APIView):
    """Vista temporal para debuggear assigned_sections"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=400)
        
        try:
            user = CustomUser.objects.get(id=user_id)
            sections = user.sections_taught.all()
            
            return Response({
                'user_id': user.id,
                'username': user.username,
                'role': user.role,
                'sections_count': sections.count(),
                'sections': [{
                    'id': s.id,
                    'name': s.name,
                    'grade_level': s.grade_level.name if s.grade_level else None,
                    'term': s.term.name if s.term else None
                } for s in sections]
            })
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
