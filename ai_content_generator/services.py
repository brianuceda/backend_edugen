import requests
import json
import re
import ast
from typing import List, Dict, Any, Optional
import time
from django.conf import settings

class DeepSeekChatService:
    """Servicio para interactuar con la API de DeepSeek"""
    
    def __init__(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = "deepseek-chat"
    
    def chat_with_user(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Maneja la conversación con el usuario usando DeepSeek"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Construir el prompt del sistema para recolección de información
        system_prompt = self.get_collection_system_prompt()
        
        # Preparar mensajes
        chat_messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Agregar historial de conversación
        for msg in messages:
            chat_messages.append({
                "role": msg.get('role', 'user'),
                "content": msg.get('content', '')
            })
        
        payload = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": 0.7,
            "max_tokens": 4000,  # Aumentado para respuestas más completas
            "stream": False
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception(f"401 Unauthorized: API key inválida o expirada")
            elif e.response.status_code == 429:
                raise Exception(f"429 Rate Limit: Límite de solicitudes excedido")
            else:
                raise Exception(f"Error HTTP {e.response.status_code}: {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error en DeepSeek API: {str(e)}")
    
    def get_collection_system_prompt(self) -> str:
        """Obtiene el prompt del sistema para recolección de información"""
        return """
        Eres un asistente especializado en recolección de información para crear contenido educativo con el editor Gamma.
        
        FORMATO FIJO: El contenido siempre se generará en formato de bloques Gamma. NO preguntes sobre formatos.
        
        REGLAS IMPORTANTES:
        1. NO hagas preguntas obvias o redundantes
        2. Analiza el contexto antes de preguntar
        3. Si el usuario ya mencionó información, NO la preguntes de nuevo
        4. Sé inteligente y deduce información cuando sea posible
        5. Haz solo preguntas esenciales que realmente necesites
        6. NUNCA preguntes sobre formato - siempre será Gamma
        7. Si el usuario da información incompleta, haz preguntas específicas para completarla
        
        INFORMACIÓN CRÍTICA A RECOLECTAR:
        - Tema/Materia específica (OBLIGATORIO)
        - Nivel educativo (básico/intermedio/avanzado) - deduce si no está claro
        - Tipo de contenido (lección, ejercicio, evaluación, guía, etc.)
        - Objetivos de aprendizaje específicos (al menos 2-3)
        - Público objetivo (edad, nivel, características)
        - Duración estimada (opcional pero útil)
        - Secciones principales (introducción, desarrollo, ejercicios, evaluación)
        - Recursos necesarios (imágenes, videos, interactivos)
        
        ESTRATEGIA DE RECOLECCIÓN:
        1. Analiza cada mensaje del usuario cuidadosamente
        2. Identifica información explícita e implícita
        3. Haz preguntas específicas para completar información faltante
        4. Confirma tu entendimiento antes de proceder
        5. Máximo 2 preguntas por mensaje para no abrumar
        
        EJEMPLOS DE PREGUNTAS INTELIGENTES:
        ✅ "¿Qué objetivos específicos quieres que logren los estudiantes con este contenido?"
        ✅ "¿Para qué nivel de estudiantes está dirigido? (básico, intermedio, avanzado)"
        ✅ "¿Qué tipo de ejercicios prefieres incluir? (opción múltiple, problemas prácticos, etc.)"
        ✅ "¿Qué secciones específicas necesitas? (introducción, teoría, ejemplos, ejercicios, evaluación)"
        ✅ "¿Hay algún recurso específico que quieras incluir? (imágenes, videos, interactivos)"
        
        ❌ "¿Qué formato prefieres?" (NUNCA preguntes esto)
        ❌ "¿Quieres PDF o web?" (NUNCA preguntes esto)
        ❌ "¿Para qué nivel educativo?" (si ya mencionó "secundaria" o similar)
        
        CUANDO TENGAS INFORMACIÓN SUFICIENTE:
        - Haz un resumen completo de lo que vas a crear
        - Incluye: tema, nivel, tipo, objetivos, secciones principales
        - SIEMPRE pregunta: "¿Estás conforme con esta información o quieres agregar algo más?"
        - ESPERA a que el usuario responda con palabras explícitas como: "sí", "conforme", "perfecto", "está bien", "procede", "adelante", "confirmo"
        - SOLO después de que el usuario confirme con PALABRAS, di: "¡Perfecto! Ya tienes suficiente información. Usa 'Extraer Requisitos' para generar el contenido."
        - NUNCA actives el botón solo con emojis o respuestas ambiguas
        - El usuario DEBE escribir explícitamente su confirmación
        
        Mantén un tono amigable, profesional y educativo. Responde siempre en español.
        """
    
    
    def extract_requirements(self, conversation_history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """Extrae los requisitos de la conversación usando DeepSeek"""
        
        # Verificar si hay suficiente información en la conversación
        if len(conversation_history) < 1:
            return None
        
        # Buscar indicadores de que el contenido está listo
        ready_indicators = [
            "está listo tu contenido para ser generado",
            "listo tu contenido",
            "contenido para ser generado",
            "proceder con la generación",
            "extraer requisitos",
            "generar el contenido",
            "ya tienes suficiente información",
            "usa \"extraer requisitos\" para generar",
            "perfecto! ya tienes suficiente información",
            "tienes suficiente información para generar contenido",
            "estás conforme con esta información",
            "quieres agregar algo más",
            "¿estás conforme con esta información o quieres agregar algo más?",
            "confirmo la información",
            "estoy conforme",
            "proceder con la generación",
            "generar contenido"
        ]
        
        # Verificar si el asistente indicó que está listo
        last_assistant_message = None
        is_ready = False
        
        for msg in reversed(conversation_history):
            if msg.get('role') == 'assistant':
                last_assistant_message = msg.get('content', '').lower()
                # Verificar si contiene algún indicador de que está listo
                if any(indicator in last_assistant_message for indicator in ready_indicators):
                    is_ready = True
                    break
        
        # Verificar si el usuario confirmó explícitamente
        if not is_ready:
            user_confirmations = [
                'sí, estoy conforme',
                'perfecto, estoy conforme', 
                'sí, está bien',
                'está perfecto',
                'sí, procede',
                'conforme',
                'está bien',
                'perfecto',
                'sí',
                'ok',
                'okay',
                'confirmo',
                'estoy de acuerdo',
                'procede',
                'adelante',
                'si, estoy conforme',
                'si, está bien',
                'si, procede',
                'si',
                'está listo',
                'listo',
                'generar',
                'extraer requisitos'
            ]
            
            for msg in reversed(conversation_history):
                if msg.get('role') == 'user':
                    user_content = msg.get('content', '').lower()
                    if any(confirmation in user_content for confirmation in user_confirmations):
                        is_ready = True
                        break
        
        # Si no está listo por confirmación, verificar si hay suficiente información básica
        if not is_ready:
            # Buscar información básica en la conversación
            has_subject = False
            has_level = False
            has_content_type = False
            
            for msg in conversation_history:
                content = msg.get('content', '').lower()
                
                # Verificar si hay información sobre materia/tema
                if any(word in content for word in ['matemáticas', 'ciencias', 'historia', 'español', 'inglés', 'física', 'química', 'biología', 'geografía', 'polinomios', 'álgebra', 'geometría']):
                    has_subject = True
                
                # Verificar si hay información sobre nivel
                if any(word in content for word in ['primaria', 'secundaria', 'universidad', 'básico', 'intermedio', 'avanzado', '1°', '2°', '3°', '4°', '5°', '6°']):
                    has_level = True
                
                # Verificar si hay información sobre tipo de contenido
                if any(word in content for word in ['lección', 'ejercicio', 'evaluación', 'actividad', 'taller', 'práctica', 'ejercicios']):
                    has_content_type = True
            
            # Si hay al menos 2 de los 3 elementos básicos, permitir extracción
            if sum([has_subject, has_level, has_content_type]) >= 2:
                is_ready = True
        
        # Siempre extraer requisitos de la conversación cuando se llama esta función
        # El usuario hizo clic en "Extraer Requisitos", así que proceder con la extracción
        
        extraction_prompt = """
        Analiza la siguiente conversación y extrae AUTOMÁTICAMENTE todos los requisitos del usuario para crear contenido educativo con bloques Gamma.
        
        INSTRUCCIONES:
        1. Extrae TODA la información disponible en la conversación (explícita e implícita)
        2. Deduce información inteligentemente basándote en el contexto completo
        3. Si el usuario menciona "polinomios" y "1° de secundaria", extrae automáticamente:
           - Materia: Matemáticas - Polinomios
           - Nivel: Básico (1° de secundaria)
           - Tipo: Ejercicios (si menciona ejercicios)
           - Objetivos: Suma y resta de polinomios
        4. SIEMPRE marca "is_complete": true para permitir la generación
        5. Usa la información de la conversación para crear requisitos específicos
        
        REGLAS DE EXTRACCIÓN AUTOMÁTICA:
        - "1° de secundaria" → course_level: "básico", target_audience: "Estudiantes de 1° de secundaria (12-13 años)"
        - "polinomios" → subject: "Matemáticas - Polinomios"
        - "ejercicios" → content_type: "ejercicios"
        - "suma y resta" → learning_objectives: ["Aprender suma de polinomios", "Aprender resta de polinomios"]
        - Si menciona "10-15 ejercicios" → additional_requirements: "Set de 10-15 ejercicios"
        
        IMPORTANTE: 
        - SIEMPRE devuelve un JSON válido
        - SIEMPRE marca is_complete: true
        - Extrae información específica de la conversación
        - Usa valores por defecto inteligentes basados en el contexto
        
        Devuelve SOLO un JSON válido con la siguiente estructura:
        {
            "course_level": "básico",
            "subject": "Matemáticas - Polinomios",
            "content_type": "ejercicios",
            "learning_objectives": ["Aprender suma de polinomios", "Aprender resta de polinomios", "Practicar operaciones básicas"],
            "sections": ["introducción", "desarrollo", "ejercicios", "evaluación"],
            "target_audience": "Estudiantes de 1° de secundaria (12-13 años)",
            "resources": ["imágenes", "videos", "ejemplos visuales"],
            "estimated_duration": "45-60 minutos",
            "additional_requirements": "Set de 10-15 ejercicios paso a paso",
            "is_complete": true,
            "missing_info": []
        }
        
        Conversación:
        """
        
        # Agregar historial de conversación
        for msg in conversation_history:
            extraction_prompt += f"\n{msg.get('role', 'user')}: {msg.get('content', '')}"
        
        # Usar DeepSeek para extraer requisitos
        try:
            response = self.chat_with_user([
                {"role": "user", "content": extraction_prompt}
            ])
            
            content = response['choices'][0]['message']['content']
            
            # Buscar JSON en la respuesta
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                try:
                    requirements = json.loads(json_str)
                    
                    # Validar que tenga los campos mínimos necesarios
                    if not requirements.get('subject'):
                        # Si no hay materia, intentar extraer del contexto
                        for msg in conversation_history:
                            if msg.get('role') == 'user':
                                content_lower = msg.get('content', '').lower()
                                if 'matemáticas' in content_lower or 'math' in content_lower:
                                    requirements['subject'] = 'Matemáticas'
                                elif 'ciencias' in content_lower or 'science' in content_lower:
                                    requirements['subject'] = 'Ciencias'
                                elif 'historia' in content_lower or 'history' in content_lower:
                                    requirements['subject'] = 'Historia'
                                elif 'español' in content_lower or 'spanish' in content_lower:
                                    requirements['subject'] = 'Español'
                                else:
                                    requirements['subject'] = 'Tema General'
                                break
                    
                    # Asegurar que tenga objetivos de aprendizaje
                    if not requirements.get('learning_objectives') or len(requirements.get('learning_objectives', [])) < 2:
                        requirements['learning_objectives'] = [
                            f"Aprender sobre {requirements.get('subject', 'el tema')}",
                            f"Entender los conceptos fundamentales de {requirements.get('subject', 'el tema')}"
                        ]
                    
                    # Asegurar que tenga nivel de curso
                    if not requirements.get('course_level'):
                        requirements['course_level'] = 'intermedio'
                    
                    # Asegurar que tenga tipo de contenido
                    if not requirements.get('content_type'):
                        requirements['content_type'] = 'lección'
                    
                    # Asegurar que tenga secciones
                    if not requirements.get('sections'):
                        requirements['sections'] = ['introducción', 'desarrollo', 'ejercicios', 'evaluación']
                    
                    # Marcar como completo si tiene la información básica
                    if requirements.get('subject') and requirements.get('learning_objectives'):
                        requirements['is_complete'] = True
                        requirements['missing_info'] = []
                    
                    return requirements
                    
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON: {e}")
                    print(f"JSON string: {json_str}")
                    # No usar fallback manual: retornar None
                    return None
        except Exception as e:
            print(f"Error in extraction: {e}")
            # No usar fallback manual: retornar None
            return None
        
        return None
    
    def extract_requirements_fallback(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Método de respaldo para extraer requisitos automáticamente de la conversación"""
        
        # Analizar toda la conversación para extraer información
        all_content = ""
        for msg in conversation_history:
            all_content += f" {msg.get('content', '')}"
        
        all_content = all_content.lower()
        
        # Extraer información automáticamente de la conversación
        subject = "Matemáticas - Polinomios"  # Por defecto para el caso de polinomios
        course_level = "básico"
        content_type = "ejercicios"
        target_audience = "Estudiantes de 1° de secundaria (12-13 años)"
        additional_requirements = ""
        
        # Detectar materia específica
        if 'polinomios' in all_content:
            subject = "Matemáticas - Polinomios"
        elif 'matemáticas' in all_content or 'math' in all_content:
            subject = "Matemáticas"
        elif 'ciencias' in all_content:
            subject = "Ciencias"
        elif 'historia' in all_content:
            subject = "Historia"
        
        # Detectar nivel educativo
        if '1°' in all_content or 'primero' in all_content or 'primaria' in all_content:
            course_level = "básico"
            target_audience = "Estudiantes de 1° de secundaria (12-13 años)"
        elif '2°' in all_content or 'segundo' in all_content:
            course_level = "básico"
            target_audience = "Estudiantes de 2° de secundaria (13-14 años)"
        elif 'secundaria' in all_content:
            course_level = "básico"
            target_audience = "Estudiantes de secundaria"
        
        # Detectar tipo de contenido
        if 'ejercicios' in all_content or 'ejercicio' in all_content:
            content_type = "ejercicios"
        elif 'lección' in all_content or 'clase' in all_content:
            content_type = "lección"
        elif 'evaluación' in all_content or 'examen' in all_content:
            content_type = "evaluación"
        
        # Detectar requisitos adicionales
        if '10-15' in all_content or '10 a 15' in all_content:
            additional_requirements = "Set de 10-15 ejercicios"
        elif 'paso a paso' in all_content:
            additional_requirements = "Ejercicios paso a paso"
        
        # Crear objetivos específicos para polinomios
        if 'polinomios' in all_content:
            learning_objectives = [
                "Aprender a identificar y clasificar polinomios",
                "Entender las operaciones básicas con polinomios (suma y resta)",
                "Practicar ejercicios de suma y resta de polinomios",
                "Desarrollar habilidades de resolución de problemas algebraicos"
            ]
        else:
            learning_objectives = [
                f"Aprender sobre {subject}",
                f"Entender los conceptos fundamentales de {subject}",
                f"Desarrollar habilidades prácticas en {subject}"
            ]
        
        # Crear requisitos finales con la información extraída automáticamente
        requirements = {
            'subject': subject,
            'course_level': course_level,
            'content_type': content_type,
            'learning_objectives': learning_objectives,
            'sections': ['introducción', 'desarrollo', 'ejercicios', 'evaluación'],
            'target_audience': target_audience,
            'resources': ['imágenes', 'videos', 'ejemplos visuales'],
            'estimated_duration': '45-60 minutos',
            'additional_requirements': additional_requirements,
            'is_complete': True,
            'missing_info': []
        }
        
        return requirements
    
    
    def generate_content(self, requirements: Dict[str, Any]) -> Dict[str, str]:
        """Genera contenido en bloques Gamma basado en los requisitos"""
        
        # Crear prompt de generación optimizado para bloques Gamma
        generation_prompt = f"""Genera contenido educativo en formato de bloques Gamma:

Materia: {requirements.get('subject', 'Tema General')}
Nivel: {requirements.get('course_level', 'básico')}
Objetivos: {', '.join(requirements.get('learning_objectives', ['Aprender el tema']))}

TIPOS DE BLOQUES DISPONIBLES:
- hero: Encabezado principal con título, subtítulo, cuerpo y media
- paragraph: Párrafos de texto
- heading: Encabezados (h1-h6)
- list: Listas ordenadas o no ordenadas
- image: Imágenes con caption
- callout: Notas destacadas (info, warning, success, error)
- quiz: Preguntas de opción múltiple
- code: Bloques de código
- card: Tarjetas de contenido
- button: Botones interactivos
- form: Formularios

ESTRUCTURA REQUERIDA:
1. Bloque hero con título principal
2. Bloque paragraph con introducción
3. Bloques heading para secciones
4. Bloques paragraph para contenido
5. Bloques quiz para ejercicios
6. Bloques callout para información importante
7. Bloques list para objetivos y puntos clave

FORMATO DE RESPUESTA:
Devuelve SOLO un JSON válido con la forma estricta:
{{
  "blocks": [
    {{
      "id": "b1",
      "type": "hero",
      "title": "Título principal",
      "subtitle": "Subtítulo",
      "body": "Descripción breve",
      "media": {{"type": "image", "src": "url_de_imagen"}},
      "props": {{"background": "gradient", "alignment": "center", "padding": "large"}}
    }},
    {{
      "id": "b2",
      "type": "paragraph",
      "content": "Contenido del párrafo...",
      "props": {{"padding": "medium"}}
    }}
  ]
}}

ENFOQUE: Contenido educativo estructurado en bloques editables con Gamma."""
        
        try:
            response = self.generate_content_with_limits([
                {"role": "user", "content": generation_prompt}
            ], temperature=0.25, max_tokens=3000, response_format={"type": "json_object"})
            
            if 'choices' not in response or len(response['choices']) == 0:
                raise Exception("No choices in DeepSeek response")
            
            message = response['choices'][0]['message']
            content = message.get('content')

            # Fallback: algunas APIs pueden devolver function/tool calls con argumentos JSON
            if (not content or (isinstance(content, str) and ('{' not in content and '[' not in content))):
                tool_calls = message.get('tool_calls') or []
                if tool_calls:
                    try:
                        # Tomar el primer tool_call y usar sus argumentos como contenido JSON
                        arguments = tool_calls[0].get('function', {}).get('arguments')
                        if arguments:
                            content = arguments
                    except Exception:
                        pass

            # Extraer bloques Gamma de la respuesta (admite str, dict o list)
            parsed_content = self.parse_generated_content(content)
            blocks = parsed_content.get('blocks') or []

            # Si el resultado es demasiado corto, hacer una segunda generación estricta
            only_hero = len(blocks) == 1 and isinstance(blocks[0], dict) and blocks[0].get('type') == 'hero'
            if len(blocks) < 6 or only_hero:
                strict_prompt = f"""
                Genera contenido educativo COMPLETO en formato Gamma para:
                Materia: {requirements.get('subject', 'Tema General')}
                Nivel: {requirements.get('course_level', 'básico')}
                Tipo: {requirements.get('content_type', 'lección')}
                Objetivos: {', '.join(requirements.get('learning_objectives', ['Aprender el tema']))}

                Responde ÚNICAMENTE un JSON válido con esta forma:
                {{
                  "blocks": [
                    {{"id":"b1","type":"hero","title":"...","subtitle":"...","body":"...","media":{{"type":"image","src":"/api/placeholder/800/400"}},"props":{{"background":"gradient","alignment":"center","padding":"large"}}}},
                    {{"id":"b2","type":"paragraph","content":"Introducción clara al tema","props":{{"padding":"medium"}}}},
                    {{"id":"b3","type":"heading","level":2,"content":"Objetivos de aprendizaje","props":{{"align":"left"}}}},
                    {{"id":"b4","type":"list","listType":"unordered","items":["Objetivo 1","Objetivo 2","Objetivo 3"],"props":{{"padding":"medium"}}}},
                    {{"id":"b5","type":"heading","level":2,"content":"Introducción","props":{{"align":"left"}}}},
                    {{"id":"b6","type":"paragraph","content":"Desarrollo introductorio del tema","props":{{"padding":"medium"}}}},
                    {{"id":"b7","type":"heading","level":2,"content":"Desarrollo","props":{{"align":"left"}}}},
                    {{"id":"b8","type":"paragraph","content":"Explicación con ejemplos","props":{{"padding":"medium"}}}},
                    {{"id":"b9","type":"callout","variant":"info","title":"Nota","content":"Punto clave","props":{{"padding":"medium"}}}},
                    {{"id":"b10","type":"heading","level":2,"content":"Ejercicios","props":{{"align":"left"}}}},
                    {{"id":"b11","type":"quiz","question":"Pregunta 1","options":["A","B","C","D"],"correctAnswer":0,"explanation":"Explicación","points":10,"props":{{"padding":"medium"}}}},
                    {{"id":"b12","type":"paragraph","content":"Cierre del contenido","props":{{"padding":"medium"}}}}
                  ]
                }}

                REQUISITOS ESTRICTOS:
                - Al menos 10-12 bloques
                - Incluir hero, intro, objetivos (lista), 3 secciones con headings y párrafos, ejercicios (quiz), callout
                - Español, claro y educativo
                - Sin texto fuera del JSON
                """
                response2 = self.generate_content_with_limits([
                    {"role": "user", "content": strict_prompt}
                ], temperature=0.2, max_tokens=3500, response_format={"type": "json_object"})

                message2 = response2['choices'][0]['message']
                content2 = message2.get('content')
                if (not content2 or (isinstance(content2, str) and ('{' not in content2 and '[' not in content2))):
                    tool_calls2 = message2.get('tool_calls') or []
                    if tool_calls2:
                        try:
                            arguments2 = tool_calls2[0].get('function', {}).get('arguments')
                            if arguments2:
                                content2 = arguments2
                        except Exception:
                            pass
                parsed_content = self.parse_generated_content(content2)

            return parsed_content
            
        except Exception:
            # Fallback garantizado: construir bloques mínimos válidos con los requisitos
            subject = requirements.get('subject', 'Contenido Educativo')
            objectives = requirements.get('learning_objectives') or [
                f"Comprender los conceptos básicos de {subject}",
                f"Aplicar {subject} en ejemplos prácticos"
            ]
            blocks = [
                {
                    'id': 'b1',
                    'type': 'hero',
                    'title': subject,
                    'subtitle': requirements.get('content_type', 'lección').capitalize(),
                    'body': requirements.get('additional_requirements', '') or 'Contenido generado automáticamente (modo respaldo).',
                    'media': {'type': 'image', 'src': '/api/placeholder/800/400', 'alt': subject},
                    'props': {'background': 'gradient', 'alignment': 'center', 'padding': 'large'}
                },
                {
                    'id': 'b2',
                    'type': 'heading',
                    'level': 2,
                    'content': 'Objetivos de aprendizaje',
                    'props': {'align': 'left'}
                },
                {
                    'id': 'b3',
                    'type': 'list',
                    'listType': 'unordered',
                    'items': objectives,
                    'props': {'padding': 'medium'}
                },
                {
                    'id': 'b4',
                    'type': 'paragraph',
                    'content': f"Nivel: {requirements.get('course_level', 'intermedio')} — Idioma: {requirements.get('language', 'es')}",
                    'props': {'padding': 'medium'}
                }
            ]
            blocks = self.ensure_minimum_gamma_blocks(blocks, requirements)
            return {
                'blocks': blocks,
                'document': {
                    'title': 'Contenido Educativo Generado (Respaldo)',
                    'description': f"Generado sin conexión completa a IA — {subject}",
                    'blocks': blocks
                },
                'fallback': True
            }

    def ensure_minimum_gamma_blocks(self, blocks: List[Dict[str, Any]], requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Asegura una estructura mínima útil si el modelo devolvió muy poco contenido."""
        def next_id(n: int) -> str:
            return f"b{n+1}"

        # Construir índice por tipo
        types = [b.get('type') for b in blocks if isinstance(b, dict)]
        idx = len(blocks)

        subject = requirements.get('subject', 'Contenido Educativo')
        objectives = requirements.get('learning_objectives') or [
            f"Comprender los conceptos básicos de {subject}",
            f"Aplicar {subject} en ejemplos prácticos"
        ]

        # Garantizar hero al inicio
        if 'hero' not in types:
            hero_block = {
                'id': next_id(idx),
                'type': 'hero',
                'title': subject,
                'subtitle': requirements.get('content_type', 'lección').capitalize(),
                'body': requirements.get('additional_requirements', '') or 'Introducción al contenido.',
                'media': {'type': 'image', 'src': '/api/placeholder/800/400', 'alt': subject},
                'props': {'background': 'gradient', 'alignment': 'center', 'padding': 'large'}
            }
            blocks.insert(0, hero_block)
            idx += 1
            types.insert(0, 'hero')

        # Introducción (paragraph) después del hero si no existe
        if not any(t == 'paragraph' for t in types):
            blocks.append({
                'id': next_id(idx),
                'type': 'paragraph',
                'content': f"Este recurso aborda {subject} con ejemplos y ejercicios.",
                'props': {'padding': 'medium'}
            })
            idx += 1
            types.append('paragraph')

        # Lista de objetivos si no está
        has_objectives_list = any(b.get('type') == 'list' and any('objetivos' in (b.get('title','').lower() + b.get('content','').lower()) for _k in [0]) for b in blocks)
        if not has_objectives_list:
            # Añadir heading + list
            blocks.append({
                'id': next_id(idx),
                'type': 'heading',
                'level': 2,
                'content': 'Objetivos de aprendizaje',
                'props': {'align': 'left'}
            })
            idx += 1
            blocks.append({
                'id': next_id(idx),
                'type': 'list',
                'listType': 'unordered',
                'items': objectives,
                'props': {'padding': 'medium'}
            })
            idx += 1

        # Secciones principales si falta estructura
        need_sections = not any(b.get('type') == 'heading' for b in blocks)
        if need_sections:
            for title in ['Introducción', 'Desarrollo', 'Ejercicios']:
                blocks.append({
                    'id': next_id(idx),
                    'type': 'heading',
                    'level': 2,
                    'content': title,
                    'props': {'align': 'left'}
                })
                idx += 1
                para = 'Contenido de la sección.' if title != 'Ejercicios' else 'Ejercicios sugeridos: resuelve 3 problemas relacionados.'
                blocks.append({
                    'id': next_id(idx),
                    'type': 'paragraph',
                    'content': para,
                    'props': {'padding': 'medium'}
                })
                idx += 1

        return blocks
    
    def generate_content_with_limits(self, messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 2500, response_format: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Genera contenido con límites configurables para respuesta controlada"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Preparar mensajes
        chat_messages = [
            {"role": "system", "content": "Eres un experto en generar contenido educativo en formato de bloques Gamma. Genera bloques estructurados y editables para el editor Gamma, incluye elementos interactivos como quiz, callout, y formularios. Enfócate en contenido educativo bien estructurado y funcional."}
        ]
        
        # Agregar mensajes del usuario
        for msg in messages:
            chat_messages.append({
                "role": msg.get('role', 'user'),
                "content": msg.get('content', '')
            })
        
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            # Intentar forzar salida JSON (si la API lo soporta)
            "response_format": response_format if response_format is not None else {"type": "json_object"}
        }
        
        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=90
                )
                if response.status_code != 200:
                    raise Exception(f"API Error {response.status_code}: {response.text}")
                return response.json()
            except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout):
                last_error = Exception("Timeout: La API de DeepSeek tardó demasiado en responder")
            except requests.exceptions.ConnectionError:
                last_error = Exception("Error de conexión: No se pudo conectar con la API de DeepSeek")
            except requests.exceptions.RequestException as e:
                last_error = Exception(f"Error en DeepSeek API: {str(e)}")
            except Exception as e:
                last_error = Exception(f"Error inesperado: {str(e)}")
            # Backoff antes del siguiente intento
            time.sleep(2 ** attempt)
        # Si llegó aquí, fallaron todos los intentos
        assert last_error is not None
        raise last_error
    
    
    
    def parse_generated_content(self, content: Any) -> Dict[str, Any]:
        """Parsea el contenido generado para extraer bloques Gamma con tolerancia a distintos formatos.

        Acepta:
        - str: Contenido con o sin code fences
        - dict: Objeto ya parseado que puede contener "blocks"
        - list: Lista de bloques directamente
        """
        result = {
            'blocks': [],
            'document': {
                'title': '',
                'description': '',
                'blocks': []
            }
        }

        # Caso 0: si ya es dict/list, usar directamente
        if isinstance(content, list):
            blocks = content
        elif isinstance(content, dict):
            blocks = content.get('blocks') or content.get('document', {}).get('blocks') or []
            if not blocks and 'type' in content:
                # Puede ser un único bloque suelto
                blocks = [content]
        else:
            # Asegurar que sea string para parseo por regex
            if not isinstance(content, str):
                raise ValueError('AI did not return valid JSON blocks')

            def _sanitize_and_parse(raw_text: str) -> Any:
                # Primer intento: JSON estándar
                try:
                    return json.loads(raw_text)
                except json.JSONDecodeError:
                    pass

                # Segundo intento: limpiar BOM y comillas tipográficas
                sanitized = raw_text.strip().replace('\uFEFF', '')
                sanitized = sanitized.replace('“', '"').replace('”', '"').replace('‟', '"')
                sanitized = sanitized.replace('‘', "'").replace('’', "'")

                # Quitar comas colgantes antes de } o ]
                sanitized = re.sub(r",\s*(\}|\])", r"\1", sanitized)

                # Intento JSON otra vez tras saneo básico
                try:
                    return json.loads(sanitized)
                except json.JSONDecodeError:
                    pass

                # Tercer intento: convertir a literal de Python tolerante
                py_like = sanitized
                # Reemplazar true/false/null por True/False/None cuando estén fuera de comillas
                py_like = re.sub(r'(?<=[:\s\[,])true(?=[\s,\]}])', 'True', py_like, flags=re.IGNORECASE)
                py_like = re.sub(r'(?<=[:\s\[,])false(?=[\s,\]}])', 'False', py_like, flags=re.IGNORECASE)
                py_like = re.sub(r'(?<=[:\s\[,])null(?=[\s,\]}])', 'None', py_like, flags=re.IGNORECASE)
                # Si hay claves sin comillas, intentar comillarlas de forma conservadora (clave simple alfanumérica)
                py_like = re.sub(r'([\{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:) ', r'\1"\2"\3 ', py_like)

                try:
                    return ast.literal_eval(py_like)
                except Exception:
                    # Último intento: eliminar comentarios tipo // ... o /* ... */ si los hubiera
                    without_line_comments = re.sub(r"//.*", "", py_like)
                    without_block_comments = re.sub(r"/\*[\s\S]*?\*/", "", without_line_comments)
                    # Eliminar comas colgantes de nuevo tras quitar comentarios
                    without_block_comments = re.sub(r",\s*(\}|\])", r"\1", without_block_comments)
                    try:
                        return ast.literal_eval(without_block_comments)
                    except Exception:
                        # Propagar para manejo superior
                        raise

            def _find_json_candidates(text: str) -> List[str]:
                candidates: List[str] = []
                # 1) Code fences
                for m in re.finditer(r"```(?:json)?\s*([\{\[][\s\S]*?)\s*```", text, re.IGNORECASE):
                    candidates.append(m.group(1))
                # 2) Balanced scan from each '{' or '[' occurrence (cap to 20 starts)
                starts: List[int] = [i for i, ch in enumerate(text) if ch in '{['][:20]
                for start_idx in starts:
                    brace_depth = 0
                    bracket_depth = 0
                    in_string = False
                    string_quote = ''
                    escape = False
                    for i in range(start_idx, len(text)):
                        ch = text[i]
                        if in_string:
                            if escape:
                                escape = False
                            elif ch == '\\':
                                escape = True
                            elif ch == string_quote:
                                in_string = False
                        else:
                            if ch in ('"', "'"):
                                in_string = True
                                string_quote = ch
                            elif ch == '{':
                                brace_depth += 1
                            elif ch == '}':
                                if brace_depth > 0:
                                    brace_depth -= 1
                            elif ch == '[':
                                bracket_depth += 1
                            elif ch == ']':
                                if bracket_depth > 0:
                                    bracket_depth -= 1
                            if brace_depth == 0 and bracket_depth == 0 and i > start_idx:
                                candidates.append(text[start_idx:i+1])
                                break
                # Dedup preserving order
                seen = set()
                unique: List[str] = []
                for c in candidates:
                    if c not in seen:
                        unique.append(c)
                        seen.add(c)
                return unique

            candidates = _find_json_candidates(content)
            if not candidates:
                raise ValueError('AI did not return valid JSON blocks')

            # Priorizar los que contengan "\"blocks\""
            def _score(seg: str) -> tuple:
                has_blocks = '"blocks"' in seg or "'blocks'" in seg
                return (1 if has_blocks else 0, len(seg))

            candidates.sort(key=_score, reverse=True)

            data: Any = None
            last_error: Optional[Exception] = None
            for seg in candidates:
                try:
                    data = _sanitize_and_parse(seg)
                    break
                except Exception as e:
                    last_error = e
                    continue

            if data is None:
                raise last_error if last_error else ValueError('AI did not return valid JSON blocks')

            # Extraer bloques de forma robusta desde múltiples formas
            def _looks_like_block(obj: Any) -> bool:
                return isinstance(obj, dict) and isinstance(obj.get('type'), str)

            def _extract_blocks_any(value: Any) -> Optional[List[Any]]:
                # Caso lista directa
                if isinstance(value, list):
                    if all(isinstance(x, dict) for x in value) and any(_looks_like_block(x) for x in value):
                        return value
                    # Si la lista contiene un único bloque dict
                    if len(value) == 1 and isinstance(value[0], dict):
                        return value
                # Caso dict con claves habituales
                if isinstance(value, dict):
                    # Claves comunes
                    for key in ['blocks', 'items']:
                        v = value.get(key)
                        if isinstance(v, list):
                            if all(isinstance(x, dict) for x in v):
                                return v
                        if isinstance(v, dict):
                            # Mapa de id->bloque
                            mapped_list = list(v.values())
                            if all(isinstance(x, dict) for x in mapped_list):
                                return mapped_list
                    # Rutas anidadas comunes
                    for parent in ['document', 'data', 'gamma', 'payload', 'result']:
                        pv = value.get(parent)
                        if isinstance(pv, dict):
                            for key in ['blocks', 'items']:
                                v = pv.get(key)
                                if isinstance(v, list) and all(isinstance(x, dict) for x in v):
                                    return v
                                if isinstance(v, dict):
                                    mapped_list = list(v.values())
                                    if all(isinstance(x, dict) for x in mapped_list):
                                        return mapped_list
                    # Búsqueda recursiva en subvalores
                    for sub in value.values():
                        found = _extract_blocks_any(sub)
                        if found is not None:
                            return found
                return None

            blocks = _extract_blocks_any(data) if not isinstance(data, list) else data

        if not isinstance(blocks, list):
            # Intentar coerción a bloques válidos desde data crudo
            def _make_paragraph_block(text: str, idx: int) -> Dict[str, Any]:
                return {
                    'id': f"b{idx+1}",
                    'type': 'paragraph',
                    'content': text,
                    'props': {'padding': 'medium'}
                }

            def _make_hero_block(obj: Dict[str, Any]) -> Dict[str, Any]:
                return {
                    'id': 'b1',
                    'type': 'hero',
                    'title': obj.get('title') or obj.get('heading') or 'Contenido generado',
                    'subtitle': obj.get('subtitle') or '',
                    'body': obj.get('body') or obj.get('description') or '',
                    'media': obj.get('media') or {'type': 'image', 'src': '/api/placeholder/800/400', 'alt': 'Imagen'},
                    'props': obj.get('props') or {'background': 'gradient', 'alignment': 'center', 'padding': 'large'}
                }

            def _coerce_to_blocks(value: Any) -> List[Dict[str, Any]]:
                # Lista de strings → párrafos
                if isinstance(value, list) and all(isinstance(x, str) for x in value):
                    return [_make_paragraph_block(x, i) for i, x in enumerate(value)]
                # Lista de dicts sin 'type' → intentar inferir
                if isinstance(value, list) and all(isinstance(x, dict) for x in value):
                    coerced: List[Dict[str, Any]] = []
                    for i, obj in enumerate(value):
                        if isinstance(obj.get('type'), str):
                            coerced.append(obj)
                        elif any(k in obj for k in ['title', 'heading', 'body', 'subtitle']):
                            if i == 0:
                                coerced.append(_make_hero_block(obj))
                            else:
                                text = obj.get('content') or obj.get('body') or obj.get('description') or json.dumps(obj, ensure_ascii=False)
                                coerced.append(_make_paragraph_block(text, i))
                        else:
                            coerced.append(_make_paragraph_block(json.dumps(obj, ensure_ascii=False), i))
                    return coerced
                # Dict que parece un bloque único
                if isinstance(value, dict):
                    if isinstance(value.get('type'), str):
                        return [value]
                    if any(k in value for k in ['title', 'heading', 'body', 'subtitle']):
                        return [_make_hero_block(value)]
                    if isinstance(value.get('content'), str):
                        return [_make_paragraph_block(value['content'], 0)]
                    # Fallback: todo el dict como texto
                    return [_make_paragraph_block(json.dumps(value, ensure_ascii=False), 0)]
                # Otro tipo: representar como párrafo texto
                return [_make_paragraph_block(str(value), 0)]

            blocks = _coerce_to_blocks(blocks if blocks is not None else data)

        result['blocks'] = blocks
        result['document']['blocks'] = blocks
        result['document']['title'] = 'Contenido Educativo Generado'
        result['document']['description'] = 'Contenido educativo generado con IA'
        return result
    
    
 