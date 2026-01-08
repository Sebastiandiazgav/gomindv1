# Bianca - Asistente Médico Inteligente

## Descripción General

Bianca es un chatbot médico inteligente desarrollado en Streamlit que proporciona análisis de resultados médicos y gestión de citas. La aplicación integra AWS Bedrock para procesamiento de lenguaje natural y se conecta con la API de GoMind para gestión de datos médicos.

## Características Principales

- 🩺 **Análisis de Resultados Médicos**: Evaluación automática de parámetros de laboratorio
- 📅 **Sistema de Citas**: Agendamiento completo con selección de clínicas y horarios
- 🛍️ **Catálogo de Productos**: Recomendaciones de servicios de salud
- 🤖 **IA Conversacional**: Procesamiento inteligente de intenciones con AWS Bedrock
- 👤 **Gestión de Usuarios**: Autenticación y manejo de sesiones

## Arquitectura del Sistema

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API    │    │   AI Services   │
│   (Streamlit)   │◄──►│   (GoMind API)   │    │  (AWS Bedrock)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Session State   │    │ Medical Data     │    │ Intent Analysis │
│ User Interface  │    │ Appointments     │    │ NLP Processing  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Stack Tecnológico

### Frontend
- **Streamlit 1.50.0**: Framework de aplicación web
- **Python 3.x**: Lenguaje de programación principal

### Backend & APIs
- **GoMind API**: API REST para datos médicos y citas
- **AWS Bedrock**: Servicio de IA para análisis de texto
- **Requests**: Cliente HTTP para comunicación con APIs

### Dependencias Principales
- `boto3`: SDK de AWS para Bedrock
- `streamlit`: Framework de aplicación
- `requests`: Cliente HTTP
- `python-dotenv`: Gestión de variables de entorno

## Estructura del Proyecto

```
bianca-medical-assistant/
├── app.py                    # Aplicación principal
├── api.py                    # Script de prueba de API
├── requirements.txt          # Dependencias Python
├── .env                     # Variables de entorno (desarrollo)
├── .streamlit/
│   └── secrets.toml         # Configuración de secrets
├── appointments.json        # Datos de citas (testing)
├── users.json              # Datos de usuarios (testing)
├── user.txt                # Credenciales de prueba
└── docs/                   # Documentación (generada)
```

## Configuración e Instalación

### Prerrequisitos
- Python 3.8+
- Cuenta AWS con acceso a Bedrock
- Acceso a GoMind API

### Instalación Local

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd bianca-medical-assistant
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno**
```bash
# Copiar y editar archivo de configuración
cp .env.example .env
```

4. **Configurar Streamlit secrets**
```bash
mkdir -p .streamlit
# Editar .streamlit/secrets.toml con credenciales
```

5. **Ejecutar la aplicación**
```bash
streamlit run app.py
```

## Variables de Entorno

### AWS Bedrock
```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
```

### GoMind API
```env
API_BASE_URL=https://api-bianca-desa.gomind.cl
API_EMAIL=your_api_email
API_PASSWORD=your_api_password
```

## Flujos de Usuario

### 1. Flujo de Autenticación
```
Usuario ingresa credenciales → Validación API → Menú principal
```

### 2. Flujo de Análisis Médico
```
ID Usuario → Obtener resultados API → Análisis IA → Recomendaciones → Oferta de cita
```

### 3. Flujo de Agendamiento
```
Selección clínica → Día disponible → Hora → Confirmación → Registro API
```

## Endpoints de API Utilizados

### Autenticación
- `POST /api/auth/login`: Login de usuario
- Retorna: `{token, company: {company_id}}`

### Datos Médicos
- `GET /api/parameters/{user_id}/results`: Resultados de laboratorio
- `GET /api/companies/{company_id}/products`: Productos disponibles
- `GET /api/companies/{company_id}/health-providers`: Clínicas disponibles

### Citas
- `POST /api/appointments`: Crear nueva cita
- Payload: `{user_id, product_id, health_provider_id, date_time}`

## Deployment

### Streamlit Cloud
1. Conectar repositorio GitHub
2. Configurar secrets en dashboard
3. Deploy automático

### Docker (Opcional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

## Monitoreo y Logs

- Logs de Streamlit en consola
- Errores de API capturados y mostrados al usuario
- Session state para debugging de flujos

## Seguridad

- Credenciales en variables de entorno
- Tokens JWT para autenticación API
- Validación de entrada de usuario
- Manejo seguro de datos médicos

## Contribución

1. Fork del repositorio
2. Crear branch de feature
3. Commit de cambios
4. Push y crear Pull Request

## Soporte

Para soporte técnico contactar al equipo de desarrollo de GoMind.

---

**Versión**: 1.0.0  
**Última actualización**: Noviembre 2024  
**Mantenido por**: Equipo GoMind