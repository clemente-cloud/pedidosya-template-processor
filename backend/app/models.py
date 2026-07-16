from typing import List, Optional
from pydantic import BaseModel


class Producto(BaseModel):
    activo: str
    ean: Optional[str] = None
    sku: str
    precio: Optional[float] = None
    sec: str
    que_es: str
    marca: str
    variante: str
    cont: Optional[float] = None
    uni: Optional[str] = None
    img: str
    desc: str
    impuestos: str = ""
    ean_fraccionado: str = ""
    orig: str
    estado: str
    errs: List[str]
    warns: List[str]


class Stats(BaseModel):
    total: int
    ok: int
    warn: int
    err: int
    desc_larga: int
    sin_barcode: int = 0
    sin_imagen: int = 0


class UploadResponse(BaseModel):
    session_id: str
    filename: str
    productos: List[Producto]
    stats: Stats


class DownloadRequest(BaseModel):
    productos: List[Producto]
