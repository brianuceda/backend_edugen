from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet
from django.db import models
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum, Max
from .models import (
    Course, Topic, Section, Enrollment, Assessment, Grade, Material,
    MaterialViewingSession, MaterialInteraction, MaterialAnalytics
)
from .serializers import (
    CourseSerializer, TopicSerializer, SectionSerializer, EnrollmentSerializer, 
    AssessmentSerializer, GradeSerializer, MaterialSerializer,
    MaterialViewingSessionSerializer, MaterialInteractionSerializer, 
    MaterialAnalyticsSerializer, MaterialWithAnalyticsSerializer, MaterialTrackingSerializer
)


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
        queryset = Material.objects.all()
        
        # Filtrar por tema si se especifica
        topic_id = self.request.query_params.get('topic')
        if topic_id:
            queryset = queryset.filter(topic_id=topic_id)
        
        # Filtrar materiales según el rol del usuario
        if self.request.user.role == 'DIRECTOR':
            return queryset.filter(topic__course__institution=self.request.user.institution)
        elif self.request.user.role == 'PROFESOR':
            return queryset.filter(professor=self.request.user)
        else:  # ALUMNO
            # Los estudiantes solo pueden ver materiales asignados a ellos o materiales compartidos
            return queryset.filter(
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



class MaterialViewingSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para ver sesiones de visualización de materiales"""
    serializer_class = MaterialViewingSessionSerializer
    permission_classes = [IsAuthenticated]
    queryset = MaterialViewingSession.objects.all()
    
    def get_queryset(self):
        if self.request.user.role == 'PROFESOR':
            # Los profesores pueden ver las sesiones de sus materiales
            return MaterialViewingSession.objects.filter(
                material__professor=self.request.user
            ).select_related('student', 'material')
        elif self.request.user.role == 'ALUMNO':
            # Los estudiantes solo pueden ver sus propias sesiones
            return MaterialViewingSession.objects.filter(
                student=self.request.user
            ).select_related('student', 'material')
        else:
            return MaterialViewingSession.objects.none()


class MaterialInteractionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para ver interacciones con materiales"""
    serializer_class = MaterialInteractionSerializer
    permission_classes = [IsAuthenticated]
    queryset = MaterialInteraction.objects.all()
    
    def get_queryset(self):
        if self.request.user.role == 'PROFESOR':
            # Los profesores pueden ver las interacciones de sus materiales
            return MaterialInteraction.objects.filter(
                session__material__professor=self.request.user
            ).select_related('session__student', 'session__material')
        elif self.request.user.role == 'ALUMNO':
            # Los estudiantes solo pueden ver sus propias interacciones
            return MaterialInteraction.objects.filter(
                session__student=self.request.user
            ).select_related('session__student', 'session__material')
        else:
            return MaterialInteraction.objects.none()


class MaterialAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para ver analytics de materiales"""
    serializer_class = MaterialAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    queryset = MaterialAnalytics.objects.all()
    
    def get_queryset(self):
        if self.request.user.role == 'PROFESOR':
            # Los profesores pueden ver analytics de sus materiales
            return MaterialAnalytics.objects.filter(
                material__professor=self.request.user
            ).select_related('material')
        else:
            return MaterialAnalytics.objects.none()
    
    @action(detail=False, methods=['get'], url_path='by-course/(?P<course_id>[^/.]+)')
    def by_course(self, request, course_id=None):
        """Obtener analytics de materiales por curso"""
        if request.user.role != 'PROFESOR':
            return Response({'error': 'Solo los profesores pueden acceder'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            course = Course.objects.get(id=course_id, professor=request.user)
        except Course.DoesNotExist:
            return Response({'error': 'Curso no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        # Obtener materiales del curso
        materials = Material.objects.filter(
            topic__course=course,
            professor=request.user
        ).select_related('topic')
        
        # Obtener analytics para cada material
        analytics_data = []
        for material in materials:
            analytics, created = MaterialAnalytics.objects.get_or_create(material=material)
            analytics.update_analytics()  # Actualizar métricas
            
            analytics_data.append({
                'material_id': material.id,
                'material_name': material.name,
                'material_type': material.material_type,
                'topic_name': material.topic.name,
                'total_views': analytics.total_views,
                'unique_viewers': analytics.unique_viewers,
                'total_duration': analytics.total_duration,
                'average_duration': analytics.average_duration,
                'completion_rate': analytics.completion_rate,
                'last_updated': analytics.last_updated
            })
        
        return Response(analytics_data)
    
    @action(detail=False, methods=['get'], url_path='material/(?P<material_id>[^/.]+)/detailed')
    def material_detailed(self, request, material_id=None):
        """Obtener analytics detallados de un material específico"""
        if request.user.role != 'PROFESOR':
            return Response({'error': 'Solo los profesores pueden acceder'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            material = Material.objects.get(id=material_id, professor=request.user)
        except Material.DoesNotExist:
            return Response({'error': 'Material no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        # Obtener rango de tiempo
        time_range = request.query_params.get('time_range', '30d')
        days_back = {
            '7d': 7,
            '30d': 30,
            '90d': 90,
            'all': 365
        }.get(time_range, 30)
        
        start_date = timezone.now() - timezone.timedelta(days=days_back)
        
        # Obtener analytics del material
        analytics, created = MaterialAnalytics.objects.get_or_create(material=material)
        analytics.update_analytics()
        
        # Obtener estadísticas diarias
        daily_stats = self._get_daily_stats(material, start_date)
        
        # Obtener estadísticas semanales
        weekly_stats = self._get_weekly_stats(material, start_date)
        
        # Obtener detalles por estudiante
        student_details = self._get_student_details(material, start_date)
        
        response_data = {
            'material_id': material.id,
            'material_name': material.name,
            'material_type': material.material_type,
            'total_views': analytics.total_views,
            'unique_viewers': analytics.unique_viewers,
            'total_duration': analytics.total_duration,
            'average_duration': analytics.average_duration,
            'completion_rate': analytics.completion_rate,
            'daily_stats': daily_stats,
            'weekly_stats': weekly_stats,
            'student_details': student_details
        }
        
        return Response(response_data)
    
    def _get_daily_stats(self, material, start_date):
        """Obtener estadísticas diarias del material"""
        from django.db.models import Count, Sum
        from django.db.models.functions import TruncDate
        
        daily_data = MaterialViewingSession.objects.filter(
            material=material,
            started_at__gte=start_date
        ).annotate(
            date=TruncDate('started_at')
        ).values('date').annotate(
            views=Count('id'),
            duration=Sum('duration_seconds'),
            unique_viewers=Count('student', distinct=True)
        ).order_by('date')
        
        return list(daily_data)
    
    def _get_weekly_stats(self, material, start_date):
        """Obtener estadísticas semanales del material"""
        from django.db.models import Count, Sum
        from django.db.models.functions import TruncWeek
        
        weekly_data = MaterialViewingSession.objects.filter(
            material=material,
            started_at__gte=start_date
        ).annotate(
            week=TruncWeek('started_at')
        ).values('week').annotate(
            views=Count('id'),
            duration=Sum('duration_seconds'),
            unique_viewers=Count('student', distinct=True)
        ).order_by('week')
        
        # Formatear semanas
        formatted_data = []
        for i, week_data in enumerate(weekly_data):
            formatted_data.append({
                'week': f'Semana {i + 1}',
                'views': week_data['views'],
                'duration': week_data['duration'] or 0,
                'unique_viewers': week_data['unique_viewers']
            })
        
        return formatted_data
    
    def _get_student_details(self, material, start_date):
        """Obtener detalles por estudiante que pertenecen al mismo salón/grado/sección del curso y tienen el curso en su portafolio"""
        from django.db.models import Count, Sum, Max, Avg, Q
        from accounts.models import CustomUser
        from portfolios.models import PortfolioCourse
        
        # Obtener el curso del material
        course = material.topic.course
        
        # Obtener estudiantes que tienen acceso al material basado en el tipo
        if material.is_shared:
            # Material de clase: obtener estudiantes de las secciones que tienen este curso asignado
            # Y que además tienen el curso en su portafolio
            accessible_students = CustomUser.objects.filter(
                role='ALUMNO',
                enrollment__section__course=course,  # Mismo curso
                enrollment__is_active=True,
                portfolios__courses__course=course  # Tiene el curso en su portafolio
            ).distinct()
        else:
            # Material personalizado: obtener estudiantes asignados específicamente
            # Y que además tienen el curso en su portafolio
            accessible_students = material.assigned_students.filter(
                role='ALUMNO',
                portfolios__courses__course=course  # Tiene el curso en su portafolio
            ).distinct()
        
        # Obtener datos de sesiones de visualización para estos estudiantes
        viewing_sessions = MaterialViewingSession.objects.filter(
            material=material,
            student__in=accessible_students,
            started_at__gte=start_date
        ).values(
            'student__id',
            'student__first_name',
            'student__last_name',
            'student__username'
        ).annotate(
            total_duration=Sum('duration_seconds'),
            sessions_count=Count('id'),
            completion_rate=Avg('progress_percentage'),
            last_viewed=Max('started_at')
        )
        
        # Crear un diccionario con los datos de sesiones
        sessions_data = {session['student__id']: session for session in viewing_sessions}
        
        formatted_data = []
        for student in accessible_students:
            session_data = sessions_data.get(student.id, {})
            
            # Obtener información de la sección del estudiante para mostrar en el análisis
            student_enrollment = student.enrollment_set.filter(
                section__course=course,
                is_active=True
            ).first()
            
            # Verificar que el estudiante tiene el curso en su portafolio
            has_course_in_portfolio = PortfolioCourse.objects.filter(
                portfolio__student=student,
                course=course
            ).exists()
            
            # Solo incluir si tiene el curso en su portafolio
            if has_course_in_portfolio:
                formatted_data.append({
                    'student_id': student.id,
                    'student_name': f"{student.first_name or ''} {student.last_name or ''}".strip() or student.username,
                    'section_name': student_enrollment.section.name if student_enrollment else 'Sin sección',
                    'grade_level': student_enrollment.section.grade_level.name if student_enrollment and student_enrollment.section.grade_level else 'Sin grado',
                    'total_duration': session_data.get('total_duration', 0) or 0,
                    'sessions_count': session_data.get('sessions_count', 0) or 0,
                    'completion_rate': session_data.get('completion_rate', 0) or 0,
                    'last_viewed': session_data.get('last_viewed').isoformat() if session_data.get('last_viewed') else None
                })
        
        # Ordenar por duración total (estudiantes con más interacción primero)
        formatted_data.sort(key=lambda x: x['total_duration'], reverse=True)
        
        return formatted_data


class MaterialTrackingViewSet(GenericViewSet):
    """ViewSet para tracking de visualización de materiales"""
    permission_classes = [IsAuthenticated]
    queryset = MaterialViewingSession.objects.none()
    
    @action(detail=False, methods=['post'], url_path='track')
    def track_material(self, request):
        """Endpoint para rastrear la visualización de materiales"""
        if request.user.role != 'ALUMNO':
            return Response(
                {'error': 'Solo los estudiantes pueden rastrear materiales'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MaterialTrackingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        material_id = data['material_id']
        action_type = data['action']
        progress_percentage = data.get('progress_percentage', 0)
        duration_seconds = data.get('duration_seconds', 0)
        metadata = data.get('metadata', {})
        
        try:
            material = Material.objects.get(id=material_id)
            
            # Verificar que el estudiante tiene acceso al material
            if not self._has_access_to_material(request.user, material):
                return Response(
                    {'error': 'No tienes acceso a este material'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Obtener o crear sesión activa
            session, created = MaterialViewingSession.objects.get_or_create(
                student=request.user,
                material=material,
                ended_at__isnull=True,
                defaults={'started_at': timezone.now()}
            )
            
            # Actualizar sesión según la acción
            if action_type == 'start':
                if created:
                    # Crear interacción de inicio
                    MaterialInteraction.objects.create(
                        session=session,
                        interaction_type='PLAY',
                        metadata=metadata
                    )
                else:
                    # Reanudar sesión existente
                    MaterialInteraction.objects.create(
                        session=session,
                        interaction_type='PLAY',
                        metadata=metadata
                    )
            
            elif action_type == 'pause':
                MaterialInteraction.objects.create(
                    session=session,
                    interaction_type='PAUSE',
                    metadata=metadata
                )
            
            elif action_type == 'seek':
                MaterialInteraction.objects.create(
                    session=session,
                    interaction_type='SEEK',
                    metadata=metadata
                )
            
            elif action_type == 'complete':
                session.ended_at = timezone.now()
                session.is_completed = True
                session.progress_percentage = 100.0
                session.duration_seconds = duration_seconds
                session.save()
                
                MaterialInteraction.objects.create(
                    session=session,
                    interaction_type='COMPLETE',
                    metadata=metadata
                )
                
                # Actualizar analytics
                self._update_material_analytics(material)
            
            elif action_type == 'abandon':
                session.ended_at = timezone.now()
                session.is_completed = False
                session.progress_percentage = progress_percentage
                session.duration_seconds = duration_seconds
                session.save()
                
                MaterialInteraction.objects.create(
                    session=session,
                    interaction_type='ABANDON',
                    metadata=metadata
                )
                
                # Actualizar analytics
                self._update_material_analytics(material)
            
            else:  # resume o actualización de progreso
                session.progress_percentage = progress_percentage
                session.duration_seconds = duration_seconds
                session.save()
            
            return Response({
                'success': True,
                'session_id': session.id,
                'action': action_type,
                'progress': session.progress_percentage
            })
            
        except Material.DoesNotExist:
            return Response(
                {'error': 'Material no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _has_access_to_material(self, student, material):
        """Verificar si el estudiante tiene acceso al material"""
        # Si es material compartido, verificar que el estudiante esté en una sección del curso
        if material.is_shared:
            return Enrollment.objects.filter(
                student=student,
                section__course=material.topic.course,
                is_active=True
            ).exists()
        
        # Si es material personalizado, verificar que esté asignado al estudiante
        return material.assigned_students.filter(id=student.id).exists()
    
    def _update_material_analytics(self, material):
        """Actualizar analytics del material"""
        analytics, created = MaterialAnalytics.objects.get_or_create(material=material)
        analytics.update_analytics()
    
    @action(detail=False, methods=['get'], url_path='my-materials')
    def my_materials_with_analytics(self, request):
        """Obtener materiales del estudiante con analytics"""
        if request.user.role != 'ALUMNO':
            return Response(
                {'error': 'Solo los estudiantes pueden acceder a este endpoint'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Obtener materiales accesibles para el estudiante
        accessible_materials = Material.objects.filter(
            Q(is_shared=True, topic__course__sections__enrollment__student=request.user) |
            Q(is_shared=False, assigned_students=request.user)
        ).distinct().select_related('topic', 'professor')
        
        serializer = MaterialWithAnalyticsSerializer(accessible_materials, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='professor-analytics')
    def professor_analytics(self, request):
        """Obtener analytics para profesores"""
        if request.user.role != 'PROFESOR':
            return Response(
                {'error': 'Solo los profesores pueden acceder a este endpoint'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Obtener KPIs generales
        materials = Material.objects.filter(professor=request.user)
        total_materials = materials.count()
        
        # Obtener analytics agregadas
        analytics_data = MaterialAnalytics.objects.filter(
            material__professor=request.user
        ).aggregate(
            total_views=Sum('total_views'),
            total_unique_viewers=Sum('unique_viewers'),
            total_duration=Sum('total_duration'),
            avg_completion_rate=Avg('completion_rate')
        )
        
        # Obtener materiales más populares
        popular_materials = MaterialAnalytics.objects.filter(
            material__professor=request.user
        ).order_by('-total_views')[:5]
        
        # Obtener estudiantes más activos
        active_students = MaterialViewingSession.objects.filter(
            material__professor=request.user
        ).values('student__username', 'student__first_name', 'student__last_name').annotate(
            total_sessions=Count('id'),
            total_duration=Sum('duration_seconds')
        ).order_by('-total_duration')[:10]
        
        return Response({
            'total_materials': total_materials,
            'analytics': analytics_data,
            'popular_materials': MaterialAnalyticsSerializer(popular_materials, many=True).data,
            'active_students': active_students
        })
