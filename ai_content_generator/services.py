import requests
import json
import re
from typing import List, Dict, Any, Optional
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
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error en DeepSeek API: {str(e)}")
    
    def get_collection_system_prompt(self) -> str:
        """Obtiene el prompt del sistema para recolección de información"""
        return """
        Eres un asistente especializado en recolección de información para crear contenido educativo interactivo SCORM con GrapesJS.
        
        FORMATO FIJO: El contenido siempre se generará en formato SCORM para GrapesJS. NO preguntes sobre formatos.
        
        REGLAS IMPORTANTES:
        1. NO hagas preguntas obvias o redundantes
        2. Analiza el contexto antes de preguntar
        3. Si el usuario ya mencionó información, NO la preguntes de nuevo
        4. Sé inteligente y deduce información cuando sea posible
        5. Haz solo preguntas esenciales que realmente necesites
        6. NUNCA preguntes sobre formato - siempre será SCORM
        
        INFORMACIÓN A RECOLECTAR (solo si no está clara):
        - Nivel del curso (solo si no es obvio del contexto)
        - Materia o tema específico (solo si no está claro)
        - Tipo de contenido educativo (lección, ejercicio, evaluación, etc.)
        - Objetivos de aprendizaje específicos
        - Duración estimada del contenido
        - Secciones necesarias (solo si no son obvias)
        - Recursos necesarios (solo si son específicos)
        
        EJEMPLOS DE PREGUNTAS INTELIGENTES:
        ✅ "¿Qué objetivos específicos quieres que logren los estudiantes?"
        ✅ "¿Qué tipo de ejercicios prefieres incluir?"
        ✅ "¿Qué secciones específicas necesitas en el contenido?"
        ❌ "¿Para qué nivel educativo va dirigido?" (si ya mencionó "secundaria")
        ❌ "¿Qué formato prefieres?" (NUNCA preguntes esto - siempre es SCORM)
        ❌ "¿Quieres PDF, tarjetas o contenido web?" (NUNCA preguntes esto)
        
        ESTRATEGIA:
        1. Analiza lo que el usuario ya dijo
        2. Identifica qué información falta realmente
        3. Haz solo 1-2 preguntas esenciales por mensaje
        4. Si tienes suficiente información, confirma y procede
        5. Recuerda: el contenido será SCORM para GrapesJS
        
        CUANDO TENGAS TODA LA INFORMACIÓN NECESARIA:
        - Di exactamente: "¡Perfecto! Está listo tu contenido para ser generado"
        - Resumen brevemente lo que vas a crear
        - Agrega al final: "Usa el botón 'Extraer Requisitos' para proceder con la generación del contenido SCORM."
        - NO hagas más preguntas después de esto
        
        Mantén un tono amigable y profesional. Responde siempre en español.
        """
    
    
    def extract_requirements(self, conversation_history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """Extrae los requisitos de la conversación usando DeepSeek"""
        
        # Verificar si el asistente dijo que está listo
        last_assistant_message = None
        for msg in reversed(conversation_history):
            if msg.get('role') == 'assistant':
                last_assistant_message = msg.get('content', '').lower()
                break
        
        # Si el asistente no dijo que está listo, no extraer requisitos
        if not last_assistant_message or "está listo tu contenido para ser generado" not in last_assistant_message:
            return None
        
        extraction_prompt = """
        Analiza la siguiente conversación y extrae los requisitos del usuario para crear contenido educativo interactivo.
        
        INSTRUCCIONES:
        1. Extrae SOLO la información que está explícitamente mencionada
        2. NO inventes información que no esté en la conversación
        3. Si falta información importante, marca "is_complete": false
        4. Si hay suficiente información para generar contenido, marca "is_complete": true
        5. Para "missing_info", incluye solo información realmente necesaria
        
        Devuelve SOLO un JSON válido con la siguiente estructura:
        {
            "course_level": "básico/intermedio/avanzado" (solo si se menciona),
            "subject": "materia o tema específico",
            "content_type": "tipo de contenido educativo",
            "learning_objectives": ["objetivo1", "objetivo2"],
            "sections": ["introducción", "desarrollo", "ejercicios", "evaluación"],
            "target_audience": "público objetivo" (solo si se menciona),
            "resources": ["imágenes", "videos", "audios"] (solo si se mencionan),
            "responsive": true/false (por defecto true),
            "is_complete": true/false,
            "missing_info": ["información realmente faltante y necesaria"]
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
                return json.loads(json_match.group())
        except Exception as e:
            pass
        
        return None
    
    
    def generate_content(self, requirements: Dict[str, Any]) -> Dict[str, str]:
        """Genera contenido HTML/CSS/JS basado en los requisitos"""
        
        # Crear prompt de generación optimizado para contenido compatible con GrapesJS
        generation_prompt = f"""Genera contenido educativo SCORM COMPATIBLE CON GRAPESJS:

Materia: {requirements.get('subject', 'Tema General')}
Nivel: {requirements.get('course_level', 'básico')}
Objetivos: {', '.join(requirements.get('learning_objectives', ['Aprender el tema']))}

REQUISITOS PARA GRAPESJS:
- HTML con data-gjs-type en TODOS los elementos editables
- Elementos de texto editables con data-gjs-type="text"
- Botones interactivos con data-gjs-type="button"
- Formularios con data-gjs-type="form"
- Contenedores con data-gjs-type="container"
- Imágenes con data-gjs-type="image"
- Tablas con data-gjs-type="table"
- Listas con data-gjs-type="list"

ESTRUCTURA REQUERIDA:
1. Header con título editable
2. Introducción con texto editable
3. Secciones de contenido con elementos editables
4. Ejercicios interactivos con botones y formularios
5. Resumen con elementos editables

ELEMENTOS INTERACTIVOS NECESARIOS:
- Botones para ejercicios
- Campos de texto para respuestas
- Checkboxes para opciones múltiples
- Tablas editables para ejercicios
- Áreas de texto para respuestas largas

Formato de respuesta:
```html
[HTML con data-gjs-type en TODOS los elementos para GrapesJS]
```
```css
[CSS responsive y profesional]
```
```javascript
// JavaScript básico para interactividad
```

ENFOQUE: Contenido educativo EDITABLE con GrapesJS, elementos interactivos y estructura clara."""
        
        try:
            response = self.generate_content_with_limits([
                {"role": "user", "content": generation_prompt}
            ])
            
            if 'choices' not in response or len(response['choices']) == 0:
                raise Exception("No choices in DeepSeek response")
            
            content = response['choices'][0]['message']['content']
            
            # Extraer HTML, CSS y JS de la respuesta
            parsed_content = self.parse_generated_content(content)
            
            # TEMPORAL: Usar fallback para probar compatibilidad con GrapesJS
            return self.generate_fallback_content(requirements)
            
        except Exception as e:
            return self.generate_fallback_content(requirements)
    
    def generate_content_with_limits(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Genera contenido con límites estrictos de tokens para respuesta rápida"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Preparar mensajes
        chat_messages = [
            {"role": "system", "content": "Eres un experto en generar contenido educativo SCORM COMPATIBLE CON GRAPESJS. Genera HTML con data-gjs-type en todos los elementos editables, incluye elementos interactivos como botones, formularios y campos de texto. Enfócate en contenido educativo editable y funcional para GrapesJS."}
        ]
        
        # Agregar mensajes del usuario
        for msg in messages:
            chat_messages.append({
                "role": msg.get('role', 'user'),
                "content": msg.get('content', '')
            })
        
        payload = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": 0.3,  # Menor temperatura para respuestas más determinísticas
            "max_tokens": 1500,  # Reducido para respuesta más rápida
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions", 
                headers=headers, 
                json=payload, 
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"API Error {response.status_code}: {response.text}")
            
            response_data = response.json()
            return response_data
        except requests.exceptions.Timeout:
            raise Exception("Timeout: La API de DeepSeek tardó demasiado en responder")
        except requests.exceptions.ConnectionError as e:
            raise Exception("Error de conexión: No se pudo conectar con la API de DeepSeek")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error en DeepSeek API: {str(e)}")
        except Exception as e:
            raise Exception(f"Error inesperado: {str(e)}")
    
    
    
    def parse_generated_content(self, content: str) -> Dict[str, str]:
        """Parsea el contenido generado para extraer HTML, CSS y JS"""
        result = {
            'html': '',
            'css': '',
            'js': ''
        }
        
        # Parse content
        
        # Extraer HTML - múltiples patrones
        html_patterns = [
            r'```html\s*(.*?)\s*```',
            r'<div class="scorm-content"',
            r'<html',
            r'<body'
        ]
        
        for pattern in html_patterns:
            if pattern.startswith('```'):
                html_match = re.search(pattern, content, re.DOTALL)
                if html_match:
                    result['html'] = html_match.group(1).strip()
                    break
            else:
                # Buscar desde el inicio del HTML
                html_start = content.find('<div class="scorm-content"')
                if html_start == -1:
                    html_start = content.find('<html')
                if html_start == -1:
                    html_start = content.find('<body')
                
                if html_start != -1:
                    # Buscar el final del HTML (antes del CSS o JS)
                    html_end = content.find('```css', html_start)
                    if html_end == -1:
                        html_end = content.find('```javascript', html_start)
                    if html_end == -1:
                        html_end = content.find('</body>', html_start)
                    if html_end == -1:
                        html_end = content.find('</html>', html_start)
                    if html_end == -1:
                        html_end = len(content)
                    
                    result['html'] = content[html_start:html_end].strip()
                    break
        
        # Extraer CSS - múltiples patrones
        css_patterns = [
            r'```css\s*(.*?)\s*```',
            r'\.container\s*\{',
            r'<style>'
        ]
        
        for pattern in css_patterns:
            if pattern.startswith('```'):
                css_match = re.search(pattern, content, re.DOTALL)
                if css_match:
                    result['css'] = css_match.group(1).strip()
                    break
            else:
                css_start = content.find('.container {')
                if css_start == -1:
                    css_start = content.find('<style>')
                
                if css_start != -1:
                    # Buscar el final del CSS
                    css_end = content.find('```javascript', css_start)
                    if css_end == -1:
                        css_end = content.find('```', css_start)
                    if css_end == -1:
                        css_end = content.find('</style>', css_start)
                    if css_end == -1:
                        # Si no encuentra el final, tomar hasta el final del contenido
                        css_end = len(content)
                    
                    result['css'] = content[css_start:css_end].strip()
                    break
        
        # Extraer JavaScript - múltiples patrones
        js_patterns = [
            r'```javascript\s*(.*?)\s*```',
            r'<script>',
            r'function SCORMContent',
            r'addEventListener'
        ]
        
        for pattern in js_patterns:
            if pattern.startswith('```'):
                js_match = re.search(pattern, content, re.DOTALL)
                if js_match:
                    result['js'] = js_match.group(1).strip()
                    break
            else:
                js_start = content.find('<script>')
                if js_start == -1:
                    js_start = content.find('function SCORMContent')
                if js_start == -1:
                    js_start = content.find('addEventListener')
                
                if js_start != -1:
                    js_end = content.find('</script>', js_start)
                    if js_end == -1:
                        # Si no encuentra </script>, tomar hasta el final del contenido
                        js_end = len(content)
                    
                    result['js'] = content[js_start:js_end].strip()
                    break
        
        # Si no se encontró CSS o JS, generar fallback básico
        if not result['css']:
            result['css'] = """
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

.header-section {
  text-align: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 30px;
  border-radius: 10px;
  margin-bottom: 30px;
}

.theory-section, .exercise-section, .interactive-section, .quiz-section {
  background: #f8f9fa;
  padding: 25px;
  margin-bottom: 25px;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.exercise-form, .quiz-form {
  margin-top: 20px;
}

.input, .answer-input, .poly1-input, .poly2-input {
  width: 100%;
  padding: 10px;
  margin: 10px 0;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.button, .check-btn, .op-btn, .submit-quiz {
  background: #667eea;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin: 5px;
}

.button:hover, .check-btn:hover, .op-btn:hover, .submit-quiz:hover {
  background: #5a6fd8;
}

.feedback {
  margin-top: 10px;
  padding: 10px;
  border-radius: 4px;
}

.feedback.correct {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.feedback.incorrect {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}
"""
        
        if not result['js']:
            result['js'] = """
// Funcionalidad básica para ejercicios (compatible con iframe)
document.addEventListener('DOMContentLoaded', function() {
  console.log('Contenido SCORM cargado');
  
  // Función para guardar respuestas (sin localStorage)
  window.saveAnswer = function(exerciseId, button) {
    const textarea = button.closest('.exercise-item').querySelector('textarea');
    const answer = textarea.value;
    
    if (answer.trim()) {
      // Simular guardado sin localStorage
      button.textContent = '✓ Guardado';
      button.style.background = '#28a745';
      
      // Mostrar feedback
      const feedback = button.parentElement.querySelector('.feedback');
      if (feedback) {
        feedback.style.display = 'block';
        feedback.textContent = '¡Respuesta guardada!';
        feedback.className = 'feedback correct';
      }
      
      setTimeout(() => {
        button.textContent = 'Guardar Respuesta';
        button.style.background = '#007bff';
      }, 2000);
    } else {
      alert('Por favor escribe una respuesta antes de guardar');
    }
  };
  
  // Manejar botones de verificación
  const checkButtons = document.querySelectorAll('.check-btn');
  checkButtons.forEach(button => {
    button.addEventListener('click', function() {
      const input = this.parentElement.querySelector('input[type="text"]');
      if (input && input.value.trim()) {
        // Simular verificación
        const feedback = this.parentElement.querySelector('.feedback');
        if (feedback) {
          feedback.style.display = 'block';
          feedback.textContent = '¡Respuesta enviada! (Verificación simulada)';
          feedback.className = 'feedback correct';
        }
      }
    });
  });
  
  // Manejar botones de operaciones
  const opButtons = document.querySelectorAll('.op-btn');
  opButtons.forEach(button => {
    button.addEventListener('click', function() {
      const operation = this.getAttribute('data-operation');
      const poly1 = document.querySelector('.poly1-input')?.value || '';
      const poly2 = document.querySelector('.poly2-input')?.value || '';
      
      if (poly1 && poly2) {
        const resultDisplay = document.querySelector('.result-text');
        if (resultDisplay) {
          resultDisplay.textContent = `Operación ${operation}: ${poly1} ${operation} ${poly2}`;
        }
      }
    });
  });
  
  // Manejar envío de quiz
  const submitQuiz = document.querySelector('.submit-quiz');
  if (submitQuiz) {
    submitQuiz.addEventListener('click', function() {
      alert('¡Quiz enviado! (Funcionalidad simulada)');
    });
  }
});
"""
        
        # Return parsed content
        return result
    
    def generate_fallback_content(self, requirements: Dict[str, Any]) -> Dict[str, str]:
        """Genera contenido SCORM SIMPLE para GrapesJS como fallback cuando la API falla"""
        subject = requirements.get('subject', 'Tema General')
        course_level = requirements.get('course_level', 'básico')
        sections = requirements.get('sections', ['introducción', 'desarrollo', 'ejercicios'])
        learning_objectives = requirements.get('learning_objectives', ['Aprender el tema'])
        
        # Generar HTML SCORM compatible con GrapesJS
        html_content = f"""
        <div class="scorm-content" data-gjs-type="container">
            <header class="scorm-header" data-gjs-type="container">
                <h1 class="scorm-title" data-gjs-type="text">{subject}</h1>
                <div class="scorm-meta" data-gjs-type="container">
                    <span class="scorm-level" data-gjs-type="text">Nivel: {course_level}</span>
                </div>
            </header>
            
            <section class="scorm-objectives" data-gjs-type="container">
                <h2 data-gjs-type="text">Objetivos de Aprendizaje</h2>
                <div class="objectives-content" data-gjs-type="container">
                    <p data-gjs-type="text">Al finalizar esta lección, serás capaz de:</p>
                    <ul class="objectives-list" data-gjs-type="list">
                        <li data-gjs-type="text">Comprender los conceptos fundamentales de {subject}</li>
                        <li data-gjs-type="text">Aplicar los conocimientos en ejercicios prácticos</li>
                        <li data-gjs-type="text">Evaluar tu comprensión mediante ejercicios</li>
                    </ul>
                </div>
            </section>
            
            <main class="scorm-content-body" data-gjs-type="container">
                <section class="scorm-section" data-gjs-type="container" data-section="introduction">
                    <h2 class="section-title" data-gjs-type="text">Introducción</h2>
                    <div class="section-content" data-gjs-type="container">
                        <p data-gjs-type="text">Bienvenido a esta lección sobre <strong>{subject}</strong>. Este contenido está diseñado para ayudarte a comprender los conceptos fundamentales de manera clara y estructurada.</p>
                        
                        <div class="text-content" data-gjs-type="container">
                            <h3 data-gjs-type="text">¿Qué es {subject}?</h3>
                            <p data-gjs-type="text">{subject} es un tema fundamental que forma parte del currículo educativo. En esta lección exploraremos sus aspectos más importantes de manera progresiva y fácil de entender.</p>
                            
                            <h3 data-gjs-type="text">Importancia del tema</h3>
                            <p data-gjs-type="text">Comprender {subject} es esencial porque:</p>
                            <ul data-gjs-type="list">
                                <li data-gjs-type="text">Proporciona conocimientos fundamentales para el desarrollo académico</li>
                                <li data-gjs-type="text">Desarrolla habilidades de pensamiento crítico</li>
                                <li data-gjs-type="text">Prepara para temas más avanzados</li>
                                <li data-gjs-type="text">Tiene aplicaciones prácticas en la vida diaria</li>
                            </ul>
                        </div>
                    </div>
                </section>
                
                <section class="scorm-section" data-gjs-type="scorm-section" data-section="development">
                    <h2 class="section-title" data-gjs-type="section-title">Desarrollo del Tema</h2>
                    <div class="section-content" data-gjs-type="section-content">
                        <div class="text-content" data-gjs-type="text-content">
                            <h3>Conceptos Fundamentales</h3>
                            <p>En esta sección exploraremos los aspectos más importantes de <strong>{subject}</strong> de manera clara y estructurada.</p>
                            
                            <h4>1. Definición y Características</h4>
                            <p>Para comprender {subject}, es importante conocer su definición y las características que lo distinguen. Este conocimiento forma la base para todo el aprendizaje posterior.</p>
                            
                            <h4>2. Principios Básicos</h4>
                            <p>Los principios básicos de {subject} nos ayudan a entender cómo funciona y por qué es importante. Estos principios son fundamentales para aplicar el conocimiento en situaciones prácticas.</p>
                            
                            <h4>3. Aplicaciones Prácticas</h4>
                            <p>Conocer las aplicaciones prácticas de {subject} nos permite ver su relevancia en la vida real y comprender mejor su utilidad en diferentes contextos.</p>
                        </div>
                    </div>
                </section>
                
                <section class="scorm-section" data-gjs-type="container" data-section="practice">
                    <h2 class="section-title" data-gjs-type="text">Ejercicios de Práctica</h2>
                    <div class="section-content" data-gjs-type="container">
                        <div class="exercise-container" data-gjs-type="container">
                            <div class="exercise-item" data-gjs-type="container">
                                <h3 data-gjs-type="text">Ejercicio 1: Comprensión</h3>
                                <p data-gjs-type="text">Explica con tus propias palabras qué es {subject} y por qué es importante:</p>
                                <textarea class="scorm-textarea" data-gjs-type="form" placeholder="Escribe tu respuesta aquí..." rows="4"></textarea>
                                <button class="scorm-button" data-gjs-type="button" onclick="saveAnswer('exercise1', this)">Guardar Respuesta</button>
                            </div>
                            
                            <div class="exercise-item" data-gjs-type="container">
                                <h3 data-gjs-type="text">Ejercicio 2: Reflexión</h3>
                                <p data-gjs-type="text">Describe una situación real donde aplicarías los conocimientos de {subject}:</p>
                                <textarea class="scorm-textarea" data-gjs-type="form" placeholder="Describe tu situación..." rows="4"></textarea>
                                <button class="scorm-button" data-gjs-type="button" onclick="saveAnswer('exercise2', this)">Guardar Respuesta</button>
                            </div>
                            
                            <div class="exercise-item" data-gjs-type="container">
                                <h3 data-gjs-type="text">Ejercicio 3: Síntesis</h3>
                                <p data-gjs-type="text">Resume los puntos más importantes que has aprendido sobre {subject}:</p>
                                <textarea class="scorm-textarea" data-gjs-type="form" placeholder="Escribe tu resumen..." rows="4"></textarea>
                                <button class="scorm-button" data-gjs-type="button" onclick="saveAnswer('exercise3', this)">Guardar Respuesta</button>
                            </div>
                        </div>
                    </div>
                </section>
                
                <section class="scorm-section" data-gjs-type="container" data-section="evaluation">
                    <h2 class="section-title" data-gjs-type="text">Resumen y Conclusiones</h2>
                    <div class="section-content" data-gjs-type="container">
                        <div class="text-content" data-gjs-type="container">
                            <h3 data-gjs-type="text">Lo que has aprendido</h3>
                            <p data-gjs-type="text">En esta lección sobre {subject}, has explorado los conceptos fundamentales y has tenido la oportunidad de reflexionar sobre su importancia y aplicaciones.</p>
                            
                            <h3 data-gjs-type="text">Puntos clave a recordar</h3>
                            <ul data-gjs-type="list">
                                <li data-gjs-type="text">La comprensión de {subject} es fundamental para el desarrollo académico</li>
                                <li data-gjs-type="text">Los conceptos aprendidos tienen aplicaciones prácticas importantes</li>
                                <li data-gjs-type="text">La reflexión personal ayuda a consolidar el aprendizaje</li>
                                <li data-gjs-type="text">El conocimiento adquirido prepara para temas más avanzados</li>
                            </ul>
                            
                            <h3 data-gjs-type="text">Próximos pasos</h3>
                            <p data-gjs-type="text">Te recomendamos continuar explorando {subject} a través de ejercicios adicionales y aplicando los conocimientos en situaciones reales.</p>
                        </div>
                    </div>
                </section>
            </main>
            
            <footer class="scorm-footer" data-gjs-type="container">
                <div class="footer-content" data-gjs-type="container">
                    <p data-gjs-type="text">Lección completada: {subject}</p>
                    <p data-gjs-type="text">Nivel: {course_level}</p>
                </div>
            </footer>
        </div>
        """
        
        # Generar CSS SCORM SIMPLE para GrapesJS
        css_content = """
        .scorm-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #fff;
        }
        
        .scorm-header {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .scorm-title {
            font-size: 2rem;
            margin: 0 0 15px 0;
            font-weight: 600;
            color: #2c3e50;
        }
        
        .scorm-meta {
            display: flex;
            justify-content: center;
            gap: 20px;
            font-size: 1rem;
        }
        
        .scorm-level {
            background: #e9ecef;
            padding: 8px 16px;
            border-radius: 4px;
            color: #495057;
        }
        
        .scorm-objectives {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 30px;
            border-left: 4px solid #007bff;
        }
        
        .scorm-objectives h2 {
            color: #007bff;
            margin-top: 0;
            font-size: 1.5rem;
        }
        
        .objectives-list {
            list-style: none;
            padding: 0;
        }
        
        .objectives-list li {
            background: white;
            margin: 10px 0;
            padding: 15px;
            border-radius: 4px;
            border: 1px solid #e9ecef;
            position: relative;
            padding-left: 30px;
        }
        
        .objectives-list li:before {
            content: "•";
            position: absolute;
            left: 15px;
            top: 15px;
            color: #007bff;
            font-weight: bold;
            font-size: 1.2rem;
        }
        
        .scorm-section {
            background: white;
            margin: 20px 0;
            border-radius: 8px;
            border: 1px solid #e9ecef;
            overflow: hidden;
        }
        
        .section-title {
            background: #f8f9fa;
            color: #2c3e50;
            margin: 0;
            padding: 20px;
            font-size: 1.3rem;
            font-weight: 600;
            border-bottom: 1px solid #e9ecef;
        }
        
        .section-content {
            padding: 25px;
        }
        
        .text-content {
            margin: 20px 0;
        }
        
        .text-content h3 {
            color: #2c3e50;
            margin-top: 25px;
            margin-bottom: 15px;
            font-size: 1.2rem;
        }
        
        .text-content h4 {
            color: #495057;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 1.1rem;
        }
        
        .text-content ul {
            margin: 15px 0;
            padding-left: 20px;
        }
        
        .text-content li {
            margin: 8px 0;
        }
        
        .key-points {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .point-item {
            display: flex;
            align-items: flex-start;
            gap: 15px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .point-number {
            background: #667eea;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            flex-shrink: 0;
        }
        
        .point-content h4 {
            margin: 0 0 8px 0;
            color: #333;
        }
        
        .exercise-container {
            margin: 20px 0;
        }
        
        .exercise-item {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
        }
        
        .exercise-item h3 {
            color: #495057;
            margin-top: 0;
        }
        
        .scorm-textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-family: inherit;
            font-size: 14px;
            resize: vertical;
            margin: 10px 0;
        }
        
        .scorm-textarea:focus {
            outline: none;
            border-color: #007bff;
            box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
        }
        
        .scorm-button {
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
        }
        
        .scorm-button:hover {
            background: #0056b3;
        }
        
        .scorm-button.primary {
            background: #28a745;
        }
        
        .scorm-button.primary:hover {
            background: #1e7e34;
        }
        
        .quiz-container {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 8px;
        }
        
        .quiz-question {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .quiz-question h3 {
            color: #495057;
            margin-top: 0;
        }
        
        .quiz-options {
            margin: 15px 0;
        }
        
        .option-label {
            display: block;
            padding: 10px;
            margin: 8px 0;
            background: #f8f9fa;
            border-radius: 6px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }
        
        .option-label:hover {
            background: #e9ecef;
        }
        
        .option-label input[type="radio"] {
            margin-right: 10px;
        }
        
        .scorm-footer {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 30px;
            border: 1px solid #e9ecef;
        }
        
        .footer-content {
            text-align: center;
        }
        
        .footer-content p {
            margin: 5px 0;
            color: #6c757d;
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            .scorm-content {
                padding: 10px;
            }
            
            .scorm-title {
                font-size: 2rem;
            }
            
            .scorm-meta {
                flex-direction: column;
                gap: 10px;
            }
            
            .point-item {
                flex-direction: column;
                text-align: center;
            }
        }
        """
        
        # Generar JavaScript básico para interactividad
        js_content = """
        // JavaScript básico para funcionalidad SCORM
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Contenido SCORM cargado');
            
            // Función para guardar respuestas
            window.saveAnswer = function(exerciseId, button) {
                const textarea = button.closest('.exercise-item').querySelector('textarea');
                const answer = textarea.value;
                
                if (answer.trim()) {
                    // Simular guardado
                    button.textContent = '✓ Guardado';
                    button.style.background = '#28a745';
                    
                    // Guardar en localStorage
                    localStorage.setItem('scorm_answer_' + exerciseId, answer);
                    
                    setTimeout(() => {
                        button.textContent = 'Guardar Respuesta';
                        button.style.background = '#007bff';
                    }, 2000);
                } else {
                    alert('Por favor escribe una respuesta antes de guardar');
                }
            };
            
            // Cargar respuestas guardadas
            document.querySelectorAll('textarea').forEach(textarea => {
                const exerciseItem = textarea.closest('.exercise-item');
                const exerciseId = exerciseItem.querySelector('h3').textContent.toLowerCase().replace(/\s+/g, '_');
                const savedAnswer = localStorage.getItem('scorm_answer_' + exerciseId);
                if (savedAnswer) {
                    textarea.value = savedAnswer;
                }
            });
        });
        """
        
        return {
            'html': html_content.strip(),
            'css': css_content.strip(),
            'js': js_content.strip()
        }
 