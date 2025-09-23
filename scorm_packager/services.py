import os
import json
import zipfile
import tempfile
from typing import Dict, Any
from django.conf import settings

class SCORMPackager:
    """Servicio para crear paquetes SCORM a partir de contenido Gamma"""
    
    def __init__(self):
        self.scorm_version = "1.2"
        
    def create_scorm_package(self, content_data: Dict[str, Any], title: str) -> str:
        """Crea un paquete SCORM y retorna la ruta del archivo ZIP"""
        
        # Crear directorio temporal
        temp_dir = tempfile.mkdtemp()
        package_dir = os.path.join(temp_dir, f"{title.replace(' ', '_')}_scorm")
        os.makedirs(package_dir, exist_ok=True)
        
        try:
            # Generar HTML del contenido
            html_content = self._generate_html_content(content_data, title)
            
            # Crear archivos SCORM
            self._create_imsmanifest(package_dir, title)
            self._create_index_html(package_dir, html_content, title)
            self._create_scorm_api(package_dir)
            
            # Crear archivo ZIP
            zip_path = os.path.join(temp_dir, f"{title.replace(' ', '_')}_scorm.zip")
            self._create_zip_package(package_dir, zip_path)
            
            return zip_path
            
        except Exception as e:
            # Limpiar en caso de error
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e
    
    def _generate_html_content(self, content_data: Dict[str, Any], title: str) -> str:
        """Genera el HTML del contenido basado en los bloques Gamma"""
        
        html_parts = [
            f"<h1>{title}</h1>",
            "<div class='scorm-content'>"
        ]
        
        if 'blocks' in content_data:
            for block in content_data['blocks']:
                html_parts.append(self._render_block(block))
        
        html_parts.extend([
            "</div>",
            "<style>",
            self._get_scorm_styles(),
            "</style>",
            "<script>",
            self._get_scorm_scripts(),
            "</script>"
        ])
        
        return '\n'.join(html_parts)
    
    def _render_block(self, block: Dict[str, Any]) -> str:
        """Renderiza un bloque individual"""
        block_type = block.get('type', 'paragraph')
        
        if block_type == 'hero':
            return f"""
            <div class="hero-block">
                <h1>{block.get('title', '')}</h1>
                <h2>{block.get('subtitle', '')}</h2>
                <p>{block.get('body', '')}</p>
            </div>
            """
        elif block_type == 'paragraph':
            return f"<p class='paragraph-block'>{block.get('content', '')}</p>"
        elif block_type == 'heading':
            return f"<h2 class='heading-block'>{block.get('content', '')}</h2>"
        elif block_type == 'list':
            items = block.get('items', [])
            list_items = ''.join([f"<li>{item}</li>" for item in items])
            return f"<ul class='list-block'>{list_items}</ul>"
        elif block_type == 'quiz':
            return self._render_quiz_block(block)
        elif block_type == 'form':
            return self._render_form_block(block)
        elif block_type == 'flashcard':
            return self._render_flashcard_block(block)
        elif block_type == 'callout':
            variant = block.get('variant', 'info')
            return f"""
            <div class="callout-block callout-{variant}">
                <h3>{block.get('title', '')}</h3>
                <p>{block.get('content', '')}</p>
            </div>
            """
        else:
            return f"<div class='unknown-block'>{block.get('content', '')}</div>"
    
    def _render_quiz_block(self, block: Dict[str, Any]) -> str:
        """Renderiza un bloque de quiz"""
        question = block.get('question', '')
        options = block.get('options', [])
        correct_answer = block.get('correctAnswer', 0)
        
        options_html = ''
        for i, option in enumerate(options):
            options_html += f"""
            <label class="quiz-option">
                <input type="radio" name="quiz_{block.get('id', '')}" value="{i}" data-correct="{i == correct_answer}">
                {option}
            </label>
            """
        
        return f"""
        <div class="quiz-block">
            <h3>Quiz: {question}</h3>
            <div class="quiz-options">{options_html}</div>
            <button onclick="checkQuizAnswer('quiz_{block.get('id', '')}')">Verificar Respuesta</button>
            <div class="quiz-explanation" style="display:none;">
                <p><strong>Explicación:</strong> {block.get('explanation', '')}</p>
            </div>
        </div>
        """
    
    def _render_form_block(self, block: Dict[str, Any]) -> str:
        """Renderiza un bloque de formulario"""
        title = block.get('title', '')
        description = block.get('description', '')
        fields = block.get('fields', [])
        
        fields_html = ''
        for field in fields:
            field_type = field.get('type', 'text')
            field_name = field.get('name', '')
            field_label = field.get('label', '')
            field_required = field.get('required', False)
            
            if field_type == 'textarea':
                fields_html += f"""
                <div class="form-field">
                    <label>{field_label}{'*' if field_required else ''}</label>
                    <textarea name="{field_name}" {'required' if field_required else ''}></textarea>
                </div>
                """
            else:
                fields_html += f"""
                <div class="form-field">
                    <label>{field_label}{'*' if field_required else ''}</label>
                    <input type="{field_type}" name="{field_name}" {'required' if field_required else ''}>
                </div>
                """
        
        return f"""
        <div class="form-block">
            <h3>{title}</h3>
            <p>{description}</p>
            <form>{fields_html}</form>
        </div>
        """
    
    def _render_flashcard_block(self, block: Dict[str, Any]) -> str:
        """Renderiza un bloque de flashcard"""
        front = block.get('front', '')
        back = block.get('back', '')
        category = block.get('category', 'General')
        difficulty = block.get('difficulty', 'medium')
        
        return f"""
        <div class="flashcard-block">
            <div class="flashcard" onclick="flipCard(this)">
                <div class="flashcard-front">
                    <h4>FRENTE</h4>
                    <p>{front}</p>
                </div>
                <div class="flashcard-back">
                    <h4>REVERSO</h4>
                    <p>{back}</p>
                </div>
            </div>
            <div class="flashcard-meta">
                <span class="category">{category}</span>
                <span class="difficulty difficulty-{difficulty}">{difficulty}</span>
            </div>
        </div>
        """
    
    def _get_scorm_styles(self) -> str:
        """Retorna los estilos CSS para el contenido SCORM"""
        return """
        body { font-family: Arial, sans-serif; margin: 20px; }
        .scorm-content { max-width: 800px; margin: 0 auto; }
        .hero-block { text-align: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 10px; margin: 20px 0; }
        .paragraph-block { margin: 15px 0; line-height: 1.6; }
        .heading-block { color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
        .list-block { margin: 15px 0; }
        .quiz-block { border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .quiz-option { display: block; margin: 10px 0; }
        .form-block { border: 1px solid #ddd; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .form-field { margin: 15px 0; }
        .form-field label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-field input, .form-field textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .flashcard-block { margin: 20px 0; }
        .flashcard { width: 300px; height: 200px; margin: 0 auto; position: relative; perspective: 1000px; cursor: pointer; }
        .flashcard-front, .flashcard-back { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border: 1px solid #ddd; border-radius: 8px; padding: 20px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
        .flashcard-back { transform: rotateY(180deg); }
        .flashcard.flipped .flashcard-front { transform: rotateY(180deg); }
        .flashcard.flipped .flashcard-back { transform: rotateY(0deg); }
        .flashcard-meta { text-align: center; margin-top: 10px; }
        .category, .difficulty { padding: 4px 8px; border-radius: 4px; font-size: 12px; margin: 0 5px; }
        .category { background: #e3f2fd; color: #1976d2; }
        .difficulty-easy { background: #e8f5e8; color: #2e7d32; }
        .difficulty-medium { background: #fff3e0; color: #f57c00; }
        .difficulty-hard { background: #ffebee; color: #c62828; }
        .callout-block { padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid; }
        .callout-info { background: #e3f2fd; border-color: #2196f3; }
        .callout-warning { background: #fff3e0; border-color: #ff9800; }
        .callout-success { background: #e8f5e8; border-color: #4caf50; }
        .callout-error { background: #ffebee; border-color: #f44336; }
        """
    
    def _get_scorm_scripts(self) -> str:
        """Retorna los scripts JavaScript para el contenido SCORM"""
        return """
        function checkQuizAnswer(quizName) {
            const selectedOption = document.querySelector(`input[name="${quizName}"]:checked`);
            if (!selectedOption) {
                alert('Por favor selecciona una respuesta');
                return;
            }
            
            const isCorrect = selectedOption.dataset.correct === 'true';
            const explanation = selectedOption.closest('.quiz-block').querySelector('.quiz-explanation');
            
            if (isCorrect) {
                alert('¡Correcto!');
                explanation.style.display = 'block';
            } else {
                alert('Incorrecto. Inténtalo de nuevo.');
            }
        }
        
        function flipCard(card) {
            card.classList.toggle('flipped');
        }
        
        // SCORM API functions
        function Initialize(param) {
            return "true";
        }
        
        function GetValue(element) {
            return "";
        }
        
        function SetValue(element, value) {
            return "true";
        }
        
        function Commit(param) {
            return "true";
        }
        
        function GetLastError() {
            return "0";
        }
        
        function GetErrorString(errorCode) {
            return "";
        }
        
        function GetDiagnostic(errorCode) {
            return "";
        }
        """
    
    def _create_imsmanifest(self, package_dir: str, title: str):
        """Crea el archivo imsmanifest.xml"""
        manifest_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="scorm_{title.replace(' ', '_')}" version="1.0" 
          xmlns="http://www.imsglobal.org/xsd/imscp_v1p1" 
          xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3" 
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <metadata>
        <schema>ADL SCORM</schema>
        <schemaversion>1.2</schemaversion>
    </metadata>
    <organizations default="default_org">
        <organization identifier="default_org">
            <title>{title}</title>
            <item identifier="item_1" identifierref="resource_1">
                <title>{title}</title>
            </item>
        </organization>
    </organizations>
    <resources>
        <resource identifier="resource_1" type="webcontent" adlcp:scormtype="sco" href="index.html">
            <file href="index.html"/>
        </resource>
    </resources>
</manifest>"""
        
        with open(os.path.join(package_dir, 'imsmanifest.xml'), 'w', encoding='utf-8') as f:
            f.write(manifest_content)
    
    def _create_index_html(self, package_dir: str, html_content: str, title: str):
        """Crea el archivo index.html"""
        full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="scorm_api.js"></script>
</head>
<body>
    {html_content}
</body>
</html>"""
        
        with open(os.path.join(package_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(full_html)
    
    def _create_scorm_api(self, package_dir: str):
        """Crea el archivo scorm_api.js"""
        api_content = """// SCORM API Implementation
var API = null;

function findAPI(win) {
    var findAttempts = 0;
    while ((win.API == null) && (win.parent != null) && (findAttempts < 7)) {
        findAttempts++;
        win = win.parent;
    }
    return win.API;
}

function getAPI() {
    if ((API == null) && (window.parent != null)) {
        API = findAPI(window.parent);
    }
    return API;
}

function Initialize(param) {
    var api = getAPI();
    if (api == null) {
        return "false";
    }
    return api.Initialize(param);
}

function GetValue(element) {
    var api = getAPI();
    if (api == null) {
        return "";
    }
    return api.GetValue(element);
}

function SetValue(element, value) {
    var api = getAPI();
    if (api == null) {
        return "false";
    }
    return api.SetValue(element, value);
}

function Commit(param) {
    var api = getAPI();
    if (api == null) {
        return "false";
    }
    return api.Commit(param);
}

function GetLastError() {
    var api = getAPI();
    if (api == null) {
        return "0";
    }
    return api.GetLastError();
}

function GetErrorString(errorCode) {
    var api = getAPI();
    if (api == null) {
        return "";
    }
    return api.GetErrorString(errorCode);
}

function GetDiagnostic(errorCode) {
    var api = getAPI();
    if (api == null) {
        return "";
    }
    return api.GetDiagnostic(errorCode);
}

function Terminate(param) {
    var api = getAPI();
    if (api == null) {
        return "false";
    }
    return api.Terminate(param);
}

// Initialize SCORM when page loads
window.onload = function() {
    Initialize("");
};"""
        
        with open(os.path.join(package_dir, 'scorm_api.js'), 'w', encoding='utf-8') as f:
            f.write(api_content)
    
    def _create_zip_package(self, package_dir: str, zip_path: str):
        """Crea el archivo ZIP del paquete SCORM"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, package_dir)
                    zipf.write(file_path, arcname)
