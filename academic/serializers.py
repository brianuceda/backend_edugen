from rest_framework import serializers
from .models import Course, Topic, Section, Enrollment, Assessment, Grade
from accounts.serializers import UserSerializer
from institutions.serializers import InstitutionSerializer, TermSerializer


class CourseSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    
    class Meta:
        model = Course
        fields = '__all__'
        extra_kwargs = {
            'institution': {'required': False}
        }
    
    def validate_description(self, value):
        """Handle empty description"""
        return value if value else ""


class TopicSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    professor_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Topic
        fields = [
            'id', 'name', 'description', 'course', 'course_name', 'course_code',
            'professor', 'professor_name', 'order', 'is_active', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'course': {'required': True},
            'professor': {'required': False}
        }
    
    def get_professor_name(self, obj):
        return f"{obj.professor.first_name} {obj.professor.last_name}" if obj.professor else ""
    
    def create(self, validated_data):
        # Asignar el profesor actual al crear el tema
        if 'professor' not in validated_data:
            validated_data['professor'] = self.context['request'].user
        
        # Asignar orden automático si no se proporciona
        if 'order' not in validated_data or validated_data['order'] == 0:
            course = validated_data['course']
            # Obtener el último orden para este curso y agregar 1
            last_topic = Topic.objects.filter(course=course).order_by('-order').first()
            validated_data['order'] = (last_topic.order + 1) if last_topic else 1
        
        return super().create(validated_data)


class SectionSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    professors_names = serializers.SerializerMethodField()
    term_name = serializers.CharField(source='term.name', read_only=True)
    course = serializers.SerializerMethodField()
    grade_level = serializers.SerializerMethodField()
    term = serializers.SerializerMethodField()
    
    class Meta:
        model = Section
        fields = '__all__'
    
    def get_professors_names(self, obj):
        """Return a list of professor names"""
        return [prof.get_full_name() for prof in obj.professors.all()]
    
    def get_course(self, obj):
        """Return course details"""
        if obj.course:
            return {
                'id': obj.course.id,
                'name': obj.course.name,
                'code': obj.course.code
            }
        return None
    
    def get_grade_level(self, obj):
        """Return grade level details"""
        if obj.grade_level:
            return {
                'id': obj.grade_level.id,
                'name': obj.grade_level.name,
                'level': obj.grade_level.level
            }
        return None
    
    def get_term(self, obj):
        """Return term details"""
        if obj.term:
            return {
                'id': obj.term.id,
                'name': obj.term.name,
                'is_active': obj.term.is_active
            }
        return None


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    section_name = serializers.CharField(source='section.name', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = '__all__'


class AssessmentSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source='section.name', read_only=True)
    
    class Meta:
        model = Assessment
        fields = '__all__'


class GradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    assessment_name = serializers.CharField(source='assessment.name', read_only=True)
    
    class Meta:
        model = Grade
        fields = '__all__'