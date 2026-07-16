"""Store en memoria de sesiones de procesamiento.

Cada sesion guarda los bytes originales del archivo subido y el nombre de la
hoja detectada (necesarios en Fase 3 para reabrir el template real e inyectar
los datos editados de vuelta) junto con los productos parseados/validados.
Alcanza para el volumen esperado (~1500 filas); si hace falta persistencia
entre reinicios del proceso, se puede migrar a disco o Redis mas adelante sin
cambiar la interfaz de estas funciones.

Las sesiones expiran solas despues de SESSION_TTL_SECONDS: sin esto, cada
upload queda en memoria para siempre y en un proceso de larga duracion es una
fuga de memoria lenta. La limpieza se hace de forma perezosa (al crear una
sesion nueva), sin necesidad de un hilo de fondo aparte.
"""
import time
import uuid
from typing import Optional

SESSION_TTL_SECONDS = 2 * 60 * 60  # 2 horas

_sessions: dict[str, dict] = {}


def _limpiar_expiradas() -> None:
    ahora = time.time()
    vencidas = [sid for sid, s in _sessions.items() if ahora - s["creada_en"] > SESSION_TTL_SECONDS]
    for sid in vencidas:
        del _sessions[sid]


def create_session(filename: str, original_bytes: bytes, sheet_name: str, productos: list[dict]) -> str:
    _limpiar_expiradas()
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "filename": filename,
        "original_bytes": original_bytes,
        "sheet_name": sheet_name,
        "productos": productos,
        "creada_en": time.time(),
    }
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    return _sessions.get(session_id)
