from rest_framework import serializers
from accounts.models import CustomUser
from academic.models import Section, Course
from institutions.models import Term, GradeLevel


class DirectorUserSerializer(serializers.ModelSerializer):
    """
    Serializer para gestión de usuarios por el director
    """
    password = serializers.CharField(write_only=True)
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    assigned_sections = serializers.SerializerMethodField()
    assigned_sections_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'institution', 'institution_name', 'password', 'is_active', 'specialty', 'specialty_display', 'assigned_sections', 'assigned_sections_ids']
        extra_kwargs = {
            'password': {'write_only': True},
            'institution': {'read_only': True}
        }
    
    def get_assigned_sections(self, obj):
        try:
            if obj.role == 'PROFESOR':
                sections = obj.sections_taught.all()
                result = []
                for section in sections:
                    section_data = {
                        'id': section.id, 
                        'name': section.name,
                        'grade_level_name': section.grade_level.name if section.grade_level else 'Sin grado',
                        'term_name': section.term.name if section.term else 'Sin período'
                    }
                    result.append(section_data)
                return result
            elif obj.role == 'ALUMNO':
                # Para estudiantes, obtener secciones a través de enrollments
                from academic.models import Enrollment
                enrollments = Enrollment.objects.filter(student=obj, is_active=True)
                result = []
                for enrollment in enrollments:
                    section = enrollment.section
                    section_data = {
                        'id': section.id, 
                        'name': section.name,
                        'grade_level_name': section.grade_level.name if section.grade_level else 'Sin grado',
                        'term_name': section.term.name if section.term else 'Sin período'
                    }
                    result.append(section_data)
                return result
        except Exception as e:
            return []
        return []
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        assigned_sections_ids = validated_data.pop('assigned_sections_ids', [])
        user = CustomUser.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        
        # Asignar secciones según el rol
        if assigned_sections_ids:
            if user.role == 'PROFESOR':
                user.sections_taught.set(assigned_sections_ids)
            elif user.role == 'ALUMNO':
                # Para estudiantes, crear enrollments
                from academic.models import Enrollment
                for section_id in assigned_sections_ids:
                    Enrollment.objects.get_or_create(
                        student=user,
                        section_id=section_id,
                        defaults={'is_active': True}
                    )
        
        return user
    
    def update(self, instance, validated_data):
        assigned_sections_ids = validated_data.pop('assigned_sections_ids', None)
        
        # Actualizar campos básicos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar secciones asignadas según el rol
        if assigned_sections_ids is not None:
            if instance.role == 'PROFESOR':
                instance.sections_taught.set(assigned_sections_ids)
            elif instance.role == 'ALUMNO':
                # Para estudiantes, actualizar enrollments
                from academic.models import Enrollment
                # Desactivar enrollments existentes
                Enrollment.objects.filter(student=instance).update(is_active=False)
                # Crear nuevos enrollments
                for section_id in assigned_sections_ids:
                    Enrollment.objects.get_or_create(
                        student=instance,
                        section_id=section_id,
                        defaults={'is_active': True}
                    )
        
        return instance


class DirectorTermSerializer(serializers.ModelSerializer):
    """
    Serializer para gestión de períodos por el director
    """
    class Meta:
        model = Term
        fields = ['id', 'name', 'start_date', 'end_date', 'is_active', 'created_at']
        extra_kwargs = {
            'institution': {'write_only': True}
        }


class DirectorGradeLevelSerializer(serializers.ModelSerializer):
    """
    Serializer para gestión de grados por el director
    """
    class Meta:
        model = GradeLevel
        fields = ['id', 'name', 'level', 'created_at']
        extra_kwargs = {
            'institution': {'write_only': True}
        }


class DirectorSectionSerializer(serializers.ModelSerializer):
    """
    Serializer para gestión de secciones por el director
    """
    professors_names = serializers.SerializerMethodField()
    term_name = serializers.CharField(source='term.name', read_only=True)
    grade_level_name = serializers.CharField(source='grade_level.name', read_only=True)
    
    class Meta:
        model = Section
        fields = ['id', 'name', 'capacity', 'professors', 'professors_names', 'term', 'term_name', 'grade_level', 'grade_level_name', 'created_at']
        extra_kwargs = {
            'professors': {'required': False},
            'term': {'required': True},
            'grade_level': {'required': True}
        }
    
    def get_professors_names(self, obj):
        return [f"{prof.get_full_name()}" for prof in obj.professors.all()]
