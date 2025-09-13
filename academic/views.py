from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from .models import Course, Topic, Section, Enrollment, Assessment, Grade, Material
from .serializers import CourseSerializer, TopicSerializer, SectionSerializer, EnrollmentSerializer, AssessmentSerializer, GradeSerializer, MaterialSerializer


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar cursos de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return Course.objects.filter(institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            # Los profesores solo pueden ver los cursos que ellos crearon
            return Course.objects.filter(professor=self.request.user)
        else:  # ALUMNO
            return Course.objects.filter(sections__enrollment__student=self.request.user)
    
    def perform_create(self, serializer):
        # Asignar la institución y profesor al crear el curso
        if self.request.user.role == 'PROFESOR':
            if not self.request.user.institution:
                raise serializers.ValidationError("El usuario no tiene una institución asignada")
            serializer.save(institution=self.request.user.institution, professor=self.request.user)
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
        
        # Antes de eliminar el curso, remover las relaciones con portafolios
        from portfolios.models import PortfolioCourse
        PortfolioCourse.objects.filter(course=instance).delete()
        
        # Eliminar el curso (las secciones se quedarán sin curso por SET_NULL)
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
            from academic.models import Section
            from institutions.models import GradeLevel
            sections = []
            
            for section_id in section_ids:
                try:
                    section = Section.objects.get(id=section_id)
                    # Verificar que la sección pertenece a la institución del profesor
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
                
                # Actualizar portafolios existentes de estudiantes en esta sección
                from portfolios.models import Portfolio, PortfolioCourse
                portfolios_updated = Portfolio.objects.filter(section=section)
                
                for portfolio in portfolios_updated:
                    # Agregar el curso al portafolio si no existe
                    PortfolioCourse.objects.get_or_create(
                        portfolio=portfolio,
                        course=course
                    )
                
                assigned_sections.append({
                    'id': section.id,
                    'name': section.name,
                    'grade_level': section.grade_level.name if section.grade_level else None,
                    'portfolios_updated': portfolios_updated.count()
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
                {'error': f'Error al asignar curso a las secciones: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='students')
    def get_students_by_course(self, request, pk=None):
        """Obtener estudiantes que tienen este curso en su portafolio"""
        try:
            course = self.get_object()
            
            # Verificar que el profesor tenga acceso a este curso
            if request.user.role == 'PROFESOR' and course.professor != request.user:
                return Response(
                    {'error': 'No tienes acceso a este curso'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Obtener estudiantes que tienen este curso en su portafolio
            from portfolios.models import PortfolioCourse
            portfolio_courses = PortfolioCourse.objects.filter(
                course=course
            ).select_related('portfolio__student', 'portfolio__section')
            
            students_data = []
            for portfolio_course in portfolio_courses:
                student = portfolio_course.portfolio.student
                section = portfolio_course.portfolio.section
                students_data.append({
                    'id': student.id,
                    'username': student.username,
                    'email': student.email,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'section': {
                        'id': section.id if section else None,
                        'name': section.name if section else 'Sin sección'
                    } if section else None,
                    'added_at': portfolio_course.added_at,
                    'portfolio_id': portfolio_course.portfolio.id
                })
            
            return Response({
                'course': {
                    'id': course.id,
                    'name': course.name,
                    'code': course.code
                },
                'students': students_data,
                'total_students': len(students_data)
            })
            
        except Course.DoesNotExist:
            return Response(
                {'error': 'Curso no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': 'Error al obtener estudiantes'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TopicViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar temas de cursos"""
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'PROFESOR':
            # Los profesores solo pueden ver los temas de los cursos que crearon
            return Topic.objects.filter(professor=user).select_related('course')
        elif user.role == 'DIRECTOR':
            # Los directores pueden ver todos los temas de su institución
            return Topic.objects.filter(course__institution=user.institution).select_related('course')
        else:  # ALUMNO
            # Los estudiantes pueden ver los temas de los cursos en los que están inscritos
            return Topic.objects.filter(
                course__sections__enrollment__student=user
            ).select_related('course')
    
    def perform_create(self, serializer):
        # Asignar el profesor actual al crear el tema
        serializer.save(professor=self.request.user)
    
    def perform_update(self, serializer):
        # Verificar que el usuario puede editar este tema
        topic = self.get_object()
        if self.request.user.role == 'PROFESOR':
            if topic.professor != self.request.user:
                raise serializers.ValidationError("No tienes permisos para editar este tema")
        serializer.save()
    
    def perform_destroy(self, instance):
        # Verificar que el usuario puede eliminar este tema
        if self.request.user.role == 'PROFESOR':
            if instance.professor != self.request.user:
                raise serializers.ValidationError("No tienes permisos para eliminar este tema")
        instance.delete()
    
    @action(detail=False, methods=['get'], url_path='by-course/(?P<course_id>[^/.]+)')
    def by_course(self, request, course_id=None):
        """Obtener temas de un curso específico"""
        try:
            course = Course.objects.get(id=course_id)
            topics = self.get_queryset().filter(course=course)
            serializer = self.get_serializer(topics, many=True)
            return Response(serializer.data)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Curso no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar secciones de la institución del usuario
        if self.request.user.role == 'DIRECTOR':
            return Section.objects.filter(term__institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            # Los profesores pueden ver todas las secciones de su institución para asignar cursos
            return Section.objects.filter(term__institution=self.request.user.institution)
        else:  # ALUMNO
            return Section.objects.filter(enrollment__student=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='my-sections')
    def get_my_sections(self, request):
        """Obtener secciones asignadas al profesor actual"""
        if request.user.role == 'PROFESOR':
            sections = Section.objects.filter(professors=request.user)
            serializer = self.get_serializer(sections, many=True)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Solo los profesores pueden acceder a esta información'}, 
                status=status.HTTP_403_FORBIDDEN
            )
    
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


class MaterialViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar materiales educativos"""
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Filtrar materiales según el rol del usuario
        if self.request.user.role == 'DIRECTOR':
            return Material.objects.filter(topic__course__institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return Material.objects.filter(professor=self.request.user)
        else:  # ALUMNO
            # Los estudiantes solo pueden ver materiales asignados a ellos o materiales compartidos
            return Material.objects.filter(
                models.Q(assigned_students=self.request.user) | 
                models.Q(is_shared=True)
            ).distinct()
    
    def perform_create(self, serializer):
        # Asignar el profesor actual al crear el material
        serializer.save(professor=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='by-topic/(?P<topic_id>[^/.]+)')
    def get_materials_by_topic(self, request, topic_id=None):
        """Obtener materiales de un tema específico"""
        try:
            topic = Topic.objects.get(id=topic_id)
            
            # Verificar que el usuario tenga acceso al tema
            if request.user.role == 'PROFESOR' and topic.professor != request.user:
                return Response(
                    {'error': 'No tienes acceso a este tema'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            materials = Material.objects.filter(topic=topic)
            serializer = self.get_serializer(materials, many=True)
            
            return Response({
                'topic': {
                    'id': topic.id,
                    'name': topic.name,
                    'course_name': topic.course.name,
                    'course_code': topic.course.code
                },
                'materials': serializer.data,
                'total_materials': materials.count()
            })
            
        except Topic.DoesNotExist:
            return Response(
                {'error': 'Tema no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': 'Error al obtener materiales'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request, *args, **kwargs):
        """Override create method for error handling"""
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'], url_path='test-create')
    def test_create_material(self, request):
        """Endpoint de prueba para crear materiales sin autenticación"""
        try:
            # Crear un material de prueba
            material = Material.objects.create(
                name=request.data.get('name', 'Test Material'),
                description=request.data.get('description', 'Test Description'),
                material_type=request.data.get('material_type', 'DOCUMENT'),
                topic_id=request.data.get('topic', 1),
                professor_id=1,  # Usuario de prueba
                is_shared=request.data.get('is_shared', True)
            )
            
            return Response({
                'message': 'Material de prueba creado exitosamente',
                'material_id': material.id,
                'material_name': material.name
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
