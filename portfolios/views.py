from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Portfolio, Activity, ActivityAssignment, Artifact
from .serializers import (
    PortfolioSerializer, ActivitySerializer, ActivityCreateSerializer,
    ActivityAssignmentSerializer, ActivityAssignmentCreateSerializer,
    PortfolioDetailSerializer, ArtifactSerializer
)
from academic.models import Course, Section


class PortfolioViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar portafolios"""
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'PROFESOR':
            # Los profesores pueden ver portafolios de secciones donde tienen cursos asignados
            return Portfolio.objects.filter(
                courses__course__professor=user  # Solo portafolios con cursos creados por este profesor
            ).select_related('student', 'section').prefetch_related('courses__course')
        elif user.role == 'ALUMNO':
            # Los estudiantes solo ven sus propios portafolios
            return Portfolio.objects.filter(
                student=user
            ).select_related('student', 'section').prefetch_related('courses__course')
        else:
            # Directores pueden ver todos los portafolios de su institución
            return Portfolio.objects.filter(
                student__institution=user.institution
            ).select_related('student', 'section').prefetch_related('courses__course')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PortfolioDetailSerializer
        return PortfolioSerializer

    @action(detail=False, methods=['get'], url_path='by-course')
    def by_course(self, request):
        """Obtener portafolios por curso"""
        course_id = request.query_params.get('course_id')
        if not course_id:
            return Response(
                {'error': 'course_id es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            course = Course.objects.get(id=course_id)
            portfolios = self.get_queryset().filter(course=course)
            serializer = self.get_serializer(portfolios, many=True)
            return Response(serializer.data)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Curso no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='by-section')
    def by_section(self, request):
        """Obtener portafolios por sección"""
        section_id = request.query_params.get('section_id')
        if not section_id:
            return Response(
                {'error': 'section_id es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            section = Section.objects.get(id=section_id)
            portfolios = self.get_queryset().filter(section=section)
            serializer = self.get_serializer(portfolios, many=True)
            return Response(serializer.data)
        except Section.DoesNotExist:
            return Response(
                {'error': 'Sección no encontrada'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class ActivityViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar actividades"""
    queryset = Activity.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'PROFESOR':
            # Los profesores pueden ver sus propias actividades
            return Activity.objects.filter(
                professor=user
            ).select_related('professor', 'course', 'section')
        elif user.role == 'ALUMNO':
            # Los estudiantes ven actividades asignadas a sus secciones
            return Activity.objects.filter(
                section__enrollment__student=user
            ).select_related('professor', 'course', 'section')
        else:
            # Directores pueden ver todas las actividades de su institución
            return Activity.objects.filter(
                professor__institution=user.institution
            ).select_related('professor', 'course', 'section')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ActivityCreateSerializer
        return ActivitySerializer

    def perform_create(self, serializer):
        serializer.save(professor=self.request.user)

    @action(detail=True, methods=['post'], url_path='assign-to-students')
    def assign_to_students(self, request, pk=None):
        """Asignar actividad a estudiantes específicos"""
        activity = self.get_object()
        serializer = ActivityAssignmentCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            student_ids = serializer.validated_data['student_ids']
            
            # Verificar que los estudiantes pertenecen a la sección de la actividad
            valid_students = activity.section.enrollment_set.filter(
                student_id__in=student_ids
            ).values_list('student_id', flat=True)
            
            if len(valid_students) != len(student_ids):
                return Response(
                    {'error': 'Algunos estudiantes no pertenecen a esta sección'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Crear asignaciones
            assignments = []
            for student_id in valid_students:
                from accounts.models import CustomUser
                student = CustomUser.objects.get(id=student_id)
                
                # Crear o obtener portafolio
                portfolio, created = Portfolio.objects.get_or_create(
                    student=student,
                    course=activity.course,
                    section=activity.section,
                    defaults={
                        'title': f"Portafolio de {student.first_name} {student.last_name} - {activity.course.name}",
                        'description': f"Portafolio personal para el curso {activity.course.name}"
                    }
                )
                
                assignment, created = ActivityAssignment.objects.get_or_create(
                    activity=activity,
                    student=student,
                    defaults={'portfolio': portfolio}
                )
                assignments.append(assignment)
            
            response_serializer = ActivityAssignmentSerializer(assignments, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='assign-to-all-students')
    def assign_to_all_students(self, request, pk=None):
        """Asignar actividad a todos los estudiantes de la sección"""
        activity = self.get_object()
        
        # Obtener todos los estudiantes de la sección
        student_ids = activity.section.enrollment_set.values_list('student_id', flat=True)
        
        if not student_ids:
            return Response(
                {'error': 'No hay estudiantes en esta sección'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear asignaciones
        assignments = []
        for student_id in student_ids:
            from accounts.models import CustomUser
            student = CustomUser.objects.get(id=student_id)
            
            # Crear o obtener portafolio
            portfolio, created = Portfolio.objects.get_or_create(
                student=student,
                course=activity.course,
                section=activity.section,
                defaults={
                    'title': f"Portafolio de {student.first_name} {student.last_name} - {activity.course.name}",
                    'description': f"Portafolio personal para el curso {activity.course.name}"
                }
            )
            
            assignment, created = ActivityAssignment.objects.get_or_create(
                activity=activity,
                student=student,
                defaults={'portfolio': portfolio}
            )
            assignments.append(assignment)
        
        response_serializer = ActivityAssignmentSerializer(assignments, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='by-course')
    def by_course(self, request):
        """Obtener actividades por curso"""
        course_id = request.query_params.get('course_id')
        if not course_id:
            return Response(
                {'error': 'course_id es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            course = Course.objects.get(id=course_id)
            activities = self.get_queryset().filter(course=course)
            serializer = self.get_serializer(activities, many=True)
            return Response(serializer.data)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Curso no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='by-section')
    def by_section(self, request):
        """Obtener actividades por sección"""
        section_id = request.query_params.get('section_id')
        if not section_id:
            return Response(
                {'error': 'section_id es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            section = Section.objects.get(id=section_id)
            activities = self.get_queryset().filter(section=section)
            serializer = self.get_serializer(activities, many=True)
            return Response(serializer.data)
        except Section.DoesNotExist:
            return Response(
                {'error': 'Sección no encontrada'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class ActivityAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar asignaciones de actividades"""
    queryset = ActivityAssignment.objects.all()
    serializer_class = ActivityAssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'PROFESOR':
            # Los profesores pueden ver asignaciones de sus actividades
            return ActivityAssignment.objects.filter(
                activity__professor=user
            ).select_related('activity', 'student', 'portfolio')
        elif user.role == 'ALUMNO':
            # Los estudiantes ven sus propias asignaciones
            return ActivityAssignment.objects.filter(
                student=user
            ).select_related('activity', 'student', 'portfolio')
        else:
            # Directores pueden ver todas las asignaciones de su institución
            return ActivityAssignment.objects.filter(
                student__institution=user.institution
            ).select_related('activity', 'student', 'portfolio')

    @action(detail=True, methods=['post'], url_path='submit')
    def submit_assignment(self, request, pk=None):
        """El estudiante entrega su actividad"""
        assignment = self.get_object()
        
        if request.user.role != 'ALUMNO' or assignment.student != request.user:
            return Response(
                {'error': 'No tienes permisos para realizar esta acción'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        assignment.is_completed = True
        assignment.submission_notes = request.data.get('submission_notes', '')
        assignment.save()
        
        serializer = self.get_serializer(assignment)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='grade')
    def grade_assignment(self, request, pk=None):
        """El profesor califica la actividad"""
        assignment = self.get_object()
        
        if request.user.role != 'PROFESOR' or assignment.activity.professor != request.user:
            return Response(
                {'error': 'No tienes permisos para realizar esta acción'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        grade = request.data.get('grade')
        feedback = request.data.get('feedback', '')
        
        if grade is not None:
            assignment.grade = grade
        if feedback:
            assignment.feedback = feedback
        
        assignment.save()
        
        serializer = self.get_serializer(assignment)
        return Response(serializer.data)


class ArtifactViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar artefactos"""
    queryset = Artifact.objects.all()
    serializer_class = ArtifactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'ALUMNO':
            # Los estudiantes solo ven sus propios artefactos
            return Artifact.objects.filter(
                assignment__student=user
            ).select_related('assignment', 'assignment__activity')
        else:
            # Profesores y directores pueden ver artefactos de sus estudiantes
            return Artifact.objects.filter(
                assignment__activity__professor__institution=user.institution
            ).select_related('assignment', 'assignment__activity')

    def perform_create(self, serializer):
        # Verificar que el estudiante puede subir artefactos para esta asignación
        assignment = serializer.validated_data['assignment']
        if self.request.user.role == 'ALUMNO' and assignment.student != self.request.user:
            raise serializers.ValidationError("No puedes subir artefactos para esta asignación")
        
        serializer.save()