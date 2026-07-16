"""Reglas de parsing y validacion de templates de productos PedidosYa.

Puerto de la logica que antes corria en el navegador (procesador_templates_pedidosya.html),
mas las politicas de catalogo de "Reglas de Negocio y Politicas de Catalogo -
PedidosYa" (SKU, unidades de medida, imagen, longitud de nombre formado).

Notas sobre bugs reales que encontramos y corregimos durante la migracion:

1. El script original tomaba el "nombre" del producto desde la columna A
   (Activo, que siempre vale "SI") en vez de la columna F (Que producto es),
   y nunca leia Contenido/Unidad (I/J) aunque el template ya las trae
   separadas. Se corrigio: el nombre base se toma de F, y Contenido/Unidad
   se usan directo de I/J cuando vienen cargados.
2. Una fila con F lleno pero Precio vacio se trataba como "fila de
   categoria" y se descartaba en silencio. Eso solo tiene sentido para
   templates genericos con filas divisorias — en el template fijo de
   PedidosYa toda fila con F lleno es un producto real.
3. La formula P (Validation INFO) del Excel real exige datos en C, D, F, I
   y J — o sea que, igual que SKU/Precio/Seccion, F/I/J tambien son
   obligatorios para crear un producto nuevo. Antes se completaban solos
   (ej. "1 Unidad") con una advertencia; ahora, para el template fijo, se
   exigen como error igual que el resto de las columnas obligatorias.
"""
import re

UM = {
    "cc": "mL", "ml": "mL", "mL": "mL", "ML": "mL", "cl": "cl",
    "l": "L", "L": "L", "lt": "L", "lts": "L", "litro": "L", "litros": "L",
    "kg": "kg", "KG": "kg", "g": "g", "G": "g", "gr": "g", "grs": "g", "mg": "mg",
    "oz": "oz", "lb": "lb",
    "un": "Unidad", "unid": "Unidad", "unidad": "Unidad", "unidades": "Unidades",
    "pack": "Paquetes", "packs": "Paquetes",
    "cm2": "cm2", "cm3": "cm3",
}

MARCAS = [
    "Coca Cola", "Coca-Cola", "Pepsi", "Nestle", "Unilever",
    "Dove", "Rexona", "Axe", "Lux", "Clear", "Pantene", "Herbal Essences", "Johnsons",
    "Colgate", "Oral-B", "Gillette", "Nivea", "Lays", "Pringles", "Doritos", "Cheetos",
    "Ruffles", "Maggi", "Knorr", "Hellmanns", "Quaker", "Kelloggs", "Nescafe", "Lipton",
    "Milo", "Tang", "Zuko", "Escudo", "Cristal", "Brahma", "Heineken", "Corona", "Stella",
    "Budweiser", "Johnnie Walker", "Buchanans", "Chivas", "Ballantine", "Jack Daniel",
    "Absolut", "Smirnoff", "Bacardi", "Havana", "Carozzi", "Watts", "Soprole", "Colun",
    "Loncoleche", "Costa", "McKay", "Oreo", "Trident", "Halls", "Tic Tac",
    "Bon Yurt", "Yogu Yogu", "Danonino", "Activia", "Actimel",
]

PRESENTACIONES = [
    "Lata", "Botella", "Tarro", "Caja", "Pack", "Sobre", "Sachet", "Bolsa",
    "Paquete", "Frasco", "Tubo", "Doypack", "Pouch", "Brik", "Brick", "Tetra",
]

SABORES = [
    "Frutilla", "Fresa", "Menta", "Chocolate", "Vainilla", "Limon", "Lima", "Naranja",
    "Manzana", "Durazno", "Pera", "Uva", "Maracuya", "Mora", "Frambuesa", "Coco",
    "Almendra", "Avellana", "Caramelo", "Natural", "Original", "Light", "Zero",
    "Sin Azucar", "Tinto", "Blanco", "Rose", "Picante", "Suave", "Clasico",
]

_CONTENIDO_UNIDAD_RE = re.compile(
    r"(\d+[.,]?\d*)\s*(cc|ml|mL|cl|L|lt\.?|lts\.?|litros?|kg|g(?!al)|gr\.?|grs\.?|mg|oz|lb|un\.?|unid\.?|unidades?|packs?|cm2|cm3)\s*\.?",
    re.IGNORECASE,
)

# ═══ Politica de unidades de medida ══════════════════════════════
# Unidades validas segun las politicas de catalogo (casing exacto pedido).
UNIDADES_VALIDAS = [
    "m", "cm", "L", "cl", "mL", "gal", "cm2", "cm3", "kg", "g", "mg", "oz", "lb",
    "Unidad", "Unidades", "Sachets", "Piezas", "Bolsas", "Cajas", "Paquetes",
    "Sobres", "Cápsulas", "Tabletas", "Comprimidos", "Hojas",
]

# Abreviaciones/alternativas invalidas -> forma valida (case-insensitive).
_ALIAS_UNIDAD = {
    "lt": "L", "l.": "L", "litro": "L", "litros": "L",
    "ml": "mL", "cc": "mL",
    "gr": "g", "grs": "g", "g.": "g",
    "un": "Unidad", "unid": "Unidad", "unidad": "Unidad", "unidades": "Unidades",
    "pack": "Paquetes", "packs": "Paquetes", "paquete": "Paquetes",
    "sachet": "Sachets", "pieza": "Piezas", "bolsa": "Bolsas", "sobre": "Sobres",
    "hoja": "Hojas", "capsula": "Cápsulas", "cápsula": "Cápsulas",
    "tableta": "Tabletas", "comprimido": "Comprimidos",
}

# Palabras de envase (no son una unidad real): se mapean a Unidad/Unidades
# segun si estan en singular o plural, y siempre generan advertencia para
# que el KAM lo revise a mano.
_ENVASES_GENERICOS = {
    "botella": False, "botellas": True,
    "bidon": False, "bidón": False, "bidones": True,
    "taza": False, "tazas": True,
    "lata": False, "latas": True,
}

_UNIDADES_PROHIBIDAS = {
    "porcion", "porción", "porciones", "racion", "ración", "raciones",
    "plancha", "planchas", "servicio", "servicios", "rebanada", "rebanadas",
    "barra", "barras", "bandeja", "bandejas", "rollo", "rollos", "atado", "atados",
    "mitad", "mitades", "docena", "docenas", "cajetilla", "cajetillas",
    "orden", "órden", "ordenes", "órdenes",
}


def normalizar_unidad(unidad_raw, contenido):
    """Normaliza una unidad de medida segun la politica de catalogo.

    Devuelve (unidad_normalizada, advertencia_o_None). Cuando la unidad
    resuelta es de tipo "conteo" (Unidad/Unidades), el singular/plural se
    decide siempre por el valor real de `contenido` — no por la palabra que
    escribio el partner — para que "Botella" con contenido=6 termine en
    "Unidades", no en "Unidad".
    """
    if not unidad_raw:
        return unidad_raw, None

    u = str(unidad_raw).strip()
    u_low = u.lower().rstrip(".")
    advertencia = None
    resultado = None

    for valida in UNIDADES_VALIDAS:
        if valida.lower() == u_low:
            resultado = valida
            break

    if resultado is None and u_low in _ALIAS_UNIDAD:
        resultado = _ALIAS_UNIDAD[u_low]

    if resultado is None and u_low in _ENVASES_GENERICOS:
        es_plural = _ENVASES_GENERICOS[u_low]
        resultado = "Unidades" if es_plural else "Unidad"
        advertencia = f"Unidad '{u}' se interpretó como '{resultado}' — revisar manualmente"

    if resultado is None and u_low in _UNIDADES_PROHIBIDAS:
        es_plural = u_low.endswith("s")
        resultado = "Unidades" if es_plural else "Unidad"
        advertencia = f"Unidad '{u}' no está permitida, se usó '{resultado}' — revisar manualmente"

    if resultado is None:
        es_plural = u_low.endswith("s")
        resultado = "Unidades" if es_plural else "Unidad"
        advertencia = f"Unidad '{u}' no reconocida, se usó '{resultado}' — revisar manualmente"

    if resultado in ("Unidad", "Unidades") and contenido is not None:
        try:
            es_uno = float(contenido) == 1
        except (TypeError, ValueError):
            es_uno = False
        resultado = "Unidad" if es_uno else "Unidades"

    return resultado, advertencia


# ═══ Politica de imagen ══════════════════════════════════════════
_IMG_RE = re.compile(r"^https?://.+\.(jpg|jpeg|png)$", re.IGNORECASE)


def validar_imagen(url):
    """Mensaje de error si el link de imagen no cumple la politica, o None si esta OK."""
    u = str(url).strip()
    if "es.imgbb.com" in u.lower():
        return "El link de imagen no puede alojarse en es.imgbb.com"
    if not _IMG_RE.match(u):
        return "Link de imagen inválido (debe empezar con http(s):// y terminar en .jpg/.jpeg/.png)"
    return None


# ═══ Politica de SKU ═════════════════════════════════════════════
_SKU_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def validar_sku_caracteres(sku):
    """Mensaje de error si el SKU tiene caracteres no permitidos, o None si esta OK."""
    if sku and not _SKU_RE.match(sku):
        return "SKU contiene caracteres no permitidos (solo letras, números, - y _)"
    return None


# ═══ Nombre formado (K) — mismo calculo que la formula de Excel ═
def _proper_case(s):
    if not s:
        return ""
    out = []
    prev_es_letra = False
    for ch in str(s):
        if ch.isalpha():
            out.append(ch.lower() if prev_es_letra else ch.upper())
            prev_es_letra = True
        else:
            out.append(ch)
            prev_es_letra = False
    return "".join(out)


def nombre_formado(que_es, marca, variante, cont, uni):
    cont_txt = "" if cont is None else str(cont)
    partes = [_proper_case(que_es), _proper_case(marca), _proper_case(variante), _proper_case(cont_txt), uni or ""]
    return re.sub(r"\s+", " ", " ".join(partes)).strip()


# ═══ Emojis y abreviaciones (calidad de contenido) ══════════════
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
)


def _tiene_emoji(texto):
    return bool(texto and _EMOJI_RE.search(str(texto)))


# Lista de arranque, pensada para extenderse con casos reales que vayan
# apareciendo — no es exhaustiva ni intenta cubrir todas las abreviaciones
# posibles de todos los rubros de producto.
_ABREVIACIONES_CONOCIDAS = {
    "comp": "comprimidos", "caps": "cápsulas",
    "tab": "tabletas", "und": "unidad", "uds": "unidades",
    "pza": "pieza", "pzas": "piezas", "paq": "paquete", "sob": "sobre",
    "bot": "botella",
}


def _detectar_abreviacion(texto):
    if not texto:
        return None
    for palabra in re.findall(r"[A-Za-zÀ-ÿ]+", str(texto)):
        completa = _ABREVIACIONES_CONOCIDAS.get(palabra.lower())
        if completa:
            return f"Posible abreviación '{palabra}' — ¿'{completa}'?"
    return None


def _num(v):
    """Entero si no tiene decimales, float si tiene (misma logica que `% 1 === 0` en JS)."""
    return int(v) if v % 1 == 0 else v


def extraer_contenido_unidad(nombre):
    matches = list(_CONTENIDO_UNIDAD_RE.finditer(nombre))
    if not matches:
        return {"nombre": nombre.strip(), "contenido": None, "unidad": None}
    last = matches[-1]
    cs = last.group(1).replace(",", ".")
    ru = re.sub(r"\.$", "", last.group(2))
    uk = None
    for k, v in UM.items():
        if k.lower() == ru.lower():
            uk = v
            break
    if uk is None:
        return {"nombre": nombre.strip(), "contenido": None, "unidad": None}
    try:
        c = float(cs)
    except ValueError:
        return {"nombre": nombre.strip(), "contenido": None, "unidad": None}
    limpio = (nombre[: last.start()] + nombre[last.end():])
    limpio = re.sub(r"\s+", " ", limpio)
    limpio = re.sub(r"[\s.]+$", "", limpio).strip()
    return {"nombre": limpio, "contenido": _num(c), "unidad": uk}


def _palabra_re(texto):
    return re.compile(r"(^|\s)" + re.escape(texto) + r"(\s|$)", re.IGNORECASE)


def detectar_marca(nombre):
    for marca in MARCAS:
        if _palabra_re(marca).search(nombre):
            return marca
    return None


def remover(nombre, texto):
    re_ = re.compile(r"(^|\s)" + re.escape(texto) + r"(\s|$)", re.IGNORECASE)
    return re.sub(r"\s+", " ", re_.sub(" ", nombre)).strip()


def extraer_variante(nombre):
    for item in PRESENTACIONES + SABORES:
        m = _palabra_re(item).search(nombre)
        if m:
            match = m.group(0).strip()
            return {"variante": match, "nombre": remover(nombre, match)}
    return {"variante": None, "nombre": nombre}


def limpiar_nombre(n):
    n = re.sub(r"^\d+[xX]?\s+", "", n)
    n = re.sub(r"\(\d{4}\)", "", n)
    return re.sub(r"\s+", " ", n).strip()


def limpiar_precio(p):
    if p is None or p == "-" or str(p).strip() == "":
        return None
    s = re.sub(r"[$\s]", "", str(p)).replace(".", "").replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return None
    if v <= 0:
        return None
    return _num(v)


def limpiar_ean(e):
    if not e:
        return None
    s = re.sub(r"[^0-9]", "", str(e))
    return s if 8 <= len(s) <= 14 else None


def limpiar_sku(s):
    if not s:
        return None
    return re.sub(r"\s+", "_", str(s).strip())[:64]


def cantidad_inv(inv):
    if not inv:
        return 1
    m = re.match(r"^(\d+)\s+", str(inv), re.IGNORECASE)
    return int(m.group(1)) if m else 1


def detectar_header(rows):
    for i, row in enumerate(rows[:5]):
        cells = [str(c).upper().strip() if c not in (None, "") else "" for c in row]
        if any(c in ("NOMBRE", "ITEM", "PRODUCTO") or "PRODUCTO" in c for c in cells):
            return i
        if any("ACTIVO" in c or "BARRAS" in c for c in cells):
            return i
    return 0


def map_cols(header_row):
    m = {}
    for i, cell in enumerate(header_row):
        if cell in (None, ""):
            continue
        c = str(cell).upper().strip()
        if c in ("NOMBRE", "ITEM", "PRODUCTO") and "nombre" not in m:
            m["nombre"] = i
        if c in ("PRECIO", "PRICE", "COSTO"):
            m["precio"] = i
        if "DESCRIPCI" in c and "nombre" in m:
            m["desc"] = i
        if "IMAGEN" in c or "IMAGE" in c or "FOTO" in c or "URL" in c:
            m["img"] = i
        if c == "SKU":
            m["sku"] = i
        if ("REF" in c or "CODIGO INT" in c) and "sku" not in m:
            m["sku"] = i
        if "EAN" in c or "GTIN" in c or "BARRA" in c:
            m["ean"] = i
        if "INVENTARIO" in c or "STOCK" in c:
            m["inv"] = i
        if "CATEG" in c or "SECCION" in c or "DEPART" in c:
            m["sec"] = i
        if c in ("MARCA", "BRAND"):
            m["marca"] = i
        if "VARIANTE" in c or "SABOR" in c or "PRESENT" in c:
            m["variante"] = i
    return m


def _cell(row, idx, default=""):
    if idx is None or idx < 0 or idx >= len(row):
        return default
    v = row[idx]
    return default if v is None else v


def detectar_es_template_peya(rows):
    if len(rows) < 2:
        return False
    r2 = rows[1] or []
    c0 = str(_cell(r2, 0, "")).upper()
    c4 = str(_cell(r2, 4, "")).upper()
    return "ACTIVO" in c0 and "SECCION" in c4


def procesar_filas(rows):
    """rows: lista de listas (una por fila de la hoja, 0-indexed, incluye header).

    Devuelve la lista de productos procesados y validados (mismo shape que
    `procData` en el HTML original).
    """
    es_template_peya = detectar_es_template_peya(rows)

    if es_template_peya:
        # Columnas fijas del template PedidosYa v9 (indices 0-based).
        # Header real esta en la fila 2 (indice 1); los datos arrancan en la
        # fila 3 (indice 2).
        hi = 1
        cm = {
            "activo": 0, "nombre": 5, "ean": 1, "sku": 2, "precio": 3, "sec": 4,
            "marca": 6, "variante": 7, "cont_col": 8, "uni_col": 9,
            "img": 11, "desc": 12, "inv": None,
            "impuestos": 13, "ean_fraccionado": 14,
        }
    else:
        hi = detectar_header(rows)
        cm = map_cols(rows[hi] if hi < len(rows) else [])
        cm.setdefault("nombre", 0)
        cm.setdefault("precio", 1)
        cm.setdefault("desc", 2)
        cm.setdefault("inv", 3)
        cm.setdefault("img", 13)
        cm.setdefault("sku", 14)
        cm.setdefault("ean", 15)

    prods = []
    cat = None
    for row in rows[hi + 1:]:
        raw_n = _cell(row, cm.get("nombre"), None)
        raw_p = _cell(row, cm.get("precio"), None)
        if raw_n is None or str(raw_n).strip() == "":
            continue
        if not es_template_peya and (raw_p is None or raw_p == "-" or str(raw_p).strip() == ""):
            # Heuristica de "fila de categoria": solo aplica a templates
            # genericos con filas divisorias. En el template fijo de
            # PedidosYa, F (Que producto es) y D (Precio) son obligatorios
            # para el partner — una fila con F lleno siempre es un producto,
            # y si D viene vacio debe marcarse como error, no descartarse.
            cat = str(raw_n).strip()
            continue
        prods.append({
            "nombre_orig": str(raw_n).strip(),
            "precio": raw_p,
            "desc": str(_cell(row, cm.get("desc"), "")).strip(),
            "inv": _cell(row, cm.get("inv"), ""),
            "img": str(_cell(row, cm.get("img"), "")).strip(),
            "sku_r": _cell(row, cm.get("sku"), ""),
            "ean_r": _cell(row, cm.get("ean"), ""),
            "sec": (str(_cell(row, cm.get("sec"), "")) if "sec" in cm else (cat or "")).strip(),
            "marca_r": str(_cell(row, cm.get("marca"), "")).strip(),
            "var_r": str(_cell(row, cm.get("variante"), "")).strip(),
            "cont_r": _cell(row, cm.get("cont_col"), None) if es_template_peya else None,
            "uni_r": str(_cell(row, cm.get("uni_col"), "")).strip() if es_template_peya else "",
            "impuestos_r": str(_cell(row, cm.get("impuestos"), "")).strip(),
            "ean_frac_r": str(_cell(row, cm.get("ean_fraccionado"), "")).strip(),
            "activo_r": str(_cell(row, cm.get("activo"), "")).strip().upper(),
        })

    res = []
    for p in prods:
        nom = limpiar_nombre(p["nombre_orig"])

        if es_template_peya:
            # El template ya trae el nombre base separado en la columna F.
            nom = p["nombre_orig"].strip()
        else:
            ex = extraer_contenido_unidad(nom)
            nom = ex["nombre"]

        cont = uni = None
        uni_def = False
        if p["cont_r"] not in (None, "") and p["uni_r"]:
            try:
                cv = float(str(p["cont_r"]).replace(",", "."))
                cont = _num(cv)
            except (ValueError, TypeError):
                cont = None
            uni = p["uni_r"]
        elif not es_template_peya:
            ex2 = extraer_contenido_unidad(p["nombre_orig"])
            cont, uni = ex2["contenido"], ex2["unidad"]

        if cont is None and not es_template_peya:
            # Solo se autocompleta en modo generico. En el template fijo,
            # Contenido/Unidad son obligatorios (ver mas abajo) y no se
            # inventa un valor por defecto.
            q = cantidad_inv(p["inv"])
            cont = q
            uni = "Unidad" if q == 1 else "Unidades"
            uni_def = True

        unidad_warn = None
        if uni:
            uni, unidad_warn = normalizar_unidad(uni, cont)

        marca = p["marca_r"] or ""
        if not marca:
            md = detectar_marca(nom)
            if md:
                marca = md
                nom = remover(nom, md)

        variante = p["var_r"] or ""
        if not variante:
            vx = extraer_variante(nom)
            variante = vx["variante"] or ""
            nom = vx["nombre"]

        precio = limpiar_precio(p["precio"])
        ean = limpiar_ean(p["ean_r"])
        sku = limpiar_sku(p["sku_r"]) or ean or ""
        desc = p["desc"] or ""
        img = p["img"] or ""
        nom = nom.strip()

        errs, warns = [], []
        if not sku:
            errs.append("SKU vacío")
        else:
            sku_err = validar_sku_caracteres(sku)
            if sku_err:
                errs.append(sku_err)
        if not precio:
            errs.append("Precio vacío o inválido")
        if not p["sec"]:
            errs.append("Sección vacía")

        if es_template_peya:
            # F, I, J y L son obligatorios para crear un producto nuevo,
            # igual que exige la formula real de Validation INFO (P).
            if not nom:
                errs.append("Que producto es vacío")
            if cont is None or not uni:
                errs.append("Contenido/Unidad vacíos")
            if not img:
                errs.append("Imagen vacía — el partner debe enviar el link")
            else:
                img_err = validar_imagen(img)
                if img_err:
                    errs.append(img_err)
        else:
            if uni_def:
                warns.append(f"Unidad por defecto ({uni})")
            if not img:
                warns.append("Sin imagen")
            if not nom:
                warns.append("Nombre quedó vacío")

        if unidad_warn:
            warns.append(unidad_warn)

        if len(desc) > 250:
            warns.append(f"Descripción {len(desc)} car. (máx 250)")

        nf = nombre_formado(nom, marca, variante, cont, uni)
        if len(nf) > 64:
            warns.append(f"Nombre formado {len(nf)} car. (máx 64)")

        for valor in (nom, marca, variante):
            if _tiene_emoji(valor):
                warns.append("El nombre/marca/variante contiene emojis")
                break
        for valor in (nom, marca, variante):
            abrev = _detectar_abreviacion(valor)
            if abrev:
                warns.append(abrev)
                break

        estado = "err" if errs else ("warn" if warns else "ok")
        res.append({
            "activo": p["activo_r"] or "SI", "ean": ean, "sku": sku, "precio": precio,
            "sec": p["sec"], "que_es": nom, "marca": marca, "variante": variante,
            "cont": cont, "uni": uni, "img": img, "desc": desc,
            "impuestos": p["impuestos_r"], "ean_fraccionado": p["ean_frac_r"],
            "orig": p["nombre_orig"],
            "estado": estado, "errs": errs, "warns": warns,
        })

    return res
