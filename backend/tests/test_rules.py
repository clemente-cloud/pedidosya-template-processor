"""Tests para app/rules.py.

Ademas de cubrir los helpers de parsing, varios tests fijan explicitamente
el comportamiento de bugs reales que encontramos leyendo el script original
y corregimos durante la migracion, y las politicas de catalogo de "Reglas
de Negocio y Politicas de Catalogo - PedidosYa":

1. El nombre de un producto (en modo template fijo) debe salir de la
   columna F (Que producto es), no de la columna A (Activo).
2. Contenido/Unidad deben usarse directo de las columnas I/J cuando el
   template ya las trae cargadas, sin re-derivarlas del nombre.
3. Una fila con F lleno pero Precio vacio es un producto con error, no una
   fila de categoria que se descarta en silencio (eso solo aplica a
   templates genericos con filas divisorias).
4. F (Que producto es), Contenido, Unidad e Imagen son obligatorios para
   crear un producto nuevo — igual que exige la formula real de Validation
   INFO (P) del Excel — y Codigo de Barras (B) es opcional.
"""
from app import rules


# ═══ Helpers de limpieza/parsing ════════════════════════════════

class TestLimpiarPrecio:
    def test_valor_numerico_simple(self):
        assert rules.limpiar_precio(1990) == 1990

    def test_con_signo_pesos_y_puntos_de_miles(self):
        assert rules.limpiar_precio("$1.990") == 1990

    def test_con_coma_decimal(self):
        assert rules.limpiar_precio("1990,50") == 1990.5

    def test_guion_es_invalido(self):
        assert rules.limpiar_precio("-") is None

    def test_vacio_es_invalido(self):
        assert rules.limpiar_precio("") is None
        assert rules.limpiar_precio(None) is None

    def test_cero_o_negativo_es_invalido(self):
        assert rules.limpiar_precio(0) is None
        assert rules.limpiar_precio(-5) is None


class TestLimpiarEan:
    def test_ean_valido(self):
        assert rules.limpiar_ean("7801234567890") == "7801234567890"

    def test_quita_caracteres_no_numericos(self):
        assert rules.limpiar_ean("780-123-4567890") == "7801234567890"

    def test_muy_corto_es_invalido(self):
        assert rules.limpiar_ean("1234") is None

    def test_muy_largo_es_invalido(self):
        assert rules.limpiar_ean("1234567890123456789") is None

    def test_vacio(self):
        assert rules.limpiar_ean("") is None
        assert rules.limpiar_ean(None) is None


class TestLimpiarSku:
    def test_espacios_se_reemplazan_por_guion_bajo(self):
        assert rules.limpiar_sku("SKU 001") == "SKU_001"

    def test_trunca_a_64_caracteres(self):
        assert len(rules.limpiar_sku("A" * 100)) == 64

    def test_vacio_devuelve_none(self):
        assert rules.limpiar_sku("") is None
        assert rules.limpiar_sku(None) is None


class TestExtraerContenidoUnidad:
    def test_extrae_contenido_y_unidad(self):
        r = rules.extraer_contenido_unidad("Bebida Cola 350 ml")
        assert r["contenido"] == 350
        assert r["unidad"] == "mL"
        assert r["nombre"] == "Bebida Cola"

    def test_sin_unidad_reconocible(self):
        r = rules.extraer_contenido_unidad("Producto Generico")
        assert r["contenido"] is None
        assert r["unidad"] is None

    def test_usa_la_ultima_coincidencia(self):
        r = rules.extraer_contenido_unidad("Pack 6 un 350 ml")
        assert r["contenido"] == 350
        assert r["unidad"] == "mL"


class TestDetectarMarca:
    def test_detecta_marca_conocida(self):
        assert rules.detectar_marca("Bebida Coca-Cola") == "Coca-Cola"

    def test_no_detecta_marca_desconocida(self):
        assert rules.detectar_marca("Producto Sin Marca Registrada") is None


class TestCantidadInv:
    def test_extrae_cantidad_inicial(self):
        assert rules.cantidad_inv("6 unidades por caja") == 6

    def test_default_es_1(self):
        assert rules.cantidad_inv("") == 1
        assert rules.cantidad_inv(None) == 1
        assert rules.cantidad_inv("sin numero") == 1


class TestNormalizarUnidad:
    def test_unidad_valida_pasa_directo(self):
        assert rules.normalizar_unidad("g", 500) == ("g", None)
        assert rules.normalizar_unidad("kg", 2) == ("kg", None)

    def test_cm2_cm3_son_texto_plano_no_superindice(self):
        assert rules.normalizar_unidad("cm2", 10) == ("cm2", None)
        assert rules.normalizar_unidad("cm3", 10) == ("cm3", None)

    def test_alias_invalido_se_convierte(self):
        uni, warn = rules.normalizar_unidad("Lt", 2)
        assert uni == "L"
        assert warn is None

    def test_grs_se_convierte_a_g(self):
        uni, warn = rules.normalizar_unidad("grs", 500)
        assert uni == "g"
        assert warn is None

    def test_envase_botella_singular_da_unidad(self):
        uni, warn = rules.normalizar_unidad("Botella", 1)
        assert uni == "Unidad"
        assert warn is not None

    def test_envase_botellas_plural_da_unidades(self):
        uni, warn = rules.normalizar_unidad("Botellas", 6)
        assert uni == "Unidades"
        assert warn is not None

    def test_contenido_manda_sobre_la_palabra_para_singular_plural(self):
        # "Botella" (singular) pero contenido=6 -> igual "Unidades".
        uni, _ = rules.normalizar_unidad("Botella", 6)
        assert uni == "Unidades"

    def test_unidad_prohibida_se_avisa(self):
        uni, warn = rules.normalizar_unidad("Porciones", 4)
        assert uni == "Unidades"
        assert warn is not None
        assert "no está permitida" in warn

    def test_unidad_desconocida_hace_fallback_y_avisa(self):
        uni, warn = rules.normalizar_unidad("Cositas", 3)
        assert uni == "Unidades"
        assert warn is not None


class TestValidarImagen:
    def test_link_valido_jpg(self):
        assert rules.validar_imagen("https://cdn.example.com/foto.jpg") is None

    def test_link_valido_png(self):
        assert rules.validar_imagen("http://cdn.example.com/foto.PNG") is None

    def test_sin_protocolo_es_invalido(self):
        assert rules.validar_imagen("cdn.example.com/foto.jpg") is not None

    def test_extension_no_permitida_es_invalida(self):
        assert rules.validar_imagen("https://cdn.example.com/foto.webp") is not None

    def test_dominio_imgbb_bloqueado(self):
        assert rules.validar_imagen("https://es.imgbb.com/foto.jpg") is not None


class TestValidarSkuCaracteres:
    def test_letras_numeros_guion_y_guion_bajo_son_validos(self):
        assert rules.validar_sku_caracteres("SKU-001_A") is None

    def test_caracteres_especiales_son_invalidos(self):
        assert rules.validar_sku_caracteres("SKU@001!") is not None

    def test_sku_vacio_no_genera_error_aca(self):
        # La obligatoriedad de SKU se valida aparte; esta funcion solo mira caracteres.
        assert rules.validar_sku_caracteres("") is None


class TestNombreFormado:
    def test_concatena_en_orden_y_capitaliza(self):
        nf = rules.nombre_formado("bebida gaseosa", "coca-cola", "lata", 350, "mL")
        assert nf == "Bebida Gaseosa Coca-Cola Lata 350 mL"

    def test_supera_64_caracteres(self):
        nf = rules.nombre_formado("Producto Con Nombre Muy Largo Para Forzar El Limite", "Marca Larga", "Variante Larga", 1, "Unidad")
        assert len(nf) > 64


class TestDetectarEsTemplatePeya:
    def test_detecta_template_fijo(self):
        rows = [
            [""] * 16,
            ["Activo (SI/NO)", "Codigo de Barras", "SKU", "Precio", "Seccion"] + [""] * 11,
        ]
        assert rules.detectar_es_template_peya(rows) is True

    def test_no_detecta_generico(self):
        rows = [["Nombre", "Precio", "Descripcion"]]
        assert rules.detectar_es_template_peya(rows) is False


# ═══ procesar_filas — modo template fijo PedidosYa ══════════════

def _fila_peya(activo="SI", ean="", sku="", precio="", sec="", que_es="",
                marca="", variante="", cont="", uni="", img="", desc="",
                impuestos="", ean_frac=""):
    row = [""] * 16
    row[0], row[1], row[2], row[3], row[4] = activo, ean, sku, precio, sec
    row[5], row[6], row[7], row[8], row[9] = que_es, marca, variante, cont, uni
    # row[10] = K (Nombre formado), formula, no se llena en el input
    row[11], row[12], row[13], row[14] = img, desc, impuestos, ean_frac
    return row


def _template_peya_rows(filas_producto):
    nota = [""] * 16
    header = [
        "Activo (SI/NO)", "Codigo de Barras", "SKU", "Precio", "Seccion",
        "Que producto es", "Marca (brand)", "Variante", "Contenido", "Unidad",
        "Nombre formado", "Link/URL de la Imagen", "Descripcion",
        "Impuestos", "EAN de la caja del fraccionado", "Validation INFO",
    ]
    return [nota, header] + filas_producto


class TestProcesarFilasTemplatePeya:
    def test_producto_completo_queda_ok(self):
        rows = _template_peya_rows([
            _fila_peya(ean="7801234567890", sku="SKU-1", precio=1990, sec="Bebidas",
                       que_es="Bebida Gaseosa", marca="Coca-Cola", variante="Lata",
                       cont=350, uni="mL", img="https://cdn.example.com/img.jpg", desc="desc corta"),
        ])
        productos = rules.procesar_filas(rows)
        assert len(productos) == 1
        p = productos[0]
        assert p["estado"] == "ok"
        assert p["que_es"] == "Bebida Gaseosa"
        assert p["marca"] == "Coca-Cola"
        assert p["cont"] == 350
        assert p["uni"] == "mL"

    def test_regresion_nombre_sale_de_columna_f_no_de_activo(self):
        rows = _template_peya_rows([
            _fila_peya(precio=100, sec="X", que_es="Producto Real"),
        ])
        p = rules.procesar_filas(rows)[0]
        assert p["que_es"] == "Producto Real"
        assert p["orig"] == "Producto Real"

    def test_regresion_contenido_y_unidad_vienen_directo_del_template(self):
        rows = _template_peya_rows([
            _fila_peya(precio=100, sec="X", que_es="Producto", cont=500, uni="g"),
        ])
        p = rules.procesar_filas(rows)[0]
        assert p["cont"] == 500
        assert p["uni"] == "g"
        assert not any("Unidad por defecto" in w for w in p["warns"])

    def test_regresion_fila_con_nombre_y_sin_precio_es_error_no_se_descarta(self):
        rows = _template_peya_rows([
            _fila_peya(sec="X", que_es="Producto Sin Precio"),
        ])
        productos = rules.procesar_filas(rows)
        assert len(productos) == 1
        assert productos[0]["estado"] == "err"
        assert "Precio vacío o inválido" in productos[0]["errs"]

    def test_fila_totalmente_vacia_se_omite(self):
        rows = _template_peya_rows([_fila_peya()])
        assert rules.procesar_filas(rows) == []

    def test_sku_faltante_usa_ean_como_fallback(self):
        rows = _template_peya_rows([
            _fila_peya(ean="7801234567890", precio=100, sec="X", que_es="Producto"),
        ])
        p = rules.procesar_filas(rows)[0]
        assert p["sku"] == "7801234567890"

    def test_descripcion_larga_genera_advertencia(self):
        rows = _template_peya_rows([
            _fila_peya(precio=100, sec="X", que_es="Producto", sku="S1", desc="a" * 300,
                       cont=1, uni="Unidad", img="https://cdn.example.com/img.jpg"),
        ])
        p = rules.procesar_filas(rows)[0]
        assert p["estado"] == "warn"
        assert any("250" in w for w in p["warns"])

    def test_sin_imagen_es_error_no_advertencia(self):
        # Politica de catalogo: la imagen es obligatoria para crear un
        # producto nuevo, el partner no puede mandar el template sin los
        # links — por eso ahora es un error, no una advertencia como antes.
        rows = _template_peya_rows([
            _fila_peya(precio=100, sec="X", que_es="Producto", sku="S1",
                       cont=1, uni="Unidad"),
        ])
        p = rules.procesar_filas(rows)[0]
        assert p["estado"] == "err"
        assert any("magen" in e for e in p["errs"])

    def test_sin_codigo_de_barras_no_es_error(self):
        # Politica de catalogo: el codigo de barras (B) es opcional.
        rows = _template_peya_rows([
            _fila_peya(precio=100, sec="X", que_es="Producto", sku="S1",
                       cont=1, uni="Unidad", img="https://cdn.example.com/img.jpg"),
        ])
        p = rules.procesar_filas(rows)[0]
        assert p["estado"] == "ok"
        assert not any("barras" in e.lower() or "ean" in e.lower() for e in p["errs"])

    def test_contenido_y_unidad_vacios_son_error(self):
        rows = _template_peya_rows([
            _fila_peya(precio=100, sec="X", que_es="Producto", sku="S1",
                       img="https://cdn.example.com/img.jpg"),
        ])
        p = rules.procesar_filas(rows)[0]
        assert p["estado"] == "err"
        assert any("Contenido/Unidad" in e for e in p["errs"])

    def test_que_producto_es_vacio_es_error(self):
        rows = _template_peya_rows([
            _fila_peya(precio=100, sec="X", sku="S1",
                       cont=1, uni="Unidad", img="https://cdn.example.com/img.jpg"),
        ])
        productos = rules.procesar_filas(rows)
        # Sin F, la fila ni siquiera se toma como producto (se salta como vacia).
        assert productos == []

    def test_imagen_con_extension_invalida_es_error(self):
        rows = _template_peya_rows([
            _fila_peya(precio=100, sec="X", que_es="Producto", sku="S1",
                       cont=1, uni="Unidad", img="https://cdn.example.com/img.webp"),
        ])
        p = rules.procesar_filas(rows)[0]
        assert p["estado"] == "err"
        assert any("inválido" in e for e in p["errs"])

    def test_sku_con_caracteres_invalidos_es_error(self):
        rows = _template_peya_rows([
            _fila_peya(precio=100, sec="X", que_es="Producto", sku="SKU@001!",
                       cont=1, uni="Unidad", img="https://cdn.example.com/img.jpg"),
        ])
        p = rules.procesar_filas(rows)[0]
        assert p["estado"] == "err"
        assert any("caracteres no permitidos" in e for e in p["errs"])

    def test_impuestos_y_ean_fraccionado_se_capturan(self):
        rows = _template_peya_rows([
            _fila_peya(precio=100, sec="X", que_es="Producto", sku="S1",
                       cont=1, uni="Unidad", img="https://cdn.example.com/img.jpg",
                       impuestos="IVA", ean_frac="1234567890123"),
        ])
        p = rules.procesar_filas(rows)[0]
        assert p["impuestos"] == "IVA"
        assert p["ean_fraccionado"] == "1234567890123"

    def test_activo_se_lee_del_archivo_no_se_hardcodea(self):
        rows = _template_peya_rows([
            _fila_peya(activo="NO", precio=100, sec="X", que_es="Producto", sku="S1",
                       cont=1, uni="Unidad", img="https://cdn.example.com/img.jpg"),
        ])
        p = rules.procesar_filas(rows)[0]
        assert p["activo"] == "NO"


# ═══ procesar_filas — modo template generico ════════════════════

class TestProcesarFilasGenerico:
    def test_detecta_header_y_mapea_columnas(self):
        rows = [
            ["Nombre", "Precio", "Descripcion", "Inventario"],
            ["Producto Basico", "1990", "Descripcion de prueba", "10 unidades"],
        ]
        productos = rules.procesar_filas(rows)
        assert len(productos) == 1
        assert productos[0]["precio"] == 1990
        assert productos[0]["desc"] == "Descripcion de prueba"

    def test_fila_de_categoria_se_omite(self):
        rows = [
            ["Nombre", "Precio", "Descripcion", "Inventario"],
            ["Bebidas", "", "", ""],
            ["Producto Basico", "1990", "Descripcion", "10 unidades"],
        ]
        productos = rules.procesar_filas(rows)
        assert len(productos) == 1
