# FraudAI Agent -- API Reference

**Proyecto:** FraudAI Agent (Harvey AI)
**Version:** 0.1.0
**Fecha:** 2026-04-06
**Autor:** ARCA (@docs-writer) / Adrian Infantes
**Fase:** F6 -- Deployment

---

## Informacion general

| Campo | Valor |
|---|---|
| **Base URL** | `http://localhost:8000/api/v1` |
| **Formato** | JSON (application/json) |
| **Autenticacion** | OAuth2 Bearer Token via header `Authorization` |
| **Documentacion interactiva** | Swagger UI: `http://localhost:8000/docs` / ReDoc: `http://localhost:8000/redoc` |
| **Versionado** | Prefijo `/api/v1` en todas las rutas |

---

## Autenticacion

Todos los endpoints (excepto `/health`) requieren un token JWT valido en el header `Authorization`.

```
Authorization: Bearer <token>
```

### Obtener token

> **Nota:** La implementacion completa de autenticacion OAuth2/JWT esta planificada para F4. El esquema utiliza `OAuth2PasswordBearer` con `tokenUrl="/auth/token"`.

El token contiene los siguientes claims:
- `user_id`: Identificador unico del usuario
- `tenant_id`: Identificador del tenant (aislamiento de datos, SR-009)
- `email`: Email del usuario
- `tier`: Nivel de suscripcion (`free`, `pro`, `enterprise`)
- `is_admin`: Privilegios de administrador

### Modelo de usuario

```json
{
    "user_id": "usr_abc123",
    "tenant_id": "tenant_xyz",
    "email": "analyst@fintech.com",
    "tier": "pro",
    "is_admin": false
}
```

---

## Endpoints

### POST /chat

Envia un mensaje al sistema FraudAI. Donna (router) clasifica la intencion y deriva al agente especializado apropiado.

**Flujo:** Mensaje usuario -> Donna (clasificacion) -> Sub-agente -> Respuesta.

**SLAs (F2):**
- Donna routing P95: < 1.5s
- Primera respuesta agente P95: < 5s
- Respuesta completa P95: < 10s

#### Request

| Campo | Tipo | Obligatorio | Descripcion |
|---|---|---|---|
| `message` | string (1-50,000 chars) | SI | Mensaje del usuario |
| `session_id` | string | NO | ID de sesion existente. Si es `null`, se crea una nueva sesion |
| `agent_override` | string | NO | Forzar routing a un agente especifico, saltando a Donna. Valores: `harvey`, `louis`, `jessica`, `mike`, `rachel` |
| `language` | string | NO | Idioma de respuesta: `es` (default) o `en` |

```json
{
    "message": "Necesito analizar un patron de transacciones sospechosas de carding",
    "session_id": null,
    "agent_override": null,
    "language": "es"
}
```

#### Response (200 OK)

| Campo | Tipo | Descripcion |
|---|---|---|
| `session_id` | string | ID de sesion (nuevo o existente) |
| `agent` | string | Agente que proceso la peticion (ej: `harvey`, `louis`) |
| `message` | string | Respuesta del agente en lenguaje natural |
| `citations` | Citation[] | Citas normativas del corpus RAG (puede estar vacia) |
| `tool_results` | ToolResult[] | Resultados de herramientas ejecutadas (puede estar vacia) |
| `metadata` | ResponseMetadata | Metadata de observabilidad |

```json
{
    "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "agent": "harvey",
    "message": "He analizado el patron que describes. Se trata de un esquema clasico de carding con las siguientes caracteristicas...",
    "citations": [
        {
            "boe_id": "BOE-A-2010-6737",
            "norma_titulo": "Ley 10/2010, de 28 de abril, de prevencion del blanqueo de capitales",
            "articulo": "Art. 18",
            "texto_relevante": "Los sujetos obligados examinaran con especial atencion cualquier hecho u operacion...",
            "score": 0.92
        }
    ],
    "tool_results": [],
    "metadata": {
        "routing_agent": "harvey",
        "routing_confidence": 0.95,
        "tokens_used": 1250,
        "latency_ms": 3200,
        "corpus_version": "2026-W14"
    }
}
```

#### Ejemplo curl

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "message": "Necesito analizar un patron de transacciones sospechosas de carding",
    "language": "es"
  }'
```

#### Ejemplo con agent_override (saltar Donna)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "message": "Genera un checklist de cumplimiento PSD2",
    "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "agent_override": "louis",
    "language": "es"
  }'
```

#### Errores

| Codigo | Descripcion |
|---|---|
| 401 | Token invalido o expirado |
| 422 | Request body invalido (mensaje vacio, agent_override desconocido, etc.) |
| 500 | Error interno del grafo de agentes. Reintentar la peticion |

---

### POST /chat/stream

Endpoint SSE (Server-Sent Events) para respuestas en streaming en tiempo real. Recomendado para todas las integraciones de cliente para cumplir el target de latencia percibida < 2s (F2 5.3).

**Request:** Identico a `POST /chat`.

**Response:** `text/event-stream` con eventos incrementales.

#### Tipos de evento SSE

| Tipo | Descripcion | Payload |
|---|---|---|
| `token` | Token de texto incremental del agente | `{"type": "token", "content": "texto..."}` |
| `tool_start` | Una herramienta ha comenzado a ejecutarse | `{"type": "tool_start", "tool_name": "analyze_transactions"}` |
| `tool_end` | Una herramienta ha terminado de ejecutarse | `{"type": "tool_end", "tool_name": "analyze_transactions", "result": "..."}` |
| `done` | Stream completado | `{"type": "done", "session_id": "..."}` |
| `error` | Error durante el procesamiento | `{"type": "error", "message": "..."}` |

#### Ejemplo de stream SSE

```
data: {"type": "token", "content": "He "}

data: {"type": "token", "content": "analizado "}

data: {"type": "token", "content": "el patron..."}

data: {"type": "tool_start", "tool_name": "search_boe"}

data: {"type": "tool_end", "tool_name": "search_boe", "result": "3 documentos encontrados"}

data: {"type": "token", "content": "Segun el Art. 18 de la Ley 10/2010..."}

data: {"type": "done", "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"}

```

#### Ejemplo curl

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "message": "Que normativa aplica al KYC reforzado en operaciones superiores a 15.000 EUR?",
    "language": "es"
  }'
```

> La flag `-N` desactiva el buffering de curl, necesario para ver los eventos SSE en tiempo real.

#### Headers de respuesta

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

#### Errores

| Codigo | Descripcion |
|---|---|
| 401 | Token invalido o expirado |
| 422 | Request body invalido |

Los errores durante el stream se envian como eventos SSE de tipo `error` (no como codigos HTTP, ya que la conexion SSE ya esta abierta).

---

### POST /files/upload

Sube un documento para usarlo como contexto en la sesion. El archivo se indexa en una coleccion efimera de Qdrant vinculada a la sesion (T-RAG-04).

**Formatos aceptados:** CSV, JSON, PDF, TXT
**Tamano maximo:** 100 MB (SR-008)
**SLA de indexacion:** < 30s (SR-007)

#### Request

Multipart form data:

| Campo | Tipo | Obligatorio | Descripcion |
|---|---|---|---|
| `file` | binary (multipart) | SI | Archivo a subir |
| `session_id` | string (query param) | SI | ID de sesion donde asociar el archivo |

#### Response (200 OK)

```json
{
    "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "filename": "transacciones_sospechosas.csv",
    "size_bytes": 5242880,
    "indexed": true,
    "chunks_generated": 42
}
```

| Campo | Tipo | Descripcion |
|---|---|---|
| `file_id` | string (UUID) | Identificador unico del archivo |
| `filename` | string | Nombre original del archivo |
| `size_bytes` | int | Tamano del archivo en bytes |
| `indexed` | bool | Si el archivo fue indexado correctamente en el contexto RAG de la sesion |
| `chunks_generated` | int | Numero de chunks generados durante la indexacion |

#### Ejemplo curl

```bash
curl -X POST "http://localhost:8000/api/v1/files/upload?session_id=f47ac10b-58cc-4372-a567-0e02b2c3d479" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@transacciones_sospechosas.csv"
```

#### Errores

| Codigo | Descripcion |
|---|---|
| 400 | Tipo de archivo no soportado. Permitidos: `.csv`, `.json`, `.pdf`, `.txt` |
| 401 | Token invalido o expirado |
| 413 | Archivo demasiado grande (> 100 MB) |

---

### GET /sessions/{session_id}

Obtiene informacion y metadatos de una sesion. Restringido al tenant del usuario autenticado (SR-009 tenant isolation).

#### Parametros de ruta

| Parametro | Tipo | Descripcion |
|---|---|---|
| `session_id` | string | ID de la sesion a consultar |

#### Response (200 OK)

```json
{
    "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "created_at": "2026-04-06T10:30:00+00:00",
    "agent_history": ["donna", "harvey", "donna", "louis"],
    "uploaded_files": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
    "turn_count": 4
}
```

| Campo | Tipo | Descripcion |
|---|---|---|
| `session_id` | string | ID de la sesion |
| `created_at` | string (ISO 8601) | Timestamp de creacion |
| `agent_history` | string[] | Lista ordenada de agentes que participaron en la sesion |
| `uploaded_files` | string[] | Lista de IDs de archivos subidos |
| `turn_count` | int | Numero de turnos usuario-agente |

#### Ejemplo curl

```bash
curl -X GET http://localhost:8000/api/v1/sessions/f47ac10b-58cc-4372-a567-0e02b2c3d479 \
  -H "Authorization: Bearer <TOKEN>"
```

#### Errores

| Codigo | Descripcion |
|---|---|
| 401 | Token invalido o expirado |
| 403 | La sesion pertenece a otro tenant |
| 404 | Sesion no encontrada |

---

### DELETE /sessions/{session_id}

Elimina una sesion y todos sus datos asociados. Elimina la coleccion efimera de Qdrant con documentos indexados de la sesion. Los registros de audit log se **conservan** segun SEC-004 (retencion 1 ano).

#### Parametros de ruta

| Parametro | Tipo | Descripcion |
|---|---|---|
| `session_id` | string | ID de la sesion a eliminar |

#### Response

204 No Content (sin cuerpo).

#### Ejemplo curl

```bash
curl -X DELETE http://localhost:8000/api/v1/sessions/f47ac10b-58cc-4372-a567-0e02b2c3d479 \
  -H "Authorization: Bearer <TOKEN>"
```

#### Errores

| Codigo | Descripcion |
|---|---|
| 401 | Token invalido o expirado |
| 403 | La sesion pertenece a otro tenant |
| 404 | Sesion no encontrada |

---

### POST /confirm

Aprueba o rechaza una accion pendiente de red teaming (Mike Ross HITL -- Human-In-The-Loop).

Cuando Mike Ross propone una accion ofensiva (evasion adversarial, test de prompt injection, extraccion de modelo), el grafo LangGraph se pausa via `interrupt()` (ADR-003) y espera la confirmacion del usuario.

**SEC-006:** Ninguna herramienta ofensiva se ejecuta sin aprobacion explicita del usuario.

#### Request

```json
{
    "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "action_id": "action_789xyz",
    "approved": true
}
```

| Campo | Tipo | Obligatorio | Descripcion |
|---|---|---|---|
| `session_id` | string | SI | Sesion con una accion pendiente de confirmacion |
| `action_id` | string | SI | Identificador de la accion pendiente |
| `approved` | bool | SI | `true` para aprobar la ejecucion, `false` para rechazarla |

#### Response (200 OK)

Misma estructura que `POST /chat`:

```json
{
    "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "agent": "mike",
    "message": "Ejecutando test de prompt injection contra el endpoint especificado. Resultados: 3 vulnerabilidades detectadas...",
    "citations": [],
    "tool_results": [
        {
            "tool_name": "prompt_injection_suite",
            "status": "success",
            "result": {
                "vulnerabilities_found": 3,
                "severity_max": "high",
                "payloads_successful": ["DAN bypass", "system prompt extraction"]
            },
            "duration_ms": 45000
        }
    ],
    "metadata": {
        "routing_agent": "mike",
        "routing_confidence": 1.0,
        "tokens_used": 3400,
        "latency_ms": 48000,
        "corpus_version": "2026-W14"
    }
}
```

#### Ejemplo curl (aprobar)

```bash
curl -X POST http://localhost:8000/api/v1/confirm \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "action_id": "action_789xyz",
    "approved": true
  }'
```

#### Ejemplo curl (rechazar)

```bash
curl -X POST http://localhost:8000/api/v1/confirm \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "action_id": "action_789xyz",
    "approved": false
  }'
```

#### Errores

| Codigo | Descripcion |
|---|---|
| 401 | Token invalido o expirado |
| 500 | No hay accion pendiente de confirmacion en la sesion, o la sesion no existe |

---

### POST /feedback

Envia feedback sobre una respuesta de un agente. El feedback se almacena para evaluacion continua y mejora del sistema (prompt tuning, calidad de retrieval).

#### Request

```json
{
    "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "message_id": "msg_abc123",
    "rating": 4,
    "comment": "La cita normativa fue precisa, pero faltaba mencionar el RD 304/2014"
}
```

| Campo | Tipo | Obligatorio | Descripcion |
|---|---|---|---|
| `session_id` | string | SI | ID de la sesion |
| `message_id` | string | SI | ID del mensaje del agente que se evalua |
| `rating` | int (1-5) | SI | Valoracion: 1 (malo) a 5 (excelente) |
| `comment` | string (max 2,000 chars) | NO | Comentario libre de texto (default: vacio) |

#### Response (201 Created)

```json
{
    "status": "accepted",
    "feedback_id": "fb_def456"
}
```

#### Ejemplo curl

```bash
curl -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "session_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "message_id": "msg_abc123",
    "rating": 5,
    "comment": "Excelente analisis de las transacciones"
  }'
```

#### Errores

| Codigo | Descripcion |
|---|---|
| 401 | Token invalido o expirado |
| 422 | Rating fuera de rango (1-5) o comment demasiado largo |

---

### GET /health

Health check de todos los componentes de infraestructura. **No requiere autenticacion** -- disenado para load balancers y sistemas de monitorizacion.

Verifica conectividad con:
- **Qdrant** (vector DB)
- **Ollama** (LLM local para Donna)
- **Anthropic Claude API** (LLM remoto para agentes)

#### Request

Sin parametros ni cuerpo.

#### Response (200 OK)

```json
{
    "status": "healthy",
    "qdrant": true,
    "ollama": true,
    "claude_api": true,
    "corpus_version": "2026-W14"
}
```

| Campo | Tipo | Descripcion |
|---|---|---|
| `status` | string | Estado general: `healthy` (todo OK), `degraded` (al menos un servicio operativo), `unhealthy` (todo caido) |
| `qdrant` | bool | Qdrant vector DB accesible |
| `ollama` | bool | Ollama (LLM local para Donna) accesible |
| `claude_api` | bool | Anthropic Claude API accesible |
| `corpus_version` | string o null | Version del corpus RAG activo (ej: `"2026-W14"`). `null` si no disponible |

#### Logica de estado

| Condicion | Estado |
|---|---|
| Qdrant + Ollama + Claude API = OK | `healthy` |
| Al menos uno OK, al menos uno caido | `degraded` |
| Todos caidos | `unhealthy` |

#### Ejemplo curl

```bash
curl -s http://localhost:8000/api/v1/health | python -m json.tool
```

#### Ejemplos de respuestas degradadas

Ollama caido (Donna no puede routear, pero agentes Claude funcionan si se usa `agent_override`):
```json
{
    "status": "degraded",
    "qdrant": true,
    "ollama": false,
    "claude_api": true,
    "corpus_version": "2026-W14"
}
```

Claude API caida (solo Donna funciona para routing, agentes no responden):
```json
{
    "status": "degraded",
    "qdrant": true,
    "ollama": true,
    "claude_api": false,
    "corpus_version": "2026-W14"
}
```

---

### GET /admin/metrics

Endpoint de metricas compatible con Prometheus. Requiere privilegios de administrador.

> **Nota:** Este endpoint esta planificado para la fase F7 (monitorizacion). Actualmente devuelve `501 Not Implemented`.

Metricas previstas (SR-012):
- Request count y histogramas de latencia por endpoint
- Consumo de tokens por agente y por tenant
- Conteo de tool calls y duraciones
- Latencia de retrieval RAG y tasa de cache hit
- Sesiones activas y usuarios concurrentes

#### Ejemplo curl

```bash
curl -s http://localhost:8000/api/v1/admin/metrics \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

#### Errores

| Codigo | Descripcion |
|---|---|
| 401 | Token invalido o expirado |
| 403 | El usuario no tiene privilegios de administrador |
| 501 | Endpoint no implementado (hasta F7) |

---

## Modelos de datos

### Citation

Cita normativa recuperada del corpus RAG (BOE/EU).

```json
{
    "boe_id": "BOE-A-2010-6737",
    "norma_titulo": "Ley 10/2010, de 28 de abril, de prevencion del blanqueo de capitales y de la financiacion del terrorismo",
    "articulo": "Art. 18",
    "texto_relevante": "Los sujetos obligados examinaran con especial atencion cualquier hecho u operacion, con independencia de su cuantia...",
    "score": 0.92
}
```

| Campo | Tipo | Descripcion |
|---|---|---|
| `boe_id` | string | Identificador del documento BOE (ej: `BOE-A-2010-6737`) |
| `norma_titulo` | string | Titulo completo de la normativa citada |
| `articulo` | string | Articulo o seccion especifica citada |
| `texto_relevante` | string | Fragmento de texto recuperado del chunk |
| `score` | float (0.0-1.0) | Confianza del retrieval (0 = irrelevante, 1 = match perfecto) |

### ToolResult

Resultado de la ejecucion de una herramienta por un agente.

```json
{
    "tool_name": "analyze_transactions",
    "status": "success",
    "result": {
        "anomalies_detected": 12,
        "risk_score_avg": 78.5,
        "top_patterns": ["carding", "velocity_abuse"]
    },
    "duration_ms": 15000
}
```

| Campo | Tipo | Descripcion |
|---|---|---|
| `tool_name` | string | Nombre canonico de la herramienta (ej: `analyze_transactions`, `search_boe`) |
| `status` | string | Estado: `success`, `error`, `pending` |
| `result` | object o null | Payload del resultado. `null` cuando status es `pending` o `error` |
| `duration_ms` | int | Tiempo de ejecucion en milisegundos |

### ResponseMetadata

Metadata de observabilidad adjunta a cada respuesta de chat (SR-012).

```json
{
    "routing_agent": "harvey",
    "routing_confidence": 0.95,
    "tokens_used": 1250,
    "latency_ms": 3200,
    "corpus_version": "2026-W14"
}
```

| Campo | Tipo | Descripcion |
|---|---|---|
| `routing_agent` | string | Agente asignado por Donna (ej: `harvey`, `louis`) |
| `routing_confidence` | float (0.0-1.0) | Confianza de clasificacion de Donna. Fallback si < 0.7 |
| `tokens_used` | int | Total de tokens LLM consumidos (input + output) |
| `latency_ms` | int | Latencia end-to-end en milisegundos |
| `corpus_version` | string | Version del corpus RAG usada para esta respuesta (MLR-006) |

---

## Agentes disponibles

Referencia rapida de los agentes accesibles via `agent_override` en `POST /chat`:

| Agente | ID | Especialidad | LLM | Herramientas principales |
|---|---|---|---|---|
| **Donna Paulsen** | `donna` | Router / Clasificacion de intenciones | Llama 3.1 8B (local) | Ninguna (solo routing) |
| **Harvey Specter** | `harvey` | Deteccion de fraude transaccional | Claude Sonnet 4 (API) | analyze_transactions, detect_patterns, generate_rules, risk_scoring, search_boe |
| **Louis Litt** | `louis` | AML / KYC / Compliance | Claude Sonnet 4 (API) | search_boe, search_eu_regulation, generate_sar_report, compliance_checklist, kyc_assessment |
| **Jessica Pearson** | `jessica` | Inteligencia de fraude / Investigacion | Claude Sonnet 4 (API) | graph_analysis, identity_resolution, pattern_matching, timeline_analysis, search_boe |
| **Mike Ross** | `mike` | AI Red Teaming / Seguridad adversarial | Claude Sonnet 4 (API) | adversarial_evasion, prompt_injection_suite, model_extraction, ai_governance_audit, synthetic_fraud_gen, search_boe |
| **Rachel Zane** | `rachel` | Data Engineering / Feature Intelligence | Claude Sonnet 4 (API) | generate_pipeline, feature_engineering, data_quality_check, schema_design, code_executor, search_boe |

> **Nota:** Mike Ross requiere confirmacion HITL (Human-In-The-Loop) antes de ejecutar herramientas ofensivas. Ver endpoint `POST /confirm`.

---

## Codigos de error HTTP

| Codigo | Significado | Cuando se produce |
|---|---|---|
| **200** | OK | Peticion procesada correctamente |
| **201** | Created | Recurso creado (ej: feedback) |
| **204** | No Content | Operacion exitosa sin cuerpo de respuesta (ej: delete session) |
| **400** | Bad Request | Tipo de archivo no soportado, parametros invalidos |
| **401** | Unauthorized | Token JWT ausente, invalido, o expirado |
| **403** | Forbidden | Acceso denegado (otro tenant, o falta de privilegios admin) |
| **404** | Not Found | Sesion no encontrada |
| **413** | Payload Too Large | Archivo subido supera 100 MB |
| **422** | Unprocessable Entity | Request body no cumple el schema (validacion Pydantic) |
| **500** | Internal Server Error | Error del grafo de agentes o fallo interno |
| **501** | Not Implemented | Endpoint no implementado aun (ej: /admin/metrics) |

---

## Rate limits

Los rate limits se aplican por tier de suscripcion (SR-010):

| Tier | Requests/min | Tokens/min | Sesiones concurrentes |
|---|---|---|---|
| **Free** | 10 | 10,000 | 1 |
| **Pro** | 60 | 100,000 | 10 |
| **Enterprise** | 300 | 500,000 | 100 |

> **Nota:** Los rate limits estan planificados para implementacion en F4. Los valores son targets de diseno.

Cuando se excede el rate limit, la API devuelve `429 Too Many Requests` con headers indicando el tiempo de espera.
