# Guía de Seguridad - Bianca

## Visión General de Seguridad

Bianca maneja información médica sensible y requiere implementar las mejores prácticas de seguridad para proteger los datos de los usuarios y cumplir con regulaciones de privacidad.

## Clasificación de Datos

### Datos Altamente Sensibles
- **Resultados médicos**: Valores de laboratorio, diagnósticos
- **Información personal**: Nombres, IDs de usuario
- **Credenciales**: Passwords, tokens JWT
- **Datos de citas**: Fechas, horarios, clínicas

### Datos Moderadamente Sensibles
- **Logs de aplicación**: Pueden contener IDs de usuario
- **Métricas de uso**: Patrones de comportamiento
- **Configuración**: URLs de API, configuraciones

### Datos Públicos
- **Catálogo de productos**: Servicios disponibles
- **Lista de clínicas**: Información pública de proveedores
- **Rangos de referencia**: Valores médicos estándar

---

## Autenticación y Autorización

### 1. Autenticación de Usuario

#### Flujo Actual
```python
def authenticate_user(email, password):
    """
    Autentica usuario contra GoMind API
    
    Security considerations:
    - Passwords no se almacenan localmente
    - Comunicación vía HTTPS
    - Tokens JWT con expiración
    """
    payload = {"email": email, "password": password}
    response = requests.post(f"{API_BASE_URL}/api/auth/login", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        return {
            'token': data.get('token'),
            'company_id': data.get('company', {}).get('company_id')
        }
    else:
        raise AuthenticationError("Credenciales inválidas")
```

#### Mejoras de Seguridad Recomendadas
1. **Rate Limiting**: Limitar intentos de login
2. **Account Lockout**: Bloquear después de X intentos fallidos
3. **2FA**: Implementar autenticación de dos factores
4. **Password Policy**: Validar complejidad de contraseñas

### 2. Gestión de Tokens JWT

#### Almacenamiento Seguro
```python
# ❌ Inseguro - No hacer
st.session_state.token = "jwt_token_here"

# ✅ Seguro - Implementar
class SecureTokenManager:
    def __init__(self):
        self._token = None
        self._expires_at = None
    
    def set_token(self, token, expires_in=3600):
        self._token = token
        self._expires_at = time.time() + expires_in
    
    def get_token(self):
        if self._expires_at and time.time() > self._expires_at:
            self._token = None
            raise TokenExpiredError("Token has expired")
        return self._token
    
    def is_valid(self):
        return self._token and time.time() < self._expires_at
```

#### Validación de Tokens
```python
def validate_token(token):
    """
    Valida token JWT antes de usar
    """
    try:
        # Verificar formato
        if not token or not isinstance(token, str):
            return False
        
        # Verificar estructura JWT (3 partes separadas por .)
        parts = token.split('.')
        if len(parts) != 3:
            return False
        
        # Verificar expiración (si es posible decodificar)
        # Nota: En producción, usar biblioteca JWT apropiada
        return True
        
    except Exception:
        return False
```

---

## Protección de Datos Médicos

### 1. Encriptación en Tránsito

#### HTTPS Obligatorio
```python
# Verificar que todas las URLs usen HTTPS
def validate_api_url(url):
    if not url.startswith('https://'):
        raise SecurityError("API URL must use HTTPS")
    return url

API_BASE_URL = validate_api_url(st.secrets["api"]["BASE_URL"])
```

#### Configuración de Requests
```python
# Configuración segura para requests
session = requests.Session()
session.verify = True  # Verificar certificados SSL
session.timeout = 30   # Timeout para evitar hanging connections

# Headers de seguridad
session.headers.update({
    'User-Agent': 'Bianca-Medical-Assistant/1.0',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
})
```

### 2. Sanitización de Datos

#### Input Validation
```python
import re
from html import escape

def sanitize_user_input(user_input):
    """
    Sanitiza entrada del usuario para prevenir inyecciones
    """
    if not isinstance(user_input, str):
        return str(user_input)
    
    # Remover caracteres peligrosos
    sanitized = re.sub(r'[<>"\']', '', user_input)
    
    # Escapar HTML
    sanitized = escape(sanitized)
    
    # Limitar longitud
    sanitized = sanitized[:1000]
    
    return sanitized.strip()

def validate_user_id(user_id):
    """
    Valida formato de ID de usuario
    """
    if not user_id:
        raise ValueError("User ID is required")
    
    # Solo números y letras
    if not re.match(r'^[a-zA-Z0-9]+$', str(user_id)):
        raise ValueError("Invalid user ID format")
    
    return str(user_id)
```

#### Output Sanitization
```python
def sanitize_medical_data(data):
    """
    Sanitiza datos médicos antes de mostrar
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Sanitizar claves
            clean_key = re.sub(r'[^\w\s-]', '', str(key))
            # Sanitizar valores
            if isinstance(value, (int, float)):
                sanitized[clean_key] = value
            else:
                sanitized[clean_key] = sanitize_user_input(str(value))
        return sanitized
    
    return sanitize_user_input(str(data))
```

### 3. Logging Seguro

#### Configuración de Logs
```python
import logging
from logging.handlers import RotatingFileHandler

# Configurar logging seguro
def setup_secure_logging():
    logger = logging.getLogger('bianca')
    logger.setLevel(logging.INFO)
    
    # Handler con rotación
    handler = RotatingFileHandler(
        'logs/bianca.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    
    # Formato sin datos sensibles
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

# Función para logging seguro
def log_user_action(action, user_id=None, success=True):
    """
    Log de acciones sin exponer datos sensibles
    """
    # Anonimizar user_id
    anonymous_id = hashlib.sha256(str(user_id).encode()).hexdigest()[:8] if user_id else "anonymous"
    
    logger.info(f"Action: {action}, User: {anonymous_id}, Success: {success}")
```

#### Qué NO Loggear
```python
# ❌ NUNCA loggear estos datos
# - Contraseñas
# - Tokens JWT completos
# - Resultados médicos específicos
# - Información personal identificable

# ✅ Sí loggear (de forma segura)
# - Acciones del usuario (login, logout, agendar cita)
# - Errores de sistema (sin datos sensibles)
# - Métricas de performance
# - IDs anonimizados
```

---

## Gestión de Secretos

### 1. Variables de Entorno

#### Estructura Segura
```bash
# .env (desarrollo local)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
API_BASE_URL=https://api-bianca-desa.gomind.cl
API_EMAIL=bianca@gomind.cl
API_PASSWORD=...

# Nunca commitear este archivo
echo ".env" >> .gitignore
```

#### Validación de Secretos
```python
def validate_secrets():
    """
    Valida que todos los secretos requeridos estén presentes
    """
    required_secrets = [
        'aws.ACCESS_KEY_ID',
        'aws.SECRET_ACCESS_KEY',
        'aws.REGION',
        'api.BASE_URL',
        'api.EMAIL',
        'api.PASSWORD'
    ]
    
    missing_secrets = []
    for secret in required_secrets:
        try:
            keys = secret.split('.')
            value = st.secrets
            for key in keys:
                value = value[key]
            if not value:
                missing_secrets.append(secret)
        except KeyError:
            missing_secrets.append(secret)
    
    if missing_secrets:
        raise ConfigurationError(f"Missing secrets: {missing_secrets}")
```

### 2. Rotación de Credenciales

#### Estrategia de Rotación
```python
class CredentialManager:
    def __init__(self):
        self.token_refresh_threshold = 300  # 5 minutos antes de expirar
    
    def should_refresh_token(self, token_expires_at):
        """
        Determina si el token necesita renovación
        """
        return time.time() > (token_expires_at - self.token_refresh_threshold)
    
    def refresh_token_if_needed(self):
        """
        Renueva token automáticamente si es necesario
        """
        if hasattr(st.session_state, 'token_expires_at'):
            if self.should_refresh_token(st.session_state.token_expires_at):
                new_token_data = get_api_token()
                st.session_state.auth_token = new_token_data['token']
                st.session_state.token_expires_at = time.time() + 3600
```

---

## Seguridad de AWS Bedrock

### 1. Configuración Segura

#### IAM Policy Mínima
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"
            ]
        }
    ]
}
```

#### Cliente Seguro
```python
def create_secure_bedrock_client():
    """
    Crea cliente Bedrock con configuración segura
    """
    try:
        client = boto3.client(
            service_name='bedrock-runtime',
            region_name=st.secrets["aws"]["REGION"],
            aws_access_key_id=st.secrets["aws"]["ACCESS_KEY_ID"],
            aws_secret_access_key=st.secrets["aws"]["SECRET_ACCESS_KEY"],
            config=Config(
                retries={'max_attempts': 3},
                read_timeout=30,
                connect_timeout=10
            )
        )
        return client
    except Exception as e:
        logger.error(f"Failed to create Bedrock client: {str(e)}")
        raise SecurityError("Unable to initialize AI service")
```

### 2. Sanitización de Prompts

#### Limpieza de Datos Médicos
```python
def sanitize_prompt_data(user_message, context_stage):
    """
    Sanitiza datos antes de enviar a Bedrock
    """
    # Remover información personal identificable
    sanitized_message = re.sub(r'\b\d{7,}\b', '[ID]', user_message)  # IDs numéricos
    sanitized_message = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', sanitized_message)  # Emails
    
    # Limitar longitud
    sanitized_message = sanitized_message[:500]
    
    return sanitized_message, context_stage

def create_safe_prompt(user_message, context_stage):
    """
    Crea prompt seguro para Bedrock
    """
    sanitized_message, sanitized_context = sanitize_prompt_data(user_message, context_stage)
    
    prompt = f"""Analiza la siguiente respuesta del usuario y determina su intención exacta.

Contexto: {sanitized_context}
Mensaje del usuario: "{sanitized_message}"

Responde ÚNICAMENTE con una de estas palabras: POSITIVA, NEGATIVA, AMBIGUA, PRODUCTOS, o NUEVA_CITA"""
    
    return prompt
```

---

## Compliance y Regulaciones

### 1. GDPR / Protección de Datos

#### Principios Implementados
- **Minimización de datos**: Solo recopilar datos necesarios
- **Propósito específico**: Datos usados solo para análisis médico y citas
- **Retención limitada**: No almacenar datos más tiempo del necesario
- **Seguridad**: Encriptación y acceso controlado

#### Derechos del Usuario
```python
def handle_data_request(request_type, user_id):
    """
    Maneja solicitudes de datos del usuario (GDPR)
    """
    if request_type == 'access':
        # Proporcionar datos que tenemos del usuario
        return get_user_data_summary(user_id)
    
    elif request_type == 'deletion':
        # Eliminar datos del usuario
        return delete_user_data(user_id)
    
    elif request_type == 'portability':
        # Exportar datos en formato legible
        return export_user_data(user_id)
```

### 2. HIPAA (si aplica)

#### Salvaguardas Técnicas
- Encriptación de datos en tránsito y reposo
- Control de acceso basado en roles
- Auditoría de accesos
- Integridad de datos

#### Salvaguardas Administrativas
- Políticas de seguridad documentadas
- Entrenamiento del personal
- Procedimientos de respuesta a incidentes
- Evaluaciones regulares de seguridad

---

## Monitoreo y Detección de Amenazas

### 1. Detección de Anomalías

#### Patrones Sospechosos
```python
def detect_suspicious_activity(user_id, action):
    """
    Detecta actividad sospechosa
    """
    # Múltiples intentos de login fallidos
    if action == 'failed_login':
        failed_attempts = get_failed_login_count(user_id, last_minutes=15)
        if failed_attempts > 5:
            alert_security_team(f"Multiple failed logins for user {user_id}")
    
    # Acceso desde ubicaciones inusuales
    if action == 'login_success':
        if is_unusual_location(user_id):
            log_security_event(f"Unusual location login for user {user_id}")
    
    # Volumen anormal de requests
    if action == 'api_request':
        request_count = get_request_count(user_id, last_minutes=5)
        if request_count > 50:
            rate_limit_user(user_id)
```

### 2. Alertas de Seguridad

#### Sistema de Alertas
```python
def setup_security_alerts():
    """
    Configura alertas de seguridad
    """
    alerts = {
        'failed_authentication': {
            'threshold': 5,
            'window': '15m',
            'action': 'block_ip'
        },
        'unusual_data_access': {
            'threshold': 1,
            'window': '1h',
            'action': 'notify_admin'
        },
        'api_errors': {
            'threshold': 10,
            'window': '5m',
            'action': 'investigate'
        }
    }
    return alerts
```

---

## Respuesta a Incidentes

### 1. Plan de Respuesta

#### Clasificación de Incidentes
- **Crítico**: Brecha de datos médicos, acceso no autorizado
- **Alto**: Falla de autenticación, exposición de tokens
- **Medio**: Errores de aplicación, problemas de performance
- **Bajo**: Logs anómalos, alertas menores

#### Procedimiento de Respuesta
```python
def handle_security_incident(incident_type, severity, details):
    """
    Maneja incidentes de seguridad
    """
    # 1. Contención inmediata
    if severity == 'critical':
        disable_affected_accounts()
        rotate_compromised_credentials()
    
    # 2. Investigación
    collect_forensic_data(incident_type, details)
    
    # 3. Notificación
    notify_stakeholders(severity, details)
    
    # 4. Recuperación
    implement_fixes()
    
    # 5. Lecciones aprendidas
    document_incident(incident_type, severity, details)
```

### 2. Comunicación de Brechas

#### Template de Notificación
```python
def create_breach_notification(incident_details):
    """
    Crea notificación de brecha de seguridad
    """
    notification = {
        'incident_id': generate_incident_id(),
        'date_discovered': datetime.now().isoformat(),
        'affected_users': incident_details.get('user_count', 0),
        'data_types': incident_details.get('data_types', []),
        'containment_actions': incident_details.get('actions_taken', []),
        'next_steps': incident_details.get('remediation_plan', [])
    }
    return notification
```

---

## Checklist de Seguridad

### Desarrollo
- [ ] Validación de entrada en todos los endpoints
- [ ] Sanitización de salida de datos
- [ ] Manejo seguro de errores (sin exposición de datos)
- [ ] Logging sin información sensible
- [ ] Tests de seguridad automatizados

### Deployment
- [ ] HTTPS habilitado en todos los endpoints
- [ ] Secretos configurados correctamente
- [ ] Permisos mínimos en AWS IAM
- [ ] Monitoreo de seguridad activo
- [ ] Plan de respuesta a incidentes documentado

### Operaciones
- [ ] Rotación regular de credenciales
- [ ] Auditorías de acceso periódicas
- [ ] Actualizaciones de seguridad aplicadas
- [ ] Backup de configuraciones críticas
- [ ] Entrenamiento del equipo en seguridad

---

## Recursos Adicionales

### Herramientas Recomendadas
- **SAST**: Bandit para análisis estático de Python
- **Dependency Scanning**: Safety para vulnerabilidades en dependencias
- **Secrets Detection**: GitLeaks para detectar secretos en código
- **Container Security**: Trivy para escaneo de imágenes Docker

### Referencias
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [AWS Security Best Practices](https://aws.amazon.com/security/security-resources/)
- [Streamlit Security Guidelines](https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso)
- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)