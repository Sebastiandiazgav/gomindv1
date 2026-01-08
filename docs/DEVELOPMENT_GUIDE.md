# Guía de Desarrollo - Bianca

## Configuración del Entorno de Desarrollo

### Prerrequisitos
- Python 3.8+
- Git
- Editor de código (VS Code recomendado)
- Cuenta AWS con acceso a Bedrock
- Acceso a GoMind API

### Setup Inicial

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd bianca-medical-assistant
```

2. **Crear entorno virtual**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus credenciales
```

5. **Configurar Streamlit secrets**
```bash
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Editar con tus credenciales
```

6. **Ejecutar la aplicación**
```bash
streamlit run app.py
```

---

## Estructura del Código

### Archivo Principal: `app.py`

#### Secciones Principales

1. **Imports y Configuración**
```python
import os
import json
import re
import boto3
import streamlit as st
from datetime import datetime, timedelta
import requests
```

2. **Configuración de Clientes**
```python
# Cliente Bedrock
bedrock_client = boto3.client(
    service_name='bedrock-runtime',
    region_name=st.secrets["aws"]["REGION"],
    aws_access_key_id=st.secrets["aws"]["ACCESS_KEY_ID"],
    aws_secret_access_key=st.secrets["aws"]["SECRET_ACCESS_KEY"]
)

# Configuración API GoMind
API_BASE_URL = st.secrets["api"]["BASE_URL"]
API_EMAIL = st.secrets["api"]["EMAIL"]
API_PASSWORD = st.secrets["api"]["PASSWORD"]
```

3. **Constantes**
```python
SPANISH_WEEKDAYS = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes']
SPANISH_MONTHS = ['enero', 'febrero', 'marzo', ...]
API_TIMEOUT = 30
BEDROCK_MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"
BEDROCK_MAX_TOKENS = 1000
```

### Funciones Principales

#### 1. Análisis de IA
```python
def analyze_user_intent(user_message, context_stage):
    """
    Analiza la intención del usuario usando Bedrock
    
    Args:
        user_message: El mensaje del usuario
        context_stage: El contexto/etapa actual
    
    Returns:
        str: 'POSITIVA', 'NEGATIVA', 'AMBIGUA', etc.
    """
```

#### 2. Gestión de API
```python
def get_api_token(email=None, password=None):
    """Obtiene token de autenticación de GoMind API"""

def get_user_results(user_id):
    """Obtiene resultados médicos de un usuario"""

def send_appointment_to_api(appointment_api_data):
    """Envía datos de cita a la API"""
```

#### 3. Análisis Médico
```python
def analyze_results(results):
    """
    Analiza resultados médicos contra rangos de referencia
    
    Returns:
        tuple: (issues_list, needs_appointment_bool)
    """
```

#### 4. Manejo de Flujos
```python
def handle_appointment_request():
    """Inicia el flujo de agendamiento"""

def handle_clinic_selection(prompt):
    """Maneja selección de clínica"""

def handle_day_selection(prompt):
    """Maneja selección de día"""

def handle_time_selection(prompt):
    """Maneja selección de hora"""
```

---

## Patrones de Desarrollo

### 1. Manejo de Estado con Session State

```python
# Inicialización
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'stage' not in st.session_state:
    st.session_state.stage = 'inicio'

# Uso
st.session_state.auth_token = token
st.session_state.user_data = user_info
```

### 2. Manejo de Errores

```python
def handle_appointment_error(error, error_type='general'):
    """Maneja errores de manera consistente"""
    if error_type == 'clinic_fetch':
        return MESSAGES['clinic_error'].format(error=str(error)), 'completed'
    elif error_type == 'api_connection':
        return MESSAGES['connection_error'], 'completed'
    # ... más casos
```

### 3. Validación de Datos

```python
def validate_appointment_data():
    """Valida que todos los datos requeridos estén presentes"""
    required_fields = ['selected_clinic', 'selected_day', 'selected_time']
    missing_fields = [field for field in required_fields 
                     if not hasattr(st.session_state, field) 
                     or not getattr(st.session_state, field)]
    
    if missing_fields:
        raise ValueError(f"Faltan datos requeridos: {', '.join(missing_fields)}")
```

### 4. Mensajes Centralizados

```python
MESSAGES = {
    'healthy_results': "¡Excelente noticia, tus valores están todos dentro del rango saludable...",
    'unhealthy_results': "He revisado tus valores y me gustaría comentarte lo que veo...",
    'appointment_question': "¿Te gustaría que te ayude a agendar una cita...",
    # ... más mensajes
}
```

---

## Testing

### Setup de Testing

```bash
pip install pytest pytest-mock streamlit-testing
```

### Estructura de Tests

```
tests/
├── __init__.py
├── test_api_functions.py
├── test_medical_analysis.py
├── test_appointment_flow.py
└── test_ui_components.py
```

### Ejemplo de Test

```python
# tests/test_medical_analysis.py
import pytest
from unittest.mock import patch, MagicMock
from app import analyze_results, REFERENCE_RANGES

def test_analyze_results_healthy():
    """Test análisis con valores saludables"""
    results = {
        'Colesterol Total': 180,
        'Glicemia Basal': 90,
        'Hemoglobina': 14
    }
    
    issues, needs_appointment = analyze_results(results)
    
    assert issues == []
    assert needs_appointment == False

def test_analyze_results_unhealthy():
    """Test análisis con valores fuera de rango"""
    results = {
        'Colesterol Total': 250,  # Alto
        'Glicemia Basal': 120,    # Alto
    }
    
    issues, needs_appointment = analyze_results(results)
    
    assert len(issues) == 2
    assert needs_appointment == True
    assert 'Colesterol Total' in issues[0]
    assert 'Glicemia Basal' in issues[1]

@patch('app.bedrock_client')
def test_analyze_user_intent(mock_bedrock):
    """Test análisis de intención con Bedrock"""
    # Mock response
    mock_response = {
        'body': MagicMock()
    }
    mock_response['body'].read.return_value = json.dumps({
        'content': [{'text': 'POSITIVA'}]
    }).encode()
    mock_bedrock.invoke_model.return_value = mock_response
    
    result = analyze_user_intent("sí, me parece bien", "analyzing")
    
    assert result == 'POSITIVA'
```

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Tests específicos
pytest tests/test_medical_analysis.py

# Con coverage
pytest --cov=app tests/
```

---

## Debugging

### 1. Logging

```python
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Usar en funciones
def analyze_user_intent(user_message, context_stage):
    logger.debug(f"Analyzing intent for: {user_message}")
    # ... lógica
    logger.info(f"Intent result: {intent}")
    return intent
```

### 2. Streamlit Debugging

```python
# Debug session state
st.write("Debug - Session State:")
st.write(st.session_state)

# Debug variables
st.write(f"Debug - Current stage: {st.session_state.get('stage', 'None')}")
st.write(f"Debug - User data: {st.session_state.get('user_data', 'None')}")
```

### 3. API Debugging

```python
def debug_api_call(url, method, data=None, headers=None):
    """Helper para debuggear llamadas API"""
    print(f"API Call: {method} {url}")
    print(f"Headers: {headers}")
    print(f"Data: {data}")
    
    response = requests.request(method, url, json=data, headers=headers)
    
    print(f"Response Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    return response
```

---

## Mejores Prácticas

### 1. Código Limpio

```python
# Usar nombres descriptivos
def get_next_business_days(n=3):
    """Obtiene los próximos días hábiles excluyendo fines de semana"""
    
# Funciones pequeñas y enfocadas
def format_spanish_date(date_obj):
    """Formatea una fecha en español"""
    day_name = SPANISH_WEEKDAYS[date_obj.weekday()]
    day_num = date_obj.day
    month_name = SPANISH_MONTHS[date_obj.month - 1]
    return f"{day_name} {day_num} de {month_name}"

# Constantes en mayúsculas
REFERENCE_RANGES = {
    'Colesterol Total': {'min': 0, 'max': 200, 'unit': 'mg/dL'},
    # ...
}
```

### 2. Manejo de Errores

```python
# Específico y útil
try:
    results = get_user_results(user_id)
except requests.exceptions.Timeout:
    return "Error de conexión: tiempo de espera agotado", 'error'
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        return "Usuario no encontrado", 'error'
    else:
        return f"Error de API: {e.response.status_code}", 'error'
except Exception as e:
    logger.error(f"Error inesperado: {str(e)}")
    return "Error interno del sistema", 'error'
```

### 3. Documentación

```python
def convert_spanish_date_to_iso(date_str, time_str):
    """
    Convierte fecha en español a formato ISO 8601.
    
    Args:
        date_str (str): Fecha en formato "Lunes 20 de enero"
        time_str (str): Hora en formato "14:00"
    
    Returns:
        str: Fecha en formato ISO 8601 UTC
        
    Raises:
        ValueError: Si el formato de fecha es inválido
        
    Example:
        >>> convert_spanish_date_to_iso("Lunes 20 de enero", "14:00")
        "2024-01-20T14:00:00.000Z"
    """
```

---

## Extensiones Recomendadas (VS Code)

```json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.flake8",
        "ms-python.black-formatter",
        "ms-toolsai.jupyter",
        "redhat.vscode-yaml",
        "ms-vscode.vscode-json"
    ]
}
```

---

## Git Workflow

### Branching Strategy

```bash
# Feature branch
git checkout -b feature/nueva-funcionalidad
git commit -m "feat: agregar nueva funcionalidad"
git push origin feature/nueva-funcionalidad

# Hotfix
git checkout -b hotfix/corregir-bug-critico
git commit -m "fix: corregir bug crítico en API"
git push origin hotfix/corregir-bug-critico
```

### Commit Messages

```bash
# Formato: tipo(scope): descripción

feat(api): agregar endpoint para cancelar citas
fix(ui): corregir error en selección de fecha
docs(readme): actualizar instrucciones de instalación
refactor(analysis): simplificar lógica de análisis médico
test(appointment): agregar tests para flujo de citas
```

---

## Performance Optimization

### 1. Caching

```python
@st.cache_data(ttl=300)  # Cache por 5 minutos
def get_company_products(company_id):
    """Cache productos de empresa"""
    # ... lógica

@st.cache_resource
def get_bedrock_client():
    """Cache cliente Bedrock"""
    return boto3.client('bedrock-runtime', ...)
```

### 2. Lazy Loading

```python
# Cargar datos solo cuando se necesiten
if st.session_state.stage == 'selecting_clinic':
    if 'clinics' not in st.session_state:
        st.session_state.clinics = get_health_providers(company_id)
```

### 3. Optimización de Requests

```python
# Timeout apropiado
response = requests.get(url, timeout=30)

# Reutilizar sesiones
session = requests.Session()
session.headers.update({'Authorization': f'Bearer {token}'})
```

---

## Troubleshooting Común

### Error: "Bedrock model not available"
```python
# Verificar región y modelo
print(f"Region: {boto3.Session().region_name}")
print(f"Model ID: {BEDROCK_MODEL_ID}")
```

### Error: "Session state not persisting"
```python
# Verificar inicialización
if 'key' not in st.session_state:
    st.session_state.key = default_value
```

### Error: "API timeout"
```python
# Aumentar timeout y agregar retry
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator
```