# Guía de Deployment - Bianca

## Opciones de Deployment

### 1. Streamlit Cloud (Recomendado)

#### Prerrequisitos
- Repositorio en GitHub
- Cuenta en Streamlit Cloud
- Credenciales de AWS y GoMind API

#### Pasos de Deployment

1. **Preparar el repositorio**
```bash
# Asegurar que todos los archivos estén en el repo
git add .
git commit -m "Preparar para deployment"
git push origin main
```

2. **Configurar Streamlit Cloud**
- Ir a [share.streamlit.io](https://share.streamlit.io)
- Conectar con GitHub
- Seleccionar repositorio `bianca-medical-assistant`
- Archivo principal: `app.py`

3. **Configurar Secrets**
En el dashboard de Streamlit Cloud, agregar en "Secrets":

```toml
[aws]
REGION = "us-east-1"
ACCESS_KEY_ID = "AKIA..."
SECRET_ACCESS_KEY = "..."

[api]
BASE_URL = "https://api-bianca-desa.gomind.cl"
EMAIL = "bianca@gomind.cl"
PASSWORD = "..."
```

4. **Deploy**
- Click en "Deploy"
- Monitorear logs durante el deployment
- Verificar que la aplicación esté funcionando

#### URL de Acceso
```
https://bianca-medical-assistant-<random>.streamlit.app
```

---

### 2. Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Exponer puerto
EXPOSE 8501

# Configurar Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Comando de inicio
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### Docker Compose
```yaml
version: '3.8'

services:
  bianca:
    build: .
    ports:
      - "8501:8501"
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=${AWS_REGION}
      - API_BASE_URL=${API_BASE_URL}
      - API_EMAIL=${API_EMAIL}
      - API_PASSWORD=${API_PASSWORD}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

#### Comandos de Deployment
```bash
# Construir imagen
docker build -t bianca-medical-assistant .

# Ejecutar contenedor
docker run -d \
  --name bianca \
  -p 8501:8501 \
  --env-file .env \
  bianca-medical-assistant

# Con Docker Compose
docker-compose up -d
```

---

### 3. AWS ECS Deployment

#### Task Definition
```json
{
  "family": "bianca-medical-assistant",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "bianca",
      "image": "your-account.dkr.ecr.region.amazonaws.com/bianca:latest",
      "portMappings": [
        {
          "containerPort": 8501,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "AWS_REGION",
          "value": "us-east-1"
        }
      ],
      "secrets": [
        {
          "name": "AWS_ACCESS_KEY_ID",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:bianca/aws-credentials"
        },
        {
          "name": "AWS_SECRET_ACCESS_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:bianca/aws-credentials"
        },
        {
          "name": "API_EMAIL",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:bianca/api-credentials"
        },
        {
          "name": "API_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:bianca/api-credentials"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/bianca-medical-assistant",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

---

### 4. Heroku Deployment

#### Archivos Necesarios

**Procfile:**
```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

**runtime.txt:**
```
python-3.9.18
```

#### Comandos de Deployment
```bash
# Instalar Heroku CLI y login
heroku login

# Crear aplicación
heroku create bianca-medical-assistant

# Configurar variables de entorno
heroku config:set AWS_ACCESS_KEY_ID=AKIA...
heroku config:set AWS_SECRET_ACCESS_KEY=...
heroku config:set AWS_REGION=us-east-1
heroku config:set API_BASE_URL=https://api-bianca-desa.gomind.cl
heroku config:set API_EMAIL=bianca@gomind.cl
heroku config:set API_PASSWORD=...

# Deploy
git push heroku main
```

---

## Configuración de Entornos

### Desarrollo Local
```bash
# .env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
API_BASE_URL=https://api-bianca-desa.gomind.cl
API_EMAIL=dev@gomind.cl
API_PASSWORD=dev_password
```

### Staging
```bash
# Variables de entorno para staging
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
API_BASE_URL=https://api-bianca-staging.gomind.cl
API_EMAIL=staging@gomind.cl
API_PASSWORD=staging_password
```

### Producción
```bash
# Variables de entorno para producción
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
API_BASE_URL=https://api-bianca.gomind.cl
API_EMAIL=bianca@gomind.cl
API_PASSWORD=production_password
```

---

## Monitoreo y Logging

### Streamlit Cloud
- Logs disponibles en dashboard
- Métricas básicas de uso
- Alertas por email en caso de errores

### Docker/ECS
```python
# Configuración de logging en app.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/bianca.log'),
        logging.StreamHandler()
    ]
)
```

### Métricas Recomendadas
- Número de usuarios activos
- Tiempo de respuesta de APIs
- Errores de autenticación
- Citas creadas exitosamente
- Uso de Bedrock (tokens consumidos)

---

## Backup y Recuperación

### Datos Críticos
- Configuración de secrets
- Logs de aplicación
- Métricas de uso

### Estrategia de Backup
1. **Código**: Repositorio Git con tags de versión
2. **Configuración**: Secrets respaldados en AWS Secrets Manager
3. **Logs**: Rotación automática y archivado
4. **Base de datos**: No aplica (stateless application)

---

## Rollback Strategy

### Streamlit Cloud
1. Revertir commit en GitHub
2. Redeploy automático
3. Verificar funcionalidad

### Docker/ECS
```bash
# Rollback a versión anterior
docker tag bianca-medical-assistant:v1.0 bianca-medical-assistant:latest
docker push your-registry/bianca-medical-assistant:latest

# Actualizar servicio ECS
aws ecs update-service --cluster bianca-cluster --service bianca-service --force-new-deployment
```

---

## Checklist de Deployment

### Pre-deployment
- [ ] Tests unitarios pasando
- [ ] Variables de entorno configuradas
- [ ] Credenciales de API válidas
- [ ] Acceso a AWS Bedrock verificado
- [ ] Requirements.txt actualizado

### Post-deployment
- [ ] Aplicación accesible via URL
- [ ] Login funcionando correctamente
- [ ] Análisis médico operativo
- [ ] Agendamiento de citas funcional
- [ ] Logs sin errores críticos
- [ ] Performance aceptable (<3s respuesta)

### Monitoreo Continuo
- [ ] Alertas configuradas
- [ ] Métricas siendo recolectadas
- [ ] Backup automático funcionando
- [ ] Documentación actualizada

---

## Troubleshooting Común

### Error: "Module not found"
```bash
# Verificar requirements.txt
pip freeze > requirements.txt
```

### Error: "AWS credentials not found"
```bash
# Verificar variables de entorno
echo $AWS_ACCESS_KEY_ID
```

### Error: "API connection failed"
```bash
# Verificar conectividad
curl -X POST https://api-bianca-desa.gomind.cl/api/auth/login
```

### Error: "Streamlit port already in use"
```bash
# Cambiar puerto
streamlit run app.py --server.port=8502
```