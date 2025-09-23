from django.db import models
from django.conf import settings
import uuid

def generate_session_id():
    return str(uuid.uuid4())

class Conversation(models.Model):
    """Modelo para conversaciones con DeepSeek"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_conversations')
    session_id = models.CharField(max_length=100, unique=True, default=generate_session_id)
    title = models.CharField(max_length=200, blank=True)
    requirements = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Conversación'
        verbose_name_plural = 'Conversaciones'
    
    def __str__(self):
        return f"{self.user.first_name} - {self.title or 'Sin título'}"

class ConversationMessage(models.Model):
    """Modelo para mensajes de conversación"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=[('user', 'Usuario'), ('assistant', 'Asistente')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = 'Mensaje'
        verbose_name_plural = 'Mensajes'
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

class ContentTemplate(models.Model):
    """Modelo para plantillas de contenido"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    prompt_template = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Plantilla de Contenido'
        verbose_name_plural = 'Plantillas de Contenido'
    
    def __str__(self):
        return self.name

class GeneratedContent(models.Model):
    """Modelo para contenido generado por IA"""
    conversation = models.ForeignKey(Conversation, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_content')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    content_type = models.CharField(max_length=50, default='gamma', choices=[
        ('gamma', 'Gamma Blocks')
    ])
    
    # Contenido Gamma
    gamma_blocks = models.JSONField(default=list, blank=True)
    gamma_document = models.JSONField(default=dict, blank=True)
    
    # Metadatos
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contenido Generado'
        verbose_name_plural = 'Contenidos Generados'
    
    def __str__(self):
        return f"{self.title} - {self.conversation.user.first_name if self.conversation else 'Sin usuario'}"
    
    @property
    def user_name(self):
        return self.conversation.user.first_name if self.conversation else 'Usuario desconocido'