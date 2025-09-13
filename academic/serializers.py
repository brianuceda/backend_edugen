from rest_framework import serializers
from .models import Course, Topic, Section, Enrollment, Assessment, Grade, Material
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


class MaterialSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    professor_name = serializers.SerializerMethodField()
    assigned_students_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Material
        fields = [
            'id', 'name', 'description', 'material_type', 'file', 'url',
            'topic', 'topic_name', 'professor', 'professor_name',
            'is_shared', 'assigned_students', 'assigned_students_data',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'professor': {'required': False},
            'assigned_students': {'required': False, 'many': True}
        }
    
    def get_professor_name(self, obj):
        return f"{obj.professor.first_name} {obj.professor.last_name}" if obj.professor else ""
    
    def get_assigned_students_data(self, obj):
        """Return assigned students data"""
        return [
            {
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'username': student.username
            }
            for student in obj.assigned_students.all()
        ]
    
    def create(self, validated_data):
        # Asignar el profesor actual al crear el material
        if 'professor' not in validated_data:
            validated_data['professor'] = self.context['request'].user
        
        # Obtener estudiantes asignados
        assigned_students = validated_data.pop('assigned_students', [])
        
        # Crear el material
        material = super().create(validated_data)
        
        # Asignar estudiantes si es material personalizado
        if not validated_data.get('is_shared', True) and assigned_students:
            material.assigned_students.set(assigned_students)
        
        return material
    
    def to_internal_value(self, data):
        """Manejar FormData correctamente"""
        if hasattr(data, 'getlist'):
            # Es FormData, procesar campos múltiples
            processed_data = {}
            for key, value in data.items():
                if key == 'assigned_students':
                    # Manejar lista de estudiantes - convertir strings a enteros
                    student_ids = data.getlist(key)
                    processed_data[key] = [int(sid) for sid in student_ids if sid]
                elif key == 'is_shared':
                    # Convertir string a boolean
                    processed_data[key] = value.lower() == 'true'
                elif key == 'topic':
                    # Convertir string a entero
                    processed_data[key] = int(value)
                elif key == 'file':
                    # Solo incluir el archivo si existe y no está vacío
                    if value and value != {} and value != '':
                        processed_data[key] = value
                else:
                    processed_data[key] = value
            return super().to_internal_value(processed_data)
        
        return super().to_internal_value(data)
    
    def update(self, instance, validated_data):
        # Obtener estudiantes asignados
        assigned_students = validated_data.pop('assigned_students', None)
        
        # Actualizar el material
        material = super().update(instance, validated_data)
        
        # Actualizar estudiantes asignados si se proporcionan
        if assigned_students is not None:
            material.assigned_students.set(assigned_students)
        
        return material
    
    def validate(self, data):
        """Validar que el material tenga archivo o URL según el tipo"""
        material_type = data.get('material_type')
        file = data.get('file')
        url = data.get('url')
        
        # Validaciones básicas
        if material_type == 'LINK' and not url:
            raise serializers.ValidationError('Los materiales de tipo enlace deben tener una URL')
        
        # Verificar si hay un archivo válido (no vacío ni None)
        has_valid_file = file is not None and file != {} and file != '' and hasattr(file, 'name')
        
        if material_type != 'LINK' and not has_valid_file:
            raise serializers.ValidationError('Los materiales que no son enlaces deben tener un archivo')
        
        if url and has_valid_file:
            raise serializers.ValidationError('Un material no puede tener tanto archivo como URL')
        
        return data