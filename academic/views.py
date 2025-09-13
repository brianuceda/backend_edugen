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
            # Los profesores pueden ver todos los cursos de su institución
            return Course.objects.filter(institution=self.request.user.institution)
        else:  # ALUMNO
            return Course.objects.filter(sections__enrollment__student=self.request.user)
    
    def perform_create(self, serializer):
        # Asignar la institución del usuario al crear el curso
        if self.request.user.role == 'PROFESOR':
            if not self.request.user.institution:
                raise serializers.ValidationError("El usuario no tiene una institución asignada")
            serializer.save(institution=self.request.user.institution)
        else:
            serializer.save()

    def perform_update(self, serializer):
        # Verificar que el usuario puede editar este curso
        course = self.get_object()
        if self.request.user.role == 'PROFESOR':
            if course.institution != self.request.user.institution:
                raise serializers.ValidationError("No tienes permisos para editar este curso")
        serializer.save()

    def perform_destroy(self, instance):
        # Verificar que el usuario puede eliminar este curso
        if self.request.user.role == 'PROFESOR':
            if instance.institution != self.request.user.institution:
                raise serializers.ValidationError("No tienes permisos para eliminar este curso")
        instance.delete()
    
    @action(detail=True, methods=['post'], url_path='assign-to-sections')
    def assign_to_sections(self, request, pk=None):
        """Asignar curso a múltiples secciones"""
        try:
            course = self.get_object()
            section_ids = request.data.get('section_ids', [])
            grade_level_id = request.data.get('grade_level_id')
            
            if not section_ids:
                return Response(
                    {'error': 'section_ids es requerido'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verificar que las secciones existen y pertenecen a la institución del profesor
            from academic.models import Section, GradeLevel
            sections = []
            for section_id in section_ids:
                try:
                    section = Section.objects.get(id=section_id)
                    # Verificar que la sección pertenece a la institución del profesor
                    # Las secciones están asociadas a la institución a través del term
                    if section.term.institution != request.user.institution:
                        return Response(
                            {'error': f'No tienes acceso a la sección {section.name}'}, 
                            status=status.HTTP_403_FORBIDDEN
                        )
                    sections.append(section)
                except Section.DoesNotExist:
                    return Response(
                        {'error': f'Sección {section_id} no encontrada'}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Asignar el curso a todas las secciones
            assigned_sections = []
            for section in sections:
                section.course = course
                section.save()
                
                # Si se proporciona grade_level, asignarlo también
                if grade_level_id:
                    try:
                        grade_level = GradeLevel.objects.get(id=grade_level_id)
                        section.grade_level = grade_level
                        section.save()
                    except GradeLevel.DoesNotExist:
                        return Response(
                            {'error': 'Grado no encontrado'}, 
                            status=status.HTTP_404_NOT_FOUND
                        )
                
                assigned_sections.append({
                    'id': section.id,
                    'name': section.name,
                    'grade_level': section.grade_level.name if section.grade_level else None
                })
            
            return Response({
                'message': f'Curso asignado exitosamente a {len(assigned_sections)} secciones',
                'course': {
                    'id': course.id,
                    'name': course.name,
                    'code': course.code
                },
                'sections': assigned_sections
            })
            
        except Exception as e:
            return Response(
                {'error': 'Error al asignar curso a las secciones'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
