# Ingresos de la TV abierta chilena, 2016–2026

¿Qué parte de los ingresos de la televisión abierta chilena viene de **vender audiencias** a los anunciantes y qué parte de **vender contenidos**? Este repositorio construye esa serie desde las notas «Ingresos de actividades ordinarias» de los estados financieros (EEFF) de seis canales, usando como marco la Tabla 1.1 de Napoli (2003), *Audience Economics: Media Institutions and the Audience Marketplace*.

Investigador responsable: Cristian Buzeta (Universidad de los Andes, Chile).

**Visualización:** `viz/ingresos_tv.html` (autocontenida; se abre en cualquier navegador).

## Cobertura

| Canal | Sociedad informante | Período |
|---|---|---|
| TVN | Televisión Nacional de Chile | 2016–2026, trimestral |
| Canal 13 | Canal 13 SpA | 2016–2026 (trimestral desde 2020) |
| Mega | Megamedia S.A., consolidado (Red Televisiva Megavisión hasta 2019) | 2016–2026 (trimestral desde 2020) |
| Chilevisión | Red de Televisión Chilevisión S.A. | 2016–2026 (trimestral desde 2020) |
| La Red | Compañía Chilena de Televisión S.A. | 2016–2026 (trimestral desde 2020) |
| TV+ | TVMAS SpA (UCVTV SpA en 2017) | 2017–2026 (trimestral desde 2020) |

Fuentes: sección de concesionarias de TV de la CMF y ficha de TVN. Montos en miles de pesos (M$) tal como vienen en los EEFF.

## Clasificación

- **Nivel 1:** Publicidad / Otros ingresos.
- **Nivel 2:** Publicidad / Otros ingresos operacionales / Transferencias del Estado (subvención NTV).
- **Nivel 3** (7 grupos) y **Nivel 4** (15 categorías): desglose más fino, anidado en el Nivel 2. Lo que un canal no informa queda como «sin desglose»; no se reparte por supuesto.
- **Napoli con rangos:** cada línea se codifica como Audiencias, Contenidos o Fuera de Napoli, pura o mixta. Por canal y período se calcula un **piso** (líneas puras), un **techo** (líneas que pueden contener la categoría) y un **punto** (código principal).

Cada decisión de clasificación está en `mapeo/lineas_mapeo.csv`, con su justificación y fecha. Los desgloses tomados de las notas (por ejemplo, la venta de activos de Canal 13 en 2018 y 2020) están en `mapeo/desgloses_nota.csv`, con documento y página.

## Controles

- En cada EEFF, la suma de las líneas de la nota es igual al total en todas las columnas, y el total aparece en el estado de resultados.
- La serie reproduce exactamente los 48 montos validados a mano del piloto (`piloto/semilla_lineas_validadas.csv`).
- Toda cifra se puede rastrear hasta un documento y una página. Las cifras que no se pudieron extraer del PDF están en `revision/manual_lineas.csv`, con su fuente.
- Cuando un período aparece distinto en dos EEFF (reclasificación o reexpresión), se guardan ambas versiones; la serie principal usa la más reciente.

## Unidades

$ nominales; $ de 2025 (IPC del Banco Central, variación mensual encadenada); UF y US$ (promedio del período de la UF diaria y del dólar observado, Banco Central). Series en `data/externos/`.

## Cómo reproducir

Los PDF originales no están en el repositorio. `data/manifest.csv` lista cada archivo con su número de artículo de la CMF y su hash SHA-256. Para reconstruir la base, bajarlos en `data/{canal}/` y correr:

```
python src/00_externos.py      # series del Banco Central
python src/01_inventario.py    # inventario y descompresión
python src/03_identificar.py   # identifica el PDF de EEFF en cada paquete
python src/04_extraer_nota.py  # extrae la nota de ingresos (OCR para los escaneados)
python src/04b_mega_geografia.py  # Mega: ventas nacionales / al extranjero (nota 7 b)
python src/05_mapear.py        # aplica el mapeo; se detiene si hay líneas nuevas sin clasificar
python src/validar_semilla.py  # debe dar 48/48
python src/06_exportar.py      # salidas/ y viz/
```

Requisitos: Python 3.12 (pandas, pdfplumber, openpyxl, requests), poppler (`pdftotext`, `pdftoppm`), Tesseract con el modelo `spa`, y 7-Zip para un paquete que viene en RAR.

## Salidas

- `salidas/ingresos_tv_chile.xlsx`: planilla con Nivel 1, Nivel 2, Napoli, versiones y mapeo.
- `salidas/agregados.csv`: serie por canal, agregado de industria y período.
- `salidas/lineas_larga.csv`: una fila por línea de nota, período y documento.
- `data/ingresos.sqlite`: la misma base en SQLite.

## Licencia

Todos los derechos reservados. El repositorio es público solo para consulta; ver `LICENSE`.
