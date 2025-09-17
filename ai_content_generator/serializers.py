from rest_framework import serializers
from .models import Conversation, ConversationMessage, ContentTemplate, GeneratedContent
from accounts.serializers import UserSerializer

class ConversationMessageSerializer(serializers.ModelSerializer):
    """Serializer para mensajes de conversación"""
    
    class Meta:
        model = ConversationMessage
        fields = ['id', 'role', 'content', 'timestamp']
        read_only_fields = ['id', 'timestamp']

class ConversationSerializer(serializers.ModelSerializer):
    """Serializer para conversaciones"""
    user_name = serializers.SerializerMethodField()
    messages = ConversationMessageSerializer(many=True, read_only=True)
    messages_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'user', 'user_name', 'session_id', 'title', 'requirements',
            'is_active', 'created_at', 'updated_at', 'messages', 'messages_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'session_id']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    
    def get_messages_count(self, obj):
        return obj.messages.count()

class ContentTemplateSerializer(serializers.ModelSerializer):
    """Serializer para plantillas de contenido"""
    
    class Meta:
        model = ContentTemplate
        fields = [
            'id', 'name', 'description', 'prompt_template',
            'grapesjs_config', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class GeneratedContentSerializer(serializers.ModelSerializer):
    """Serializer para contenido generado"""
    conversation_title = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = GeneratedContent
        fields = [
            'id', 'conversation', 'conversation_title', 'user_name',
            'title', 'html_content', 'css_content', 'js_content',
            'grapesjs_components', 'is_public', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_conversation_title(self, obj):
        return obj.conversation.title or f"Conversación {obj.conversation.id}"
    
    def get_user_name(self, obj):
        return f"{obj.conversation.user.first_name} {obj.conversation.user.last_name}"

class CreateConversationSerializer(serializers.Serializer):
    """Serializer para crear nueva conversación"""
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    
    def create(self, validated_data):
        user = self.context['request'].user
        return Conversation.objects.create(
            user=user,
            title=validated_data.get('title', '')
        )

class SendMessageSerializer(serializers.Serializer):
    """Serializer para enviar mensaje"""
    content = serializers.CharField(max_length=5000)
    
    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("El contenido del mensaje no puede estar vacío")
        return value

class GenerateContentSerializer(serializers.Serializer):
    """Serializer para generar contenido"""
    requirements = serializers.JSONField()
    title = serializers.CharField(max_length=200)
    
    def validate_requirements(self, value):
        # Validar que los requisitos existan y no estén vacíos
        if not value or not isinstance(value, dict):
            raise serializers.ValidationError("Los requisitos deben ser un objeto válido")
        
        # Verificar que tenga los campos mínimos necesarios para generar contenido
        required_fields = ['subject', 'content_type']
        missing_fields = [field for field in required_fields if not value.get(field)]
        
        if missing_fields:
            raise serializers.ValidationError(f"Los requisitos deben contener: {', '.join(missing_fields)}")
        
        # Si is_complete es False pero tenemos campos básicos, permitir la generación
        # pero mostrar una advertencia en los logs
        if value.get('is_complete', False) is False:
            print(f"⚠️ [VALIDATION] Requisitos marcados como incompletos pero tienen campos básicos suficientes")
            print(f"⚠️ [VALIDATION] Campos disponibles: {list(value.keys())}")
        
        return value
