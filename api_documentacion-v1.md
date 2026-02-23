# API Documentation - appv1.py (Twilio Integration)

## Descripción General

`appv1.py` es la versión sin Streamlit de Bianca, diseñada específicamente para integrarse con Twilio (WhatsApp/SMS). Proporciona una API REST mediante Flask para procesar mensajes conversacionales.

---

## Configuración

### Variables de Entorno Requeridas

```env
# AWS Bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key

# API GoMind
API_BASE_URL=https://api-bianca-desa.gomind.cl
API_EMAIL=tu_email
API_PASSWORD=tu_password
```

### Instalación

```bash
pip install boto3 requests python-dotenv flask twilio
python appv1.py
```

---

## Endpoints

### 1. POST /webhook

**Descripción**: Webhook principal para recibir mensajes de Twilio

**URL**: `http://localhost:5000/webhook`

**Método**: `POST`

**Content-Type**: `application/x-www-form-urlencoded`

**Parámetros (Form Data)**:

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `From` | string | Sí | Número de teléfono del usuario (formato: +56912345678) |
| `Body` | string | Sí | Contenido del mensaje del usuario |

**Respuesta**:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Texto de respuesta de Bianca</Message>
</Response>
```

**Ejemplo de Request (cURL)**:

```bash
curl -X POST http://localhost:5000/webhook \
  -d "From=+56912345678" \
  -d "Body=Hola"
```

**Ejemplo de Respuesta**:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>👋 ¡Hola! Soy Bianca 😊, tu asistente de salud de GoMind.

Ingresa tu correo electrónico para enviarte un código de verificación y así confirmar tu identidad</Message>
</Response>
```

---

### 2. GET /health

**Descripción**: Health check endpoint para verificar el estado del servicio

**URL**: `http://localhost:5000/health`

**Método**: `GET`

**Respuesta**:

```json
{
  "status": "ok",
  "service": "Bianca WhatsApp Bot"
}
```

**Ejemplo de Request**:

```bash
curl http://localhost:5000/health
```

---

## Función Principal

### `process_message(session_id, user_message)`

**Descripción**: Función principal para procesar mensajes. Puede ser llamada directamente sin usar el webhook de Flask.

**Parámetros**:

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `session_id` | string | Identificador único del usuario (ej: número de teléfono) |
| `user_message` | string | Mensaje del usuario a procesar |

**Retorna**:

```python
{
    'response': str,      # Texto de respuesta generado
    'stage': str,         # Stage actual de la conversación
    'session_id': str     # ID de la sesión
}
```

**Ejemplo de Uso**:

```python
from appv1 import process_message

result = process_message(
    session_id="+56912345678",
    user_message="ralf@gomind.cl"
)

print(result['response'])
# Output: "🔒 Para confirmar tu identidad, te envié un código..."
```

---

## Stages de Conversación

El sistema maneja diferentes stages (etapas) de conversación:

| Stage | Descripción | Input Esperado |
|-------|-------------|----------------|
| `waiting_email` | Esperando correo electrónico | Email válido |
| `waiting_verification_code` | Esperando código de verificación | Código numérico de 4 dígitos |
| `main_menu` | Menú principal después de login | 1 o 2 |
| `selecting_product` | Seleccionando producto | Número de producto |
| `selecting_clinic` | Seleccionando clínica | Número de clínica |
| `scheduling` | Seleccionando día | Número de día |
| `selecting_time` | Seleccionando hora | Número de hora |
| `confirming` | Confirmando cita | Sí/No |
| `analyzing` | Analizando si quiere agendar | Sí/No |
| `completed` | Proceso completado | Cualquier mensaje |
| `conversation_ended` | Conversación finalizada | Cualquier mensaje |

---

## Clase ConversationSession

### Atributos

```python
class ConversationSession:
    session_id: str                    # ID único del usuario
    stage: str                         # Stage actual
    user_data: dict                    # Datos del usuario
    messages: list                     # Historial de mensajes
    context: str                       # Contexto conversacional
    company_id: int                    # ID de la empresa
    clinics: list                      # Lista de clínicas disponibles
    user_email: str                    # Email del usuario
    auth_token: str                    # Token de autenticación
    company_products: list             # Productos de la empresa
    selected_clinic: str               # Clínica seleccionada
    selected_day: str                  # Día seleccionado
    selected_time: str                 # Hora seleccionada
    next_days: list                    # Próximos días disponibles
    available_hours: list              # Horas disponibles
    selected_product: dict             # Producto seleccionado
```

---

## Funciones de API Externa

### `send_verification_code(email)`

**Descripción**: Envía código de verificación al correo del usuario

**Endpoint Externo**: `POST /api/auth/login/user-exist`

**Parámetros**:
- `email` (string): Correo electrónico del usuario

**Retorna**: `True` si el código fue enviado exitosamente

**Excepciones**:
- `Exception`: Si el usuario no existe o hay error en el envío

---

### `authenticate_with_code(email, auth_code)`

**Descripción**: Autentica al usuario con el código de verificación

**Endpoint Externo**: `POST /api/auth/login/wsp`

**Parámetros**:
- `email` (string): Correo electrónico
- `auth_code` (int): Código de verificación

**Retorna**:
```python
{
    'token': str,           # Token JWT
    'company_id': int,      # ID de la empresa
    'user_data': dict       # Datos del usuario
}
```

**Excepciones**:
- `Exception`: Si el código es inválido o hay error de autenticación

---

### `get_company_products(company_id, token)`

**Descripción**: Obtiene los productos disponibles de la empresa

**Endpoint Externo**: `GET /api/companies/{company_id}/products`

**Headers**: `Authorization: Bearer {token}`

**Retorna**: Lista de productos

---

### `get_health_providers(company_id, token)`

**Descripción**: Obtiene los proveedores de salud (clínicas) disponibles

**Endpoint Externo**: `GET /api/companies/{company_id}/health-providers`

**Headers**: `Authorization: Bearer {token}`

**Retorna**: Lista de clínicas

---

### `get_user_results(token)`

**Descripción**: Obtiene los resultados médicos del usuario autenticado

**Endpoint Externo**: `GET /api/parameters/results-user`

**Headers**: `Authorization: Bearer {token}`

**Retorna**: Diccionario con parámetros médicos y valores

---

### `send_appointment_to_api(appointment_api_data, token)`

**Descripción**: Crea una cita médica

**Endpoint Externo**: `POST /api/appointments`

**Headers**: `Authorization: Bearer {token}`

**Body**:
```json
{
    "user_id": 4,
    "product_id": 2,
    "health_provider_id": 1,
    "date_time": "2025-02-10T14:00:00.000Z"
}
```

**Retorna**: Response object de requests

---

## Funciones de IA (Bedrock)

### `analyze_user_intent(user_message, context_stage)`

**Descripción**: Analiza la intención del usuario usando Claude (Bedrock)

**Modelo**: `anthropic.claude-3-5-sonnet-20240620-v1:0`

**Retorna**: `'POSITIVA'`, `'NEGATIVA'`, `'AMBIGUA'`, `'PRODUCTOS'`, o `'NUEVA_CITA'`

---

### `generate_action_steps_with_ai(results, issues, is_healthy)`

**Descripción**: Genera pasos a seguir personalizados basados en resultados médicos

**Modelo**: `anthropic.claude-sonnet-4-5-20250929-v1:0`

**Max Tokens**: 150

**Retorna**: String con 4 pasos numerados (máximo 8-10 palabras por paso)

---

### `analyze_farewell_intent(message, session)`

**Descripción**: Detecta si el usuario se está despidiendo

**Modelo**: `anthropic.claude-3-5-sonnet-20240620-v1:0`

**Retorna**: `'DESPEDIDA'`, `'CONTINUANDO'`, o `'AMBIGUO'`

---

### `invoke_bedrock_smart(user_message, context_type, context_data)`

**Descripción**: Invoca Bedrock para conversación contextual general

**Modelo**: `anthropic.claude-sonnet-4-5-20250929-v1:0`

**Max Tokens**: 1000

**Parámetros**:
- `user_message` (string): Mensaje del usuario
- `context_type` (string): `'general'` o `'contextual'`
- `context_data` (string): Datos de contexto adicionales

**Retorna**: Respuesta generada por la IA

---

## Flujo de Conversación Completo

### 1. Autenticación

```
Usuario: ralf@gomind.cl
Stage: waiting_email → waiting_verification_code

Usuario: 1234
Stage: waiting_verification_code → main_menu
```

### 2. Menú Principal

```
Bianca: ¿Cómo te ayudamos hoy?
1. Agendar mi chequeo preventivo
2. Quiero analizar mis resultados de exámenes

Usuario: 1
Stage: main_menu → selecting_product
```

### 3. Selección de Producto

```
Bianca: Productos disponibles:
1. Chequeo Preventivo
2. Examen Completo

Usuario: 1
Stage: selecting_product → selecting_clinic
```

### 4. Agendamiento de Cita

```
Bianca: Clínicas disponibles:
1. Inmunomedica Concepción
2. Laboratorio Blanco Santiago

Usuario: 1
Stage: selecting_clinic → scheduling

Bianca: Días disponibles:
1. Lunes 10 de febrero
2. Martes 11 de febrero

Usuario: 1
Stage: scheduling → selecting_time

Bianca: Horarios disponibles:
1. 09:00
2. 10:00
...

Usuario: 3
Stage: selecting_time → confirming

Bianca: ¿Confirmo tu cita?

Usuario: Sí
Stage: confirming → completed
```

---

## Manejo de Sesiones

### Sistema de Persistencia

Las sesiones se almacenan en memoria usando un diccionario global:

```python
sessions = {}

def get_or_create_session(session_id):
    if session_id not in sessions:
        sessions[session_id] = ConversationSession(session_id)
    return sessions[session_id]

def save_session(session):
    sessions[session.session_id] = session
```

**Nota**: En producción, se recomienda usar Redis, MongoDB o PostgreSQL para persistencia.

---

## Mensajes Predefinidos

Todos los mensajes están centralizados en el diccionario `MESSAGES`:

```python
MESSAGES = {
    'verification_code_sent': "🔒 Para confirmar tu identidad...",
    'code_authentication_success': "🎉 ¡Perfecto! Ya verifiqué tu identidad.",
    'login_success_menu': "¡Bienvenido/a, {user_name}!...",
    'appointment_success': "¡Excelente! Tu cita quedó confirmada...",
    # ... más mensajes
}
```

---

## Rangos Médicos

Rangos de referencia para análisis de resultados:

```python
RANGES = {
    "Glicemia Basal": (75, 100),
    "Hemoglobina": (11.5, 14.5),
    "Colesterol": (0, 200),
    # ... 21 parámetros en total
}
```

---

## Códigos de Error

| Código | Descripción | Solución |
|--------|-------------|----------|
| `Usuario no encontrado` | Email no registrado en el sistema | Verificar email o registrarse |
| `Código inválido` | Código de verificación incorrecto | Reingresar código correcto |
| `Token de autenticación no disponible` | Sesión expirada | Reiniciar autenticación |
| `Clínica no encontrada` | ID de clínica inválido | Seleccionar clínica válida |
| `Error obteniendo resultados: 404` | Usuario sin resultados médicos | Contactar soporte |

---

## Integración con Twilio

### Configuración de Webhook en Twilio

1. Ir a Twilio Console → Messaging → Settings
2. Configurar webhook URL: `https://tu-dominio.com/webhook`
3. Método: `POST`
4. Content-Type: `application/x-www-form-urlencoded`

### Ejemplo de Configuración

```python
# Twilio enviará automáticamente:
# From: +56912345678
# Body: Hola Bianca

# appv1.py procesará y responderá automáticamente
```

---

## Seguridad

### Recomendaciones

1. **HTTPS**: Usar siempre HTTPS en producción
2. **Validación de Twilio**: Validar que requests vengan de Twilio usando firma
3. **Rate Limiting**: Implementar límite de requests por usuario
4. **Sanitización**: Validar y sanitizar todos los inputs del usuario
5. **Tokens**: Nunca exponer tokens en logs o respuestas

### Validación de Firma de Twilio

```python
from twilio.request_validator import RequestValidator

validator = RequestValidator(os.getenv('TWILIO_AUTH_TOKEN'))

@app.route('/webhook', methods=['POST'])
def twilio_webhook():
    signature = request.headers.get('X-Twilio-Signature', '')
    url = request.url
    params = request.form.to_dict()
    
    if not validator.validate(url, params, signature):
        return 'Unauthorized', 401
    
    # Procesar mensaje...
```

---

## Limitaciones

1. **Persistencia**: Sesiones en memoria se pierden al reiniciar servidor
2. **Escalabilidad**: No soporta múltiples instancias sin base de datos compartida
3. **Límite de Caracteres**: Twilio tiene límite de ~1600 caracteres por mensaje
4. **Timeout**: Twilio espera respuesta en máximo 15 segundos

---

## Troubleshooting

### Problema: "Error al invocar Bedrock"

**Causa**: Credenciales AWS incorrectas o región inválida

**Solución**: Verificar variables de entorno `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`

---

### Problema: "Error obteniendo productos: 401"

**Causa**: Token expirado o inválido

**Solución**: Usuario debe re-autenticarse ingresando email y código nuevamente

---

### Problema: Sesión se pierde entre mensajes

**Causa**: Servidor reiniciado o sesión no guardada

**Solución**: Implementar persistencia en base de datos (Redis/MongoDB)

---

## Ejemplo Completo de Integración

```python
from appv1 import process_message

# Simular conversación
session_id = "+56912345678"

# Paso 1: Enviar email
result1 = process_message(session_id, "ralf@gomind.cl")
print(result1['response'])
# "🔒 Para confirmar tu identidad, te envié un código..."

# Paso 2: Enviar código
result2 = process_message(session_id, "1234")
print(result2['response'])
# "🎉 ¡Perfecto! Ya verifiqué tu identidad..."

# Paso 3: Seleccionar opción
result3 = process_message(session_id, "1")
print(result3['response'])
# "Productos disponibles: 1. Chequeo Preventivo..."

# ... continuar flujo
```

---

## Contacto y Soporte

Para preguntas o problemas con la API, contactar al equipo de desarrollo de GoMind.

**Versión**: 1.0.0  
**Última actualización**: Febrero 2025
