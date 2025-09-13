from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Course, Section, Enrollment, Assessment, Grade
from .serializers import CourseSerializer, SectionSerializer, EnrollmentSerializer, AssessmentSerializer, GradeSerializer


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar cursos de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return Course.objects.filter(institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return Course.objects.filter(sections__professors=self.request.user)
        else:  # ALUMNO
            return Course.objects.filter(sections__enrollment__student=self.request.user)


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar secciones de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return Section.objects.filter(course__institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return Section.objects.filter(professors=self.request.user)
        else:  # ALUMNO
            return Section.objects.filter(enrollment__student=self.request.user)
    
    @action(detail=True, methods=['get'], url_path='students')
    def get_students(self, request, pk=None):
        """Obtener estudiantes de una sección específica"""
        try:
            section = self.get_object()
            
            # Verificar que el profesor tenga acceso a esta sección
            if request.user.role == 'PROFESOR' and not section.professors.filter(id=request.user.id).exists():
                return Response(
                    {'error': 'No tienes acceso a esta sección'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Obtener estudiantes activos de la sección
            enrollments = Enrollment.objects.filter(
                section=section, 
                is_active=True
            ).select_related('student')
            
            students_data = []
            for enrollment in enrollments:
                student = enrollment.student
                students_data.append({
                    'id': student.id,
                    'username': student.username,
                    'email': student.email,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'enrolled_at': enrollment.enrolled_at,
                    'is_active': enrollment.is_active
                })
            
            return Response({
                'section': {
                    'id': section.id,
                    'name': section.name,
                    'course_name': section.course.name if section.course else None,
                    'grade_level_name': section.grade_level.name if section.grade_level else None,
                    'term_name': section.term.name if section.term else None,
                },
                'students': students_data,
                'total_students': len(students_data)
            })
            
        except Section.DoesNotExist:
            return Response(
                {'error': 'Sección no encontrada'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': 'Error al obtener estudiantes'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar matrículas de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return Enrollment.objects.filter(section__course__institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return Enrollment.objects.filter(section__professors=self.request.user)
        else:  # ALUMNO
            return Enrollment.objects.filter(student=self.request.user)



class AssessmentViewSet(viewsets.ModelViewSet):
    queryset = Assessment.objects.all()
    serializer_class = AssessmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar evaluaciones de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return Assessment.objects.filter(section__course__institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return Assessment.objects.filter(section__professors=self.request.user)
        else:  # ALUMNO
            return Assessment.objects.filter(section__enrollment__student=self.request.user)


class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar calificaciones de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return Grade.objects.filter(assessment__section__course__institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return Grade.objects.filter(assessment__section__professors=self.request.user)
        else:  # ALUMNO
            return Grade.objects.filter(student=self.request.user)
