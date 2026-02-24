# Flujos de Usuario - Bianca

## Visión General

Bianca maneja múltiples flujos de usuario dependiendo del punto de entrada y las necesidades del usuario. Cada flujo está diseñado para ser intuitivo y guiar al usuario hacia su objetivo.

## Estados del Sistema

```python
STAGES = {
    'inicio': 'Estado inicial, esperando credenciales',
    'main_menu': 'Menú principal después del login',
    'selecting_product': 'Seleccionando producto del catálogo',
    'analyzing': 'Preguntando si quiere agendar cita',
    'selecting_clinic': 'Eligiendo clínica para la cita',
    'scheduling': 'Seleccionando día para la cita',
    'selecting_time': 'Eligiendo hora específica',
    'confirming': 'Confirmando los detalles de la cita',
    'completed': 'Proceso completado exitosamente',
    'waiting_json': 'Esperando resultados médicos en JSON'
}
```

---

## Flujo 1: Autenticación y Menú Principal

### Diagrama de Flujo
```
Inicio → Credenciales → Validación API → Menú Principal
   ↓         ↓              ↓              ↓
Usuario   Email/Pass    Token JWT    Opciones de servicio
```

### Pasos Detallados

1. **Estado Inicial**
   - Usuario accede a la aplicación
   - Sistema muestra mensaje de bienvenida
   - Solicita credenciales de acceso

2. **Entrada de Credenciales**
   ```
   Usuario: "barbara@gomind.cl"
   Sistema: "Por favor, ingresa tu contraseña"
   Usuario: "**rfap1982"
   ```

3. **Validación**
   - Sistema llama a `/api/auth/login`
   - Obtiene token JWT y company_id
   - Almacena en session_state

4. **Menú Principal**
   ```
   Sistema: "¡Ingresaste con éxito! Bienvenido/a [Nombre].
   
   ¿Qué te gustaría hacer hoy?
   
   - Agendar mi cita
   - Revisa mi examen
   
   ¿Cómo te ayudamos hoy? Escribe la opción que prefieras."
   ```

### Manejo de Errores
- **Credenciales inválidas**: Mensaje de error y nueva solicitud
- **Error de API**: Mensaje de conexión y retry
- **Formato inválido**: Guía sobre formato esperado

---

## Flujo 2: Análisis de Resultados Médicos

### Diagrama de Flujo
```
Menú → ID Usuario → API Call → Análisis → Recomendación → Oferta Cita
  ↓       ↓          ↓         ↓           ↓             ↓
Opción 2  Número   Resultados  IA Analysis  Mensaje    Sí/No/Ambiguo
```

### Pasos Detallados

1. **Solicitud de ID**
   ```
   Usuario: "2"
   Sistema: "Para analizar tus resultados médicos, necesito tu ID de usuario. 
            Por favor compártelo conmigo."
   Usuario: "14"
   ```

2. **Obtención de Resultados**
   - Sistema llama a `/api/parameters/14/results`
   - Procesa y normaliza los datos
   - Extrae parámetros médicos

3. **Análisis Automático**
   ```python
   # Ejemplo de resultados procesados
   results = {
       'Colesterol Total': 220,
       'Glicemia Basal': 110,
       'Hemoglobina': 13.5
   }
   
   # Análisis contra rangos de referencia
   issues = analyze_results(results)
   ```

4. **Respuesta Personalizada**
   
   **Caso A: Valores Saludables**
   ```
   Sistema: "¡Usuario! Gracias por compartir tus resultados conmigo. 
            Me da gusto poder revisarlos contigo.
            
            ¡Excelente noticia, tus valores están todos dentro del rango saludable:
            
            - Colesterol Total: 180
            - Glicemia Basal: 90
            - Hemoglobina: 14
            
            Estos resultados indican que estás llevando un estilo de vida saludable. 
            ¡Felicitaciones! Sigue así con tus buenos hábitos."
   ```
   
   **Caso B: Valores Requieren Atención**
   ```
   Sistema: "Usuario! Gracias por compartir tus resultados conmigo. 
            He revisado tus valores y me gustaría comentarte lo que veo:
            
            - Colesterol Total elevado (220 mg/dL, normal: <200)
            - Glicemia Basal ligeramente alta (110 mg/dL, normal: 70-100)
            
            Aunque no están muy elevados, sería recomendable que un médico 
            los revise más a fondo.
            
            ¿Te gustaría que te ayude a agendar una cita para que puedas 
            discutir estos resultados con un profesional?"
   ```

5. **Análisis de Respuesta con IA**
   ```python
   # Bedrock analiza la intención del usuario
   user_response = "podría ser una buena idea"
   intent = analyze_user_intent(user_response, 'analyzing')
   # Resultado: 'POSITIVA'
   ```

### Casos Especiales

**Usuario sin resultados:**
```
Sistema: "Lo siento, no se logró identificar al paciente con el ID 14. 
         Verifica que el número sea correcto o contacta a soporte."
```

**Error de API:**
```
Sistema: "Error obteniendo resultados de la API. ¿Puedes compartir tus 
         resultados médicos en formato JSON? 
         Ejemplo: {'Glicemia Basal': 90, 'Hemoglobina': 13}"
```

---

## Flujo 3: Catálogo de Productos

### Diagrama de Flujo
```
Menú → Productos API → Lista → Selección → Agendamiento
  ↓         ↓          ↓        ↓           ↓
Opción 1   Catálogo   Opciones  Producto   Flujo Cita
```

### Pasos Detallados

1. **Obtención de Productos**
   - Sistema llama a `/api/companies/{company_id}/products`
   - Formatea lista numerada

2. **Presentación al Usuario**
   ```
   Sistema: "Aquí tienes los productos disponibles:
   
   1. Consulta Cardiológica
   2. Examen de Laboratorio Completo
   3. Evaluación Nutricional
   4. Chequeo Médico General
   
   ¿Cuál producto te interesa? Responde con el número de tu opción."
   ```

3. **Selección y Confirmación**
   ```
   Usuario: "2"
   Sistema: "Has seleccionado: **Examen de Laboratorio Completo**
            
            Ahora te ayudo a agendar una cita para este servicio."
   ```

4. **Transición a Agendamiento**
   - Sistema guarda producto seleccionado
   - Inicia flujo de agendamiento de citas

---

## Flujo 4: Agendamiento de Citas

### Diagrama de Flujo
```
Inicio → Clínicas → Selección → Días → Selección → Horas → Selección → Confirmación → API
   ↓        ↓         ↓        ↓        ↓        ↓        ↓           ↓         ↓
Solicitud Lista   Clínica   Lista   Día     Lista    Hora      Detalles   Cita ID
```

### Pasos Detallados

1. **Obtención de Clínicas**
   ```
   Sistema: "Tenemos estas clínicas disponibles:
   
   1. Inmunomedica Concepción
   2. Laboratorio Blanco Santiago  
   3. Red Salud Santiago Centro
   
   ¿En cuál clínica prefieres agendar tu cita? Responde con el número de tu opción"
   ```

2. **Selección de Clínica**
   ```
   Usuario: "2" o "Laboratorio Blanco"
   Sistema: "¡Excelente! Has seleccionado Laboratorio Blanco Santiago.
            
            Ahora, tengo disponibilidad para agendar una cita en los próximos días hábiles:
            
            1. Martes 12 de noviembre
            2. Miércoles 13 de noviembre
            3. Jueves 14 de noviembre
            
            ¿Para qué día te gustaría agendar? (Selecciona el número)"
   ```

3. **Selección de Día**
   ```
   Usuario: "1"
   Sistema: "Genial, el Martes 12 de noviembre tengo disponibilidad en los siguientes horarios:
            
            1. 9:00    7. 15:00
            2. 10:00   8. 16:00
            3. 11:00   9. 17:00
            4. 12:00   10. 18:00
            5. 13:00
            6. 14:00
            
            ¿A qué hora te gustaría agendar? Por favor, responde con el número 
            de tu opción (1-10)."
   ```

4. **Selección de Hora**
   ```
   Usuario: "8"
   Sistema: "Perfecto, reservo para el Martes 12 de noviembre a las 16:00. 
            ¿Confirmo tu cita?"
   ```

5. **Confirmación Final**
   ```
   Usuario: "sí"
   Sistema: "¡Excelente! Tu cita quedó confirmada para el Martes 12 de noviembre 
            a las 16:00 en Laboratorio Blanco Santiago.
            
            La cita ha sido registrada correctamente en nuestro sistema. 
            Te enviaremos un recordatorio antes de la hora programada."
   ```

### Manejo de Respuestas Flexibles

**Reconocimiento por nombre:**
```
Usuario: "prefiero la clínica de santiago centro"
Sistema: [Reconoce "Red Salud Santiago Centro"]
```

**Reconocimiento por día:**
```
Usuario: "mejor el miércoles"
Sistema: [Reconoce "Miércoles 13 de noviembre"]
```

**Formato de hora flexible:**
```
Usuario: "16:00" o "4 de la tarde" o "16"
Sistema: [Convierte a formato estándar]
```

---

## Flujo 5: Manejo de Respuestas Ambiguas

### Estrategias de Clarificación

1. **Respuesta No Clara**
   ```
   Usuario: "mmm no sé"
   Sistema: "Entiendo que puedas tener dudas. ¿Te gustaría que te explique 
            más sobre algún aspecto específico, o prefieres que te ayude 
            con algo diferente?"
   ```

2. **Múltiples Interpretaciones**
   ```
   Usuario: "tal vez más tarde"
   Sistema: "Perfecto, no hay problema. Cuando estés listo para agendar 
            una cita, solo dímelo. ¿Hay algo más en lo que pueda ayudarte 
            mientras tanto?"
   ```

3. **Solicitud de Aclaración**
   ```
   Usuario: "no entendí bien"
   Sistema: "Te explico de nuevo: necesito que elijas una de las opciones 
            numeradas. Por ejemplo, si quieres la primera clínica, 
            responde '1'."
   ```

---

## Flujo 6: Despedida y Finalización

### Detección de Despedida

**Palabras clave detectadas:**
- "gracias", "adiós", "hasta luego", "nos vemos"
- "chao", "bye", "eso es todo", "ya terminé"

### Respuestas Contextuales

1. **Con cita agendada:**
   ```
   Usuario: "perfecto, gracias"
   Sistema: "¡Perfecto, [Nombre]! Me alegra haber podido ayudarte para tu cita 
            del Martes 12 de noviembre a las 16:00 en Laboratorio Blanco Santiago. 
            ¡Que tengas un excelente día y nos vemos pronto!"
   ```

2. **Sin cita agendada:**
   ```
   Usuario: "gracias por la información"
   Sistema: "¡Gracias por usar nuestros servicios, [Nombre]! Espero haber 
            podido ayudarte. ¡Que tengas un excelente día!"
   ```

3. **Genérica:**
   ```
   Usuario: "hasta luego"
   Sistema: "¡Hasta luego! Fue un placer ayudarte. Si necesitas algo más, 
            no dudes en volver. ¡Cuídate!"
   ```

---

## Flujos de Error y Recuperación

### 1. Error de Conexión API
```
Sistema: "Lo siento, hubo un problema de conexión al procesar tu solicitud. 
         Por favor, verifica tu conexión a internet e intenta nuevamente, 
         o contacta a nuestro soporte técnico."
```

### 2. Token Expirado
```
Sistema: "Tu sesión ha expirado. Por favor, ingresa tus credenciales 
         nuevamente para continuar."
```

### 3. Datos Incompletos
```
Sistema: "Parece que falta información para completar tu solicitud. 
         Empecemos de nuevo: ¿qué te gustaría hacer hoy?"
```

### 4. Horario No Disponible
```
Sistema: "Lo siento, ese horario ya no está disponible. Te muestro 
         las opciones actualizadas: [nueva lista]"
```

---

## Métricas y Analytics

### Puntos de Medición

1. **Conversión por Flujo**
   - Usuarios que completan autenticación
   - Usuarios que solicitan análisis médico
   - Usuarios que agendan citas exitosamente

2. **Puntos de Abandono**
   - Etapa donde usuarios dejan el flujo
   - Errores más comunes
   - Tiempo promedio por etapa

3. **Satisfacción del Usuario**
   - Respuestas positivas vs negativas
   - Solicitudes de clarificación
   - Reintentos por errores

### Optimización Continua

- **A/B Testing**: Diferentes versiones de mensajes
- **Análisis de Patrones**: Respuestas más comunes
- **Mejora de IA**: Entrenamiento basado en interacciones reales