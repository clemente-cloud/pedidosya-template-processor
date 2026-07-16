# Template Processor — PedidosYa Content

Procesador de templates de productos para KAMs de PedidosYa. Un solo
archivo HTML, sin servidor ni backend: todo el parseo, las validaciones y
la generación de la descarga corren en el navegador del KAM.

## Cómo usarlo

Abrí `index.html` en el navegador (doble clic, o subilo a GitHub Pages —
ver más abajo). Nada se instala, nada se sube a ningún servidor.

## Cómo funciona

1. **Cargar archivo**: el KAM sube el `.xlsx` que le devolvió el partner.
   Se lee con [SheetJS](https://sheetjs.com) directamente en el navegador.
2. **Procesar**: se detecta si es el template fijo de PedidosYa (columnas
   A-P) o uno genérico, se extraen los productos y se aplican las
   políticas de catálogo (SKU, precio, sección, unidades de medida,
   imagen, longitud de nombre formado, etc.) — toda la lógica está en el
   `<script>` de `index.html`.
3. **Revisar y editar**: la tabla de resultados es un espejo 1:1 de las
   columnas A-P del template real (mismos colores de header, K y P
   calculadas en vivo como fórmulas de solo lectura). Cualquier celda es
   editable y revalida al instante.
4. **Descargar**: con [ExcelJS](https://github.com/exceljs/exceljs) se
   abre el archivo **original** que subió el partner (no uno nuevo) y se
   inyectan solo las celdas de datos editadas desde la fila 3, sin tocar
   K, P, estilos, colores, anchos de columna ni la hoja de instrucciones.
   Puede tardar varios segundos en archivos grandes (el template trae
   20.000 filas preformateadas) — el botón muestra "Generando..." mientras
   tanto.

## Desplegar en GitHub Pages (gratis, sin servidor)

1. Subí este repo a GitHub (ya está en
   `github.com/clemente-cloud/pedidosya-template-processor`).
2. En GitHub: **Settings → Pages → Source**, elegí la rama `main` y
   carpeta `/ (root)`.
3. GitHub te da una URL tipo
   `https://clemente-cloud.github.io/pedidosya-template-processor/` —
   esa es la app, ya online, gratis, sin límites de memoria ni de tiempo
   de actividad porque no hay ningún servidor corriendo.

## Por qué no hay backend

Hasta una versión anterior, esto corría con un backend en Python
(FastAPI + openpyxl) desplegado en Render, para poder preservar el Excel
original al descargar. Se volvió a una arquitectura 100% client-side
porque:

- El plan gratuito de un servidor real trae límites de memoria/tiempo que
  complicaban archivos grandes (y romper esto en producción no vale la
  pena para una herramienta interna de bajo volumen).
- `ExcelJS` (JavaScript) hace exactamente lo mismo que `openpyxl`
  (Python) — abre el archivo, preserva estilos/fórmulas/anchos de
  columna, inyecta solo los datos — pero corriendo en la PC del KAM, que
  tiene muchos más recursos disponibles que un plan gratuito de hosting.
- Sin servidor no hay sesiones que expiren, ni "se durmió por
  inactividad", ni nada que desplegar o mantener — igual que GitHub
  Pages para cualquier página estática.

## Reglas de negocio implementadas

- **SKU**: obligatorio, solo letras/números/guion/guion bajo, máx. 64
  caracteres. Si viene vacío, usa el código de barras como fallback.
- **Precio, Sección**: obligatorios siempre.
- **Que producto es, Contenido, Unidad, Imagen**: obligatorios para
  crear un producto nuevo (igual que exige la fórmula real de Validation
  INFO del Excel).
- **Código de Barras (EAN)**: opcional — si falta, no es error, pero se
  avisa en un popup aparte cuántos productos quedaron sin código.
- **Unidades de medida**: se normalizan contra una lista de unidades
  válidas, alias conocidos (`Lt`→`L`, `grs`→`g`, etc.), palabras de
  envase genéricas (`Botella`/`Botellas`→`Unidad`/`Unidades` según
  contenido) y una lista de unidades prohibidas — todo con advertencia
  para que el KAM lo revise.
- **Imagen**: debe ser `http(s)://` y terminar en `.jpg/.jpeg/.png`; no
  puede alojarse en `es.imgbb.com`.
- **Nombre formado**: no puede superar 64 caracteres; se avisa si
  contiene emojis o abreviaciones conocidas (`comp`→comprimidos, etc. —
  lista chica pensada para ampliarse con casos reales).

## Pendiente / ideas de mejora

- La lista de abreviaciones conocidas (`ABREVIACIONES_CONOCIDAS` en el
  script) es un punto de partida chico — se puede ampliar con casos
  reales que reporten los KAMs.
- Sin autenticación: cualquiera con el link puede usar la herramienta. Si
  se comparte más allá del equipo de KAMs, conviene restringir el acceso
  (GitHub Pages no tiene login nativo — habría que ponerlo detrás de algo
  como Cloudflare Access, o volver a un backend si hace falta).
