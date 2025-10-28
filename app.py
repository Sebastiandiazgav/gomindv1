import os
import json
import boto3
import streamlit as st
from datetime import datetime, timedelta
import requests

# Configurar cliente de Bedrock usando st.secrets
bedrock_client = boto3.client(
    service_name='bedrock-runtime',
    region_name=st.secrets["aws"]["REGION"],
    aws_access_key_id=st.secrets["aws"]["ACCESS_KEY_ID"],
    aws_secret_access_key=st.secrets["aws"]["SECRET_ACCESS_KEY"]
)

# Configurar API GoMind usando st.secrets
API_BASE_URL = st.secrets["api"]["BASE_URL"]
API_EMAIL = st.secrets["api"]["EMAIL"]
API_PASSWORD = st.secrets["api"]["PASSWORD"]

# Función de análisis de intención con Bedrock
def analyze_user_intent(user_message, context_stage):
    """
    Analiza la intención del usuario usando Bedrock en lugar de keywords.
    
    Args:
        user_message: El mensaje del usuario
        context_stage: El contexto/etapa actual de la conversación
    
    Returns:
        str: 'POSITIVA', 'NEGATIVA', 'AMBIGUA', o tipo específico como 'PRODUCTOS'
    """
    try:
        # Definir el contexto según la etapa
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
        
        # Validar respuesta
        valid_intents = ['POSITIVA', 'NEGATIVA', 'AMBIGUA', 'PRODUCTOS', 'NUEVA_CITA']
        if intent in valid_intents:
            return intent
        else:
            return 'AMBIGUA'  # Fallback si la respuesta no es válida
            
    except Exception as e:
        # Fallback simple en caso de error con Bedrock
        user_lower = user_message.lower()
        if any(word in user_lower for word in ['no', 'nunca', 'jamás']):
            return 'NEGATIVA'
        elif any(word in user_lower for word in ['si', 'sí', 'yes', 'ok', 'claro']):
            return 'POSITIVA'
        else:
            return 'AMBIGUA'

MESSAGES = {
    'healthy_results': "¡Excelente noticia, tus valores están todos dentro del rango saludable:\n\n{results}\n\nEstos resultados indican que estás llevando un estilo de vida saludable. ¡Felicitaciones! Sigue así con tus buenos hábitos de alimentación y ejercicio.",
    'unhealthy_results': "He revisado tus valores y me gustaría comentarte lo que veo:\n\n{issues}\n\nAunque no son valores alarmantes, sería recomendable que un médico los revise más a fondo.",
    'appointment_question': "¿Te gustaría que te ayude a agendar una cita para que puedas discutir estos resultados con un profesional?",
    'appointment_success': "¡Excelente! Tu cita quedó confirmada para el {day} a las {time} en {clinic}.\n\nLa cita ha sido registrada correctamente en nuestro sistema. Te enviaremos un recordatorio antes de la hora programada.\n\n¿Necesitas agendar otra cita? Solo escribe 'nueva cita' y te ayudo inmediatamente.",
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
    'new_appointment_medical_request': "Entiendo que necesitas una nueva cita. Para brindarte el mejor servicio, ¿podrías compartirme el ID de usuario para revisar tus resultados médicos más recientes? Esto me ayudará a determinar si necesitas una cita médica."
}

def get_api_token(email=None, password=None):
    if email and password:
        payload = {"email": email, "password": password}
    else:
        payload = {"email": API_EMAIL, "password": API_PASSWORD}

    url = f"{API_BASE_URL}/api/auth/login"
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        token = data.get('token')
        company_id = data.get('company', {}).get('company_id')
        return {'token': token, 'company_id': company_id}
    else:
        raise Exception(f"Error obteniendo token: {response.text}")

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

def get_company_products(company_id):
    token = st.session_state.auth_token
    url = f"{API_BASE_URL}/api/companies/{company_id}/products"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get('products', [])
    else:
        raise Exception(f"Error obteniendo productos: {response.status_code} - {response.text}")

def get_health_providers(company_id):
    token = st.session_state.auth_token
    url = f"{API_BASE_URL}/api/companies/{company_id}/health-providers"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get('healthProviders', [])
    else:
        raise Exception(f"Error obteniendo proveedores de salud: {response.status_code} - {response.text}")

# Tabla de mapeo: nombre de clínica → health_provider_id
CLINIC_MAPPING = {
    "Inmunomedica Concepción": 1,
    "Laboratorio Blanco Santiago": 3,
    "Red Salud Santiago Centro": 4
}

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

def prepare_api_appointment_data():
    clinic_name = st.session_state.selected_clinic
    
    # Buscar el health_provider_id en los datos del endpoint
    health_provider_id = None
    for clinic in st.session_state.clinics:
        if clinic['name'] == clinic_name:
            health_provider_id = clinic['health_provider_id']
            break

    if not health_provider_id:
        raise ValueError(f"Clínica no encontrada en datos del endpoint: {clinic_name}")

    # Verificar que user_data tenga el campo 'id'
    if not hasattr(st.session_state, 'user_data') or not st.session_state.user_data:
        raise ValueError("user_data no está disponible en session_state")
    
    if 'id' not in st.session_state.user_data:
        raise ValueError(f"Campo 'id' no encontrado en user_data. Campos disponibles: {list(st.session_state.user_data.keys())}")

    try:
        date_time_iso = convert_spanish_date_to_iso(
            st.session_state.selected_day,
            st.session_state.selected_time
        )
    except Exception as e:
        raise ValueError(f"Error procesando fecha y hora: {str(e)}")

    return {
        "user_id": st.session_state.user_data["id"],
        "product_id": 2,
        "health_provider_id": health_provider_id,
        "date_time": date_time_iso
    }

def send_appointment_to_api(appointment_api_data):
    token = st.session_state.auth_token
    url = f"{API_BASE_URL}/api/appointments"
    headers = {"Authorization": f"Bearer {token}"}

    if not token:
        raise ValueError("Token de autenticación no disponible")

    response = requests.post(url, json=appointment_api_data, headers=headers, timeout=30)
    return response

def get_user_results(user_id):
    token = st.session_state.auth_token
    url = f"{API_BASE_URL}/api/parameters/{user_id}/results"
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

# Users database removed - not used in current implementation

# Funciones utilitarias

def find_text_match(prompt, text_list):
    prompt_lower = prompt.lower()
    for text in text_list:
        text_parts = [p.lower() for p in text.split()]
        if any(part in prompt_lower for part in text_parts):
            return text
    return None

def find_clinic_match(prompt, clinics):
    prompt_lower = prompt.lower()
    for clinic in clinics:
        clinic_name_lower = clinic['name'].lower()
        clinic_words = clinic_name_lower.split()
        if any(word in prompt_lower for word in clinic_words):
            return clinic['name']
    return None

def handle_appointment_error(error, error_type='general'):
    if error_type == 'clinic_fetch':
        return MESSAGES['clinic_error'].format(error=str(error)), 'completed'
    elif error_type == 'api_connection':
        return MESSAGES['connection_error'], 'completed'
    elif error_type == 'api_error':
        return MESSAGES['appointment_error'].format(status=getattr(error, 'status_code', 'Unknown')), 'completed'
    else:
        return f"Error inesperado: {str(error)}. ¿Te gustaría intentarlo más tarde?", 'completed'

def validate_appointment_data():
    required_fields = ['selected_clinic', 'selected_day', 'selected_time']
    missing_fields = [field for field in required_fields if not hasattr(st.session_state, field) or not getattr(st.session_state, field)]
    
    if missing_fields:
        raise ValueError(f"Faltan datos requeridos: {', '.join(missing_fields)}")
    
    if not hasattr(st.session_state, 'user_data') or not st.session_state.user_data.get('id'):
        raise ValueError("ID de usuario no disponible")
    
    return True

def generate_medical_response(results, issues, user_name="Usuario"):
    if not issues:
        results_text = "\n".join([f"- {k}: {v}" for k, v in results.items()])
        response = f"¡Hola, {user_name}! Gracias por compartir tus resultados conmigo. Me da gusto poder revisarlos contigo.\n\n"
        response += MESSAGES['healthy_results'].format(results=results_text)
        return response, 'completed'
    else:
        issues_text = "\n".join([f"- {issue}" for issue in issues])
        response = f"¡Hola, {user_name}! Gracias por compartir tus resultados conmigo. "
        response += MESSAGES['unhealthy_results'].format(issues=issues_text)
        
        if st.session_state.company_products:
            relevant_products = get_relevant_products(issues)
            if relevant_products:
                response += f"\n\n**Productos recomendados de tu compañía:**\n\n"
                for product in relevant_products[:2]:
                    response += f"- {product.get('name', 'Producto')}\n"
        
        response += f"\n\n{MESSAGES['appointment_question']}"
        return response, 'analyzing'

def process_medical_results(user_id, user_name="Usuario"):
    try:
        results = get_user_results(user_id)
        st.session_state.user_data = {"id": user_id, "results": results}
        
        issues, needs_appointment = analyze_results(results)
        
        return generate_medical_response(results, issues, user_name)
            
    except Exception as e:
        error_msg = str(e)
        if "Paciente no identificado" in error_msg:
            return f"Lo siento, no se logró identificar al paciente con el ID {user_id}. Verifica que el número sea correcto o contacta a soporte. ¿Hay algo más en lo que pueda ayudarte?", 'completed'
        else:
            return f"Error obteniendo resultados de la API: {error_msg}. ¿Puedes compartir tus resultados médicos en formato JSON? Ejemplo: {{\"Glicemia Basal\": 90, \"Hemoglobina\": 13}}", 'waiting_json'

def get_relevant_products(issues):
    if not st.session_state.company_products:
        return []
    
    relevant_products = []
    issues_text = " ".join(issues).lower()
    
    for product in st.session_state.company_products:
        product_name = product.get('name', '').lower()
        if ('colesterol' in issues_text and 'corazón' in product_name) or \
           ('glucosa' in issues_text and 'diabetes' in product_name):
            relevant_products.append(product)
    
    return relevant_products

def handle_appointment_request():
    try:
        # Obtener clínicas directamente del endpoint
        clinics = get_health_providers(st.session_state.company_id)
        
        if not clinics:
            return MESSAGES['clinic_unavailable'], 'completed'
            
        st.session_state.clinics = clinics
        
        response = f"¡Perfecto! Te ayudo a agendar tu cita. Tenemos estas clínicas disponibles:\n\n"
        for i, clinic in enumerate(clinics):
            response += f"{i+1}. {clinic['name']}\n"
        response += "\n¿En cuál clínica prefieres agendar tu cita? (di el número o el nombre de la clínica)"
        return response, 'selecting_clinic'
    except Exception as e:
        return handle_appointment_error(e, 'clinic_fetch')

def handle_clinic_selection(prompt):
    clinics = st.session_state.clinics
    selected_clinic = None
    
    try:
        clinic_num = int(prompt.strip()) - 1
        if 0 <= clinic_num < len(clinics):
            selected_clinic = clinics[clinic_num]['name']
    except ValueError:
        selected_clinic = find_clinic_match(prompt, clinics)
    
    if not selected_clinic:
        return MESSAGES['clinic_not_recognized'], 'selecting_clinic'
        
    st.session_state.selected_clinic = selected_clinic
    next_days = get_next_business_days(3)
    st.session_state.next_days = next_days
    response = f"¡Excelente! Has seleccionado {selected_clinic}.\n\nAhora, tengo disponibilidad para agendar una cita en los próximos días hábiles:\n\n"
    for i, day in enumerate(next_days):
        response += f"{i+1}. {day}\n"
    response += "\n¿Para qué día te gustaría agendar? (Selecciona el numero)"
    return response, 'scheduling'

def handle_day_selection(prompt):
    next_days = st.session_state.next_days
    selected_day = None
    
    try:
        day_num = int(prompt.strip()) - 1
        if 0 <= day_num < len(next_days):
            selected_day = next_days[day_num]
    except ValueError:
        selected_day = find_text_match(prompt, next_days)
    
    if not selected_day:
        return MESSAGES['day_not_recognized'], 'scheduling'
        
    # Crear lista de horarios con números
    hours = [f"{h}:00" for h in range(9, 19)]
    hours_str = "\n".join(f"{i+1}. {h}" for i, h in enumerate(hours))
    response = f"Genial, el {selected_day} tengo disponibilidad en los siguientes horarios:\n\n{hours_str}\n\n¿A qué hora te gustaría agendar? Por favor, responde con el número de tu opción (1-{len(hours)})."
    
    # Guardar tanto el día como los horarios disponibles para referencia
    st.session_state.selected_day = selected_day
    st.session_state.available_hours = hours
    return response, 'selecting_time'

def handle_time_selection(prompt):
    user_input = prompt.strip()
    
    # Obtener los horarios disponibles guardados
    available_hours = getattr(st.session_state, 'available_hours', [f"{h}:00" for h in range(9, 19)])
    
    try:
        # Intentar interpretar como número de opción
        option_num = int(user_input)
        
        # Validar que el número esté en el rango correcto
        if 1 <= option_num <= len(available_hours):
            selected_hour = available_hours[option_num - 1]
            response = f"Perfecto, reservo para el {st.session_state.selected_day} a las {selected_hour}. ¿Confirmo tu cita?"
            st.session_state.selected_time = selected_hour
            return response, 'confirming'
        else:
            return f"Por favor, elige un número entre 1 y {len(available_hours)}.", 'selecting_time'
            
    except ValueError:
        # Fallback: intentar interpretar como hora directa (para compatibilidad)
        try:
            if ":" in user_input:
                hour, minute = user_input.split(":")
                hour_num = int(hour)
            else:
                hour_num = int(user_input)
                user_input = f"{hour_num}:00"
            
            if not (9 <= hour_num <= 18):
                return f"Esa hora no está disponible. Por favor, elige un número entre 1 y {len(available_hours)}.", 'selecting_time'
                
            response = f"Perfecto, reservo para el {st.session_state.selected_day} a las {user_input}. ¿Confirmo tu cita?"
            st.session_state.selected_time = user_input
            return response, 'confirming'
            
        except ValueError:
            return f"Por favor, responde con el número de la opción que prefieres (1-{len(available_hours)}).", 'selecting_time'

def handle_appointment_confirmation():
    try:
        validate_appointment_data()
        
        api_appointment_data = prepare_api_appointment_data()
        api_response = send_appointment_to_api(api_appointment_data)
        
        if api_response.status_code in [200, 201]:
            return MESSAGES['appointment_success'].format(
                day=st.session_state.selected_day,
                time=st.session_state.selected_time,
                clinic=st.session_state.selected_clinic
            ), 'completed'
        else:
            return handle_appointment_error(api_response, 'api_error')
            
    except requests.exceptions.RequestException:
        return handle_appointment_error(None, 'api_connection')
    except ValueError as e:
        # Si faltan datos de cita, reiniciar el flujo de agendamiento
        if "Faltan datos requeridos" in str(e):
            return handle_appointment_request()
        else:
            return handle_appointment_error(e, 'general')
    except Exception as e:
        return handle_appointment_error(e, 'general')

def get_next_business_days(n=3):
    days = []
    current = datetime.now()
    weekdays = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes']
    months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    while len(days) < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            day_name = weekdays[current.weekday()]
            day_num = current.day
            month_name = months[current.month - 1]
            days.append(f"{day_name} {day_num} de {month_name}")
    return days

def handle_medical_input(prompt):
    if prompt.strip().isdigit() and len(prompt.strip()) > 0:
        user_id = prompt.strip()
        user_name = "Usuario"
        return process_medical_results(user_id, user_name)
    
    try:
        data = json.loads(prompt)
        if isinstance(data, dict) and any(key in str(data).lower() for key in ['glicemia', 'hemoglobina', 'colesterol', 'glucosa']):
            user_name = data.get('nombre_usuario', 'Usuario')
            results = {k: v for k, v in data.items() if k != 'nombre_usuario'}
            st.session_state.user_data = {"results": results}
            
            issues, needs_appointment = analyze_results(results)
            return generate_medical_response(results, issues, user_name)
    except json.JSONDecodeError:
        pass
    
    return None, None

def handle_appointment_flow(stage, prompt):
    if stage == 'analyzing':
        intent = analyze_user_intent(prompt, 'analyzing')
        if intent == 'POSITIVA':
            return handle_appointment_request()
        elif intent == 'AMBIGUA':
            return "¿Te gustaría que te ayude a agendar una cita? Por favor responde sí o no para continuar.", 'analyzing'
        else:
            return MESSAGES['appointment_general_declined'], 'completed'
    
    elif stage == 'selecting_clinic':
        return handle_clinic_selection(prompt)
    
    elif stage == 'scheduling':
        return handle_day_selection(prompt)
    
    elif stage == 'selecting_time':
        return handle_time_selection(prompt)
    
    elif stage == 'confirming':
        intent = analyze_user_intent(prompt, 'confirming')
        if intent == 'POSITIVA':
            return handle_appointment_confirmation()
        elif intent == 'AMBIGUA':
            return "¿Confirmas tu cita? Por favor responde sí o no.", 'confirming'
        else:
            return MESSAGES['appointment_declined'], 'completed'
    
    return None, None

def handle_new_appointment_request(prompt):
    """Maneja solicitudes de nueva cita con opción híbrida de usuario"""
    # Reset appointment-related session state
    appointment_keys = ['selected_clinic', 'selected_day', 'selected_time', 'clinics', 'next_days']
    for key in appointment_keys:
        if hasattr(st.session_state, key):
            delattr(st.session_state, key)
    
    # Si ya hay datos de usuario autenticado, ofrecer opciones
    if (hasattr(st.session_state, 'auth_token') and 
        st.session_state.auth_token and 
        hasattr(st.session_state, 'user_data') and 
        st.session_state.user_data):
        
        user_name = st.session_state.user_data.get('name', 'Usuario actual')
        
        response = f"""¿Para quién quieres agendar la nueva cita?

1. Mismo usuario ({user_name})
2. Cambiar de usuario

Por favor, responde con el número de tu opción (1 o 2)."""
        
        return response, 'selecting_user_for_new_appointment'
    else:
        # Si no hay datos, ir directo a autenticación
        return "Para agendar una nueva cita, necesito que te autentiques. Por favor ingresa tu correo electrónico:", 'waiting_email'

def handle_user_selection_for_new_appointment(prompt):
    """Maneja la selección del usuario para nueva cita"""
    user_choice = prompt.strip()
    
    if user_choice == '1':
        # Reutilizar datos existentes - ir directo a selección de clínica
        return handle_appointment_request()
    elif user_choice == '2':
        # Limpiar datos y reiniciar flujo
        clear_user_session_data()
        return "Perfecto, vamos a cambiar de usuario. Por favor ingresa tu correo electrónico:", 'waiting_email'
    else:
        # Respuesta inválida, pedir clarificación
        return "Por favor, responde con **1** para el mismo usuario o **2** para cambiar de usuario.", 'selecting_user_for_new_appointment'

def clear_user_session_data():
    """Limpia los datos de sesión del usuario para permitir cambio de usuario"""
    keys_to_clear = [
        'auth_token', 'user_data', 'company_id', 'company_products', 
        'selected_clinic', 'selected_day', 'selected_time', 'clinics', 
        'next_days', 'user_email'
    ]
    for key in keys_to_clear:
        if hasattr(st.session_state, key):
            delattr(st.session_state, key)

def handle_authentication_flow(stage, prompt):
    if stage == 'waiting_email':
        email = prompt.strip().lower()
        if '@' in email and '.' in email:
            st.session_state.user_email = email
            return "Gracias. Ahora, por favor ingresa tu contraseña para verificar tu identidad.", 'waiting_password'
        else:
            return "El dato ingresado no parece ser válido. Por favor, verifica la información.", 'waiting_email'
    
    elif stage == 'waiting_password':
        password = prompt.strip()
        try:
            url = f"{API_BASE_URL}/api/auth/login"
            payload = {"email": st.session_state.user_email, "password": password}
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('token')
                company_id = data.get('company', {}).get('company_id')
                
                if token and company_id:
                    st.session_state.auth_token = token
                    st.session_state.company_id = company_id
                    
                    patient_id = data.get('user', {}).get('user_id')
                    
                    if patient_id:
                        products = data.get('company', {}).get('products', [])
                        st.session_state.company_products = products
                        
                        try:
                            user_name = data.get('user', {}).get('name', 'Usuario')
                            medical_response, new_stage = process_medical_results(patient_id, user_name)
                            
                            response_text = f"¡Autenticación exitosa! Bienvenido/a {user_name}.\n\n"
                            if st.session_state.company_products:
                                response_text += f"**Productos de salud disponibles:**\n\n"
                                for product in st.session_state.company_products:
                                    response_text += f"- {product.get('name')}\n"
                                response_text += f"\n"
                            
                            response_text += medical_response.split("¡Hola, " + user_name + "! Gracias por compartir tus resultados conmigo. Me da gusto poder revisarlos contigo.\n\n", 1)[-1]
                            return response_text, new_stage
                            
                        except Exception as e:
                            response_text = f"¡Autenticación exitosa! Bienvenido/a. Sin embargo, no pude obtener tus resultados médicos automáticamente. ¿Puedes proporcionarme tu número de identificación para acceder a ellos?"
                            return response_text, 'authenticated'
                    else:
                        try:
                            products = get_company_products(company_id)
                            st.session_state.company_products = products
                            new_stage = 'showing_products'
                        except:
                            st.session_state.company_products = []
                            new_stage = 'authenticated'
                        
                        response_text = f"¡Autenticación exitosa! Bienvenido/a.\n\n"
                        if st.session_state.company_products:
                            response_text += f"Tu compañía tiene disponibles {len(st.session_state.company_products)} productos de salud.\n\n"
                        
                        response_text += "Ingresa tu número de identificación para acceder a tus resultados médicos:"
                        return response_text, new_stage
                else:
                    return "Error en la autenticación. Credenciales inválidas. Por favor, intenta nuevamente con tu correo electrónico.", 'waiting_email'
            else:
                return "Credenciales inválidas. Por favor, verifica tu correo electrónico y contraseña, e intenta nuevamente.", 'waiting_email'
                
        except Exception as e:
            return f"Error de conexión. Por favor, intenta nuevamente más tarde. Detalles: {str(e)}", 'waiting_email'
    
    elif stage == 'authenticated':
        user_id = prompt.strip()
        try:
            user_name = "Usuario"
            return process_medical_results(user_id, user_name)
        except Exception as e:
            error_msg = str(e)
            if "Paciente no identificado" in error_msg:
                response_text = f"Lo siento, no se logró identificar al paciente con el ID {user_id}. Verifica que el número sea correcto o contacta a soporte. ¿Hay algo más en lo que pueda ayudarte?"
                return response_text, 'completed'
            else:
                response_text = f"Error obteniendo resultados de la API: {error_msg}. ¿Puedes compartir tus resultados médicos en formato JSON? Ejemplo: {{\"Glicemia Basal\": 90, \"Hemoglobina\": 13}}"
                return response_text, 'waiting_json'
    
    return None, None

def get_input_placeholder(stage):
    """Placeholder completamente estático - elimina todos los cambios dinámicos"""
    # Solo mantener placeholder específico para JSON (que no causa transiciones problemáticas)
    if stage == 'waiting_json':
        return "Ingresa tus resultados médicos en formato JSON..."
    
    # Para TODOS los demás stages, usar placeholder genérico estático
    return "Escribe tu mensaje aquí..."

def dispatch_conversation_stage(stage, prompt):
    # Handle authentication flow stages
    auth_stages = ['waiting_email', 'waiting_password', 'authenticated']
    if stage in auth_stages:
        response, new_stage = handle_authentication_flow(stage, prompt)
        if response is not None:
            return response, new_stage
    
    # Handle product-related queries
    if stage == 'showing_products':
        intent = analyze_user_intent(prompt, 'showing_products')
        if intent == 'PRODUCTOS':
            products = st.session_state.company_products
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
    
    # Handle new appointment user selection
    if stage == 'selecting_user_for_new_appointment':
        return handle_user_selection_for_new_appointment(prompt)
    
    # Handle appointment flow stages
    appointment_stages = ['analyzing', 'selecting_clinic', 'scheduling', 'selecting_time', 'confirming']
    if stage in appointment_stages:
        response, new_stage = handle_appointment_flow(stage, prompt)
        if response is not None:
            return response, new_stage
    
    # Handle medical input stages
    medical_stages = ['waiting_json', 'completed']
    if stage in medical_stages:
        response, new_stage = handle_medical_input(prompt)
        if response is not None:
            return response, new_stage
        
        if stage == 'completed':
            # Check if user wants a new appointment
            intent = analyze_user_intent(prompt, 'completed')
            if intent in ['NUEVA_CITA', 'POSITIVA']:
                return handle_new_appointment_request(prompt)
            
            return invoke_bedrock(BIANCA_PROMPT, prompt, st.session_state.context), 'completed'
        
        if stage == 'waiting_json':
            return "El formato JSON no es válido. Por favor, comparte tus resultados en formato JSON válido, ejemplo: {\"Glicemia Basal\": 90, \"Hemoglobina\": 13}", 'waiting_json'
    
    # Default fallback - use Bedrock for general conversation
    return invoke_bedrock(BIANCA_PROMPT, prompt, st.session_state.context), stage

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

# Optimized Bianca prompt - Reduced from 120+ lines to 15 lines
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

def invoke_bedrock(prompt, user_message, context=""):
    full_prompt = f"{BIANCA_PROMPT}\n\nContexto de conversación: {context}\n\nUsuario: {user_message}\n\nBianca:"
    try:
        response = bedrock_client.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ]
            })
        )
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    except Exception as e:
        return f"Error al invocar Bedrock: {str(e)}"

# Título de la aplicación
st.title("Chat con Bianca - Asistente de Salud GoMind")

if 'stage' not in st.session_state:
    st.session_state.stage = 'waiting_email'

if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
    # Agregar mensaje de bienvenida inicial
    welcome_message = """👋 ¡Hola! Soy **Bianca**, tu asistente de salud de GoMind.

Para comenzar, por favor ingresa tu **correo electrónico** para verificar tu identidad y acceder a tus resultados médicos."""
    st.session_state.messages.append({"role": "assistant", "content": welcome_message})
if 'context' not in st.session_state:
    st.session_state.context = ""
if 'company_id' not in st.session_state:
    st.session_state.company_id = None
if 'clinics' not in st.session_state:
    st.session_state.clinics = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'company_products' not in st.session_state:
    st.session_state.company_products = None
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Unified conversation flow using dispatcher pattern
if prompt := st.chat_input(get_input_placeholder(st.session_state.stage), key="chat_widget"):
    # Handle password masking for display
    display_prompt = "••••••••" if st.session_state.stage == 'waiting_password' else prompt
    
    st.session_state.messages.append({"role": "user", "content": display_prompt})
    with st.chat_message("user"):
        st.markdown(display_prompt)

    # Use dispatcher pattern to handle all conversation stages
    response, new_stage = dispatch_conversation_stage(st.session_state.stage, prompt)
    
    # Update stage if it changed
    if new_stage != st.session_state.stage:
        st.session_state.stage = new_stage

    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)