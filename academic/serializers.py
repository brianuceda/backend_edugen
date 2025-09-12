from rest_framework import serializers
from .models import Course, Section, Enrollment, Assessment, Grade
from accounts.serializers import UserSerializer
from institutions.serializers import InstitutionSerializer, TermSerializer


class CourseSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    
    class Meta:
        model = Course
        fields = '__all__'


class SectionSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    professor_name = serializers.CharField(source='professor.get_full_name', read_only=True)
    term_name = serializers.CharField(source='term.name', read_only=True)
    
    class Meta:
        model = Section
        fields = '__all__'


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