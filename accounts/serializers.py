from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    section = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'specialty', 'specialty_display', 'institution', 'section', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_section(self, obj):
        """Obtener la sección del estudiante si es un alumno"""
        if obj.role == 'ALUMNO':
            try:
                from academic.models import Enrollment
                enrollment = Enrollment.objects.filter(student=obj, is_active=True).first()
                if enrollment:
                    return {
                        'id': enrollment.section.id,
                        'name': enrollment.section.name,
                        'course_name': enrollment.section.course.name if enrollment.section.course else None,
                        'grade_level_name': enrollment.section.grade_level.name if enrollment.section.grade_level else None,
                        'term_name': enrollment.section.term.name if enrollment.section.term else None,
                    }
            except Exception:
                pass
        return None


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
