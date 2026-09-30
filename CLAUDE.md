# Economía de audiencias en la TV abierta chilena

Proyecto para medir, a lo largo del tiempo, qué parte de los ingresos de los principales canales de TV abierta de Chile viene de **vender audiencias a los anunciantes** y qué parte de **vender contenido**. El marco de referencia es la Tabla 1.1 de Napoli (2003), *Audience Economics: Media Institutions and the Audience Marketplace*, Columbia University Press.

Investigador responsable: Cristian Buzeta (Universidad de los Andes, Chile).

Este archivo es la guía de trabajo del proyecto. Claude Code lo lee al inicio de cada sesión. Si cambia una decisión, se registra en la sección **Decisiones**.

---

## 1. Estado al inicio (29-sep-2026)

Hay un piloto validado a mano para 2024, 2025, el primer semestre 2025 y el primer semestre 2026 de los cuatro canales, construido desde las notas de ingresos de los estados financieros (EEFF) publicados en la CMF. Todo cuadra al peso con los totales de cada estado.

Archivos del piloto, en `piloto/`:
- `ingresos_canales_tv_chile_napoli.xlsx`: planilla con la clasificación común (Nivel 1 y Nivel 2), la codificación estilo Napoli con rangos y el contraste con la AAM.
- `semilla_lineas_validadas.csv`: 48 líneas de nota extraídas y verificadas. **Es el conjunto de validación**: el pipeline automático debe reproducir exactamente estos montos.

Objetivo de esta etapa: extender la serie a **2016–2026**, idealmente con semestres, de forma automática, reproducible y actualizable cada trimestre. Además, construir una **herramienta de visualización** del cambio en el tiempo.

---

## 2. Unidades de análisis

| Canal | Sociedad informante | RUT | Dónde publica en la CMF |
|---|---|---|---|
| TVN | Televisión Nacional de Chile | 81.689.800-5 | Ficha de entidad (emisor, Ley 20.382) |
| Canal 13 | Canal 13 SpA | 76.115.132-0 | Estados financieros de concesionarias de TV |
| Mega | Megamedia S.A. (consolidado) | 76.185.964-1 | Estados financieros de concesionarias de TV |
| Chilevisión | Red de Televisión Chilevisión S.A. | — | Estados financieros de concesionarias de TV |

**Moneda:** miles de pesos chilenos nominales (M$), tal como vienen en los EEFF. El deflactor se aplica después (ver 6.4).

**Perímetro:** en Mega se usa el consolidado, que incluye radios y cable. Los estados individuales de Megamedia (anexos del Oficio Circular 498) no traen desglose de ingresos. La variante "perímetro TV" se calcula restando la publicidad radial y de cable.

---

## 3. Fuentes

### 3.1 Canal 13, Mega y Chilevisión: sección de concesionarias de TV de la CMF

Cada canal tiene una página que lista todos sus EEFF trimestrales, desde 2020, más diciembre 2017 y diciembre 2019:

- Canal 13 SpA: https://www.cmfchile.cl/portal/estadisticas/617/w3-propertyvalue-46330.html
- Megamedia S.A.: https://www.cmfchile.cl/portal/estadisticas/617/w3-propertyvalue-46333.html
- Chilevisión: https://www.cmfchile.cl/portal/estadisticas/617/w3-propertyvalue-46334.html

Cada período enlaza a una página `.../626/w4-article-NNNNN.html`. Esa página tiene un ZIP `.../626/articles-NNNNN_recurso_1.zip`. Hay que tomar el enlace del ZIP desde la página del artículo, porque a veces lleva un parámetro `?ts=`.

Artículos ya identificados, útiles para comprobar el scraper:

| Período | Canal 13 | Mega | Chilevisión |
|---|---|---|---|
| 30-06-2026 | 113709 | 113710 | 113714 |
| 31-03-2026 | 111123 | 111125 | 111126 |
| 31-12-2025 | 109182 | 109207 | 109184 |
| 30-06-2025 | 98820 | 98823 | 98825 |
| 31-12-2024 | 93013 | 93019 | 93017 |
| 31-12-2022 | 68977 | 68984 | 68983 |
| 31-12-2020 | 47350 | 47352 | 47353 |
| 31-12-2019 | 28617 | 28606 | 28710 |
| 31-12-2017 | 29080 | 29085 | 29083 |

Cada ZIP trae varios PDF: carta conductora, estados financieros, análisis razonado, declaración de responsabilidad, hechos esenciales y, en Mega, anexos del Oficio Circular 498. **Solo interesa el PDF de estados financieros.** Los nombres de archivo no sirven para identificarlos (por ejemplo, `2026090594832-1.pdf`).

### 3.2 TVN

- Ficha de la CMF, "Información financiera": https://www.cmfchile.cl/institucional/mercados/entidad.php?mercado=V&rut=81689800&grupo=0&tipoentidad=RGEIN&vig=VI&row=AAAwy2ACTAAAByxAAA&mm=12&aa=2025&tipo=I&orig=lista&control=svs&tipo_norma=IFRS&pestania=3
  - Se cambian los parámetros `mm` (03, 06, 09, 12) y `aa`.
  - Los enlaces a PDF son del tipo `safec_ifrs_verarchivo.php?auth=...&send=...`, con tokens de sesión. Hay que obtenerlos navegando la página, no construirlos.
- Alternativa: sitio de TVN, `https://estaticos.tvn.cl/skins/web-assets/images/corporativo/{AÑO}/estados-financieros/LIBROFECUTVNDIC{AÑO}.pdf` (comprobado para 2021; en otros años puede cambiar el nombre).
- Totales de control: la ficha de TVN en el SEP (https://empresasestatales.gob.cl/informacion-por-empresa?id=33) y la base masiva IFRS de la CMF (archivos `eifrs*.txt`, que traen solo los estados principales, sin notas).

### 3.3 Datos de mercado, para contrastar

AAM (Asociación de Agencias de Medios): inversión publicitaria total y por medio. Sirve solo para verificar que las cifras sean razonables, porque la AAM mide inversión bruta y los canales informan ingresos netos de comisiones.

---

## 4. Pipeline

Lenguaje sugerido: Python (pdfplumber o pdftotext, pandas, sqlite3). Puede portarse a R si se prefiere para el análisis.

```
proyecto/
├── CLAUDE.md                 ← este archivo
├── piloto/                   ← planilla y CSV semilla del piloto
├── data/
│   ├── raw/zip/              ← ZIP tal como vienen de la CMF (no se editan)
│   ├── raw/pdf/              ← PDF descomprimidos, en carpetas {canal}/{periodo}/
│   ├── manifest.csv          ← inventario: canal, período, URL artículo, URL zip, fecha de descarga, hash
│   ├── documentos.csv        ← cada PDF clasificado: canal, fecha_cierre, tipo_documento, páginas
│   └── ingresos.sqlite       ← base final
├── src/
│   ├── 01_inventario.py
│   ├── 02_descarga.py
│   ├── 03_identificar.py
│   ├── 04_extraer_nota.py
│   ├── 05_mapear.py
│   └── 06_exportar.py
├── mapeo/lineas_mapeo.csv    ← tabla de mapeo línea→categorías (versionada, editable a mano)
├── revision/                 ← casos marcados para revisión manual
├── salidas/                  ← planilla, CSV para la visualización, gráficos
└── viz/                      ← herramienta de visualización
```

### Paso 1. Inventario
Leer las tres páginas de canal (3.1) y la ficha de TVN (3.2), y producir `manifest.csv` con todos los períodos disponibles. **Criterio de aceptación:** los números de artículo de la tabla 3.1 aparecen en el manifest.

### Paso 2. Descarga
Descargar los ZIP con pausas entre solicitudes, para no saturar el sitio de la CMF. No volver a bajar lo que ya está (verificar con el hash). Descomprimir en `data/raw/pdf/`.

### Paso 3. Identificación por contenido
Para cada PDF, leer las primeras páginas y detectar:
- **Sociedad:** "CANAL 13 SpA", "MEGAMEDIA S.A.", "RED DE TELEVISIÓN CHILEVISIÓN", "TELEVISIÓN NACIONAL".
- **Fecha de cierre:** "al 31 de diciembre de 2025", "30 de junio de 2026", etc.
- **Tipo de documento:** "Estados Financieros" / "Estados financieros consolidados" / "Estados Financieros Intermedios" frente a "ANÁLISIS RAZONADO", "Hechos Esenciales", "Oficio Circular N° 498", carta o declaración.

Se conserva solo `tipo = EEFF`. **Criterio de aceptación:** exactamente un EEFF por canal y período. Si hay cero o más de uno, el caso va a `revision/`.

### Paso 4. Extracción de la nota de ingresos
Localizar la nota "Ingresos de actividades ordinarias". Su número cambia según el canal y el año (C13 Nota 20/21, Mega Nota 7, CHV Nota 20, TVN Nota 21/22). Extraer cada línea con su monto para **todas las columnas**: período actual, comparativo y, en los intermedios, los trimestres.

Registrar por cada monto: `canal, fecha_cierre, tipo_periodo (anual|semestre|trimestre|acumulado9m), linea_original, monto, documento_origen, rol (actual|comparativo), pagina`.

**Controles obligatorios:**
- La suma de las líneas es igual al total de la nota, y este es igual a "Ingresos de actividades ordinarias" del estado de resultados.
- Los montos de `piloto/semilla_lineas_validadas.csv` se reproducen exactamente.
- Si el texto extraído es ilegible (fuente corrupta, ver 7.4), el caso va a `revision/` y no se inventan cifras.

### Paso 5. Mapeo
`mapeo/lineas_mapeo.csv` asigna cada `(canal, linea_original normalizada)` a sus categorías (sección 5). Las líneas nuevas que no estén mapeadas detienen el proceso y se listan para decidir a mano. Nunca se asignan categorías por adivinación.

### Paso 6. Exportación
- Tabla larga (una fila por línea, período y versión) y tablas anchas por nivel.
- Planilla de Excel actualizada, con la misma estructura del piloto.
- CSV o JSON para la visualización.

---

## 5. Esquema de clasificación

### 5.1 Nivel 1: básico (común a los cuatro canales)
- **Publicidad:** toda línea que la nota rotula como publicidad.
- **Otros ingresos:** todo lo demás.

### 5.2 Nivel 2: común máximo (la partición más fina posible sin supuestos)
- **Publicidad**
- **Otros ingresos operacionales**
- **Transferencias del Estado**: subvención NTV, solo TVN desde 2025. En los privados es un cero estructural.

No se puede desagregar más de forma común: solo C13 separa la publicidad digital, solo Mega separa radio y cable, y solo Mega tiene una línea pura de contenidos.

### 5.2b Niveles 3 y 4 (aprobados 30-sep-2026)
Anidados en el Nivel 2 (la suma de cada nivel es igual al total). Columnas `nivel3` y `nivel4` de `mapeo/lineas_mapeo.csv`.
- **Nivel 3** (7): Publicidad TV y digital · Publicidad en otros medios · Arriendo de pantalla · Contenidos y señales · Otros ingresos · Venta de activos · Transferencias del Estado.
- **Nivel 4** (13): Publicidad TV abierta · Publicidad digital · Publicidad TV + digital (sin desglose) · Canje (publicidad en especie) · Publicidad radio y cable · Comisión publicidad TV paga · Arriendo de pantalla · Contenidos y señales · Eventos · Arriendos y servicios · Otros sin desglose · Venta de activos · Transferencias del Estado.
- «Sin desglose» deja explícito lo que el canal no informa; nunca se reparte por supuesto.
- CHV «Ingresos por publicidad» = Publicidad TV abierta; desde 2023 incluye la comisión por TV paga (antes línea TILA): quiebre marcado.
- Pendiente: desagregación nacional/extranjero de Mega (nota 7 b, desde 2018) como detalle de «Contenidos y señales».

### 5.3 Codificación estilo Napoli (con rangos)
Cada línea recibe:
- Código principal: `Audiencias`, `Contenidos` o `Fuera de Napoli`.
- Pureza: `Pura` o `Mixta`.
- Banderas S/N de las categorías que la línea puede contener.
- Medio: TV abierta, digital, radio/cable, mixto o no aplica.

Por cada canal y período se calculan: **piso** (suma de las líneas puras de la categoría), **techo** (suma de todas las líneas que pueden pertenecer a ella) y **punto** (según el código principal). También la variante de **perímetro TV** (sin radio ni cable).

### 5.4 Mapeo vigente (2024–2026)

| Canal | Línea en la nota | N1 | N2 | Napoli (pureza) |
|---|---|---|---|---|
| TVN | Ingresos por publicidad en televisión abierta | Publicidad | Publicidad | Audiencias (pura, TV) |
| TVN | Otros ingresos | Otros | Otros operacionales | Contenidos (mixta A/C/F) |
| TVN | Subvención NTV | Otros | Transferencias del Estado | Fuera (pura) |
| Canal 13 | Ingresos de Publicidad Pantalla abierta | Publicidad | Publicidad | Audiencias (pura, TV) |
| Canal 13 | Ingresos de Publicidad Otras plataformas | Publicidad | Publicidad | Audiencias (pura, digital) |
| Canal 13 | Otros ingresos de explotación | Otros | Otros operacionales | Contenidos (mixta C/F) |
| Mega | Ingresos por publicidad de televisión e internet | Publicidad | Publicidad | Audiencias (pura, TV+digital) |
| Mega | Ingresos por publicidad radial y cable | Publicidad | Publicidad | Audiencias (pura, radio/cable) |
| Mega | Ingresos por ventas en plataformas y contenidos | Otros | Otros operacionales | Contenidos (pura) |
| Chilevisión | Ingresos por publicidad | Publicidad | Publicidad | Audiencias (pura, TV + comisión TV paga) |
| Chilevisión | Ingresos nuevos negocios | Otros | Otros operacionales | Contenidos (mixta A/C/F) |

Los nombres de las líneas en años anteriores serán distintos. Hay que mapearlos explícitamente, por ejemplo los de Mega en la sección 7.2.

---

## 6. Decisiones

### 6.1 Cifras reexpresadas o reclasificadas
**Confirmado (30-sep-2026).** Guardar todas las versiones (original y comparativos posteriores) con `documento_origen` y `rol`. La serie principal usa la **versión más reciente** de cada período, y la versión original queda disponible para análisis de sensibilidad. Se marca `reclasificado = TRUE` cuando las versiones difieren.

### 6.2 Frecuencia
**Confirmado (30-sep-2026).** H2 se deriva como anual − H1. Los privados tienen semestres desde 2019 (la CMF no publica intermedios 2018). serie anual 2016–2025 como núcleo, más primeros semestres (enero–junio) de todos los años disponibles. Los trimestres se extraen igual, porque vienen en los mismos documentos, pero no son el foco.

### 6.3 Horizonte
2016–2026, limitado por la sección de concesionarias de la CMF (el primer EEFF es de diciembre 2017, que trae 2016 como comparativo). TVN podría llegar más atrás, pero no se hace, para mantener un panel equilibrado. No se mezclan cifras anteriores a IFRS (FECU en norma chilena, antes de 2009).

### 6.4 Pesos reales y otras unidades
**Confirmado (30-sep-2026).** Fuente: Banco Central de Chile (BDE, `src/00_externos.py`). $ de 2025: IPC general, variación mensual oficial encadenada (promedio 2025 = 100). UF: promedio de la UF diaria del período. US$: promedio del dólar observado diario del período.

### 6.5 Perímetro de la muestra
**Confirmado (30-sep-2026).** Se incluyen La Red y TV+ (y su antecesora UCVTV SpA, 2017). Agregados de industria: «4 grandes» y «6 canales CMF», solo en períodos donde todos informan. No cubren canales que no reportan a la CMF.

### 6.6 Venta de activos de C13
**Confirmado (30-sep-2026).** Los montos que la nota informa se separan de «Otros ingresos de explotación» como línea propia, Fuera de Napoli pura (`mapeo/desgloses_nota.csv`, con documento y página). Q1 y Q2 2020 quedan sin desglose porque la nota no los informa por trimestre.

---

## 7. Particularidades conocidas (leer antes de extraer)

### 7.1 Canal 13
- Tres líneas estables en 2023–2026. El EEFF 2024 y el comparativo 2025 coinciden, sin reexpresión.
- La nota (a) de "Otros ingresos de explotación" mezcla cableoperadores, digital no publicitario, nuevas señales, venta de contenidos, venta de activos y arriendos.
- 2023 (del EEFF 2024): pantalla abierta 52.680.675; otras plataformas 3.244.433; otros 16.137.671; total 72.062.779.

### 7.2 Mega
- **Cambio de rótulos en 2025:**
  - Hasta el EEFF de septiembre 2025 las líneas eran "Ingresos por publicidad de televisión e internet", "Ingresos por otros negocios" y "Ingresos propios de subsidiarias" (a veces "publicidad propios de subsidiarias").
  - Desde diciembre 2025 son "…televisión e internet", "…ventas en plataformas y contenidos" y "…publicidad radial y cable".
  - Los montos de 2024 coinciden entre ambas versiones: otros negocios = plataformas y contenidos; subsidiarias = radial y cable.
- 2023 (del EEFF 2024): TV e internet 73.261.527; otros negocios 17.439.342; subsidiarias 7.116.952; total 97.817.821.
- La nota 7 b) desagrega además entre ventas nacionales y al extranjero. Conviene extraerla también.
- Los anexos del Oficio Circular 498 traen el estado de resultados individual (ingresos de 96.666.662 en 2025 y 94.456.363 en 2024), sin desglose. No se usan para la serie, pero la prensa suele citar esas cifras.

### 7.3 Chilevisión
- Dos líneas: "Ingresos por publicidad" (TV abierta más comisión por TV paga) e "Ingresos nuevos negocios".
- **Reclasificación sin nota explicativa:** el primer semestre 2025 difiere según el documento.
  - En el EEFF de septiembre 2025 implica publicidad 31.256.166 y nuevos negocios 3.970.381.
  - En el comparativo del EEFF de junio 2026 es 33.494.199 y 1.732.348.
  - El total es el mismo (35.226.547); se movieron unos 2.238.033 de una línea a otra.
  - El comparativo del primer trimestre 2025 en el EEFF de marzo 2026 **no** está reclasificado (nuevos negocios 2.150.807).
  - Coincide con el cambio de controlador a Vytal Group (enero 2026) y con una política contable más detallada.
- Cambios de controlador: Turner/WarnerMedia (2010), Paramount/ViacomCBS (2021) y Vytal (2026). Vigilar reclasificaciones en cada cambio.
- El EEFF 2025 menciona una "Re-expresión de Estados Financieros" (Nota 29) del balance 2024.

### 7.4 TVN
- Dos líneas hasta 2024: "Ingresos por publicidad en televisión abierta" y "Otros ingresos" (principalmente venta de señal internacional a operadores de TV pago).
- Desde 2025 se suma la **subvención NTV**:
  - En el EEFF de diciembre 2025 está incluida dentro de "Otros ingresos" (M$2.000.000).
  - En el de junio 2026 aparece como línea separada.
  - Se registra siempre como línea propia.
- **El PDF de diciembre 2025 tiene la tabla de la nota 22 con la fuente corrupta.** Las cifras se reconstruyeron con el texto del análisis (total 47.915.398) y los comparativos: publicidad 28.787.675; otros 19.127.723, que incluyen la subvención NTV de 2.000.000. Para casos así conviene extraer con OCR o recurrir a otra fuente, y siempre marcarlos para revisión.
- 2023 (del EEFF 2024): publicidad 34.655.366; otros 17.370.782; total 52.026.148.

### 7.5 Cambios de norma
- **IFRS 15 (2018):** puede cambiar el tratamiento de comisiones de agencia y canjes. Hay que marcar 2017→2018 como posible quiebre y revisar la nota de políticas contables de cada canal.
- IFRS 16 (2019) no afecta los ingresos.

---

## 8. Herramienta de visualización

Una página interactiva, autocontenida y compartible, que muestre:
1. **Áreas apiladas** de la composición de ingresos en el tiempo, un panel por canal o uno a la vez.
2. **Selector de clasificación:** Nivel 1, Nivel 2 o Napoli con rangos (banda piso–techo).
3. **Selector de frecuencia:** anual o semestral.
4. **Comparación entre canales:** porcentaje de publicidad de los cuatro canales en un mismo gráfico de líneas.
5. **Referencia de Napoli:** líneas horizontales en 100% (broadcast, EE.UU. c. 2001) y 60% (cable networks).
6. **Marcas de eventos:** IFRS 15 (2018), pandemia (2020), cambios de controlador, reclasificaciones detectadas y el inicio de la subvención NTV (2025).
7. **Pesos nominales o reales** para los montos.
8. **Transparencia:** al pasar el cursor, mostrar la línea original de la nota y el documento de origen.

Los datos se leen de `salidas/` (CSV o JSON generados en el paso 6), de modo que al actualizar la base se actualiza la herramienta.

---

## 9. Orden de trabajo propuesto

1. Estructura de carpetas, copiar el piloto, `git init`.
2. Paso 1 (inventario): revisar el manifest con Cristian antes de descargar.
3. Pasos 2 y 3 (descarga e identificación): revisar `documentos.csv`.
4. Paso 4 (extracción): primero reproducir la semilla (validación) y luego extender hacia atrás año por año.
5. Paso 5 (mapeo): Cristian aprueba cada línea nueva.
6. Paso 6 (exportación): planilla y datos para la visualización.
7. Visualización: prototipo con 2023–2026 y luego la serie completa.
8. Documentar en este archivo las decisiones y hallazgos nuevos.

## 10. Reglas de trabajo

- **No inventar cifras.** Si no se puede leer o no cuadra, va a `revision/` y se pregunta.
- Toda cifra de la base debe poder rastrearse hasta un documento y una página.
- No modificar `data/raw/`.
- Una categoría nueva o un cambio de mapeo se registra en `mapeo/lineas_mapeo.csv` con fecha y justificación.
- Descargas respetuosas con la CMF: pausas entre solicitudes y sin repetir descargas.

---

## 11. Estado del pipeline (30-sep-2026)

**Cómo correrlo** (desde la raíz del proyecto; en Windows anteponer `PYTHONIOENCODING=utf-8`):
```
python src/01_inventario.py      # inventario + hash + descompresión (los ZIP ya están en data/{canal}/, bajados a mano)
python src/03_identificar.py     # data/documentos.csv; casos a revision/identificacion.csv
python src/04_extraer_nota.py    # data/lineas_extraidas.csv + data/extraccion_log.csv (~20 min la primera vez por OCR; luego usa caché)
python src/04_extraer_nota.py "Canal 13" 2026-06   # corrida parcial: reemplaza solo esos documentos
python src/05_mapear.py          # data/ingresos.sqlite; se detiene si hay líneas sin mapeo
python src/validar_semilla.py    # debe dar 48/48
python src/06_exportar.py        # salidas/ + viz/ingresos_tv.html
```
Herramientas: pdftotext/pdftoppm (poppler), pdfplumber, Tesseract en `C:\Program Files\Tesseract-OCR` con `tools/tessdata/spa.traineddata`, Node portátil en `tools/node/`.

**Método de extracción.** Para cada página con el encabezado de la nota se prueban pdfplumber, pdftotext -layout, pdftotext -raw, OCR 300 dpi y OCR 400 dpi (psm 4). Solo se acepta una tabla cuyas líneas sumen el total en todas las columnas (tolerancia ±M$2 por redondeo de la fuente, que se registra en el log), cuyos rótulos sean de ingresos (sin costo/gasto/ganancia) y cuyo total (actual o comparativo) aparezca en el estado de resultados. Las columnas se interpretan por las fechas del encabezado.

**Resultado.** 125 EEFF (TVN 39, C13 29, Mega 29, CHV 28): 124 extraídos y validados; semilla 48/48 exacta; los totales 2023 de la sección 7 coinciden. Panel anual completo 2016–2025 para los cuatro canales; semestres desde 2019 (privados) y 2016 (TVN).

**Casos en revisión.**
- Mega mar-2024: errata en la fuente (líneas suman 21.238.409; total y EERR dicen 21.238.459). Q1-2024 se toma del comparativo de mar-2025.
- TVN `estados_financieros_2018.pdf`: escaneado sin fecha legible; es una copia adicional (dic-2018 ya está cubierto por `Fecu_tvn_dic_18_libro.pdf`).
- TVN dic-2025: cifras manuales del piloto en `revision/manual_lineas.csv` (la lectura OCR de la tabla corrupta coincide).

**Hallazgos nuevos.**
- C13: "Otros ingresos de explotación" incluye venta de activos por M$13.771.539 en 2020 y ~M$6,4 millones en 2018 (Secuoya y torres). Distorsiona el punto Napoli (Contenidos); evaluar restarlo como variante.
- C13 hasta sep-2020 informa una sola línea "Ingresos de Publicidad" (sin separar otras plataformas).
- TVN 2016–mar-2018: "Publicidad en televisión abierta e internet".
- CHV 2019–2022: línea "Comisión Publicidad TV (TILA)", integrada a publicidad desde 2023; "Eventos y espectáculos" hasta sep-2024.
- Mega dic-2017 y dic-2019 los informa Red Televisiva Megavisión S.A. y subsidiarias; 2016–2017 trae "Ingresos radiales y otros". El 2019 informado por Megavisión y por Megamedia (comparativo dic-2020) coincide en todas las categorías: se acepta como comparable.
- 37 canal-períodos con versiones distintas entre EEFF (reclasificaciones o reexpresiones), en `salidas/ingresos_tv_chile.xlsx`, hoja "versiones".

**Visualización:** `viz/ingresos_tv.html`, generada desde `viz/plantilla.html` con los datos de `salidas/viz_data.json`; publicada como artifact privado: https://claude.ai/code/artifact/24b23b1a-6dd6-4ee2-8fce-21baef3ee651

**Ampliación (30-sep-2026).** La Red (28 EEFF) y TV+ (28 EEFF, incluido mar-2024 que venía en un RAR dentro del ZIP) extraídos y mapeados; decisiones de mapeo en `mapeo/lineas_mapeo.csv`. Extractor con lectura por coordenadas para celdas vacías (solo como respaldo; los 4 grandes quedan idénticos: 1.350 montos, 0 diferencias). Semilla 48/48. Series del Banco Central en `data/externos/bcch_*.csv`.
- TV+: «Arriendo espacio de transmisión» e «infomerciales» se informan juntos en los EEFF anuales; codificados igual (Otros / Audiencias mixta A-F).
- La Red: ingresos cayeron de ~M$6,7 millones (2016) a ~M$1,0 millón (2025).

**Publicación (30-sep-2026).** Repositorio público https://github.com/cbuzeta/ingresos-tv-chile (todos los derechos reservados, ver `LICENSE`). La visualización se publica en GitHub Pages: https://cbuzeta.github.io/ingresos-tv-chile/ (rama `main`, carpeta `/docs`). Para actualizarla: correr `src/06_exportar.py` (regenera `docs/index.html`), hacer commit y `git push`; Pages se reconstruye solo. Si no se reconstruye, forzar con `gh api -X POST repos/cbuzeta/ingresos-tv-chile/pages/builds`.
