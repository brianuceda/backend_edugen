from rest_framework import serializers
from accounts.models import CustomUser
from academic.models import Section


class DirectorUserSerializer(serializers.ModelSerializer):
    """
    Serializer para gestión de usuarios por el director
    """
    password = serializers.CharField(write_only=True)
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'institution', 'institution_name', 'password', 'is_active']
        extra_kwargs = {
            'password': {'write_only': True},
            'institution': {'read_only': True}
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class DirectorSectionSerializer(serializers.ModelSerializer):
    """
    Serializer para gestión de secciones por el director
    """
    course_name = serializers.CharField(source='course.name', read_only=True)
    professor_name = serializers.CharField(source='professor.get_full_name', read_only=True)
    
    class Meta:
        model = Section
        fields = ['id', 'name', 'course', 'course_name', 'professor', 'professor_name', 'capacity', 'created_at']
