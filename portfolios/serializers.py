from rest_framework import serializers
from .models import Portfolio, Activity, ActivityAssignment, Artifact, PortfolioCourse
from academic.serializers import CourseSerializer, SectionSerializer, TopicSerializer
from accounts.serializers import UserSerializer


class PortfolioCourseSerializer(serializers.ModelSerializer):
    """Serializer para cursos del portafolio"""
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    topics = serializers.SerializerMethodField()
    
    class Meta:
        model = PortfolioCourse
        fields = ['id', 'course', 'course_name', 'course_code', 'added_at', 'topics']
    
    def get_topics(self, obj):
        """Obtener los temas del curso que están activos"""
        from academic.models import Topic
        topics = Topic.objects.filter(course=obj.course, is_active=True).order_by('order', 'name')
        return TopicSerializer(topics, many=True, context=self.context).data


class PortfolioSerializer(serializers.ModelSerializer):
    """Serializer para Portfolio"""
    student_name = serializers.SerializerMethodField()
    section_name = serializers.SerializerMethodField()
    courses = PortfolioCourseSerializer(many=True, read_only=True)
    activity_assignments_count = serializers.SerializerMethodField()
    completed_assignments_count = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = [
            'id', 'student', 'section', 'title', 'description',
            'is_public', 'created_at', 'updated_at', 'student_name',
            'section_name', 'courses', 'activity_assignments_count',
            'completed_assignments_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"

    def get_section_name(self, obj):
        return obj.section.name

    def get_activity_assignments_count(self, obj):
        return obj.activity_assignments.count()

    def get_completed_assignments_count(self, obj):
        return obj.activity_assignments.filter(is_completed=True).count()


class ActivitySerializer(serializers.ModelSerializer):
    """Serializer para Activity"""
    professor_name = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField()
    section_name = serializers.SerializerMethodField()
    assignments_count = serializers.SerializerMethodField()
    completed_assignments_count = serializers.SerializerMethodField()
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id', 'professor', 'course', 'section', 'title', 'description',
            'activity_type', 'activity_type_display', 'instructions', 'due_date',
            'points', 'is_active', 'created_at', 'updated_at', 'professor_name',
            'course_name', 'section_name', 'assignments_count', 'completed_assignments_count'
        ]
        read_only_fields = ['id', 'professor', 'created_at', 'updated_at']

    def get_professor_name(self, obj):
        return f"{obj.professor.first_name} {obj.professor.last_name}"

    def get_course_name(self, obj):
        return obj.course.name

    def get_section_name(self, obj):
        return obj.section.name

    def get_assignments_count(self, obj):
        return obj.assignments.count()

    def get_completed_assignments_count(self, obj):
        return obj.assignments.filter(is_completed=True).count()


class ActivityCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear actividades"""
    class Meta:
        model = Activity
        fields = [
            'course', 'section', 'title', 'description', 'activity_type',
            'instructions', 'due_date', 'points', 'is_active'
        ]

    def create(self, validated_data):
        # El profesor se asigna automáticamente desde el request
        validated_data['professor'] = self.context['request'].user
        return super().create(validated_data)


class ArtifactSerializer(serializers.ModelSerializer):
    """Serializer para Artifact"""
    assignment_title = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Artifact
        fields = [
            'id', 'assignment', 'title', 'description', 'file', 'file_url',
            'artifact_type', 'created_at', 'assignment_title'
        ]
        read_only_fields = ['id', 'created_at']

    def get_assignment_title(self, obj):
        return obj.assignment.activity.title

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class ActivityAssignmentSerializer(serializers.ModelSerializer):
    """Serializer para ActivityAssignment"""
    student_name = serializers.SerializerMethodField()
    activity_title = serializers.SerializerMethodField()
    portfolio_title = serializers.SerializerMethodField()
    artifacts = ArtifactSerializer(many=True, read_only=True)
    days_until_due = serializers.SerializerMethodField()

    class Meta:
        model = ActivityAssignment
        fields = [
            'id', 'activity', 'student', 'portfolio', 'assigned_at',
            'completed_at', 'is_completed', 'grade', 'feedback',
            'submission_notes', 'student_name', 'activity_title',
            'portfolio_title', 'artifacts', 'days_until_due'
        ]
        read_only_fields = ['id', 'assigned_at']

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"

    def get_activity_title(self, obj):
        return obj.activity.title

    def get_portfolio_title(self, obj):
        return obj.portfolio.title

    def get_days_until_due(self, obj):
        from django.utils import timezone
        if obj.activity.due_date:
            delta = obj.activity.due_date - timezone.now()
            return delta.days
        return None


class ActivityAssignmentCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear asignaciones de actividades"""
    student_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        help_text="Lista de IDs de estudiantes a los que asignar la actividad"
    )

    class Meta:
        model = ActivityAssignment
        fields = ['activity', 'student_ids']

    def create(self, validated_data):
        student_ids = validated_data.pop('student_ids')
        activity = validated_data['activity']
        assignments = []

        for student_id in student_ids:
            # Obtener o crear el portafolio del estudiante
            from accounts.models import CustomUser
            student = CustomUser.objects.get(id=student_id)
            
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

        return assignments[0] if assignments else None


class PortfolioDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para Portfolio con actividades"""
    student_name = serializers.SerializerMethodField()
    section_name = serializers.SerializerMethodField()
    courses = PortfolioCourseSerializer(many=True, read_only=True)
    activity_assignments = ActivityAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = [
            'id', 'student', 'section', 'title', 'description',
            'is_public', 'created_at', 'updated_at', 'student_name',
            'section_name', 'courses', 'activity_assignments'
        ]

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"

    def get_section_name(self, obj):
        return obj.section.name