# Documentación de API - GoMind Integration

## Base URL
```
https://api-bianca-desa.gomind.cl
```

## Autenticación

Todas las APIs (excepto login) requieren autenticación JWT en el header:
```
Authorization: Bearer <jwt_token>
```

## Endpoints

### 1. Autenticación

#### POST /api/auth/login
Autentica usuario y obtiene token de acceso.

**Request:**
```json
{
  "email": "usuario@ejemplo.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "company": {
    "company_id": 123,
    "name": "Empresa Ejemplo"
  }
}
```

**Errores:**
- `400`: Credenciales inválidas
- `401`: Usuario no autorizado

---

### 2. Resultados Médicos

#### GET /api/parameters/{user_id}/results
Obtiene los resultados de laboratorio de un usuario específico.

**Parámetros:**
- `user_id` (path): ID del usuario

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
[
  {
    "id": 1,
    "user_id": 14,
    "parameter_id": 2,
    "value": 185.5,
    "analysis_results": "VALOR Colesterol Total. El valor de 185.5 mg/dL está dentro del rango normal...",
    "created_at": "2024-01-15T10:30:00Z"
  },
  {
    "id": 2,
    "user_id": 14,
    "parameter_id": 3,
    "value": 95.2,
    "analysis_results": "VALOR Glicemia Basal. El valor de 95.2 mg/dL está dentro del rango saludable...",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

**Casos Especiales:**
- Array vacío `[]`: Usuario sin resultados
- `404`: Usuario no encontrado

**Errores:**
- `401`: Token inválido
- `403`: Sin permisos para este usuario
- `404`: Usuario no encontrado

---

### 3. Productos de Empresa

#### GET /api/companies/{company_id}/products
Obtiene el catálogo de productos/servicios de una empresa.

**Parámetros:**
- `company_id` (path): ID de la empresa

**Response (200):**
```json
{
  "products": [
    {
      "id": 1,
      "name": "Consulta Cardiológica",
      "description": "Evaluación completa del sistema cardiovascular",
      "price": 50000,
      "category": "Cardiología",
      "active": true
    },
    {
      "id": 2,
      "name": "Examen de Laboratorio Completo",
      "description": "Panel completo de análisis de sangre",
      "price": 25000,
      "category": "Laboratorio",
      "active": true
    }
  ]
}
```

**Errores:**
- `401`: Token inválido
- `403`: Sin acceso a esta empresa
- `404`: Empresa no encontrada

---

### 4. Proveedores de Salud

#### GET /api/companies/{company_id}/health-providers
Obtiene las clínicas/proveedores disponibles para una empresa.

**Parámetros:**
- `company_id` (path): ID de la empresa

**Response (200):**
```json
{
  "healthProviders": [
    {
      "health_provider_id": 1,
      "name": "Inmunomedica Concepción",
      "address": "Av. Principal 123, Concepción",
      "phone": "+56 41 234 5678",
      "active": true
    },
    {
      "health_provider_id": 3,
      "name": "Laboratorio Blanco Santiago",
      "address": "Calle Central 456, Santiago",
      "phone": "+56 2 987 6543",
      "active": true
    },
    {
      "health_provider_id": 4,
      "name": "Red Salud Santiago Centro",
      "address": "Plaza de Armas 789, Santiago",
      "phone": "+56 2 555 1234",
      "active": true
    }
  ]
}
```

**Errores:**
- `401`: Token inválido
- `403`: Sin acceso a esta empresa
- `404`: Empresa no encontrada

---

### 5. Gestión de Citas

#### POST /api/appointments
Crea una nueva cita médica.

**Request:**
```json
{
  "user_id": 14,
  "product_id": 2,
  "health_provider_id": 1,
  "date_time": "2024-01-20T14:00:00.000Z"
}
```

**Campos Requeridos:**
- `user_id`: ID del usuario que agenda
- `product_id`: ID del producto/servicio
- `health_provider_id`: ID del proveedor de salud
- `date_time`: Fecha y hora en formato ISO 8601 UTC

**Response (201):**
```json
{
  "id": 456,
  "user_id": 14,
  "product_id": 2,
  "health_provider_id": 1,
  "date_time": "2024-01-20T14:00:00.000Z",
  "status": "confirmed",
  "created_at": "2024-01-15T11:00:00Z"
}
```

**Errores:**
- `400`: Datos inválidos o faltantes
- `401`: Token inválido
- `409`: Conflicto de horario
- `422`: Fecha/hora no válida

---

## Códigos de Estado HTTP

| Código | Significado | Descripción |
|--------|-------------|-------------|
| 200 | OK | Solicitud exitosa |
| 201 | Created | Recurso creado exitosamente |
| 400 | Bad Request | Datos de entrada inválidos |
| 401 | Unauthorized | Token faltante o inválido |
| 403 | Forbidden | Sin permisos para el recurso |
| 404 | Not Found | Recurso no encontrado |
| 409 | Conflict | Conflicto con estado actual |
| 422 | Unprocessable Entity | Datos válidos pero no procesables |
| 500 | Internal Server Error | Error del servidor |

## Manejo de Errores

### Formato de Error Estándar
```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Las credenciales proporcionadas no son válidas",
    "details": "Email o contraseña incorrectos"
  }
}
```

### Códigos de Error Comunes

| Código | Descripción |
|--------|-------------|
| `INVALID_CREDENTIALS` | Credenciales de login incorrectas |
| `TOKEN_EXPIRED` | Token JWT expirado |
| `USER_NOT_FOUND` | Usuario no existe |
| `INSUFFICIENT_PERMISSIONS` | Sin permisos para la operación |
| `APPOINTMENT_CONFLICT` | Horario no disponible |
| `INVALID_DATE_FORMAT` | Formato de fecha incorrecto |

## Rate Limiting

- **Límite**: 100 requests por minuto por token
- **Headers de respuesta**:
  ```
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 95
  X-RateLimit-Reset: 1642680000
  ```

## Timeouts

- **Timeout de conexión**: 10 segundos
- **Timeout de lectura**: 30 segundos
- **Recomendación**: Implementar retry con backoff exponencial

## Ejemplos de Uso

### Flujo Completo de Agendamiento

```python
# 1. Login
login_response = requests.post(
    f"{API_BASE_URL}/api/auth/login",
    json={"email": "user@example.com", "password": "password"}
)
token = login_response.json()["token"]
company_id = login_response.json()["company"]["company_id"]

# 2. Obtener clínicas
headers = {"Authorization": f"Bearer {token}"}
clinics_response = requests.get(
    f"{API_BASE_URL}/api/companies/{company_id}/health-providers",
    headers=headers
)
clinics = clinics_response.json()["healthProviders"]

# 3. Crear cita
appointment_data = {
    "user_id": 14,
    "product_id": 2,
    "health_provider_id": clinics[0]["health_provider_id"],
    "date_time": "2024-01-20T14:00:00.000Z"
}
appointment_response = requests.post(
    f"{API_BASE_URL}/api/appointments",
    json=appointment_data,
    headers=headers
)
```

### Manejo de Errores

```python
try:
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.Timeout:
    # Manejar timeout
    pass
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        # Token expirado, renovar
        pass
    elif e.response.status_code == 404:
        # Recurso no encontrado
        pass
except requests.exceptions.RequestException:
    # Error de conexión general
    pass
```

## Consideraciones de Seguridad

1. **HTTPS**: Todas las comunicaciones deben usar HTTPS
2. **Token Storage**: Almacenar tokens de forma segura
3. **Input Validation**: Validar todos los inputs antes de enviar
4. **Error Handling**: No exponer información sensible en errores
5. **Logging**: No loggear tokens o datos médicos sensibles