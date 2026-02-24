import os
import json
import re
import boto3
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar cliente de Bedrock usando variables de entorno
bedrock_client = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

# Configurar API GoMind usando variables de entorno
API_BASE_URL = os.getenv("API_BASE_URL")
API_EMAIL = os.getenv("API_EMAIL")
API_PASSWORD = os.getenv("API_PASSWORD")

# Constantes centralizadas
SPANISH_WEEKDAYS = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes']
SPANISH_MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
API_TIMEOUT = 30
BEDROCK_MODEL_ID = "anthropic.claude-sonnet-4-5-20250929-v1:0"
BEDROCK_MAX_TOKENS = 1000

# ============================================
# CLASE DE SESIÓN
# ============================================
class ConversationSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.stage = 'initial'
        self.user_data = None
        self.messages = []
        self.context = ""
        self.company_id = None
        self.clinics = None
        self.user_email = None
        self.auth_token = None
        self.company_products = None
        self.user_profile = None
        self.selected_clinic = None
        self.selected_day = None
        self.selected_time = None
        self.next_days = None
        self.available_hours = None
        self.selected_product = None

# ============================================
# SISTEMA DE PERSISTENCIA DE SESIONES
# ============================================
sessions = {}

def get_or_create_session(session_id):
    """Obtiene o crea una sesión para el usuario"""
    if session_id not in sessions:
        sessions[session_id] = ConversationSession(session_id)
    return sessions[session_id]

def save_session(session):
    """Guarda la sesión en memoria"""
    sessions[session.session_id] = session

# ============================================
# MENSAJES
# ============================================
MESSAGES = {
    'healthy_results_intro': "¡Excelente noticia, tus valores están todos dentro del rango saludable:\n\n{results}\n\nEstos resultados indican que estás llevando un estilo de vida saludable. ¡Felicitaciones! Sigue así con tus buenos hábitos de alimentación y ejercicio.",
    'unhealthy_results_intro': "He revisado tus valores y me gustaría comentarte lo que veo:\n\n{issues}\n\nAunque no están muy elevados, sería recomendable que un médico los revise más a fondo.",
    'disclaimer': "\n\nLos resultados obtenidos mediante IA se basan exclusivamente en los indicadores analizados y deben entenderse como una referencia de apoyo.\nLa interpretación final y la toma de decisiones corresponden siempre al criterio profesional de los colaboradores.",
    'appointment_question': "¿Te gustaría que te ayude a agendar una cita para que puedas discutir estos resultados con un profesional?",
    'appointment_success': "¡Excelente! Tu cita quedó confirmada para el {day} a las {time} en {clinic}.\n\nLa cita ha sido registrada correctamente en nuestro sistema. Te enviaremos un recordatorio antes de la hora programada.\n\n",
    'appointment_error': "Lo siento, hubo un problema al agendar tu cita (Error {status}). Por favor, intenta nuevamente en unos minutos o contacta a nuestro soporte técnico.\n\n¿Hay algo más en lo que pueda ayudarte mientras tanto?",
    'connection_error': "Lo siento, hubo un problema de conexión al procesar tu cita. Por favor, verifica tu conexión a internet e intenta nuevamente, o contacta a nuestro soporte técnico.\n\n¿Hay algo más en lo que pueda ayudarte mientras tanto?",
    'clinic_unavailable': "Lo siento, no hay clínicas disponibles en este momento. ¿Te gustaría intentarlo más tarde o tienes alguna otra consulta?",
    'clinic_error': "Error obteniendo clínicas disponibles: {error}. ¿Te gustaría intentarlo más tarde?",
    'clinic_not_recognized': "No reconocí esa clínica. ¿Puedes elegir una de las opciones disponibles?",
    'day_not_recognized': "No reconocí ese día. ¿Puedes elegir uno de los disponibles usando el número (1, 2, 3) o el nombre del día?",
    'time_unavailable': "Esa opción no está disponible. Por favor, elige un número de las opciones mostradas.",
    'time_format_error': "Por favor, responde con el número de la opción que prefieres (ejemplo: 1, 2, 3).",
    'appointment_declined': "Entiendo, no confirmo la cita. ¿Te gustaría reagendar para otro día u horario, o hay algo más en lo que pueda ayudarte?",
    'appointment_general_declined': "Entiendo. Si cambias de opinión y quieres agendar una cita más tarde, solo dímelo. ¿Hay algo más en lo que pueda ayudarte?",
    'new_appointment_offer': "¡Perfecto! Te ayudo a agendar una nueva cita. ¿Esta cita es para revisar nuevos resultados médicos o es una consulta de seguimiento?",
    'new_appointment_start': "Excelente, iniciemos el proceso para tu nueva cita. Tenemos estas clínicas disponibles:",
    'new_appointment_medical_request': "Entiendo que necesitas una nueva cita. Para brindarte el mejor servicio, ¿podrías compartirme el ID de usuario para revisar tus resultados médicos más recientes? Esto me ayudará a determinar si necesitas una cita médica.",
    'login_success_menu': "¡Bienvenido/a, {user_name}!\n\n¿Cómo te ayudamos hoy?\n\n- Agendar mi cita\n- Revisa mi examen\n\nEscribe la opción que prefieras.",
    'products_menu': "Gracias, voy a proceder a ayudarte con tu agendamiento, por favor selecciona alguno de los productos disponibles\n\n{products_list}\n¿Cuál producto te interesa? Escribe el nombre del producto.",
    'product_selected': "Perfecto ✅ Para agendar tu **{product_name}**, contamos con los siguientes centros médicos:",
    'invalid_menu_option': "No entendí tu selección. Por favor, escribe:\n- 'Agendar mi cita' para agendar una cita\n- 'Revisa mi examen' para análisis médico",
    'invalid_product_option': "No reconocí ese producto. Por favor, escribe el nombre de uno de los productos disponibles.",
    'verification_code_sent': "🔒 Para confirmar tu identidad, te envié un código de verificación a tu correo.\nEscríbelo aquí para continuar",
    'code_authentication_success': "🎉 ¡Perfecto! Ya verifiqué tu identidad.",
    'invalid_code': "Código inválido. Por favor, verifica el código e intenta nuevamente:",
    'code_error': "Error procesando el código. Por favor, intenta nuevamente:"
}

# Rangos de referencia médica
RANGES = {
    "Porcentaje (Protrombina)": (70, 100),
    "INR": (0.8, 1.2),
    "TTPK (Tiempo de Tromboplastina)": (25, 40),
    "Glicemia Basal": (75, 100),
    "Uremia": (0, 50),
    "Recuento de Eritrocitos": (3.9, 5.3),
    "Hemoglobina": (11.5, 14.5),
    "Hematocrito": (37, 47),
    "VCM": (80, 100),
    "HCM": (26, 34),
    "CHCM": (31, 36),
    "Recuento de Leucocitos": (4, 10.5),
    "Linfocitos": (20, 40),
    "Neutrófilos": (55, 70),
    "Monocitos": (2, 10),
    "Eosinófilos": (0, 5),
    "Basófilos": (0, 2),
    "Recuento de Neutrófilos (Absoluto)": (2, 7),
    "Recuento de Linfocitos (Absoluto)": (0.8, 4),
    "Recuento de Plaquetas": (150, 400),
    "VHS (Velocidad de sedimentación globular)": (0, 11),
}

CLINIC_MAPPING = {
    "Inmunomedica Concepción": 1,
    "Laboratorio Blanco Santiago": 3,
    "Red Salud Santiago Centro": 4
}

BIANCA_PROMPT = """
Eres "Bianca", asistente virtual de GoMind para salud física y emocional. Ayudas a interpretar resultados médicos y agendar citas con tono empático, claro y profesional.

### Personalidad: Usa expresiones naturales: "Perfecto", "Entiendo", "Excelente". Evita tecnicismos innecesarios y frases repetitivas. Mantén conversación coherente.

### Rangos Médicos (21 parámetros)
**Coagulación:** Protrombina 70-100%, INR 0.8-1.2, TTPK 25-40 seg
**Metabolismo:** Glicemia 75-100 mg/dL, Uremia 0-50 mg/dL  
**Hemograma:** Eritrocitos 3.9-5.3 M/μL, Hemoglobina 11.5-14.5 g/dL, Hematocrito 37-47%, VCM 80-100 fL, HCM 26-34 pg, CHCM 31-36 g/dL
**Leucocitos:** Total 4-10.5 K/μL, Linfocitos 20-40%, Neutrófilos 55-70%, Monocitos 2-10%, Eosinófilos 0-5%, Basófilos 0-2%, Neutrófilos abs 2-7 K/μL, Linfocitos abs 0.8-4 K/μL
**Otros:** Plaquetas 150-400 K/μL, VHS 0-11 mm/h

### Flujo: Valores normales → felicita, NO ofrezcas cita. Valores anormales → explica brevemente, recomienda cita. Si acepta cita, muestra 3 días hábiles con horarios 09:00-18:00.

### Intenciones de Agendamiento: Si preguntas sobre cita y responden "sí", "claro", "vamos", "dale", "ok" → procede INMEDIATAMENTE al agendamiento sin pedir más información.

### Contexto: Mantén coherencia conversacional. Si usuario dice "no" → responde empáticamente sin reiniciar. Para consultas generales: redirige amablemente a resultados, citas o productos.
"""

# ============================================
# FUNCIONES DE API
# ============================================
def send_verification_code(email):
    """Envía código de verificación al correo del usuario"""
    url = f"{API_BASE_URL}/api/auth/login/user-exist"
    payload = {"email": email}
    response = requests.post(url, json=payload, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        user_exists = data.get('user_exist', True)
        message = data.get('message', '')
        
        if not user_exists:
            raise Exception(message if message else "Usuario no encontrado")
        
        return True
    else:
        raise Exception(f"Error enviando código: {response.text}")

def authenticate_with_code(email, auth_code):
    """Autentica con código de verificación para obtener token completo"""
    url = f"{API_BASE_URL}/api/auth/login/wsp"
    payload = {"email": email, "auth_code": int(auth_code)}
    
    response = requests.post(url, json=payload, timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        
        if not data.get('success', True):
            raise Exception(f"Código inválido: {data.get('message', 'Código de verificación incorrecto')}")
        
        token = data.get('token')
        company_id = data.get('company', {}).get('company_id')
        user_data = data.get('user', {})
        
        if not token or not company_id or not user_data:
            raise Exception("Error en autenticación: datos incompletos del servidor")
        
        return {'token': token, 'company_id': company_id, 'user_data': user_data}
    else:
        raise Exception(f"Error autenticando con código: {response.text}")

def extract_parameter(analysis_results):
    if "VALOR " in analysis_results:
        start = analysis_results.find("VALOR ") + 6
        end = analysis_results.find(".", start)
        if end == -1:
            end = len(analysis_results)
        param = analysis_results[start:end].strip()
        corrections = {
            "Glisea Basal": "Glicemia Basal",
            "Recuendo de Eritrocitos": "Recuento de Eritrocitos"
        }
        return corrections.get(param, param)
    elif "Recomendacion" in analysis_results or "recomendacion" in analysis_results:
        start = analysis_results.find("Recomendacion") + 13 if "Recomendacion" in analysis_results else analysis_results.find("recomendacion") + 13
        param = analysis_results[start:].strip()
        return param
    else:
        return "Desconocido"

def get_company_products(company_id, token):
    url = f"{API_BASE_URL}/api/companies/{company_id}/products"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get('products', [])
    else:
        raise Exception(f"Error obteniendo productos: {response.status_code} - {response.text}")

def get_health_providers(company_id, token):
    url = f"{API_BASE_URL}/api/companies/{company_id}/health-providers"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get('healthProviders', [])
    else:
        raise Exception(f"Error obteniendo proveedores de salud: {response.status_code} - {response.text}")

def get_user_results(token):
    url = f"{API_BASE_URL}/api/parameters/results-user"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list):
            if len(data) == 0:
                raise Exception("Paciente no identificado o sin resultados disponibles.")
            results = {}
            for item in data:
                param = extract_parameter(item['analysis_results'])
                value = item['value']
                results[param] = value
            return results
        else:
            return data
    else:
        raise Exception(f"Error obteniendo resultados: {response.status_code} - {response.text}")

def send_appointment_to_api(appointment_api_data, token):
    url = f"{API_BASE_URL}/api/appointments"
    headers = {"Authorization": f"Bearer {token}"}

    if not token:
        raise ValueError("Token de autenticación no disponible")

    response = requests.post(url, json=appointment_api_data, headers=headers, timeout=30)
    return response

# ============================================
# FUNCIONES UTILITARIAS
# ============================================
def is_valid_email(email):
    """Valida formato básico de email usando regex"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) and ' ' not in email

def find_match(prompt, items, key_func=None):
    """Función consolidada para encontrar coincidencias en listas"""
    prompt_lower = prompt.lower()
    
    for item in items:
        if key_func:
            text_to_compare = key_func(item)
        elif isinstance(item, dict) and 'name' in item:
            text_to_compare = item['name']
        else:
            text_to_compare = str(item)
        
        text_words = text_to_compare.lower().split()
        if any(word in prompt_lower for word in text_words):
            return item['name'] if isinstance(item, dict) and 'name' in item else item
    
    return None

def has_user_data(session):
    """Verifica si hay datos de usuario disponibles"""
    return session.user_data and session.user_data.get('id')

def is_authenticated(session):
    """Verifica si el usuario está autenticado"""
    return session.auth_token is not None

def get_user_info(session):
    """Obtiene información del usuario de manera segura"""
    if has_user_data(session):
        return {
            'id': session.user_data.get('id'),
            'name': session.user_data.get('name', 'Usuario')
        }
    return {'id': None, 'name': 'Usuario'}

def format_spanish_date(date_obj):
    """Formatea una fecha en español"""
    day_name = SPANISH_WEEKDAYS[date_obj.weekday()]
    day_num = date_obj.day
    month_name = SPANISH_MONTHS[date_obj.month - 1]
    return f"{day_name} {day_num} de {month_name}"

def convert_spanish_date_to_iso(date_str, time_str):
    try:
        parts = date_str.split()
        if len(parts) >= 4 and parts[2] == 'de':
            day = int(parts[1])
            month_name = parts[3].lower()

            months = {
                'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
                'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
            }

            month = months.get(month_name)
            if not month:
                raise ValueError(f"Mes no reconocido: {month_name}")

            current_year = datetime.now().year
            hour, minute = map(int, time_str.split(':'))
            dt = datetime(current_year, month, day, hour, minute, 0)

            if dt < datetime.now():
                dt = datetime(current_year + 1, month, day, hour, minute, 0)

            iso_string = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            return iso_string

    except Exception as e:
        raise ValueError(f"Error convirtiendo fecha: {date_str} {time_str} - {str(e)}")

def get_next_business_days(n=3):
    """Obtiene los próximos días hábiles excluyendo fines de semana"""
    days = []
    current = datetime.now()

    while len(days) < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days.append(format_spanish_date(current))

    return days

def get_conversation_context(session):
    """Genera un resumen del contexto conversacional actual"""
    context_parts = []
    
    if has_user_data(session):
        user_info = get_user_info(session)
        context_parts.append(f"Usuario: {user_info['name']}")
    
    current_stage = session.stage
    stage_descriptions = {
        'main_menu': 'en menú principal',
        'selecting_product': 'seleccionando producto',
        'analyzing': 'revisando si quiere agendar cita',
        'selecting_clinic': 'eligiendo clínica',
        'scheduling': 'eligiendo día',
        'selecting_time': 'eligiendo hora',
        'confirming': 'confirmando cita',
        'completed': 'proceso completado'
    }
    stage_desc = stage_descriptions.get(current_stage, current_stage)
    context_parts.append(f"Estado: {stage_desc}")
    
    if session.messages:
        recent_messages = session.messages[-3:]
        for msg in recent_messages:
            role = "Usuario" if msg['role'] == 'user' else "Bianca"
            content = msg['content'][:60] + "..." if len(msg['content']) > 60 else msg['content']
            context_parts.append(f"{role}: {content}")
    
    return " | ".join(context_parts)

def handle_appointment_error(error, error_type='general'):
    if error_type == 'clinic_fetch':
        return MESSAGES['clinic_error'].format(error=str(error)), 'completed'
    elif error_type == 'api_connection':
        return MESSAGES['connection_error'], 'completed'
    elif error_type == 'api_error':
        return MESSAGES['appointment_error'].format(status=getattr(error, 'status_code', 'Unknown')), 'completed'
    else:
        return f"Error inesperado: {str(error)}. ¿Te gustaría intentarlo más tarde?", 'completed'

def validate_appointment_data(session):
    required_fields = ['selected_clinic', 'selected_day', 'selected_time']
    missing_fields = [field for field in required_fields if not getattr(session, field, None)]
    
    if missing_fields:
        raise ValueError(f"Faltan datos requeridos: {', '.join(missing_fields)}")
    
    if not session.user_data or not session.user_data.get('id'):
        raise ValueError("ID de usuario no disponible")
    
    return True

def prepare_api_appointment_data(session):
    clinic_name = session.selected_clinic
    
    health_provider_id = None
    for clinic in session.clinics:
        if clinic['name'] == clinic_name:
            health_provider_id = clinic['health_provider_id']
            break

    if not health_provider_id:
        raise ValueError(f"Clínica no encontrada en datos del endpoint: {clinic_name}")

    if not session.user_data:
        raise ValueError("user_data no está disponible")
    
    if 'id' not in session.user_data:
        raise ValueError(f"Campo 'id' no encontrado en user_data")

    try:
        date_time_iso = convert_spanish_date_to_iso(
            session.selected_day,
            session.selected_time
        )
    except Exception as e:
        raise ValueError(f"Error procesando fecha y hora: {str(e)}")

    return {
        "user_id": session.user_data["id"],
        "product_id": 2,
        "health_provider_id": health_provider_id,
        "date_time": date_time_iso
    }

# ============================================
# FUNCIONES DE ANÁLISIS CON IA
# ============================================
def analyze_results(results_dict):
    issues = []
    needs_appointment = False

    for param, value in results_dict.items():
        if param in RANGES:
            min_val, max_val = RANGES[param]
            if not (min_val <= value <= max_val):
                issues.append(f"{param} fuera de rango: {value}")
                needs_appointment = True

    return issues, needs_appointment

def generate_action_steps_with_ai(results, issues, is_healthy):
    """Genera pasos a seguir personalizados usando IA"""
    try:
        if is_healthy:
            results_text = ", ".join([f"{k}: {v}" for k, v in results.items()])
            prompt = f"""Eres un asistente médico virtual. El usuario tiene estos resultados de laboratorio SALUDABLES:
{results_text}

Genera exactamente 4 pasos BREVES para mantener su buena salud.

Requisitos CRÍTICOS:
- Máximo 8-10 palabras por paso
- Lenguaje directo y accionable
- Sin explicaciones adicionales
- Formato: lista numerada (1., 2., 3., 4.)

Responde SOLO con los 4 pasos breves."""
        else:
            issues_text = "\n".join(issues)
            results_text = ", ".join([f"{k}: {v}" for k, v in results.items()])
            prompt = f"""Eres un asistente médico virtual. El usuario tiene estos problemas detectados en sus exámenes:
{issues_text}

Valores completos: {results_text}

Genera exactamente 4 pasos BREVES para mejorar estos valores específicos.

Requisitos CRÍTICOS:
- Máximo 8-10 palabras por paso
- Lenguaje directo y accionable
- Enfocados en los problemas detectados
- Formato: lista numerada (1., 2., 3., 4.)
- Último paso debe ser consulta médica

Responde SOLO con los 4 pasos breves."""
        
        response = bedrock_client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 150,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        result = json.loads(response['body'].read())
        steps = result['content'][0]['text'].strip()
        
        return f"\n\n**Pasos a Seguir:**\n{steps}"
        
    except Exception as e:
        if is_healthy:
            return "\n\n**Pasos a Seguir:**\n1. Mantén tus hábitos saludables actuales\n2. Programa tu próximo chequeo preventivo\n3. Continúa con actividad física regular\n4. Mantén una alimentación balanceada"
        else:
            return "\n\n**Pasos a Seguir:**\n1. Consulta con tu médico sobre estos resultados\n2. Sigue las recomendaciones médicas\n3. Monitorea tus valores regularmente\n4. Mantén hábitos de vida saludables"

def analyze_user_intent(user_message, context_stage):
    """Analiza la intención del usuario usando Bedrock"""
    try:
        context_descriptions = {
            'analyzing': 'Se le preguntó al usuario si quiere agendar una cita médica',
            'confirming': 'Se le está pidiendo confirmación final para agendar una cita',
            'completed': 'La conversación terminó y el usuario podría querer una nueva cita',
            'showing_products': 'Se pueden mostrar productos de salud disponibles',
            'general': 'Conversación general, detectar cualquier intención'
        }
        
        context_desc = context_descriptions.get(context_stage, 'Conversación general')
        
        prompt = f"""Analiza la siguiente respuesta del usuario y determina su intención exacta.

Contexto: {context_desc}
Mensaje del usuario: "{user_message}"

Analiza si la intención es:
- POSITIVA: Quiere proceder, acepta, está de acuerdo (incluye respuestas como "podría ser", "tal vez", "me parece bien")
- NEGATIVA: No quiere proceder, rechaza claramente
- AMBIGUA: No está claro, necesita clarificación
- PRODUCTOS: Quiere ver productos o servicios disponibles
- NUEVA_CITA: Quiere agendar una nueva cita adicional

Responde ÚNICAMENTE con una de estas palabras: POSITIVA, NEGATIVA, AMBIGUA, PRODUCTOS, o NUEVA_CITA"""

        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        response_body = json.loads(response['body'].read())
        intent = response_body['content'][0]['text'].strip().upper()
        
        valid_intents = ['POSITIVA', 'NEGATIVA', 'AMBIGUA', 'PRODUCTOS', 'NUEVA_CITA']
        if intent in valid_intents:
            return intent
        else:
            return 'AMBIGUA'
            
    except Exception as e:
        user_lower = user_message.lower()
        if any(word in user_lower for word in ['no', 'nunca', 'jamás']):
            return 'NEGATIVA'
        elif any(word in user_lower for word in ['si', 'sí', 'yes', 'ok', 'claro']):
            return 'POSITIVA'
        else:
            return 'AMBIGUA'

def analyze_farewell_intent(message, session):
    """Analiza si el usuario se está despidiendo usando Bedrock"""
    try:
        conversation_context = get_conversation_context(session)
        
        prompt = f"""Analiza si el usuario se está despidiendo o finalizando la conversación.

Contexto de la conversación: {conversation_context}
Mensaje del usuario: "{message}"

Determina la intención:
- DESPEDIDA: Se está despidiendo claramente (gracias, adiós, hasta luego, nos vemos, chao, bye, eso es todo, ya terminé)
- CONTINUANDO: Quiere seguir conversando o hacer algo más
- AMBIGUO: No está claro

Responde ÚNICAMENTE con: DESPEDIDA, CONTINUANDO, o AMBIGUO"""

        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        response_body = json.loads(response['body'].read())
        intent = response_body['content'][0]['text'].strip().upper()
        
        return intent if intent in ['DESPEDIDA', 'CONTINUANDO', 'AMBIGUO'] else 'CONTINUANDO'
        
    except Exception as e:
        farewell_keywords = ['gracias', 'adiós', 'hasta luego', 'nos vemos', 'chao', 'bye', 
                           'eso es todo', 'ya terminé', 'ya está', 'perfecto gracias']
        message_lower = message.lower()
        if any(keyword in message_lower for keyword in farewell_keywords):
            return 'DESPEDIDA'
        return 'CONTINUANDO'

def invoke_bedrock_smart(user_message, context_type='general', context_data=""):
    """Función consolidada para invocar Bedrock con diferentes tipos de contexto"""
    if context_type == 'contextual':
        conversation_context = context_data
        full_prompt = f"""{BIANCA_PROMPT}

CONTEXTO CONVERSACIONAL ACTUAL:
{conversation_context}

INSTRUCCIONES ADICIONALES:
- Responde de manera coherente con el contexto de la conversación
- Si el usuario ya completó un proceso, reconócelo en tu respuesta
- Mantén un tono natural y contextual
- Si detectas que el usuario podría estar finalizando, ofrece ayuda adicional de manera sutil

Usuario: {user_message}

Bianca:"""
    else:
        full_prompt = f"{BIANCA_PROMPT}\n\nContexto de conversación: {context_data}\n\nUsuario: {user_message}\n\nBianca:"

    try:
        response = bedrock_client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": BEDROCK_MAX_TOKENS,
                "messages": [{"role": "user", "content": full_prompt}]
            })
        )
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    except Exception as e:
        return f"Error al invocar Bedrock: {str(e)}"

# ============================================
# FUNCIONES DE LÓGICA DE NEGOCIO
# ============================================
def generate_medical_response(results, issues, user_name, session):
    if not issues:
        results_text = "\n".join([f"- {k}: {v}" for k, v in results.items()])
        response = f"{user_name}! Gracias por compartir tus resultados conmigo. Me da gusto poder revisarlos contigo.\n\n"
        response += MESSAGES['healthy_results_intro'].format(results=results_text)
        
        action_steps = generate_action_steps_with_ai(results, issues, is_healthy=True)
        response += action_steps
        response += MESSAGES['disclaimer']
        
        return response, 'completed'
    else:
        issues_text = "\n".join([f"- {issue}" for issue in issues])
        response = f"{user_name}! Gracias por compartir tus resultados conmigo. "
        response += MESSAGES['unhealthy_results_intro'].format(issues=issues_text)
        
        action_steps = generate_action_steps_with_ai(results, issues, is_healthy=False)
        response += action_steps
        response += MESSAGES['disclaimer']
        response += f"\n\n{MESSAGES['appointment_question']}"
        
        return response, 'analyzing'

def process_medical_results(user_id, user_name, session):
    try:
        results = get_user_results(session.auth_token)
        session.user_data = {"id": user_id, "results": results}
        
        issues, needs_appointment = analyze_results(results)
        
        return generate_medical_response(results, issues, user_name, session)
            
    except Exception as e:
        error_msg = str(e)
        if "Paciente no identificado" in error_msg:
            return f"Lo siento, no se logró identificar al paciente con el ID {user_id}. Verifica que el número sea correcto o contacta a soporte. ¿Hay algo más en lo que pueda ayudarte?", 'completed'
        else:
            return f"Error obteniendo resultados de la API: {error_msg}. ¿Puedes compartir tus resultados médicos en formato JSON? Ejemplo: {{\"Glicemia Basal\": 90, \"Hemoglobina\": 13}}", 'waiting_json'

def generate_farewell_response(session):
    """Genera una respuesta de despedida contextual"""
    user_info = get_user_info(session)
    user_name = user_info['name'] if user_info['name'] != 'Usuario' else ""
    
    has_appointment = False
    appointment_info = ""
    
    if session.selected_clinic:
        has_appointment = True
        clinic = session.selected_clinic
        day = session.selected_day
        time = session.selected_time
        if clinic and day and time:
            appointment_info = f" para tu cita del {day} a las {time} en {clinic}"
    
    if has_appointment and appointment_info:
        if user_name:
            return f"¡Perfecto, {user_name}! Me alegra haber podido ayudarte{appointment_info}. ¡Que tengas un excelente día y nos vemos pronto!"
        else:
            return f"¡Perfecto! Me alegra haber podido ayudarte{appointment_info}. ¡Que tengas un excelente día y nos vemos pronto!"
    else:
        if user_name:
            return f"¡Gracias por usar nuestros servicios, {user_name}! Espero haber podido ayudarte. ¡Que tengas un excelente día!"
        else:
            return "¡Gracias por usar nuestros servicios! Espero haber podido ayudarte. ¡Que tengas un excelente día!"

# ============================================
# HANDLERS DE FLUJO
# ============================================
def handle_appointment_request(session):
    try:
        clinics = get_health_providers(session.company_id, session.auth_token)
        
        if not clinics:
            return MESSAGES['clinic_unavailable'], 'completed'
            
        session.clinics = clinics
        
        response = f"Contamos con los siguientes centros médicos:\n\n"
        for i, clinic in enumerate(clinics):
            response += f"{i+1}. {clinic['name']}\n"
        response += "\n¿En cuál clínica prefieres agendar tu cita?\nResponde con el número de tu opción."
        return response, 'selecting_clinic'
    except Exception as e:
        return handle_appointment_error(e, 'clinic_fetch')

def handle_clinic_selection(prompt, session):
    clinics = session.clinics
    selected_clinic = None
    
    try:
        clinic_num = int(prompt.strip()) - 1
        if 0 <= clinic_num < len(clinics):
            selected_clinic = clinics[clinic_num]['name']
    except ValueError:
        selected_clinic = find_match(prompt, clinics)
    
    if not selected_clinic:
        return MESSAGES['clinic_not_recognized'], 'selecting_clinic'
        
    session.selected_clinic = selected_clinic
    next_days = get_next_business_days(3)
    session.next_days = next_days
    response = f"¡Excelente! Has seleccionado {selected_clinic}.\n\nAhora, tengo disponibilidad para agendar una cita en los próximos días hábiles:\n\n"
    for i, day in enumerate(next_days):
        response += f"{i+1}. {day}\n"
    response += "\n¿Para qué día te gustaría agendar? (Selecciona el numero)"
    return response, 'scheduling'

def handle_day_selection(prompt, session):
    next_days = session.next_days
    selected_day = None
    
    try:
        day_num = int(prompt.strip()) - 1
        if 0 <= day_num < len(next_days):
            selected_day = next_days[day_num]
    except ValueError:
        selected_day = find_match(prompt, next_days)
    
    if not selected_day:
        return MESSAGES['day_not_recognized'], 'scheduling'
        
    hours = [f"{h}:00" for h in range(9, 19)]
    hours_str = "\n".join(f"{i+1}. {h}" for i, h in enumerate(hours))
    response = f"Genial, el {selected_day} tengo disponibilidad en los siguientes horarios:\n\n{hours_str}\n\n¿A qué hora te gustaría agendar? Por favor, Responde con el número de tu opción (1-{len(hours)})."
    
    session.selected_day = selected_day
    session.available_hours = hours
    return response, 'selecting_time'

def handle_time_selection(prompt, session):
    user_input = prompt.strip()
    
    available_hours = session.available_hours if session.available_hours else [f"{h}:00" for h in range(9, 19)]
    
    try:
        option_num = int(user_input)
        
        if 1 <= option_num <= len(available_hours):
            selected_hour = available_hours[option_num - 1]
            response = f"Perfecto, reservo para el {session.selected_day} a las {selected_hour}. ¿Confirmo tu cita?"
            session.selected_time = selected_hour
            return response, 'confirming'
        else:
            return f"Por favor, elige un número entre 1 y {len(available_hours)}.", 'selecting_time'
            
    except ValueError:
        try:
            if ":" in user_input:
                hour, minute = user_input.split(":")
                hour_num = int(hour)
            else:
                hour_num = int(user_input)
                user_input = f"{hour_num}:00"
            
            if not (9 <= hour_num <= 18):
                return f"Esa hora no está disponible. Por favor, elige un número entre 1 y {len(available_hours)}.", 'selecting_time'
                
            response = f"Perfecto, reservo para el {session.selected_day} a las {user_input}. ¿Confirmo tu cita?"
            session.selected_time = user_input
            return response, 'confirming'
            
        except ValueError:
            return f"Por favor, responde con el número de la opción que prefieres (1-{len(available_hours)}).", 'selecting_time'

def handle_appointment_confirmation(session):
    try:
        validate_appointment_data(session)

        api_appointment_data = prepare_api_appointment_data(session)
        api_response = send_appointment_to_api(api_appointment_data, session.auth_token)

        if api_response.status_code in [200, 201]:
            return MESSAGES['appointment_success'].format(
                day=session.selected_day,
                time=session.selected_time,
                clinic=session.selected_clinic
            ), 'completed'
        else:
            return handle_appointment_error(api_response, 'api_error')

    except requests.exceptions.RequestException:
        return handle_appointment_error(None, 'api_connection')
    except ValueError as e:
        if "Faltan datos requeridos" in str(e):
            return handle_appointment_request(session)
        else:
            return handle_appointment_error(e, 'general')
    except Exception as e:
        return handle_appointment_error(e, 'general')

def handle_appointment_flow(stage, prompt, session):
    if stage == 'analyzing':
        intent = analyze_user_intent(prompt, 'analyzing')
        if intent == 'POSITIVA':
            return handle_appointment_request(session)
        elif intent == 'AMBIGUA':
            return "¿Te gustaría que te ayude a agendar una cita? Por favor responde sí o no para continuar.", 'analyzing'
        else:
            return MESSAGES['appointment_general_declined'], 'completed'
    
    elif stage == 'selecting_clinic':
        return handle_clinic_selection(prompt, session)
    
    elif stage == 'scheduling':
        return handle_day_selection(prompt, session)
    
    elif stage == 'selecting_time':
        return handle_time_selection(prompt, session)
    
    elif stage == 'confirming':
        intent = analyze_user_intent(prompt, 'confirming')
        if intent == 'POSITIVA':
            return handle_appointment_confirmation(session)
        elif intent == 'AMBIGUA':
            return "¿Confirmas tu cita? Por favor responde sí o no.", 'confirming'
        else:
            session.selected_time = None
            return MESSAGES['appointment_declined'], 'completed'
    
    return None, None

def handle_main_menu_selection(prompt, session):
    """Maneja la selección del menú principal después del login"""
    user_choice = prompt.strip().lower()
    
    # Palabras clave para agendar cita
    agendar_keywords = ['agendar', 'cita', 'chequeo', 'preventivo', 'producto']
    
    # Palabras clave para revisar examen
    revisar_keywords = ['revisa', 'revisar', 'examen', 'examenes', 'exámenes', 'analizar', 'resultado', 'médico', 'medico']
    
    # Detectar intención por palabras clave
    if any(keyword in user_choice for keyword in agendar_keywords):
        return show_products_menu(session)
    elif any(keyword in user_choice for keyword in revisar_keywords):
        return start_medical_analysis(session)
    else:
        return MESSAGES['invalid_menu_option'], 'main_menu'

def show_products_menu(session):
    """Muestra el menú de productos disponibles"""
    if not session.company_products:
        return "No hay productos disponibles en este momento. ¿Te gustaría hacer un análisis médico en su lugar?", 'main_menu'
    
    products_list = ""
    for product in session.company_products:
        name = product.get('name', 'Producto sin nombre')
        products_list += f"- {name}\n"
    
    response = MESSAGES['products_menu'].format(products_list=products_list)
    return response, 'selecting_product'

def handle_product_selection(prompt, session):
    """Maneja la selección de un producto específico"""
    selected_product = None
    
    # Intentar primero con número (retrocompatibilidad)
    try:
        product_num = int(prompt.strip()) - 1
        if 0 <= product_num < len(session.company_products):
            selected_product = session.company_products[product_num]
    except ValueError:
        pass
    
    # Si no funcionó con número, buscar por nombre
    if not selected_product:
        selected_product = find_match(prompt, session.company_products)
    
    # Si encontró el producto
    if selected_product:
        product_name = selected_product.get('name', 'Producto seleccionado')
        session.selected_product = selected_product
        
        response = MESSAGES['product_selected'].format(product_name=product_name)
        appointment_response, appointment_stage = handle_appointment_request(session)
        return f"{response}\n\n{appointment_response}", appointment_stage
    else:
        return MESSAGES['invalid_product_option'], 'selecting_product'

def start_medical_analysis(session):
    """Inicia el flujo de análisis médico (opción 2)"""
    if session.user_data and session.user_data.get('id'):
        user_id = session.user_data['id']
        user_name = session.user_data.get('name', 'Usuario')
        
        return process_medical_results(user_id, user_name, session)
    else:
        return "Para analizar tus resultados médicos, por favor ingresa tu número de identificación:", 'authenticated'

def handle_medical_input(prompt, session):
    if prompt.strip().isdigit() and len(prompt.strip()) > 0:
        user_id = prompt.strip()
        user_name = "Usuario"
        return process_medical_results(user_id, user_name, session)
    
    try:
        data = json.loads(prompt)
        if isinstance(data, dict) and any(key in str(data).lower() for key in ['glicemia', 'hemoglobina', 'colesterol', 'glucosa']):
            user_name = data.get('nombre_usuario', 'Usuario')
            results = {k: v for k, v in data.items() if k != 'nombre_usuario'}
            session.user_data = {"results": results}
            
            issues, needs_appointment = analyze_results(results)
            return generate_medical_response(results, issues, user_name, session)
    except json.JSONDecodeError:
        pass
    
    return None, None

def handle_contextual_conversation(prompt, session):
    """Maneja conversación con contexto completo y detección de despedidas"""
    farewell_intent = analyze_farewell_intent(prompt, session)
    
    if farewell_intent == 'DESPEDIDA':
        return generate_farewell_response(session), 'conversation_ended'
    
    conversation_context = get_conversation_context(session)
    return invoke_bedrock_smart(prompt, 'contextual', conversation_context), 'completed'

def handle_authentication_flow(stage, prompt, session):
    if stage == 'waiting_email':
        email = prompt.strip().lower()
        if is_valid_email(email):
            session.user_email = email
            
            try:
                send_verification_code(email)
                return MESSAGES['verification_code_sent'], 'waiting_verification_code'
            except Exception as e:
                error_msg = str(e)
                if "Usuario no encontrado" in error_msg or "No encontramos" in error_msg:
                    return error_msg, 'waiting_email'
                else:
                    return f"Error enviando código de verificación: {error_msg}. Por favor, intenta nuevamente.", 'waiting_email'
        else:
            return "El dato ingresado no parece ser válido. Por favor, verifica la información.", 'waiting_email'
    
    elif stage == 'waiting_verification_code':
        verification_code = prompt.strip()
        
        try:
            auth_data = authenticate_with_code(session.user_email, verification_code)
            
            session.auth_token = auth_data['token']
            session.company_id = auth_data['company_id']
            
            user_data = auth_data['user_data']
            
            user_id = user_data.get('user_id') or user_data.get('id') or user_data.get('userId')
            user_name = user_data.get('name', 'Usuario')
            
            session.user_data = {
                'id': user_id,
                'name': user_name
            }
            
            try:
                products = get_company_products(auth_data['company_id'], auth_data['token'])
                session.company_products = products
            except Exception as prod_error:
                session.company_products = []
            
            user_name = auth_data['user_data'].get('name', 'Usuario')
            
            success_message = MESSAGES['code_authentication_success']
            menu_message = MESSAGES['login_success_menu'].format(user_name=user_name)
            
            return f"{success_message}\n\n{menu_message}", 'main_menu'
            
        except Exception as e:
            error_msg = str(e)
            if "código" in error_msg.lower() or "inválido" in error_msg.lower():
                return MESSAGES['invalid_code'], 'waiting_verification_code'
            else:
                return f"{MESSAGES['code_error']} {error_msg}", 'waiting_verification_code'
    
    elif stage == 'authenticated':
        user_id = prompt.strip()
        try:
            user_name = "Usuario"
            return process_medical_results(user_id, user_name, session)
        except Exception as e:
            error_msg = str(e)
            if "Paciente no identificado" in error_msg:
                response_text = f"Lo siento, no se logró identificar al paciente con el ID {user_id}. Verifica que el número sea correcto o contacta a soporte. ¿Hay algo más en lo que pueda ayudarte?"
                return response_text, 'completed'
            else:
                response_text = f"Error obteniendo resultados de la API: {error_msg}. ¿Puedes compartir tus resultados médicos en formato JSON? Ejemplo: {{\"Glicemia Basal\": 90, \"Hemoglobina\": 13}}"
                return response_text, 'waiting_json'
    
    return None, None

# ============================================
# DISPATCHER PRINCIPAL
# ============================================
def dispatch_conversation_stage(stage, prompt, session):
    """Dispatcher principal que maneja todos los stages de la conversación"""
    
    # Handle initial stage (primer mensaje del usuario)
    if stage == 'initial':
        # El usuario escribió algo por primera vez - mostrar mensaje de bienvenida
        welcome_message = """👋 ¡Hola! Soy **Bianca** 😊, tu asistente de salud de GoMind.

Ingresa tu **correo electrónico** para enviarte un código de verificación y así confirmar tu identidad"""
        return welcome_message, 'waiting_email'
    
    # Handle authentication flow stages
    auth_stages = ['waiting_email', 'waiting_verification_code', 'authenticated']
    if stage in auth_stages:
        response, new_stage = handle_authentication_flow(stage, prompt, session)
        return response, new_stage
    
    # Handle product-related queries
    if stage == 'showing_products':
        intent = analyze_user_intent(prompt, 'showing_products')
        if intent == 'PRODUCTOS':
            products = session.company_products
            if products:
                response = "Aquí tienes los productos disponibles de tu compañía:\n\n"
                for product in products:
                    name = product.get('name', 'Producto sin nombre')
                    description = product.get('description', 'Sin descripción')
                    price = product.get('price', 'Precio no disponible')
                    response += f"**{name}**\n{description}\nPrecio: {price}\n\n"
                return response, 'showing_products'
            else:
                return "No hay productos disponibles en este momento.", 'authenticated'
        else:
            return None, 'authenticated'
    
    # Handle main menu selection
    if stage == 'main_menu':
        return handle_main_menu_selection(prompt, session)
    
    # Handle product selection
    if stage == 'selecting_product':
        return handle_product_selection(prompt, session)
    
    # Handle appointment flow stages
    appointment_stages = ['analyzing', 'selecting_clinic', 'scheduling', 'selecting_time', 'confirming']
    if stage in appointment_stages:
        response, new_stage = handle_appointment_flow(stage, prompt, session)
        if response is not None:
            return response, new_stage
    
    # Handle medical input stages
    medical_stages = ['waiting_json', 'completed']
    if stage in medical_stages:
        response, new_stage = handle_medical_input(prompt, session)
        if response is not None:
            return response, new_stage
        
        if stage == 'completed':
            intent = analyze_user_intent(prompt, 'completed')
            if intent in ['NUEVA_CITA', 'POSITIVA']:
                # Reset appointment data
                session.selected_clinic = None
                session.selected_day = None
                session.selected_time = None
                session.clinics = None
                session.next_days = None
                return handle_appointment_request(session)
            elif intent == 'NEGATIVA':
                farewell_intent = analyze_farewell_intent(prompt, session)
                if farewell_intent == 'DESPEDIDA':
                    return generate_farewell_response(session), 'conversation_ended'
                else:
                    return generate_farewell_response(session), 'conversation_ended'

            return handle_contextual_conversation(prompt, session)
        
        if stage == 'conversation_ended':
            return "¡Que tengas un excelente día! Si necesitas algo más, estaré aquí para ayudarte.", 'conversation_ended'
        
        if stage == 'waiting_json':
            return "El formato JSON no es válido. Por favor, comparte tus resultados en formato JSON válido, ejemplo: {\"Glicemia Basal\": 90, \"Hemoglobina\": 13}", 'waiting_json'
    
    # Default fallback - use contextual conversation
    return handle_contextual_conversation(prompt, session)

# ============================================
# FUNCIÓN PRINCIPAL PARA TWILIO
# ============================================
def process_message(session_id, user_message):
    """
    Función principal para procesar mensajes de Twilio
    
    Args:
        session_id: ID único del usuario (número de teléfono)
        user_message: Mensaje del usuario
    
    Returns:
        dict: {
            'response': 'Texto de respuesta',
            'stage': 'nuevo_stage',
            'session_id': session_id
        }
    """
    # 1. Recuperar o crear sesión
    session = get_or_create_session(session_id)
    
    # 2. Agregar mensaje del usuario al historial
    session.messages.append({"role": "user", "content": user_message})
    
    # 3. Procesar mensaje usando dispatcher
    response, new_stage = dispatch_conversation_stage(session.stage, user_message, session)
    
    # 4. Actualizar stage
    session.stage = new_stage
    
    # 5. Agregar respuesta al historial
    if response:
        session.messages.append({"role": "assistant", "content": response})
    
    # 6. Guardar sesión
    save_session(session)
    
    # 7. Retornar respuesta
    return {
        'response': response if response else "Lo siento, no pude procesar tu mensaje.",
        'stage': new_stage,
        'session_id': session_id
    }

# ============================================
# ENDPOINT FLASK PARA TWILIO (OPCIONAL)
# ============================================
if __name__ == '__main__':
    from flask import Flask, request
    from twilio.twiml.messaging_response import MessagingResponse
    
    app = Flask(__name__)
    
    @app.route('/webhook', methods=['POST'])
    def twilio_webhook():
        """Webhook para recibir mensajes de Twilio"""
        from_number = request.form.get('From')
        message_body = request.form.get('Body')
        
        # Procesar mensaje
        result = process_message(from_number, message_body)
        
        # Responder a Twilio
        resp = MessagingResponse()
        resp.message(result['response'])
        return str(resp)
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return {'status': 'ok', 'service': 'Bianca WhatsApp Bot'}
    
    print("🚀 Servidor Bianca iniciado en http://localhost:5000")
    print("📱 Webhook disponible en http://localhost:5000/webhook")
    app.run(debug=True, port=5000)
