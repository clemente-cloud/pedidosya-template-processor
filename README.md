# Template Processor — PedidosYa Content

Procesador de templates de productos para KAMs de PedidosYa. Arquitectura
cliente-servidor: el backend (Python/FastAPI) parsea y valida el `.xlsx` que
sube el partner; el frontend (HTML/CSS/JS plano) muestra los resultados y
permite editarlos antes de descargar.

## Cómo correr en desarrollo

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir .
```

Abrir http://127.0.0.1:8000 — el mismo proceso sirve el frontend (`frontend/`)
y expone la API bajo `/api/*`.

### Tests

```
cd backend
pip install -r requirements-dev.txt
pytest
```

## Estado actual (Fases 1-3 completas)

- `POST /api/upload`: recibe el `.xlsx`, detecta si es el template fijo de
  PedidosYa o uno genérico, extrae y valida los productos, y guarda el
  archivo original en memoria bajo un `session_id`.
- La tabla de resultados es un espejo 1:1 de las columnas A-P del template
  real (colores de header, celdas editables, K y P como fórmulas de solo
  lectura calculadas en vivo), con Estado/Alertas fijas a la derecha.
- `POST /api/download/{session_id}`: recibe los productos editados, abre con
  openpyxl el archivo original tal cual lo subió el usuario, sobreescribe
  solo las celdas de datos desde la fila 3 (nunca toca K/P, estilos, colores,
  anchos de columna ni la hoja de instrucciones), y devuelve el `.xlsx` listo
  para descargar. El frontend ya no genera nada con SheetJS — todo el
  procesamiento pesado vive en el backend.

## Despliegue en producción (Render)

La app corre en un solo proceso Uvicorn con **un solo worker a propósito**:
`session_store.py` guarda las sesiones en memoria, así que con más de un
worker una subida y su descarga podrían caer en procesos distintos y la
sesión no se encontraría. Para el volumen de un equipo de KAMs esto alcanza
sin problema; si en algún momento hace falta escalar a más de una instancia,
hay que migrar `session_store.py` a algo compartido (Redis, disco, etc.)
antes de sacar el `--workers 1`.

Pasos (usando [Render](https://render.com), pero cualquier PaaS similar
—Railway, Fly.io— sirve con ajustes menores):

1. Crear un repo en GitHub y subir este proyecto (`git remote add origin ...`,
   `git push -u origin main`).
2. En Render: **New > Blueprint**, conectar el repo — Render va a leer
   `render.yaml` (en la raíz) y configurar todo solo: build, start command,
   y el plan **Starter** (no el free tier, que se duerme por inactividad y
   mataría las sesiones en memoria a mitad de uso).
3. Esperar el primer deploy y abrir la URL que asigna Render.

No hace falta configurar variables de entorno ni secretos — la app no usa
ninguno todavía.

## Pendiente / ideas de mejora (no implementadas)

- Sesiones en memoria: se pierden al reiniciar el proceso o al escalar a más
  de un worker/instancia. Ver nota de despliegue arriba.
- Sin autenticación: por decisión explícita, de momento cualquiera con el
  link puede subir/descargar. Si el link circula más allá del equipo de
  KAMs, conviene agregar login (usuario/clave compartido es la opción más
  simple para empezar).
- La lista de abreviaciones conocidas (`_ABREVIACIONES_CONOCIDAS` en
  `rules.py`) es un punto de partida chico, pensado para ampliarse con casos
  reales que reporten los KAMs.
