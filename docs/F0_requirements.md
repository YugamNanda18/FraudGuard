# FraudAI Agent — Business Requirements Document (F0)

**Proyecto:** FraudAI Agent (Harvey AI)
**Versión:** 1.0
**Fecha:** 2026-04-06
**Autor:** ARCA / Adrian Infantes
**Estado:** Draft — Pendiente aprobación Adrian

---

## 1. Business Requirements (BR)

### BR-001 | MUST | Objetivo de negocio
Construir una plataforma de IA agéntica Nivel 3 (consultoría + análisis + ejecución) especializada en fraude bancario y AI red teaming para FinTech.

**Criterio de aceptación:** La plataforma permite a usuarios ejecutar análisis de fraude, generar reportes regulatorios, y realizar red teaming sobre modelos ML — no solo consultar.

### BR-002 | MUST | Propuesta de valor
Ofrecer un "bufete de IA" con agentes especializados que ejecutan acciones reales, respaldados por normativa legal actualizada del BOE vía RAG, con personalidades marcadas y sin disclaimers genéricos.

**Criterio de aceptación:** Los agentes responden con autoridad profesional, citan normativa específica, y ejecutan herramientas — no solo asesoran.

### BR-003 | MUST | Diferenciadores vs competencia

| Diferenciador | FraudAI | Unit21 | Sardine | Feedzai | ComplyAdvantage |
|---|---|---|---|---|---|
| Multi-agent con personalidades | SI | NO | NO | NO | NO |
| AI Red Teaming integrado | SI | NO | NO | NO | NO |
| RAG normativa legal ES/EU | SI | NO | NO | NO | NO |
| Conversational UX (chat) | SI | NO | NO | NO | NO |
| Nivel 3 ejecución | SI | SI | SI | SI | NO |
| Especialización mercado español | SI | NO | NO | NO | NO |

**Criterio de aceptación:** Cada diferenciador es demostrable en una demo funcional.

### BR-004 | MUST | Mercado target
- Primario: Equipos de fraude en fintech/neobancos españoles y europeos
- Secundario: AI red teamers en servicios financieros
- Terciario: Consultoras de compliance (PwC, EY, KPMG como canal)

**Criterio de aceptación:** Documentados al menos 3 perfiles de usuario con casos de uso validados.

### BR-005 | SHOULD | Modelo de negocio
SaaS B2B con tiers:
- Free: Consultoría limitada (Nivel 1)
- Pro: Análisis + ejecución limitada (Nivel 2-3)
- Enterprise: Ejecución completa + red teaming + custom agents

**Criterio de aceptación:** Pricing matrix definida con feature gates por tier.

### BR-006 | MUST | Interfaz de usuario
Doble interfaz:
- **API REST (FastAPI):** Endpoint principal para integraciones B2B, SDKs, y uso programático
- **Web Chat (Next.js + React):** Interfaz conversacional para uso directo por analistas y red teamers

Estrategia de entrega:
- F4: API-only (MVP funcional, todos los agentes accesibles via endpoints)
- F4.5: Web chat (conversational UX, upload de documentos, visualización de grafos/reportes)

**Criterio de aceptación:** API documentada con OpenAPI spec. Web chat soporta conversación multi-turn, upload de archivos, y renderizado de reportes/grafos.

### BR-007 | SHOULD | Internacionalización (i18n)
Idiomas soportados:
- **MVP:** Español (ES) + Inglés (EN)
- **Post-MVP:** Portugués (PT) — mercado ibérico/latam

Alcance:
- Agentes responden en el idioma del usuario (auto-detect o configuración de sesión)
- RAG: normativa española siempre en español; normativa EU disponible en ES/EN
- Personalidades de agentes se mantienen en ambos idiomas
- UI del web chat: ES/EN

**Criterio de aceptación:** Conversación completa en español e inglés sin degradación de calidad en ningún agente.

---

## 2. User Requirements (UR)

### 2.1 Perfil: Fraud Analyst (Equipo antifraude en fintech)

#### UR-001 | MUST | Consulta de fraude transaccional
Como fraud analyst, quiero describir un patrón de transacciones sospechosas para que Harvey Specter analice el caso y me devuelva: scoring de riesgo, patrones detectados, y reglas de detección recomendadas.

**Criterio de aceptación:** El agente recibe descripción textual + datos opcionales (CSV/JSON), ejecuta análisis, y devuelve reporte estructurado con scoring, patrones, y reglas implementables.

#### UR-002 | MUST | Análisis de dataset de transacciones
Como fraud analyst, quiero subir un dataset de transacciones para que Harvey las analice en busca de anomalías, fraude potencial, y patrones de riesgo.

**Criterio de aceptación:** Acepta CSV/JSON hasta 100MB, ejecuta análisis estadístico y ML, devuelve alertas priorizadas con explicación.

#### UR-003 | MUST | Consulta regulatoria
Como fraud analyst, quiero preguntar a Louis Litt sobre normativa aplicable a mi caso (AML, KYC, PSD2) y recibir artículos específicos con interpretación.

**Criterio de aceptación:** Cita artículos exactos del BOE/normativa EU con número de ley, artículo, y fecha de última modificación. Sin disclaimers.

#### UR-004 | MUST | Generación de reportes SAR/STR
Como fraud analyst, quiero que Louis genere un borrador de reporte de actividad sospechosa (SAR/STR) basado en el caso analizado.

**Criterio de aceptación:** Genera documento en formato estructurado con todos los campos requeridos por SEPBLAC, listo para revisión humana.

#### UR-005 | SHOULD | Investigación de redes de fraude
Como fraud analyst, quiero que Jessica Pearson analice relaciones entre cuentas/transacciones para identificar redes de mulas o esquemas organizados.

**Criterio de aceptación:** Recibe datos de transacciones, genera grafo de relaciones, identifica clusters sospechosos, y devuelve visualización + reporte.

#### UR-006 | SHOULD | Pipeline de datos antifraude
Como fraud analyst, quiero que Rachel Zane me ayude a diseñar y generar código para pipelines de detección de fraude.

**Criterio de aceptación:** Genera código Python funcional para pipelines ETL, feature engineering, y data quality checks específicos para fraude.

### 2.2 Perfil: AI Red Teamer

#### UR-007 | MUST | Auditoría adversarial de modelo ML
Como AI red teamer, quiero que Mike Ross evalúe la robustez de un modelo de detección de fraude contra ataques adversariales.

**Criterio de aceptación:** Acepta modelo (endpoint API o archivo), ejecuta batería de ataques (evasion, poisoning, extraction), devuelve reporte de vulnerabilidades con severidad y mitigaciones.

#### UR-008 | MUST | Test de prompt injection en LLMs
Como AI red teamer, quiero que Mike pruebe la resistencia de un LLM desplegado en entorno financiero contra prompt injection.

**Criterio de aceptación:** Ejecuta suite de ataques de prompt injection, jailbreaking, y data exfiltration. Devuelve reporte con vulnerabilidades encontradas y payloads exitosos.

#### UR-009 | SHOULD | AI governance assessment
Como AI red teamer, quiero que Mike evalúe el cumplimiento de un sistema de IA con el AI Act EU y normativa española.

**Criterio de aceptación:** Genera checklist de cumplimiento con estado por requisito, gaps identificados, y plan de remediación.

#### UR-010 | COULD | Simulación de ataques de fraude
Como AI red teamer, quiero que Mike simule patrones de fraude realistas para probar la eficacia de sistemas de detección.

**Criterio de aceptación:** Genera transacciones sintéticas que simulan tipologías de fraude conocidas (carding, ATO, money laundering), calibradas para evadir modelos existentes.

### 2.3 Flujo de interacción general

#### UR-011 | MUST | Router inteligente (Donna)
Como usuario, quiero describir mi caso/necesidad y que el sistema me derive automáticamente al especialista correcto.

**Criterio de aceptación:** Donna clasifica correctamente >90% de los casos en primera derivación. Permite override manual del usuario.

#### UR-012 | MUST | Contexto de sesión persistente
Como usuario, quiero subir documentos (contratos, datasets, logs) y que permanezcan como contexto durante toda la sesión.

**Criterio de aceptación:** Documentos subidos se indexan en <30s y están disponibles para todos los agentes de la sesión.

#### UR-013 | SHOULD | Escalación entre agentes
Como usuario, quiero que si mi caso cruza dominios (ej: fraude + compliance), los agentes colaboren automáticamente.

**Criterio de aceptación:** LangGraph orquesta transferencia de contexto entre agentes sin pérdida de información.

#### UR-014 | SHOULD | Feedback del usuario
Como usuario, quiero poder valorar las respuestas de los agentes (util/no util) y corregir errores para que el sistema mejore.

**Criterio de aceptación:** Cada respuesta tiene opción de feedback (thumbs up/down + comentario opcional). Feedback almacenado para evaluación y mejora continua del sistema (prompt tuning, retrieval quality).

---

## 3. System Requirements (SR)

### 3.1 Requisitos funcionales por agente

#### SR-001 | MUST | Donna Paulsen — Router
- Clasificación de intención mediante LLM
- Análisis de contexto del mensaje del usuario
- Routing a sub-agente correcto via LangGraph
- Fallback: preguntar al usuario si clasificación es ambigua
- **Tools necesarios:** Ninguno (solo routing logic)

#### SR-002 | MUST | Harvey Specter — Transaction Fraud Detection
- **Tools necesarios:**
  - `analyze_transactions`: Recibe CSV/JSON, ejecuta análisis estadístico (distribuciones, anomalías, Z-scores)
  - `detect_patterns`: Ejecuta modelos ML preentrenados para detección de patrones (clustering, isolation forest, autoencoders)
  - `generate_rules`: Propone reglas de detección basadas en patrones encontrados (formato YAML/JSON para sistemas de reglas)
  - `risk_scoring`: Calcula scoring de riesgo por transacción/cuenta
  - `search_boe`: Búsqueda en RAG de normativa relevante
- **Inputs aceptados:** CSV, JSON, texto descriptivo
- **Outputs:** Reporte estructurado (JSON + texto natural), alertas priorizadas, reglas exportables

#### SR-003 | MUST | Louis Litt — AML/KYC/Compliance
- **Tools necesarios:**
  - `search_boe`: Búsqueda semántica en BOE (Ley 10/2010, PSD2, RGPD, etc.)
  - `search_eu_regulation`: Búsqueda en normativa EU (EUR-Lex)
  - `generate_sar_report`: Genera borrador de SAR/STR en formato SEPBLAC
  - `compliance_checklist`: Genera checklist de cumplimiento por normativa
  - `kyc_assessment`: Evalúa nivel de diligencia debida requerido
- **Inputs aceptados:** Descripción del caso, documentos del cliente
- **Outputs:** Informes regulatorios, artículos citados con fuente, checklists

#### SR-004 | MUST | Jessica Pearson — Fraud Intelligence & Investigation
- **Tools necesarios:**
  - `graph_analysis`: Construye y analiza grafos de transacciones (NetworkX / Neo4j)
  - `identity_resolution`: Detecta cuentas vinculadas por atributos compartidos
  - `pattern_matching`: Compara contra tipologías GAFI/FATF conocidas
  - `timeline_analysis`: Reconstruye cronología de actividad sospechosa
  - `search_boe`: Acceso a normativa vía RAG
- **Inputs aceptados:** Datasets de transacciones, metadata de cuentas
- **Outputs:** Grafos visualizables, clusters de cuentas sospechosas, cronologías, reportes de inteligencia

#### SR-005 | MUST | Mike Ross — AI Red Teaming & Adversarial Security
- **Tools necesarios:**
  - `adversarial_evasion`: Genera ejemplos adversariales contra modelo target (FGSM, PGD, C&W)
  - `prompt_injection_suite`: Ejecuta batería de ataques de prompt injection
  - `model_extraction`: Intenta extraer información del modelo vía queries
  - `data_poisoning_sim`: Simula ataques de data poisoning
  - `ai_governance_audit`: Evalúa cumplimiento AI Act EU
  - `synthetic_fraud_gen`: Genera transacciones sintéticas de fraude para testing
  - `search_boe`: Acceso a normativa de IA vía RAG
- **Inputs aceptados:** Endpoint API del modelo target, datasets, descripción del sistema
- **Outputs:** Reporte de vulnerabilidades (severidad CVSS-like), payloads exitosos, mitigaciones, datos sintéticos

#### SR-006 | SHOULD | Rachel Zane — Data Engineering & Feature Intelligence
- **Tools necesarios:**
  - `generate_pipeline`: Genera código Python para pipelines ETL antifraude
  - `feature_engineering`: Propone y genera features para modelos de detección
  - `data_quality_check`: Ejecuta validación de calidad de datos (Great Expectations)
  - `schema_design`: Diseña schemas para feature stores
  - `code_executor`: Ejecuta código Python en sandbox
  - `search_boe`: Acceso a normativa vía RAG
- **Inputs aceptados:** Datasets, descripción de requerimientos, schemas existentes
- **Outputs:** Código Python funcional, schemas, reportes de calidad, documentación

### 3.2 Requisitos no funcionales

#### SR-007 | MUST | Latencia
- Router (Donna): <2s para clasificación
- Primera respuesta de sub-agente: <5s
- Análisis de dataset (<10MB): <30s
- Análisis de dataset (<100MB): <5min
- Generación de reporte: <60s

**Criterio de aceptación:** P95 dentro de los límites especificados.

#### SR-008 | MUST | Seguridad — Sandboxing de ejecución
- Todo código ejecutado por agentes corre en sandbox aislado (Docker container)
- Sin acceso a filesystem del host
- Sin acceso a red externa (excepto APIs autorizadas)
- Timeout máximo de ejecución: 10min
- Límites de memoria: 8GB por ejecución (para soportar datasets de hasta 100MB con overhead de análisis ML)
- Límites de CPU: 4 cores por ejecución

**Criterio de aceptación:** Penetration test no logra escapar del sandbox.

#### SR-009 | MUST | Seguridad — Aislamiento de datos
- Datos de cada cliente aislados (tenant isolation)
- Documentos de sesión eliminados al cerrar sesión (o retención configurable)
- Sin cross-contamination entre sesiones/clientes
- Encriptación at-rest y in-transit (AES-256 / TLS 1.3)

**Criterio de aceptación:** Audit de seguridad confirma aislamiento completo.

#### SR-010 | MUST | Seguridad — Autenticación y autorización
- Autenticación: OAuth2 / JWT
- Autorización: RBAC por tier (Free/Pro/Enterprise)
- Rate limiting por tier
- Audit log de todas las acciones de agentes

**Criterio de aceptación:** Implementado y testeado contra OWASP Top 10.

#### SR-011 | SHOULD | Escalabilidad
- Soportar 100 sesiones concurrentes en MVP
- Horizontal scaling via containers
- Queue-based processing para análisis pesados

**Criterio de aceptación:** Load test con 100 sesiones simultáneas sin degradación >20%.

#### SR-012 | SHOULD | Observabilidad
- Logging estructurado de todas las interacciones agente-usuario
- Métricas: latencia, tokens consumidos, tool calls, errores
- Tracing distribuido (agente → tool → RAG → respuesta)

**Criterio de aceptación:** Dashboard con métricas en tiempo real.

### 3.3 APIs externas necesarias

#### SR-013 | MUST | API BOE — Legislación Consolidada
- **URL Base:** `https://www.boe.es/datosabiertos/api/legislacion-consolidada`
- **Endpoints verificados:**
  - `GET /legislacion-consolidada` — Búsqueda con query ElasticSearch
  - `GET /legislacion-consolidada/id/{id}` — Documento completo
  - `GET /legislacion-consolidada/id/{id}/texto` — Texto consolidado
  - `GET /legislacion-consolidada/id/{id}/analisis` — Análisis jurídico
- **Formatos:** JSON, XML
- **Filtros disponibles:** materia@codigo, texto (full-text), fecha, departamento, rango
- **Documentación:** https://www.boe.es/datosabiertos/documentos/APIconsolidada.pdf
- **Sin rate limits documentados**
- **Frecuencia de uso:** Descarga semanal automatizada

**Criterio de aceptación:** Script de ingestion descarga y parsea normativa relevante sin errores.

#### SR-014 | MUST | API BOE — Sumarios
- **URL:** `https://www.boe.es/datosabiertos/api/boe/sumario/{fecha}`
- **Formato fecha:** AAAAMMDD
- **Documentación:** https://www.boe.es/datosabiertos/documentos/APIsumarioBOE.pdf
- **Frecuencia de uso:** Chequeo semanal para nuevas disposiciones

**Criterio de aceptación:** Script detecta nuevas disposiciones relevantes publicadas en la última semana.

#### SR-015 | MUST | API BOE — Datos auxiliares
- **URL:** `https://www.boe.es/datosabiertos/api/datos-auxiliares/`
- **Endpoints:** materias, ambitos, departamentos, rangos, estados-consolidacion
- **Uso:** Mapear códigos de materia relevantes para fraude bancario

**Criterio de aceptación:** Mapeados todos los códigos de materia relevantes.

#### SR-016 | SHOULD | EUR-Lex API
- **URL:** https://eur-lex.europa.eu (CELLAR API)
- **Uso:** Directivas EU (AML, PSD2, AI Act) como complemento al BOE
- **Frecuencia:** Mensual

**Criterio de aceptación:** Directivas EU clave indexadas y accesibles via RAG.

#### SR-017 | MUST | LLM Provider API
- **Opciones a evaluar en F0.5:**
  - Anthropic Claude API — mejor tool use, español robusto, coste medio
  - Modelo local (Llama 3.x / Mistral) en RTX 2000 Ada — coste cero, latencia variable, privacidad total
- **Para Nivel 3:** Necesita function calling robusto y mantenimiento de personalidad via system prompt
- **Estrategia recomendada:** Claude API para agentes complejos (Mike, Harvey) + modelo local para queries simples y Donna (routing)
- **Decisión obligatoria en F0.5** con ADR que cubra: coste proyectado, latencia, privacidad, function calling quality

**Criterio de aceptación:** ADR documentado con benchmarks comparativos en tareas de fraude bancario.

### 3.4 Normativa legal clave a indexar en RAG

| ID | Normativa | Referencia BOE | Relevancia |
|---|---|---|---|
| N-001 | Ley 10/2010 PBC/FT | BOE-A-2010-6737 | Prevención blanqueo de capitales |
| N-002 | RD 304/2014 (Reglamento PBC) | BOE-A-2014-4742 | Desarrollo Ley 10/2010 |
| N-003 | Directiva UE 2015/849 (4AMLD) | DOUE | AML EU |
| N-004 | Directiva UE 2018/843 (5AMLD) | DOUE | AML EU actualización |
| N-005 | Reglamento UE 2024/1624 (AMLR) | DOUE | Nuevo marco AML/CFT |
| N-006 | Directiva 2015/2366 (PSD2) | DOUE | Servicios de pago |
| N-007 | RDL 19/2018 Servicios de Pago | BOE-A-2018-16036 | Transposición PSD2 España |
| N-008 | Código Penal (arts. 248-256, 301-304) | BOE-A-1995-25444 | Estafa, blanqueo |
| N-009 | Reglamento UE 2016/679 (RGPD) | DOUE | Protección de datos |
| N-010 | LO 3/2018 (LOPDGDD) | BOE-A-2018-16673 | RGPD España |
| N-011 | Reglamento UE 2024/1689 (AI Act) | DOUE | Regulación de IA |
| N-012 | Circulares Banco de España | BdE | Normativa bancaria |

---

## 4. ML Requirements (MLR)

### MLR-001 | MUST | Estrategia RAG — BOE
- **Ingestion:** Descarga semanal via API BOE → extracción texto → NLP cleanup → chunking → embeddings → vector DB
- **Chunking strategy:** Por artículo/sección legal (no fixed-size) para mantener coherencia semántica
- **Embedding model:** Modelo multilingüe con buen rendimiento en español legal (e.g., multilingual-e5-large, BGE-M3)
- **Vector DB:** Qdrant (MVP y producción) — hybrid search nativo, tenant isolation (ver ADR-002)
- **Retrieval:** Hybrid search (dense + sparse/BM25) con reranking
- **Top-k:** Configurable por agente (default k=10, Louis puede usar k=20 para citas exhaustivas)

**Criterio de aceptación:** Retrieval accuracy >85% en benchmark de preguntas legales de fraude bancario.

### MLR-006 | SHOULD | Versionado del corpus RAG
- Cada ingestion semanal genera una versión inmutable del corpus (snapshot)
- Metadata por chunk incluye: fecha_ingestion, fecha_publicacion_boe, estado_consolidacion, version_corpus
- Rollback posible a versiones anteriores si se detecta corrupción
- El agente incluye en su respuesta la fecha de última actualización del corpus usado
- Normativa derogada se marca como tal pero no se elimina (histórico)

**Criterio de aceptación:** El usuario puede saber qué versión del corpus se usó en cada respuesta. Rollback ejecutable en <5min.

### MLR-002 | MUST | Modelo LLM base
- **Requisito:** Soporte robusto de function calling / tool use
- **Opciones a evaluar en F0.5:**
  - Anthropic Claude API — mejor tool use, español robusto, coste medio
  - Modelo local (Llama 3.x / Mistral) en RTX 2000 Ada 8GB — coste cero, latencia variable, privacidad total
- **Nota:** No se consideran GPT/Gemini — fuera del stack del proyecto
- **Estrategia híbrida recomendada:**
  - Claude API para agentes complejos (Harvey, Mike, Jessica, Louis) que requieren tool use avanzado
  - Modelo local para Donna (routing — tarea ligera) y queries RAG simples
- **Requisito de personalidad:** El modelo debe mantener personalidad consistente (Harvey vs Louis) via system prompt sin drift durante la conversación

**Criterio de aceptación:** ADR con benchmarks comparativos en tareas de fraude bancario (function calling accuracy, personalidad, latencia, coste por sesión).

### MLR-003 | SHOULD | Modelos ML para análisis (Harvey)
- **Anomaly detection:** Isolation Forest, Autoencoders (para datasets del cliente)
- **Clustering:** DBSCAN/HDBSCAN para agrupación de transacciones
- **Scoring:** Modelo de scoring de riesgo preentrenado / fine-tunable
- **NO entrenar modelos propios en MVP** — usar modelos preentrenados + LLM para interpretación

**Criterio de aceptación:** Modelos ejecutan en <30s para datasets <10MB.

### MLR-004 | SHOULD | Graph ML para investigación (Jessica)
- **Graph construction:** NetworkX para MVP, Neo4j para producción
- **Algorithms:** Community detection, centrality measures, link prediction
- **Visualización:** Export a formato compatible con frontend (D3.js / Cytoscape)

**Criterio de aceptación:** Genera grafo interpretable desde dataset de transacciones en <60s.

### MLR-005 | MUST | Evaluación de RAG
- **Framework:** RAGAS o similar
- **Métricas:** Faithfulness, Answer Relevancy, Context Precision, Context Recall
- **Benchmark:** Set de 100+ preguntas sobre normativa de fraude bancario con ground truth

**Criterio de aceptación:** RAGAS score >0.8 en todas las métricas.

---

## 5. Security Requirements (SEC)

### SEC-001 | MUST | Sandboxing de ejecución de código
- Toda ejecución de código (Rachel, Mike) en Docker containers efímeros
- Network isolation (no internet, solo APIs whitelisted)
- Filesystem isolation (solo /tmp del container)
- Resource limits: 4GB RAM, 2 CPU cores, 10min timeout
- No persistent storage entre ejecuciones

**Criterio de aceptación:** Escape test con payloads conocidos — 0 escapes.

### SEC-002 | MUST | Tenant isolation
- Datos de cada cliente en namespace separado
- Vector DB con filtrado por tenant_id
- No shared embeddings entre clientes (solo BOE es compartido)
- Sesiones efímeras por defecto, retención opt-in

**Criterio de aceptación:** Cross-tenant access test — 0 fugas.

### SEC-003 | MUST | Prompt injection defense
- Input sanitization en todos los mensajes de usuario
- Instrucciones de sistema blindadas contra injection
- Monitorización de outputs por data leakage
- Mike Ross NO puede atacar el propio sistema (scope limitado a targets externos autorizados)

**Criterio de aceptación:** Suite de prompt injection tests — 0 bypasses del system prompt.

### SEC-004 | MUST | Audit trail
- Log inmutable de todas las interacciones usuario-agente
- Log de todas las tool calls con inputs/outputs
- Log de todos los documentos subidos/eliminados
- Retención: 1 año mínimo (compliance)

**Criterio de aceptación:** Audit log reconstruye sesión completa de cualquier usuario.

### SEC-005 | SHOULD | Compliance del propio sistema
- RGPD: Derecho de acceso, rectificación, supresión
- AI Act EU: Documentación de sistema de IA de alto riesgo (si aplica)
- PCI-DSS: Si se procesan datos de tarjetas (minimizar scope)

**Criterio de aceptación:** Checklist de compliance completado y revisado.

### SEC-006 | MUST | Red teaming scope control
- Mike Ross SOLO ejecuta contra targets autorizados explícitamente por el usuario
- Requiere confirmación del usuario antes de cada ejecución ofensiva
- No ejecuta contra sistemas de terceros sin autorización escrita
- Rate limiting en herramientas ofensivas

**Criterio de aceptación:** Imposible lanzar ataque sin confirmación explícita del usuario.

---

## 6. Constraints & Risks

### 6.1 Constraints técnicas

| ID | Constraint | Impacto |
|---|---|---|
| C-001 | Hardware dev: RTX 2000 Ada 8GB VRAM | Modelos locales limitados a <8B params quantizados |
| C-002 | API BOE sin rate limits documentados | Riesgo de throttling no anticipado |
| C-003 | BOE actualiza consolidación en 1-3 días | RAG puede tener lag de hasta 1 semana + 3 días |
| C-004 | Normativa EU no siempre disponible en BOE | Necesario EUR-Lex como complemento |
| C-005 | Ejecución Nivel 3 requiere sandboxing robusto | Complejidad de infraestructura significativa |

### 6.2 Riesgos

| ID | Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|---|
| R-001 | LLM genera información legal incorrecta | Media | Crítico | RAG con retrieval verificado + disclaimer contextual (no genérico) |
| R-002 | API BOE cambia o deja de funcionar | Baja | Alto | Cache local + fallback a scraping + monitorización |
| R-003 | Escape de sandbox en ejecución | Baja | Crítico | Defense in depth: Docker + seccomp + network isolation |
| R-004 | Responsabilidad legal por asesoramiento | Media | Crítico | ToS claros: herramienta de apoyo, no sustituto de abogado. Audit trail completo |
| R-005 | Mal uso de Mike Ross (red teaming) contra terceros no autorizados | Media | Crítico | Scope control obligatorio + confirmación + logging |
| R-006 | Coste de API LLM escala con uso | Alta | Medio | Modelo local para queries simples, API para complejas. Caching de respuestas |
| R-007 | Calidad del chunking legal afecta retrieval | Media | Alto | Evaluación continua con RAGAS + chunking semántico por artículo |

### 6.3 Dependencias externas

| Dependencia | Tipo | Riesgo |
|---|---|---|
| API BOE (datos abiertos) | Crítica | Sin SLA oficial |
| LLM Provider (Anthropic/OpenAI) | Crítica | Coste variable, posible downtime |
| EUR-Lex CELLAR API | Deseable | Complemento, no bloqueante |
| Docker / Container runtime | Crítica | Necesario para sandboxing |
| Vector DB (Chroma/Weaviate) | Crítica | Self-hosted, controlable |

---

## Apéndice A: Normativa BOE — APIs verificadas

### API Legislación Consolidada
- **Base:** `https://www.boe.es/datosabiertos/api/legislacion-consolidada`
- **Docs:** https://www.boe.es/datosabiertos/documentos/APIconsolidada.pdf
- **Formatos:** JSON, XML
- **Filtros:** materia@codigo, texto (full-text), fecha, departamento, rango
- **Paginación:** offset + limit (limit=-1 para todo)

### API Sumarios
- **Base:** `https://www.boe.es/datosabiertos/api/boe/sumario/{AAAAMMDD}`
- **Docs:** https://www.boe.es/datosabiertos/documentos/APIsumarioBOE.pdf

### API Datos Auxiliares
- **Base:** `https://www.boe.es/datosabiertos/api/datos-auxiliares/`
- **Endpoints:** materias, ambitos, departamentos, rangos, estados-consolidacion

---

## Apéndice B: Competencia analizada

| Competidor | Nivel | Tecnología | Red Teaming | RAG Legal | Conversational |
|---|---|---|---|---|---|
| Unit21 | 3 | LLM agents (OpenAI) | NO | NO | NO |
| Sardine | 3 | ML + AI agents | NO | NO | NO |
| Feedzai | 3 | ML + ScamAlert (GenAI) | NO | NO | NO |
| ComplyAdvantage | 2 | Agentic AI (emergente) | NO | NO | NO |
| NICE Actimize | 2-3 | LLMs (emergente) | NO | NO | NO |
| Featurespace | 2 | ML tradicional | NO | NO | NO |
| Hawk AI | 1-2 | Explainable AI | NO | NO | NO |
| SEON | 1 | ML + identity | NO | NO | NO |

**Mercado español:** Sin competidores directos Nivel 3. Solo Revelock (CaixaBank, narrow), Facephi (biometría), Topaz Evolution (consultoría).
