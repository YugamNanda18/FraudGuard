# FraudAI Agent -- Operations Runbook

**Proyecto:** FraudAI Agent (Harvey AI)
**Version:** 0.1.0
**Fecha:** 2026-04-06
**Autor:** ARCA (@docs-writer) / Adrian Infantes
**Fase:** F6 -- Deployment

---

## 1. Service Health Checks

### 1.1 Endpoints de salud

| Servicio | Endpoint | Metodo | Respuesta sana |
|---|---|---|---|
| **FraudAI App** | `http://localhost:8000/api/v1/health` | GET | `{"status": "healthy", ...}` |
| **Qdrant** | `http://localhost:6333/healthz` | GET | HTTP 200 (sin cuerpo) |
| **Ollama** | `http://localhost:11434/api/tags` | GET | HTTP 200 + JSON con modelos |
| **Claude API** | Verificado internamente por `/health` | -- | Campo `claude_api: true` |

### 1.2 Script de verificacion rapida

```bash
#!/usr/bin/env bash
echo "=== FraudAI Health Check ==="

# App
APP=$(curl -sf http://localhost:8000/api/v1/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "[OK] App: $(echo $APP | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')"
else
    echo "[FAIL] App: no responde"
fi

# Qdrant
if curl -sf http://localhost:6333/healthz > /dev/null 2>&1; then
    echo "[OK] Qdrant: healthy"
else
    echo "[FAIL] Qdrant: no responde"
fi

# Ollama
if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "[OK] Ollama: healthy"
else
    echo "[FAIL] Ollama: no responde"
fi

# GPU
if nvidia-smi > /dev/null 2>&1; then
    VRAM_USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    VRAM_TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits)
    echo "[OK] GPU: ${VRAM_USED}/${VRAM_TOTAL} MiB VRAM"
else
    echo "[WARN] GPU: nvidia-smi no disponible"
fi
```

---

## 2. Problemas comunes y solucion

### 2.1 Qdrant no arranca

**Sintomas:**
- `curl http://localhost:6333/healthz` devuelve error de conexion
- Health check de la app muestra `"qdrant": false`
- Logs: `Connection refused` al intentar operaciones RAG

**Causas probables y solucion:**

| Causa | Diagnostico | Solucion |
|---|---|---|
| Container no esta corriendo | `docker compose ps` -- qdrant no aparece o esta en estado "exited" | `docker compose up -d qdrant` |
| Puerto ocupado | `ss -tlnp \| grep 6333` muestra otro proceso | Parar el proceso que ocupa el puerto, o cambiar `QDRANT_PORT` en `.env` y `docker-compose.yml` |
| Volumen corrupto | `docker compose logs qdrant` muestra errores de storage | 1. `docker compose down` 2. `docker volume rm fraudai-agent_qdrant_data` 3. `docker compose up -d qdrant` (**DESTRUCTIVO: pierde datos indexados**) |
| Sin memoria suficiente | `docker compose logs qdrant` muestra OOM | Aumentar `mem_limit` en `docker-compose.yml` (default: 2GB). Verificar RAM disponible con `free -h` |

**Procedimiento paso a paso:**

```bash
# 1. Verificar estado del container
docker compose ps qdrant

# 2. Ver logs recientes
docker compose logs qdrant --tail 50

# 3. Si esta caido, intentar reiniciar
docker compose restart qdrant

# 4. Esperar a que pase health check (max 60s)
for i in $(seq 1 30); do
    if curl -sf http://localhost:6333/healthz > /dev/null 2>&1; then
        echo "Qdrant OK"; break
    fi
    sleep 2
done

# 5. Si no responde, verificar logs para causa raiz
docker compose logs qdrant --tail 100
```

---

### 2.2 Ollama OOM (Out of Memory -- VRAM)

**Sintomas:**
- Ollama no responde o responde con errores
- `nvidia-smi` muestra VRAM al 100%
- Health check: `"ollama": false`
- Logs de Ollama: `CUDA out of memory`, `OOM`, o `insufficient memory`

**Causa:**
La RTX 2000 Ada tiene 8 GB de VRAM. El modelo Llama 3.1 8B Q4_K_M consume ~5 GB. Si otros procesos (embeddings, reranker, o aplicaciones externas) consumen VRAM simultaneamente, Ollama no tiene espacio.

**Solucion:**

```bash
# 1. Verificar consumo de VRAM
nvidia-smi

# 2. Identificar procesos GPU
nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv

# 3. Liberar VRAM de otros procesos si los hay
# (Cerrar Jupyter notebooks, otros modelos, etc.)

# 4. Descargar modelo de Ollama manualmente (libera VRAM)
curl -X DELETE http://localhost:11434/api/generate

# 5. Reiniciar Ollama
docker compose restart ollama

# 6. Verificar que el modelo se carga correctamente
curl -s http://localhost:11434/api/tags | python -m json.tool
```

**Prevencion:**
- Configurar `OLLAMA_KEEP_ALIVE=5m` para que Ollama descargue el modelo tras 5 min de inactividad
- No correr notebooks de Jupyter con GPU mientras la app esta activa
- Monitorizar VRAM con `watch -n 5 nvidia-smi`

---

### 2.3 Claude API rate limited

**Sintomas:**
- Respuestas de agentes (Harvey, Louis, Jessica, Mike, Rachel) fallan
- Logs de la app: `429 Too Many Requests` o `RateLimitError`
- Health check: `"claude_api": true` (API alcanzable pero rate limited)

**Causa:**
Anthropic aplica rate limits por tier de API key. Con uso intensivo (multiples sesiones concurrentes), se puede alcanzar el limite de requests por minuto o tokens por minuto.

**Solucion:**

```bash
# 1. Verificar el estado de la API
curl -s https://status.anthropic.com/api/v2/status.json | python -m json.tool

# 2. Ver logs de la app para errores especificos
docker logs fraudai-app --tail 100 | grep -i "rate\|429\|limit"

# 3. Esperar -- los rate limits se resetean automaticamente
# Anthropic tipicamente resetea cada 60 segundos

# 4. Si es recurrente, implementar mitigaciones:
#    - Reducir concurrencia de sesiones
#    - Activar cache de respuestas RAG (previsto en F4)
#    - Solicitar aumento de rate limit a Anthropic
```

**Estrategia de fallback (ADR-001):**
- Retry exponencial: 3 reintentos con backoff 2s/4s/8s
- Si la API esta completamente caida, los agentes Claude NO degradan a modelo local (calidad insuficiente)
- Donna (modelo local) sigue funcionando independientemente

---

### 2.4 Sandbox container no se limpia

**Sintomas:**
- `docker ps` muestra containers con prefijo sandbox que llevan mas de 10 min corriendo
- Disco llenandose con containers parados
- RAM consumida por containers zombies

**Causa:**
Los containers de sandbox (usados por Harvey, Mike, Rachel para ejecutar codigo) deberian eliminarse automaticamente (`auto_remove: True` en la configuracion). Si el proceso muere abruptamente o el timeout no se aplica correctamente, pueden quedar huerfanos.

**Solucion:**

```bash
# 1. Listar containers sandbox activos
docker ps --filter "name=fraudai-sandbox" --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.RunningFor}}"

# 2. Eliminar containers sandbox viejos (mas de 15 min)
docker ps -q --filter "name=fraudai-sandbox" --filter "status=running" | while read cid; do
    CREATED=$(docker inspect --format '{{.State.StartedAt}}' "$cid")
    echo "Container $cid started at $CREATED"
done

# 3. Forzar eliminacion de todos los containers sandbox
docker ps -aq --filter "name=fraudai-sandbox" | xargs -r docker rm -f

# 4. Limpiar containers parados y imagenes dangling
docker system prune -f
```

**Prevencion:**
- La configuracion de sandbox incluye `pids_limit: 256` y timeout de 10 min
- Configurar un cron job de limpieza:

```bash
# Anadir a crontab (cada hora)
0 * * * * docker ps -aq --filter "name=fraudai-sandbox" --filter "status=exited" | xargs -r docker rm -f
```

---

### 2.5 BOE ingestion falla

**Sintomas:**
- El corpus RAG esta desactualizado (campo `corpus_version` en health check no cambia)
- Errores en logs del pipeline de ingestion
- Louis cita normativa con fecha antigua

**Causas probables:**

| Causa | Diagnostico | Solucion |
|---|---|---|
| API BOE no disponible | `curl -s "https://www.boe.es/datosabiertos/api/legislacion-consolidada" \| head` devuelve error | Esperar y reintentar. La API BOE no tiene SLA oficial |
| Error de parsing | Logs de ingestion muestran excepciones de parsing XML/JSON | Revisar si el formato de respuesta del BOE ha cambiado. Actualizar parsers |
| Qdrant lleno | Qdrant rechaza upserts por falta de espacio | Aumentar `mem_limit` de Qdrant o limpiar colecciones obsoletas |
| Embeddings fallan | Error de VRAM al generar embeddings con BGE-M3 | Verificar que Ollama no esta usando la GPU simultaneamente. Esperar a que `OLLAMA_KEEP_ALIVE` descargue el modelo |

**Procedimiento de re-ingestion:**

```bash
# 1. Verificar conectividad con API BOE
curl -s "https://www.boe.es/datosabiertos/api/legislacion-consolidada?texto=blanqueo&limit=1" | python -m json.tool

# 2. Verificar estado de Qdrant
curl -s http://localhost:6333/collections | python -m json.tool

# 3. Verificar VRAM disponible (BGE-M3 necesita ~2GB)
nvidia-smi

# 4. Re-ejecutar ingestion (cuando el modulo este disponible)
python -m fraudai.ingestion --mode full --force

# 5. Verificar que el corpus se actualizo
curl -s http://localhost:8000/api/v1/health | python -m json.tool
# corpus_version deberia reflejar la nueva version
```

---

### 2.6 La aplicacion no arranca

**Sintomas:**
- `uvicorn` falla al importar modulos
- Error de conexion a Qdrant o Ollama al arrancar

**Solucion:**

```bash
# 1. Verificar que las dependencias estan instaladas
uv sync

# 2. Verificar que .env existe y tiene valores correctos
cat .env

# 3. Verificar que Qdrant y Ollama estan corriendo
docker compose ps

# 4. Si Qdrant no esta disponible al arrancar, la app sigue en modo degradado
# (ver logs: "QdrantStore initialization failed -- continuing in degraded mode")

# 5. Verificar el puerto 8000 no esta ocupado
ss -tlnp | grep 8000

# 6. Arrancar con logs verbose para diagnostico
LOG_LEVEL=DEBUG uv run uvicorn fraudai.api.app:create_app --factory --reload
```

---

## 3. Rollback Procedure

### 3.1 Rollback de la aplicacion

```bash
# 1. Identificar la version anterior
git log --oneline -10

# 2. Parar la aplicacion actual
docker stop fraudai-app  # Si corre en Docker
# O Ctrl+C si esta en foreground

# 3. Checkout de la version anterior
git checkout <commit-hash>

# 4. Reconstruir (si usa Docker)
docker build -t fraudai-agent:rollback .

# 5. Arrancar con la imagen anterior
docker run -d --name fraudai-app \
  --network fraudai-agent_default \
  -p 8000:8000 --env-file .env \
  fraudai-agent:rollback

# 6. Verificar
curl http://localhost:8000/api/v1/health
```

### 3.2 Rollback del corpus RAG

```bash
# Si la ingestion corrompio el corpus de Qdrant:

# 1. Parar la aplicacion
docker stop fraudai-app

# 2. Eliminar la coleccion corrupta
curl -X DELETE http://localhost:6333/collections/boe_legislation

# 3. Re-ejecutar ingestion desde cero (cuando este disponible)
python -m fraudai.ingestion --mode full

# 4. Verificar
curl -s http://localhost:6333/collections/boe_legislation | python -m json.tool

# 5. Reiniciar la aplicacion
docker start fraudai-app
```

### 3.3 Rollback de Qdrant (restaurar backup)

```bash
# 1. Parar Qdrant
docker compose stop qdrant

# 2. Si tienes un snapshot previo de Qdrant:
# Los snapshots se crean via API:
# curl -X POST http://localhost:6333/collections/boe_legislation/snapshots

# 3. Restaurar snapshot
# curl -X PUT http://localhost:6333/collections/boe_legislation/snapshots/recover \
#   -H "Content-Type: application/json" \
#   -d '{"location": "/qdrant/storage/snapshots/boe_legislation/<snapshot-name>.snapshot"}'

# 4. Reiniciar Qdrant
docker compose start qdrant
```

---

## 4. Backup y Recovery

### 4.1 Datos persistentes

| Dato | Almacenamiento | Backup necesario | Estrategia |
|---|---|---|---|
| **Corpus BOE (Qdrant)** | Volume `qdrant_data` | SI | Snapshots de Qdrant + re-ingestion como fallback |
| **Modelos Ollama** | Volume `ollama_data` | NO (re-descargable) | `ollama pull` re-descarga el modelo |
| **Sesiones de usuario** | In-memory (MemorySaver) | NO (efimeras) | Se pierden al reiniciar. Aceptable para MVP |
| **Feedback** | In-memory (lista) | NO (efimero) | Se pierde al reiniciar. Persistencia en F7 |
| **Archivos subidos** | `/tmp/fraudai_uploads/` | NO (efimeros) | Se eliminan con la sesion |
| **Configuracion** | `.env` + `docker-compose.yml` | SI | Control de versiones (git). No commitear `.env` |

### 4.2 Crear snapshot de Qdrant

```bash
# Crear snapshot de la coleccion BOE
curl -X POST http://localhost:6333/collections/boe_legislation/snapshots

# Listar snapshots disponibles
curl -s http://localhost:6333/collections/boe_legislation/snapshots | python -m json.tool

# Descargar snapshot a disco local
curl -o boe_backup.snapshot \
  http://localhost:6333/collections/boe_legislation/snapshots/<snapshot-name>
```

### 4.3 Backup del volumen Docker (alternativa)

```bash
# Backup del volumen completo de Qdrant
docker run --rm -v fraudai-agent_qdrant_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/qdrant_backup_$(date +%Y%m%d).tar.gz /data

# Restaurar
docker compose stop qdrant
docker run --rm -v fraudai-agent_qdrant_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/qdrant_backup_YYYYMMDD.tar.gz -C /
docker compose start qdrant
```

---

## 5. Scaling

### 5.1 Estado actual (MVP)

- **Instancia unica** de cada servicio
- **In-memory** session management y feedback
- **Vertical scaling** (mas RAM/CPU) como primera opcion
- Target: 100 sesiones concurrentes (SR-011)

### 5.2 Futuro (post-MVP)

| Componente | Estrategia de escalado |
|---|---|
| **FraudAI App** | Horizontal: multiples instancias detras de load balancer (nginx/traefik). Requiere migrar sesiones a PostgresSaver |
| **Qdrant** | Cluster mode: sharding + replication nativo |
| **Ollama** | Vertical: GPU mas potente o multiples GPUs. No escala horizontal facilmente |
| **Sandbox containers** | Horizontal: Kubernetes para orquestacion de containers efimeros |

### 5.3 Metricas para decidir escalado

| Metrica | Umbral de alerta | Accion |
|---|---|---|
| Latencia P95 de respuesta | > 10s | Investigar bottleneck (LLM? RAG? Sandbox?) |
| Sesiones concurrentes | > 80 | Planificar horizontal scaling de la app |
| VRAM usage | > 90% sostenido | Evaluar GPU upgrade o offloading de modelos |
| RAM del host | > 80% | Aumentar RAM o reducir limites de containers |
| Disco de Qdrant | > 80% del volumen | Limpiar colecciones de sesiones expiradas |

---

## 6. Mantenimiento periodico

### 6.1 Semanal

| Tarea | Comando / Accion |
|---|---|
| Verificar health de todos los servicios | Script de verificacion (seccion 1.2) |
| Ejecutar ingestion incremental del BOE | `python -m fraudai.ingestion --mode incremental` (cuando disponible) |
| Revisar consumo de disco | `docker system df` |
| Limpiar containers sandbox huerfanos | `docker ps -aq --filter "name=fraudai-sandbox" --filter "status=exited" \| xargs -r docker rm -f` |

### 6.2 Mensual

| Tarea | Comando / Accion |
|---|---|
| Crear snapshot de Qdrant | `curl -X POST http://localhost:6333/collections/boe_legislation/snapshots` |
| Actualizar imagenes Docker | `docker compose pull && docker compose up -d` |
| Revisar logs de errores | `docker logs fraudai-app --since 720h \| grep ERROR \| wc -l` |
| Limpiar imagenes Docker no usadas | `docker image prune -a --filter "until=720h"` |
| Verificar uso de tokens Anthropic | Revisar dashboard en https://console.anthropic.com/usage |

---

## 7. Contactos y escalacion

| Nivel | Contacto | Cuando escalar |
|---|---|---|
| L1: Operaciones | Runbook (este documento) | Problema conocido, solucion documentada |
| L2: Desarrollo | Adrian Infantes | Problema no documentado, requiere cambio de codigo |
| L3: Infraestructura | Adrian Infantes | Problema de infraestructura (Docker, GPU, red) |
| Externo: Anthropic | https://support.anthropic.com | API caida o rate limits que impiden operacion normal |
| Externo: BOE | No hay soporte (API publica sin SLA) | Monitorizar y esperar |
