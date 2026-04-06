# FraudAI Agent — Technical Specification (F2)

**Proyecto:** FraudAI Agent (Harvey AI)
**Version:** 1.0
**Fecha:** 2026-04-06
**Autor:** ARCA (Adrian Infantes)
**Estado:** Draft — Pendiente aprobacion Adrian

---

## 1. Definicion de Tareas por Componente

### 1.1 RAG Pipeline (BOE)

| Tarea | Input | Output | Tipo |
|---|---|---|---|
| T-RAG-01: Ingestion semanal | API BOE (legislacion consolidada) | Chunks embedidos en Qdrant | Batch offline |
| T-RAG-02: Busqueda semantica | Query texto usuario | Top-k chunks con score y metadata | Online sync |
| T-RAG-03: Busqueda hibrida | Query texto + filtros metadata | Top-k chunks (dense + BM25 fusionados) | Online sync |
| T-RAG-04: Indexacion de sesion | Documento subido por usuario | Chunks en coleccion efimera | Online async |

### 1.2 Donna Paulsen (Router)

| Tarea | Input | Output | Tipo |
|---|---|---|---|
| T-DON-01: Clasificacion de intencion | Mensaje del usuario (texto) | Agente destino + confianza (0-1) | Online sync |
| T-DON-02: Deteccion de idioma | Mensaje del usuario | "es" o "en" | Online sync |
| T-DON-03: Fallback por ambiguedad | Mensaje ambiguo (confianza < 0.7) | Pregunta de clarificacion al usuario | Online sync |

### 1.3 Harvey Specter (Transaction Fraud)

| Tarea | Input | Output | Tipo |
|---|---|---|---|
| T-HAR-01: Analisis de transacciones | CSV/JSON dataset (hasta 100MB) | Reporte: distribuciones, anomalias, Z-scores | Online async (sandbox) |
| T-HAR-02: Deteccion de patrones | Dataset de transacciones | Clusters anomalos (Isolation Forest, DBSCAN) | Online async (sandbox) |
| T-HAR-03: Scoring de riesgo | Dataset de transacciones | Score 0-100 por transaccion/cuenta con explicacion | Online async (sandbox) |
| T-HAR-04: Generacion de reglas | Patrones detectados | Reglas YAML/JSON para sistemas de deteccion | Online sync |
| T-HAR-05: Consulta RAG | Pregunta sobre fraude transaccional | Respuesta con citas normativas | Online sync |

### 1.4 Louis Litt (AML/KYC/Compliance)

| Tarea | Input | Output | Tipo |
|---|---|---|---|
| T-LOU-01: Consulta normativa | Pregunta legal sobre AML/KYC/PSD2 | Respuesta con articulos exactos citados | Online sync |
| T-LOU-02: Generacion SAR/STR | Descripcion del caso sospechoso | Borrador de reporte SEPBLAC estructurado | Online sync |
| T-LOU-03: Checklist compliance | Normativa target (AML, PSD2, RGPD) | Checklist interactivo con estado por requisito | Online sync |
| T-LOU-04: Evaluacion KYC | Perfil del cliente | Nivel de diligencia debida (simplificada/normal/reforzada) | Online sync |

### 1.5 Jessica Pearson (Fraud Intelligence)

| Tarea | Input | Output | Tipo |
|---|---|---|---|
| T-JES-01: Analisis de grafos | Dataset de transacciones | Grafo con community detection, centralidad | Online async (sandbox) |
| T-JES-02: Identity resolution | Metadata de cuentas | Clusters de cuentas vinculadas con scoring | Online async (sandbox) |
| T-JES-03: Pattern matching GAFI | Comportamiento detectado | Match contra tipologias conocidas con confianza | Online sync |
| T-JES-04: Timeline analysis | Transacciones cronologicas | Cronologia visual de actividad sospechosa | Online async (sandbox) |

### 1.6 Mike Ross (AI Red Teaming)

| Tarea | Input | Output | Tipo |
|---|---|---|---|
| T-MIK-01: Evasion adversarial | Endpoint API o modelo serializado | Reporte de vulnerabilidades CVSS-like | Online async (sandbox, HITL) |
| T-MIK-02: Prompt injection test | Endpoint LLM o system prompt | Payloads exitosos + reporte | Online async (sandbox, HITL) |
| T-MIK-03: Model extraction | Endpoint API | Reporte de information leakage | Online async (sandbox, HITL) |
| T-MIK-04: AI governance audit | Descripcion del sistema | Checklist AI Act EU con gaps | Online sync |
| T-MIK-05: Synthetic fraud gen | Tipologia de fraude + params | Dataset sintetico de transacciones fraudulentas | Online async (sandbox) |

### 1.7 Rachel Zane (Data Engineering)

| Tarea | Input | Output | Tipo |
|---|---|---|---|
| T-RAC-01: Generacion pipeline | Descripcion de requerimientos | Codigo Python funcional (pipeline ETL) | Online sync |
| T-RAC-02: Feature engineering | Dataset + objetivo | Features propuestas + codigo de generacion | Online sync |
| T-RAC-03: Data quality check | Dataset | Reporte de calidad (nulls, distribuciones, anomalias) | Online async (sandbox) |
| T-RAC-04: Schema design | Requerimientos de feature store | Schema optimizado con documentacion | Online sync |

---

## 2. Metricas de Exito

### 2.1 Metricas RAG

| Metrica | Target MVP | Herramienta | Frecuencia |
|---|---|---|---|
| **Context Precision** (RAGAS) | >= 0.80 | RAGAS framework | Post-ingestion |
| **Context Recall** (RAGAS) | >= 0.80 | RAGAS framework | Post-ingestion |
| **Faithfulness** (RAGAS) | >= 0.85 | RAGAS framework | Post-ingestion |
| **Answer Relevancy** (RAGAS) | >= 0.80 | RAGAS framework | Post-ingestion |
| **Retrieval Latency P95** | < 200ms | Instrumentacion | Continuo |
| **Ingestion throughput** | >= 50 docs/hora | Logs pipeline | Semanal |
| **Corpus freshness** | < 10 dias desde publicacion BOE | Metadata fecha_ingestion vs fecha_publicacion | Semanal |

### 2.2 Metricas Donna (Router)

| Metrica | Target MVP | Herramienta | Frecuencia |
|---|---|---|---|
| **Classification accuracy** | >= 90% | Benchmark 200 queries etiquetadas | Pre-deploy + mensual |
| **Latencia P95** | < 1.5s | Instrumentacion Ollama | Continuo |
| **Fallback rate** | < 15% (queries que requieren clarificacion) | Logs | Continuo |
| **Misrouting rate** | < 5% (derivaciones incorrectas) | Feedback usuario + audit | Mensual |

**Benchmark de Donna:** 200 queries etiquetadas manualmente:
- 40 queries de fraude transaccional → Harvey
- 40 queries de compliance/regulatorio → Louis
- 40 queries de investigacion de redes → Jessica
- 40 queries de red teaming/seguridad IA → Mike
- 40 queries de data engineering/pipelines → Rachel

### 2.3 Metricas de Agentes (Harvey, Louis, Jessica, Mike, Rachel)

| Metrica | Target MVP | Aplica a | Herramienta |
|---|---|---|---|
| **Tool call accuracy** | >= 95% | Todos | Benchmark 100 llamadas por agente |
| **Personality consistency** | >= 90% (evaluacion humana) | Todos | Evaluacion manual 50 conversaciones |
| **Citation accuracy (Louis)** | >= 95% articulos correctos | Louis | Verificacion manual vs BOE |
| **Anomaly detection precision** | >= 70% | Harvey | Dataset etiquetado de transacciones |
| **Anomaly detection recall** | >= 80% | Harvey | Dataset etiquetado de transacciones |
| **Graph cluster quality (NMI)** | >= 0.60 | Jessica | Dataset sintetico con ground truth |
| **Adversarial success rate** | >= 60% vulnerabilidades encontradas vs conocidas | Mike | Red team benchmark |
| **Code execution success** | >= 90% codigo generado ejecuta sin errores | Rachel | Ejecucion automatica en sandbox |

### 2.4 Metricas de Sistema

| Metrica | Target MVP | Herramienta |
|---|---|---|
| **Primera respuesta P95** | < 5s | Instrumentacion FastAPI |
| **Analisis dataset (<10MB) P95** | < 30s | Instrumentacion sandbox |
| **Analisis dataset (<100MB) P95** | < 5min | Instrumentacion sandbox |
| **Generacion reporte P95** | < 60s | Instrumentacion agente |
| **Uptime** | >= 99% (en horario laboral) | Health checks |
| **Error rate** | < 2% de requests | Logs |
| **Concurrent sessions** | >= 100 | Load test |
| **Token cost per session** | < $0.40 (promedio 10 turns) | Logging tokens |

### 2.5 Metricas de Seguridad

| Metrica | Target MVP | Herramienta |
|---|---|---|
| **Sandbox escapes** | 0 | Penetration test |
| **Cross-tenant leaks** | 0 | Isolation test |
| **Prompt injection bypasses** | 0 en system prompt | Red team interno |
| **Unauthorized red team executions** | 0 sin HITL confirmation | Audit log |

---

## 3. Baselines

### 3.1 Baseline RAG

**Comparacion contra:** Busqueda keyword directa en BOE (sin embeddings, sin reranking).

| Metrica | Baseline (keyword BOE) | Target FraudAI |
|---|---|---|
| Context Precision | ~0.40 (estimado) | >= 0.80 |
| Context Recall | ~0.50 (estimado) | >= 0.80 |
| Respuesta con cita correcta | ~30% | >= 95% (Louis) |

**Como medir baseline:** 100 preguntas legales sobre fraude bancario. Buscar directamente en API BOE con query_string vs nuestro hybrid search. Comparar precision de contextos recuperados.

### 3.2 Baseline Donna (Router)

**Comparacion contra:** Clasificacion por keywords (regex matching).

| Metrica | Baseline (regex) | Target FraudAI |
|---|---|---|
| Classification accuracy | ~70% (estimado) | >= 90% |
| Latencia | < 10ms | < 1.5s |

**Justificacion:** Si regex alcanza >85%, modelo local para Donna puede ser overkill. El benchmark valida esta decision.

### 3.3 Baseline Harvey (Fraud Detection)

**Comparacion contra:** Reglas estaticas (umbrales fijos) sobre Z-scores.

| Metrica | Baseline (reglas) | Target FraudAI |
|---|---|---|
| Precision | ~50% | >= 70% |
| Recall | ~60% | >= 80% |
| Tiempo de analisis | Manual (horas) | < 30s |

**Dataset de evaluacion:** Sintetico + publicos (IEEE-CIS Fraud Detection, PaySim). Ground truth etiquetado.

### 3.4 Baseline Competencia

**Comparacion conceptual contra:** Unit21, Sardine, Feedzai.

| Capacidad | Competencia | FraudAI Target |
|---|---|---|
| Conversational UX | NO | SI |
| Multi-agent personalities | NO | SI |
| RAG normativa legal ES/EU | NO | SI |
| AI Red Teaming integrado | NO | SI |
| Time to first insight | Horas (onboarding + config) | < 5s (primera respuesta) |

---

## 4. Fairness y Sesgo

### 4.1 Riesgos de sesgo identificados

| Riesgo | Descripcion | Mitigacion |
|---|---|---|
| **Sesgo normativo temporal** | RAG puede sobrerepresentar normativa reciente vs historica | Metadata de fecha en chunks, ponderacion configurable |
| **Sesgo linguistico** | Mejor rendimiento en espanol que en ingles (corpus BOE es espanol) | Benchmark bilingue, embeddings multilingues (BGE-M3) |
| **Sesgo de scoring por sector** | Harvey puede asignar mas riesgo a patrones de ciertos sectores | Evaluacion de scoring por subgrupos (sector, tamanio transaccion, geografia) |
| **Sesgo en red teaming** | Mike puede priorizar ataques conocidos vs novedosos | Suite de ataques actualizable, no hardcoded |
| **Sesgo regulatorio por jurisdiccion** | Normativa espanola vs EU puede generar contradicciones | Louis cita siempre la fuente y jerarquia normativa (EU > ES) |

### 4.2 Plan de evaluacion de fairness

- **Harvey:** Evaluar precision/recall de deteccion por subgrupos:
  - Tamanio de transaccion (micro < 100 EUR, pequena 100-1K, media 1K-10K, grande > 10K)
  - Tipo de operacion (transferencia, pago tarjeta, domiciliacion)
  - Diferencia maxima aceptable entre subgrupos: 15 puntos en precision/recall
- **Louis:** Verificar que citas son correctas independientemente de:
  - Idioma de la consulta (ES vs EN)
  - Complejidad de la pregunta (directa vs multi-hop)
- **Donna:** Accuracy uniforme entre las 5 categorias (no sesgo hacia Harvey/Louis por mayor volumen de training data)

---

## 5. Latencia SLA

### 5.1 SLAs por operacion

| Operacion | P50 | P95 | P99 | Timeout |
|---|---|---|---|---|
| **Donna: routing** | 500ms | 1.5s | 3s | 5s |
| **RAG: busqueda** | 100ms | 200ms | 500ms | 2s |
| **Agente: primera respuesta** | 2s | 5s | 8s | 15s |
| **Agente: respuesta completa (streaming)** | 5s | 10s | 15s | 30s |
| **Tool: analyze_transactions (<10MB)** | 10s | 30s | 60s | 120s |
| **Tool: analyze_transactions (<100MB)** | 60s | 300s | 480s | 600s |
| **Tool: graph_analysis** | 15s | 60s | 120s | 300s |
| **Tool: adversarial_evasion** | 30s | 120s | 300s | 600s |
| **Tool: generate_sar_report** | 10s | 30s | 60s | 120s |
| **Pipeline: document indexing (upload)** | 10s | 30s | 60s | 120s |
| **Ingestion: single BOE document** | 5s | 15s | 30s | 60s |

### 5.2 SLA por flujo end-to-end

| Flujo | Descripcion | P95 Target |
|---|---|---|
| **Query simple** | Usuario pregunta → Donna → Agente → Respuesta | < 8s |
| **Query con RAG** | Pregunta legal → Donna → Louis → RAG → Respuesta con citas | < 10s |
| **Analisis dataset** | Upload CSV → Harvey → analyze + detect → Reporte | < 60s (<10MB) |
| **Red team scan** | Describe target → Donna → Mike → HITL → Ejecucion → Reporte | < 5min |
| **Investigacion de red** | Upload datos → Jessica → graph_analysis → Visualizacion | < 2min |

### 5.3 Estrategia de cumplimiento

- **Streaming:** Todas las respuestas de agentes via SSE para percepcion de latencia < 2s
- **Async tools:** Tools pesadas (analisis, grafos, red teaming) ejecutan en background; frontend muestra progreso
- **Caching:** Respuestas RAG identicas cacheadas 1h (mismo query + mismos filtros)
- **Timeout escalado:** Si P95 se excede, notificar al usuario; no cortar la ejecucion silenciosamente
- **Monitoring:** Alertas si P95 real excede SLA en ventana de 1h

---

## 6. Criterios de Aceptacion F2

| Criterio | Verificacion |
|---|---|
| Todas las tareas definidas con I/O claro | Tablas de seccion 1 completas |
| Metricas cuantificables por componente | Seccion 2 con targets numericos |
| Baselines definidos y medibles | Seccion 3 con plan de medicion |
| Riesgos de fairness documentados | Seccion 4 con mitigaciones |
| SLAs por operacion y flujo | Seccion 5 con P50/P95/P99/timeout |
| Adrian aprueba | Firma en este documento |

---

**Estado:** Pendiente aprobacion Adrian.
