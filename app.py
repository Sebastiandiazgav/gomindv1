import os
import json
import boto3
from dotenv import load_dotenv
import streamlit as st
from datetime import datetime, timedelta
import requests

# Cargar variables de entorno
load_dotenv()

# Configurar cliente de Bedrock
bedrock_client = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.getenv('AWS_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

# Configurar API GoMind
API_BASE_URL = os.getenv('API_BASE_URL')
API_EMAIL = os.getenv('API_EMAIL')
API_PASSWORD = os.getenv('API_PASSWORD')

def get_api_token(email=None, password=None):
    if email and password:
        # Usar credenciales proporcionadas por el usuario
        payload = {"email": email, "password": password}
    else:
        # Usar credenciales del .env (para funciones que necesitan token)
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
        # Corregir typos conocidos
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

def get_user_profile():
    token = st.session_state.auth_token
    url = f"{API_BASE_URL}/api/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        raise Exception(f"Error obteniendo perfil de usuario: {response.status_code} - {response.text}")

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

# Tabla de mapeo: nombre de clínica → health_provider_id
CLINIC_MAPPING = {
    "Innomedica Concepción": 1,
    "Laboratorio Blanco Santiago": 3,
    "Red Salud Santiago Centro": 4
}

def convert_spanish_date_to_iso(date_str, time_str):
    """Convierte fecha en español + hora a formato ISO datetime"""
    # date_str: "Miércoles 21 de octubre"
    # time_str: "17:00"
    # Resultado: "2025-10-21T17:00:00.000Z"

    try:
        # Parsear fecha en español
        parts = date_str.split()
        if len(parts) >= 4 and parts[2] == 'de':
            day = int(parts[1])
            month_name = parts[3].lower()

            # Mapear meses en español a números
            months = {
                'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
                'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
            }

            month = months.get(month_name)
            if not month:
                raise ValueError(f"Mes no reconocido: {month_name}")

            # Obtener año actual
            current_year = datetime.now().year

            # Parsear hora
            hour, minute = map(int, time_str.split(':'))

            # Crear datetime
            dt = datetime(current_year, month, day, hour, minute, 0)

            # Si la fecha ya pasó este año, asumir próximo año
            if dt < datetime.now():
                dt = datetime(current_year + 1, month, day, hour, minute, 0)

            # Convertir a ISO string con Z
            iso_string = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            return iso_string

    except Exception as e:
        raise ValueError(f"Error convirtiendo fecha: {date_str} {time_str} - {str(e)}")

def prepare_api_appointment_data():
    """Prepara los datos de cita para enviar a la API"""
    clinic_name = st.session_state.selected_clinic
    health_provider_id = CLINIC_MAPPING.get(clinic_name)

    if not health_provider_id:
        raise ValueError(f"Clínica no encontrada en mapping: {clinic_name}")

    date_time_iso = convert_spanish_date_to_iso(
        st.session_state.selected_day,
        st.session_state.selected_time
    )

    return {
        "user_id": st.session_state.user_data["id"],
        "product_id": 2,  # "Atención telefónica" como default
        "health_provider_id": health_provider_id,
        "date_time": date_time_iso
    }

def send_appointment_to_api(appointment_api_data):
    """Envía la cita a la API de GoMind"""
    token = st.session_state.auth_token
    url = f"{API_BASE_URL}/api/appointments"
    headers = {"Authorization": f"Bearer {token}"}

    # Debug: mostrar datos que se envían
    print("=== DEBUG: Enviando cita a API ===")
    print(f"URL: {url}")
    print(f"Datos: {appointment_api_data}")
    print(f"Tipos: user_id={type(appointment_api_data['user_id'])}, health_provider_id={type(appointment_api_data['health_provider_id'])}, product_id={type(appointment_api_data['product_id'])}")

    response = requests.post(url, json=appointment_api_data, headers=headers)

    # Debug: mostrar respuesta
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
    print("=== FIN DEBUG ===")

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
            # Convertir lista de objetos a dict usando analysis_results
            results = {}
            for item in data:
                param = extract_parameter(item['analysis_results'])
                value = item['value']
                results[param] = value  # Overwrite si duplicado
            return results
        else:
            return data
    else:
        raise Exception(f"Error obteniendo resultados: {response.status_code} - {response.text}")

# Cargar base de datos de usuarios
with open('users.json', 'r', encoding='utf-8') as f:
    users_db = json.load(f)

# Archivo para citas
APPOINTMENTS_FILE = 'appointments.json'
if not os.path.exists(APPOINTMENTS_FILE):
    with open(APPOINTMENTS_FILE, 'w') as f:
        json.dump([], f)

def load_appointments():
    with open(APPOINTMENTS_FILE, 'r') as f:
        return json.load(f)

def save_appointment(appointment):
    appointments = load_appointments()
    appointments.append(appointment)
    with open(APPOINTMENTS_FILE, 'w') as f:
        json.dump(appointments, f, indent=4)

def get_next_business_days(n=3):
    days = []
    current = datetime.now()
    weekdays = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes']
    months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    while len(days) < n:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Lunes a Viernes
            day_name = weekdays[current.weekday()]
            day_num = current.day
            month_name = months[current.month - 1]
            days.append(f"{day_name} {day_num} de {month_name}")
    return days

def is_future_date(date_str):
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        return date > datetime.now()
    except:
        return False

def parse_date_from_day_string(day_str):
    # day_str like "Lunes 6 de octubre"
    parts = day_str.split()
    if len(parts) >= 4 and parts[2] == 'de':
        day_num = int(parts[1])
        month_name = parts[3].lower()
        months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        if month_name in months:
            month = months.index(month_name) + 1
            year = datetime.now().year
            # If month < current month, assume next year
            if month < datetime.now().month:
                year += 1
            try:
                date = datetime(year, month, day_num)
                return date
            except:
                return None
    return None

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
    "VHS (Velocidad de sedimentación globular)": (0, 11),  # menor a 11
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

# Función legacy para compatibilidad
def analyze_legacy(colesterol, presion, glucosa):
    # Mapear a dict
    results = {
        "Glicemia Basal": glucosa,
        # Agregar mappings si es necesario, pero por ahora solo glucosa
    }
    return analyze_results(results)

# Prompt base para Bianca
BIANCA_PROMPT = """
Eres "Bianca", la asistente virtual de GoMind, una plataforma digital de salud física y emocional con recomendaciones personalizadas.
Tu rol es acompañar a los usuarios de manera amable y humana, ayudándolos a interpretar sus resultados médicos básicos
y, si es necesario, guiarlos para agendar una cita médica.

Tu tono debe ser empático, claro, cercano y profesional.
Evita sonar como un robot: usa un lenguaje natural, breve y cálido.
No uses tecnicismos innecesarios, pero comunica con responsabilidad y precisión médica.

Si los valores están normales, felicita al usuario y NO ofrezcas cita.
Si hay valores fuera de rango, ofrece orientación médica y propón agendar una cita.
Cuando se confirme que se desea agendar, continúa con el flujo de agendamiento estándar.

---

###  Datos de referencia médica (rango normal de valores)
1. Colesterol total (mg/dL):
   - Normal: 125 – 200
   - Límite alto: 201 – 239
   - Alto: ≥ 240

2. Presión arterial (mmHg):
   - Normal: hasta 129/84
   - Límite alto: 130–139/85–89
   - Alta: ≥ 140/90

3. Glucosa en sangre (mg/dL, ayuno):
   - Normal: 70 – 99
   - Prediabetes: 100 – 125
   - Diabetes probable: ≥ 126

Interpretación:
- Si todos los valores están dentro del rango normal → el usuario está saludable.
- Si hay uno o más valores en rango límite → advertencia leve (recomendación preventiva).
- Si hay uno o más valores en rango alto → alerta y recomendación médica con flujo de agendamiento.

---

###  Flujo de conversación esperado

#### Etapa 1: Análisis de resultados
El usuario envía un JSON con su información médica, ejemplo:
{ "nombre_usuario": "Luis Herrera", "colesterol": 220, "presion_arterial": 140, "glucosa": 100 }

El chatbot responde analizando los valores y explicando brevemente el resultado.
Si detecta valores fuera de rango, sugiere agendar una cita médica.

#### Etapa 2: Flujo de agendamiento (solo si aplica)
Si el usuario responde afirmativamente (sí, claro, por favor, agendar, vamos, etc.), continúa con un flujo natural de reserva.
Muestra siempre 3 días consecutivos hábiles (lunes-viernes) con su rango horario (09:00–18:00).
No permite fechas pasadas.
Si el usuario cambia de opinión o dice “no”, confirma la cancelación y cierra el flujo de forma amable.

---

###  Estilo y personalidad del asistente "Bianca"
Usa expresiones naturales y empáticas: 
"Perfecto", "Entiendo", "Muy bien", "Excelente", "¡Qué bueno!", "Gracias por compartirlo", "Claro que sí", "Por supuesto".
Mantén la conversación fluida, humana y sin tecnicismos innecesarios.

Ejemplos de tono adecuado:
- "Tus valores están dentro de lo saludable."
- "Este valor aparece un poco elevado, sería bueno revisarlo."
- "Te recomiendo una cita médica para prevenir complicaciones."
- "No es alarmante, pero sería útil revisarlo con un profesional."

Evita:
- Sonar como un bot (“No tengo contexto”, “No entiendo tu solicitud”).
- Frases rígidas o impersonales.
- Repetir valores o JSON.
- Repetir frases como “según tus resultados” más de una vez.

---

###  Manejo de contexto 
- Mantén la conversación **coherente entre mensajes**. 
  Si el usuario responde “sí”, “ok”, “vamos”, “claro”, “por favor” o algo similar, 
  entiende que quiere **continuar con la acción anterior** (por ejemplo, agendar una cita).
- Si el usuario responde “no”, “gracias”, “más tarde”, 
  entiende que **no desea continuar** y responde de forma empática, sin reiniciar el contexto.
- No digas que perdiste información o contexto; 
  simplemente redirige la conversación de forma amable, 
  por ejemplo: “Perfecto, puedo ayudarte con tus resultados o con una cita, ¿qué prefieres?”.

---

###  Explicaciones breves (nueva)
Si el usuario pregunta:
- “¿Qué significa colesterol alto?” → explica en lenguaje sencillo: 
  “Significa que hay más grasa en la sangre de lo recomendable, y eso puede afectar el corazón a largo plazo.”
- “¿Qué es la glucosa?” → “Es la cantidad de azúcar en la sangre, necesaria para darte energía.”
- “¿Qué puedo hacer?” → Da recomendaciones generales de estilo de vida (dieta, ejercicio, chequeos), 
  pero **nunca un diagnóstico ni tratamiento**.

---

### Comportamiento ante errores del usuario (optimización)
- Si el usuario escribe algo fuera del tema médico (por ejemplo: "hola", "gracias", "qué puedes hacer"),
  responde brevemente y redirígelo:
  "Hola  soy Bianca, puedo ayudarte a interpretar tus resultados, agendar una cita médica o informarte sobre productos disponibles. ¿Qué te gustaría hacer?"
- Si el formato del JSON es incorrecto o falta información,
  solicita los datos amablemente sin mostrar código técnico.

---

###  Gestión de productos de salud
- Si el usuario pregunta sobre productos disponibles, muestra la lista completa con nombre, descripción y precio.
- Si hay valores fuera de rango en los resultados médicos, sugiere productos relevantes que puedan ayudar.
- Mantén un tono informativo pero no comercial agresivo.
- Si el usuario pregunta sobre un producto específico, proporciona información detallada sin presionar la compra.

---

### Objetivo final del modelo
Proporcionar una conversación empática y natural que:
- Interprete los resultados de salud básicos.
- Detecte automáticamente si el usuario necesita una cita médica.
- Gestione el flujo de agendamiento completo con lenguaje humano.
- Informe sobre productos de salud disponibles cuando sea relevante.
- Mantenga coherencia contextual sin reiniciar el diálogo.
- Sea adaptable al tono del usuario y proyecte calidez, seguridad y profesionalismo.

"""

def invoke_bedrock(prompt, user_message, context=""):
    full_prompt = f"{BIANCA_PROMPT}\n\nContexto de conversación: {context}\n\nUsuario: {user_message}\n\nBianca:"
    try:
        response = bedrock_client.invoke_model(
            modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',  # Usando Claude 3.5 Sonnet
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

# Interfaz de Streamlit
st.title("Chat con Bianca - Asistente de Salud GoMind")
st.markdown("Hola, soy Bianca, tu asistente de salud de GoMind. Para comenzar, necesito verificar tu identidad.")

# Los productos ahora se muestran en el chat como texto

if 'stage' not in st.session_state:
    st.session_state.stage = 'waiting_email'
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
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

if st.session_state.stage == 'waiting_email':
    if prompt := st.chat_input("Ingresa tu correo electrónico..."):
        email = prompt.strip().lower()
        # Validar formato básico de email
        if '@' in email and '.' in email:
            st.session_state.user_email = email
            st.session_state.stage = 'waiting_password'
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            response = "Gracias. Ahora, por favor ingresa tu contraseña para verificar tu identidad."
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            response = "El formato del correo electrónico no es válido. Por favor, ingresa un correo electrónico válido."
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)

elif st.session_state.stage == 'waiting_password':
    if prompt := st.chat_input("Ingresa tu contraseña..."):
        password = prompt.strip()
        try:
            # Intentar autenticación con la API
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

                    # El patient_id viene en user.user_id según la respuesta de la API
                    patient_id = data.get('user', {}).get('user_id')

                    if patient_id:
                        # Los productos ya vienen en la respuesta del login
                        products = data.get('company', {}).get('products', [])
                        st.session_state.company_products = products

                        # Auto-obtener resultados médicos
                        try:
                            results = get_user_results(patient_id)
                            user_name = data.get('user', {}).get('name', 'Usuario')  # Viene en user.name
                            st.session_state.user_data = {"id": patient_id, "results": results}

                            st.session_state.messages.append({"role": "user", "content": "••••••••"})  # Ocultar contraseña
                            with st.chat_message("user"):
                                st.markdown("••••••••")

                            # Analizar automáticamente
                            issues, needs_appointment = analyze_results(results)

                            response = f"¡Autenticación exitosa! Bienvenido/a {user_name}.\n\n"
                            if st.session_state.company_products:
                                response += f"Productos de salud disponibles :\n"
                                for product in st.session_state.company_products:
                                    response += f"• {product.get('name')}\n"
                                response += f"\n"

                            if not issues:
                                response += f"Excelente noticia, tus valores están todos dentro del rango saludable:\n\n" + "\n".join([f"- {k}: {v}" for k,v in results.items()]) + "\n\nEstos resultados indican que estás llevando un estilo de vida saludable. ¡Felicitaciones! Sigue así con tus buenos hábitos de alimentación y ejercicio.\n\n¿Tienes alguna duda sobre tus resultados o hay algo más en lo que pueda ayudarte?"
                                st.session_state.stage = 'completed'
                            else:
                                response += f"He revisado tus valores y me gustaría comentarte lo que veo:\n\n"
                                for issue in issues:
                                    response += f"- {issue}\n"
                                response += "\nAunque no son valores alarmantes, sería recomendable que un médico los revise más a fondo."

                                # Sugerir productos relevantes
                                products = st.session_state.company_products or []
                                if products:
                                    relevant_products = []
                                    for product in products:
                                        product_name = product.get('name', '').lower()
                                        if 'colesterol' in str(issues).lower() and ('colesterol' in product_name or 'corazón' in product_name):
                                            relevant_products.append(product)
                                        elif 'glucosa' in str(issues).lower() and ('diabetes' in product_name or 'glucosa' in product_name):
                                            relevant_products.append(product)

                                    if relevant_products:
                                        response += f"\n\nAdicionalmente, tu compañía tiene algunos productos que podrían ser útiles:\n"
                                        for product in relevant_products[:2]:
                                            response += f"- {product.get('name', 'Producto')}\n"

                                response += "\n¿Te gustaría que te ayude a agendar una cita para que puedas discutir estos resultados con un profesional?"
                                st.session_state.stage = 'analyzing'

                            st.session_state.messages.append({"role": "assistant", "content": response})
                            with st.chat_message("assistant"):
                                st.markdown(response)

                        except Exception as e:
                            # Si falla obtener resultados, mostrar mensaje de error
                            st.session_state.messages.append({"role": "user", "content": "••••••••"})
                            with st.chat_message("user"):
                                st.markdown("••••••••")
                            response = f"¡Autenticación exitosa! Bienvenido/a. Sin embargo, no pude obtener tus resultados médicos automáticamente. ¿Puedes proporcionarme tu número de identificación para acceder a ellos?"
                            st.session_state.stage = 'authenticated'
                            st.session_state.messages.append({"role": "assistant", "content": response})
                            with st.chat_message("assistant"):
                                st.markdown(response)
                    else:
                        # No hay patient_id, pedir manualmente
                        # Obtener productos de la compañía
                        try:
                            products = get_company_products(company_id)
                            st.session_state.company_products = products
                            st.session_state.stage = 'showing_products'
                        except:
                            st.session_state.company_products = []
                            st.session_state.stage = 'authenticated'

                        st.session_state.messages.append({"role": "user", "content": "••••••••"})
                        with st.chat_message("user"):
                            st.markdown("••••••••")

                        response = f"¡Autenticación exitosa! Bienvenido/a.\n\n"
                        if st.session_state.company_products:
                            response += f"Tu compañía tiene disponibles {len(st.session_state.company_products)} productos de salud.\n\n"

                        response += "Ingresa tu número de identificación para acceder a tus resultados médicos:"
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        with st.chat_message("assistant"):
                            st.markdown(response)
                else:
                    st.session_state.messages.append({"role": "user", "content": "••••••••"})
                    with st.chat_message("user"):
                        st.markdown("••••••••")
                    response = "Error en la autenticación. Credenciales inválidas. Por favor, intenta nuevamente con tu correo electrónico."
                    st.session_state.stage = 'waiting_email'
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    with st.chat_message("assistant"):
                        st.markdown(response)
            else:
                st.session_state.messages.append({"role": "user", "content": "••••••••"})
                with st.chat_message("user"):
                    st.markdown("••••••••")
                response = "Credenciales inválidas. Por favor, verifica tu correo electrónico y contraseña, e intenta nuevamente."
                st.session_state.stage = 'waiting_email'
                st.session_state.messages.append({"role": "assistant", "content": response})
                with st.chat_message("assistant"):
                    st.markdown(response)
        except Exception as e:
            st.session_state.messages.append({"role": "user", "content": "••••••••"})
            with st.chat_message("user"):
                st.markdown("••••••••")
            response = f"Error de conexión. Por favor, intenta nuevamente más tarde. Detalles: {str(e)}"
            st.session_state.stage = 'waiting_email'
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)

elif st.session_state.stage == 'authenticated':
    if prompt := st.chat_input("Ingresa tu número de identificación o escribe tu consulta..."):
        user_id = prompt.strip()
        try:
            results = get_user_results(user_id)
            user_name = "Usuario"
            st.session_state.user_data = {"id": user_id, "results": results}
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Analizar automáticamente
            issues, needs_appointment = analyze_results(results)

            if not issues:
                response = f"¡Hola, {user_name}! Gracias por compartir tus resultados conmigo. Me da gusto poder revisarlos contigo.\n\nExcelente noticia, tus valores están todos dentro del rango saludable:\n\n" + "\n".join([f"- {k}: {v}" for k,v in results.items()]) + "\n\nEstos resultados indican que estás llevando un estilo de vida saludable. ¡Felicitaciones! Sigue así con tus buenos hábitos de alimentación y ejercicio.\n\n¿Tienes alguna duda sobre tus resultados o hay algo más en lo que pueda ayudarte?"
                st.session_state.stage = 'completed'
            else:
                response = f"¡Hola, {user_name}! Gracias por compartir tus resultados conmigo. He revisado tus valores y me gustaría comentarte lo que veo:\n\n"
                for issue in issues:
                    response += f"- {issue}\n"
                response += "\nAunque no son valores alarmantes, sería recomendable que un médico los revise más a fondo."

                # Sugerir productos relevantes si hay productos disponibles
                products = st.session_state.company_products or []
                if products:
                    relevant_products = []
                    for product in products:
                        product_name = product.get('name', '').lower()
                        # Sugerencias básicas basadas en problemas comunes
                        if 'colesterol' in str(issues).lower() and ('colesterol' in product_name or 'corazón' in product_name):
                            relevant_products.append(product)
                        elif 'glucosa' in str(issues).lower() and ('diabetes' in product_name or 'glucosa' in product_name):
                            relevant_products.append(product)

                    if relevant_products:
                        response += f"\n\nAdicionalmente, tu compañía tiene algunos productos que podrían ser útiles para complementar tu cuidado de la salud:\n"
                        for product in relevant_products[:2]:  # Máximo 2 sugerencias
                            response += f"- {product.get('name', 'Producto')}: {product.get('description', 'Producto recomendado')}\n"

                response += "\n¿Te gustaría que te ayude a agendar una cita para que puedas discutir estos resultados con un profesional?"
                st.session_state.stage = 'analyzing'

            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
        except Exception as e:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            error_msg = str(e)
            if "Paciente no identificado" in error_msg:
                response = f"Lo siento, no se logró identificar al paciente con el ID {user_id}. Verifica que el número sea correcto o contacta a soporte. ¿Hay algo más en lo que pueda ayudarte?"
                st.session_state.stage = 'completed'
            else:
                response = f"Error obteniendo resultados de la API: {error_msg}. ¿Puedes compartir tus resultados médicos en formato JSON? Ejemplo: {{\"Glicemia Basal\": 90, \"Hemoglobina\": 13}}"
                st.session_state.stage = 'waiting_json'
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
elif st.session_state.stage in ['showing_products', 'authenticated', 'analyzing', 'selecting_clinic', 'scheduling', 'selecting_time', 'confirming', 'waiting_json', 'completed']:
    if prompt := st.chat_input("Escribe tu mensaje aquí o ingresa un nuevo ID para otra consulta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Manejar consultas sobre productos en cualquier momento
        if st.session_state.stage == 'showing_products' and any(word in prompt.lower() for word in ['productos', 'product', 'lista', 'ver', 'mostrar']):
            products = st.session_state.company_products
            if products:
                response = f"Aquí tienes la lista completa de productos disponibles para tu compañía:\n\n"
                for i, product in enumerate(products):
                    name = product.get('name', 'Producto sin nombre')
                    description = product.get('description', 'Sin descripción disponible')
                    price = product.get('price', 'Precio no disponible')
                    response += f"{i+1}. **{name}**\n   {description}\n   Precio: {price}\n\n"
                response += "¿Te gustaría que te ayude con información sobre algún producto específico o prefieres continuar con tus resultados médicos?"
            else:
                response = "Tu compañía no tiene productos disponibles en este momento. ¿Te gustaría continuar con tus resultados médicos?"
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
        elif st.session_state.stage == 'showing_products':
            # Cualquier otro input en showing_products pasa a authenticated
            st.session_state.stage = 'authenticated'

        # Verificar si es un ID válido en cualquier momento
        user_id = prompt.strip()
        if user_id.isdigit() and len(user_id) > 0:
            try:
                results = get_user_results(user_id)
                user_name = "Usuario"
                st.session_state.user_data = {"id": user_id, "results": results}
                # Analizar automáticamente
                issues, needs_appointment = analyze_results(results)

                if not issues:
                    response = f"¡Hola, {user_name}! Gracias por compartir tus resultados conmigo. Me da gusto poder revisarlos contigo.\n\nExcelente noticia, tus valores están todos dentro del rango saludable:\n\n" + "\n".join([f"- {k}: {v}" for k,v in results.items()]) + "\n\nEstos resultados indican que estás llevando un estilo de vida saludable. ¡Felicitaciones! Sigue así con tus buenos hábitos de alimentación y ejercicio.\n\n¿Tienes alguna duda sobre tus resultados o hay algo más en lo que pueda ayudarte?"
                    st.session_state.stage = 'completed'
                else:
                    response = f"¡Hola, {user_name}! Gracias por compartir tus resultados conmigo. He revisado tus valores y me gustaría comentarte lo que veo:\n\n"
                    for issue in issues:
                        response += f"- {issue}\n"
                    response += "\nAunque no son valores alarmantes, sería recomendable que un médico los revise más a fondo. ¿Te gustaría que te ayude a agendar una cita para que puedas discutir estos resultados con un profesional?"
                    st.session_state.stage = 'analyzing'
            except Exception as e:
                error_msg = str(e)
                if "Paciente no identificado" in error_msg:
                    response = f"Lo siento, no se logró identificar al paciente con el ID {user_id}. Verifica que el número sea correcto o contacta a soporte. ¿Hay algo más en lo que pueda ayudarte?"
                else:
                    response = f"Error obteniendo resultados de la API: {error_msg}. ¿Puedes compartir tus resultados médicos en formato JSON? Ejemplo: {{\"Glicemia Basal\": 90, \"Hemoglobina\": 13}}"
        elif st.session_state.stage == 'analyzing' and any(word in prompt.lower() for word in ['si', 'sí', 'yes', 'claro', 'por favor']):
            # Obtener clínicas disponibles
            try:
                clinics = get_health_providers(st.session_state.company_id)
                if clinics:
                    st.session_state.clinics = clinics
                    response = f"¡Perfecto! Antes de agendar, necesito saber en qué clínica te gustaría atenderte. Estas son las opciones disponibles:\n\n"
                    for i, clinic in enumerate(clinics):
                        response += f"{i+1}. {clinic['name']}\n"
                    response += "\n¿En cuál clínica prefieres agendar tu cita? (di el número o el nombre de la clínica)"
                    st.session_state.stage = 'selecting_clinic'
                else:
                    response = "Lo siento, no hay clínicas disponibles en este momento. ¿Te gustaría intentarlo más tarde o tienes alguna otra consulta?"
                    st.session_state.stage = 'completed'
            except Exception as e:
                response = f"Error obteniendo clínicas disponibles: {str(e)}. ¿Te gustaría intentarlo más tarde?"
                st.session_state.stage = 'completed'
        elif st.session_state.stage == 'scheduling':
            next_days = st.session_state.next_days
            selected_day = None
            for day in next_days:
                day_parts = [p.lower() for p in day.split()]
                if any(part in prompt.lower() for part in day_parts):
                    parsed_date = parse_date_from_day_string(day)
                    if parsed_date and parsed_date > datetime.now():
                        selected_day = day
                        break
            if selected_day:
                hours = [f"{h}:00" for h in range(9, 19)]
                hours_str = "\n".join(f"- {h}" for h in hours)
                response = f"Genial, el {selected_day} tengo disponibilidad en los siguientes horarios:\n{hours_str}\n\n¿A qué hora te gustaría agendar?"
                st.session_state.selected_day = selected_day
                st.session_state.stage = 'selecting_time'
            else:
                response = "No reconocí ese día o la fecha ya pasó. ¿Puedes elegir uno de los disponibles?"
        elif st.session_state.stage == 'selecting_time':
            hour_input = prompt.strip()
            try:
                # Try to parse as number (9-18)
                h = int(hour_input)
                if 9 <= h <= 18:
                    hour = f"{h}:00"
                    response = f"Perfecto, reservo para el {st.session_state.selected_day} a las {hour}. ¿Confirmo tu cita?"
                    st.session_state.selected_time = hour
                    st.session_state.stage = 'confirming'
                else:
                    response = "Esa hora no está disponible. Elige un horario entre 9 y 18."
            except ValueError:
                # Try HH:MM format
                if ':' in hour_input and len(hour_input.split(':')) == 2:
                    try:
                        h, m = map(int, hour_input.split(':'))
                        if 9 <= h <= 18 and m == 0:
                            response = f"Perfecto, reservo para el {st.session_state.selected_day} a las {hour_input}. ¿Confirmo tu cita?"
                            st.session_state.selected_time = hour_input
                            st.session_state.stage = 'confirming'
                        else:
                            response = "Esa hora no está disponible. Elige un horario entre 9:00 y 18:00."
                    except:
                        response = "Formato de hora inválido. Elige un número entre 9 y 18, o formato HH:00."
                else:
                    response = "Por favor, indica la hora como un número entre 9 y 18, ej. 10."
        elif st.session_state.stage == 'selecting_clinic':
            clinics = st.session_state.clinics
            selected_clinic = None
            # Try to match by number
            try:
                clinic_num = int(prompt.strip()) - 1
                if 0 <= clinic_num < len(clinics):
                    selected_clinic = clinics[clinic_num]['name']
            except ValueError:
                # Try to match by name
                for clinic in clinics:
                    if clinic['name'].lower() in prompt.lower():
                        selected_clinic = clinic['name']
                        break
            if selected_clinic:
                st.session_state.selected_clinic = selected_clinic
                next_days = get_next_business_days(3)
                st.session_state.next_days = next_days
                response = f"¡Excelente! Has seleccionado {selected_clinic}.\n\nAhora, tengo disponibilidad para agendar una cita en los próximos días hábiles:\n\n"
                for i, day in enumerate(next_days):
                    response += f"{i+1}. {day}\n"
                response += "\n¿Para qué día te gustaría agendar? (di el nombre del día o la fecha)"
                st.session_state.stage = 'scheduling'
            else:
                response = "No reconocí esa clínica. ¿Puedes elegir una de las opciones disponibles?"
        elif st.session_state.stage == 'confirming' and any(word in prompt.lower() for word in ['si', 'sí', 'yes', 'claro', 'por favor', 'confirmo']):
            try:
                # Preparar datos para API (conversión interna)
                api_appointment_data = prepare_api_appointment_data()

                # Enviar a API
                api_response = send_appointment_to_api(api_appointment_data)

                if api_response.status_code in [200, 201]:  # Success
                    response = f"¡Excelente! Tu cita quedó confirmada para el {st.session_state.selected_day} a las {st.session_state.selected_time} en {st.session_state.selected_clinic}.\n\n"
                    response += "La cita ha sido registrada correctamente en nuestro sistema. Te enviaremos un recordatorio antes de la hora programada.\n\n"
                    response += "¿Tienes alguna otra consulta o duda sobre tu salud? Estoy aquí para ayudarte."
                    st.session_state.stage = 'completed'
                else:
                    # Error en API, intentar guardar localmente como respaldo
                    appointment = {
                        "user_id": st.session_state.user_data.get('id', "nuevo") if st.session_state.user_data else "nuevo",
                        "name": "Usuario",
                        "date": st.session_state.selected_day,
                        "time": st.session_state.selected_time,
                        "clinic": st.session_state.selected_clinic
                    }
                    save_appointment(appointment)

                    response = f"Tu cita quedó guardada localmente para el {st.session_state.selected_day} a las {st.session_state.selected_time} en {st.session_state.selected_clinic}.\n\n"
                    response += f"Nota: Hubo un problema temporal al registrar en el sistema central (Error {api_response.status_code}). Tu cita está segura y será sincronizada automáticamente.\n\n"
                    response += "¿Tienes alguna otra consulta o duda sobre tu salud? Estoy aquí para ayudarte."
                    st.session_state.stage = 'completed'

            except Exception as e:
                # Error grave, guardar localmente
                appointment = {
                    "user_id": st.session_state.user_data.get('id', "nuevo") if st.session_state.user_data else "nuevo",
                    "name": "Usuario",
                    "date": st.session_state.selected_day,
                    "time": st.session_state.selected_time,
                    "clinic": st.session_state.selected_clinic
                }
                save_appointment(appointment)

                response = f"Tu cita quedó guardada localmente para el {st.session_state.selected_day} a las {st.session_state.selected_time} en {st.session_state.selected_clinic}.\n\n"
                response += f"Nota: Error técnico al procesar la cita ({str(e)}). Tu cita está segura y será sincronizada cuando se restablezca la conexión.\n\n"
                response += "¿Tienes alguna otra consulta o duda sobre tu salud? Estoy aquí para ayudarte."
                st.session_state.stage = 'completed'
        elif st.session_state.stage == 'waiting_json':
            try:
                data = json.loads(prompt)
                results = {k: v for k, v in data.items() if k != 'nombre_usuario'}
                user_name = data.get('nombre_usuario', 'Usuario')
                issues, needs_appointment = analyze_results(results)
                if not issues:
                    response = f"¡Hola, {user_name}! Gracias por compartir tus resultados conmigo. Me da gusto poder revisarlos contigo.\n\nExcelente noticia, tus valores están todos dentro del rango saludable:\n\n" + "\n".join([f"- {k}: {v}" for k,v in results.items()]) + "\n\nEstos resultados indican que estás llevando un estilo de vida saludable. ¡Felicitaciones! Sigue así con tus buenos hábitos de alimentación y ejercicio.\n\n¿Tienes alguna duda sobre tus resultados o hay algo más en lo que pueda ayudarte?"
                    st.session_state.stage = 'completed'
                else:
                    response = f"¡Hola, {user_name}! Gracias por compartir tus resultados conmigo. He revisado tus valores y me gustaría comentarte lo que veo:\n\n"
                    for issue in issues:
                        response += f"- {issue}\n"
                    response += "\nAunque no son valores alarmantes, sería recomendable que un médico los revise más a fondo. ¿Te gustaría que te ayude a agendar una cita para que puedas discutir estos resultados con un profesional?"
                    st.session_state.stage = 'analyzing'
                st.session_state.user_data = {"results": results}
            except json.JSONDecodeError:
                response = "El formato JSON no es válido. Por favor, comparte tus resultados en formato JSON válido, ejemplo: {\"Glicemia Basal\": 90, \"Hemoglobina\": 13}"
        elif st.session_state.stage == 'completed':
            # Permitir nueva consulta o continuar conversación
            if user_id.isdigit() and len(user_id) > 0:
                # Ya manejado arriba
                pass
            else:
                # Usar Bedrock para consultas generales o nuevas
                response = invoke_bedrock(BIANCA_PROMPT, prompt, st.session_state.context)
        else:
            response = invoke_bedrock(BIANCA_PROMPT, prompt, st.session_state.context)

        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)