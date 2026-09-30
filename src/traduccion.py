"""Versión en inglés de la visualización.

- NOMBRES: canales y categorías que vienen de los datos; se traducen al mostrarlos (diccionario TR de la página).
- FRASES: textos fijos de la plantilla, reemplazados al generar docs/en/index.html (del más largo al más corto).
- RESTOS: palabras que no deberían quedar en la versión en inglés; si aparecen, la exportación se detiene.
Los rótulos de las líneas de nota se dejan en español a propósito: son citas de los EEFF.
"""
import re

NOMBRES = {
    "4 grandes": "Big 4", "6 canales CMF": "6 CMF channels", "Industria": "Industry",
    "Publicidad": "Advertising", "Otros ingresos": "Other revenue", "Otros operacionales": "Other operating revenue",
    "Otros ingresos operacionales": "Other operating revenue", "Transferencias del Estado": "State transfers",
    "Publicidad TV y digital": "TV and digital advertising", "Publicidad en otros medios": "Advertising in other media",
    "Arriendo de pantalla": "Airtime leasing", "Contenidos y señales": "Content and signals",
    "Venta de activos": "Asset sales",
    "Publicidad TV abierta": "Free-to-air TV advertising", "Publicidad digital": "Digital advertising",
    "Publicidad TV + digital (sin desglose)": "TV + digital advertising (not broken down)",
    "Canje (publicidad en especie)": "Barter (advertising in kind)", "Publicidad radio y cable": "Radio and cable advertising",
    "Comisión publicidad TV paga": "Pay-TV advertising commission",
    "Contenidos y señales (nacional)": "Content and signals (domestic)",
    "Contenidos y señales (extranjero)": "Content and signals (foreign)",
    "Contenidos y señales (sin desglose geográfico)": "Content and signals (no geographic breakdown)",
    "Eventos": "Events", "Arriendos y servicios": "Rentals and services", "Otros sin desglose": "Other (not broken down)",
}

FRASES = [
    # encabezado
    ("TV abierta · Chile · 2016–2026 · EEFF CMF", "Free-to-air TV · Chile · 2016–2026 · CMF financial statements"),
    ("<title>Audiencias en venta</title>", "<title>Audiences for sale</title>"),
    ("<h1>Audiencias en venta</h1>", "<h1>Audiences for sale</h1>"),
    ("Qué parte de los ingresos de la TV abierta chilena viene de vender audiencias a los anunciantes y qué parte de vender contenidos. "
     "Seis canales que informan a la CMF (TVN, Canal 13, Mega, Chilevisión, La Red y TV+), leídos desde la nota «Ingresos de actividades "
     "ordinarias» de cada estado financiero. Marco: Napoli (2003), <i>Audience Economics</i>, tabla 1.1.",
     "How much of Chilean free-to-air TV revenue comes from selling audiences to advertisers, and how much from selling content. "
     "Six channels that report to Chile's Financial Market Commission (TVN, Canal 13, Mega, Chilevisión, La Red and TV+), read from the "
     "revenue note of each financial statement. Framework: Napoli (2003), <i>Audience Economics</i>, table 1.1."),
    ('>Metodología</a>', '>Methodology (Spanish)</a>'), ('>Código y datos</a>', '>Code and data</a>'),
    ('<a id="otro-idioma" href="en/">English</a>', '<a id="otro-idioma" href="../">Español</a>'),
    ("Descargar:", "Download:"), (">serie por canal (CSV)<", ">series by channel (CSV)<"),
    (">líneas de nota (CSV)<", ">note lines (CSV)<"), (">planilla (Excel)<", ">workbook (Excel)<"),
    ('aria-label="Resumen del último año completo"', 'aria-label="Summary of the latest full year"'),
    ("Publicidad / ingresos, industria ${anio}", "Advertising / revenue, industry ${anio}"),
    (" en ${pri.fin.slice(0, 4)}", " in ${pri.fin.slice(0, 4)}"),
    ("Ingresos de los seis canales, ${anio}", "Revenue of the six channels, ${anio}"),
    ("$${bil(ult.total)} mil millones<small>pesos nominales</small>", "CLP ${bil(ult.total)} billion<small>nominal pesos</small>"),
    ("Rango entre canales, ${anio}", "Range across channels, ${anio}"),
    ("<small>${esc(tr(can[0].canal))} a ${", "<small>${esc(tr(can[0].canal))} to ${"),
    ("Datos generados ${DATA.generado} desde salidas/viz_data.json · ${DATA.lineas.length} montos de nota en la serie principal",
     "Data generated ${DATA.generado} from salidas/viz_data.json · ${DATA.lineas.length} note amounts in the main series"),
    # controles
    ('aria-label="Opciones de visualización"', 'aria-label="Display options"'),
    ("<span>Clasificación</span>", "<span>Classification</span>"),
    (">Nivel 1<", ">Level 1<"), (">Nivel 2<", ">Level 2<"), (">Nivel 3<", ">Level 3<"), (">Nivel 4<", ">Level 4<"),
    ("<span>Frecuencia</span>", "<span>Frequency</span>"), (">Anual<", ">Annual<"), (">Semestral<", ">Half-yearly<"),
    ("<span>Unidad</span>", "<span>Unit</span>"), (">% del total<", ">% of total<"), (">$ nominales<", ">Nominal CLP<"),
    (">$ de 2025<", ">2025 CLP<"), (">Consolidado<", ">Consolidated<"), (">Solo TV<", ">TV only<"),
    # figuras
    ("Participación de la venta de audiencias", "Share of revenue from selling audiences"),
    ('"aria-label": "Participación en el tiempo"', '"aria-label": "Share over time"'),
    ('"Publicidad sobre ingresos de actividades ordinarias."', '"Advertising as a share of operating revenue."'),
    ('" Industria = suma de los seis canales, desde 2017. Círculo hueco = período reclasificado entre EEFF."',
     '" Industry = sum of the six channels, from 2017. Hollow circle = period reclassified between filings."'),
    ('"100% broadcast EE.UU."', '"100% US broadcast"'),
    ("Referencia Napoli", "Napoli reference"),
    ("Industria = suma de los seis canales (ponderada por tamaño). Las líneas de la nota están en los paneles de cada canal.",
     "Industry = sum of the six channels (size-weighted). Note lines are in each channel's panel."),
    ("' <span class=\"flag\">reclasificado</span>'", "' <span class=\"flag\">reclassified</span>'"),
    ("<h2 id=\"t-pan\">Composición de ingresos</h2>", "<h2 id=\"t-pan\">Revenue composition</h2>"),
    ('"aria-label": "Composición de ingresos de " + ent', '"aria-label": "Revenue composition of " + tr(ent)'),
    ('"sin radio ni cable"', '"excluding radio and cable"'), ('"consolidado"', '"consolidated"'),
    ('"Porcentaje del total de ingresos de actividades ordinarias."', '"Percentage of total operating revenue."'),
    ('" Escala propia por panel."', '" Each panel has its own scale."'),
    ('" H1 = enero–junio; H2 = anual − H1."', '" H1 = January–June; H2 = full year − H1."'),
    ('" Pase el cursor para ver las líneas de la nota y su documento."', '" Hover to see the note lines and their source document."'),
    ('eje: "Miles de millones de pesos nominales."', 'eje: "Billions of nominal Chilean pesos."'),
    ('eje: "Miles de millones de pesos de 2025 (IPC Banco Central)."', 'eje: "Billions of 2025 Chilean pesos (Central Bank CPI)."'),
    ('eje: "Millones de UF (UF promedio del período)."', 'eje: "Millions of UF (period-average UF)."'),
    ('eje: "Millones de US$ (dólar observado promedio del período)."', 'eje: "Millions of US$ (period-average observed exchange rate)."'),
    ('tip: "M$ de 2025"', 'tip: "2025 M$"'),
    # tooltips
    ("<td>Total</td>", "<td>Total</td>"),
    ('<div class="doc">Montos en ${u}</div>', '<div class="doc">Amounts in ${u}</div>'),
    ("Serie del Banco Central incompleta para este período: se usa lo publicado.",
     "Central Bank series incomplete for this period: the published months are used."),
    ("Valor negativo en una categoría: el EEFF anual y el semestral clasifican distinto.",
     "Negative value in a category: the annual and half-year filings classify differently."),
    ('H2 derivado: ${esc(r.periodo.replace("H2", "año"))} − H1. Sin líneas propias.',
     'Derived H2: ${esc(r.periodo.replace("H2 ", "FY"))} − H1. No note lines of its own.'),
    ('" · cifra manual"', '" · manual figure"'),
    ("Líneas de la nota en M$ nominales · ", "Note lines (original Spanish labels), nominal M$ · "),
    ("Suma de canales; total en M$ nominales. Pase por el panel de cada canal para ver sus líneas.",
     "Sum of channels; total in nominal M$. See each channel's panel for its note lines."),
    ("Incluye canales con este período reclasificado entre EEFF; se usa la versión más reciente de cada uno.",
     "Includes channels whose figures for this period were reclassified between filings; the latest version of each is used."),
    ("Reclasificado: los EEFF de ${rc.fecha_cierre.join(\", \")} informan este período con distinta composición. Se muestra la versión más reciente.",
     "Reclassified: the filings dated ${rc.fecha_cierre.join(\", \")} report this period with a different composition. The latest version is shown."),
    # tabla y notas
    ("Tabla de datos de la vista actual", "Data table for the current view"),
    ("<th>Período</th>", "<th>Period</th>"),
    ("Publicidad / total. R = reclasificado entre EEFF.", "Advertising / total. R = reclassified between filings."),
    ("<h3>Eventos marcados</h3>", "<h3>Marked events</h3>"),
    ("<h3>Cómo leer los agregados</h3>", "<h3>How to read the aggregates</h3>"),
    ("<li><b>4 grandes</b> y <b>6 canales CMF</b> suman los canales solo en los períodos en que todos informan. No incluyen a otras concesionarias que informan a la CMF (Canal Dos/Telecanal, RDT, TBN Enlace) ni a los canales regionales.</li>",
     "<li><b>Big 4</b> and <b>6 CMF channels</b> add up channels only in periods where all of them report. They exclude other concessionaires that report to the CMF (Canal Dos/Telecanal, RDT, TBN Enlace) and regional channels.</li>"),
    ("<li>«Solo TV» resta la publicidad radial y de cable de Mega.</li>", "<li>“TV only” removes Mega's radio and cable advertising.</li>"),
    ("<li>Referencias de Napoli: 100% (broadcast, EE.UU. c. 2001) y 60% (cable networks).</li>",
     "<li>Napoli references: 100% (US broadcast, c. 2001) and 60% (cable networks).</li>"),
    ("<h3>Fuentes y advertencias</h3>", "<h3>Sources and caveats</h3>"),
    ("<li>Montos de los EEFF en miles de pesos (M$). Cada cifra lleva documento y página.</li>",
     "<li>Amounts from the financial statements in thousands of Chilean pesos (M$). Every figure carries its document and page.</li>"),
    ("<li>$ de 2025: IPC del Banco Central (variación mensual oficial, encadenada; promedio 2025 = 100). UF y US$: promedio del período de la UF diaria y del dólar observado (Banco Central).</li>",
     "<li>2025 CLP: Central Bank of Chile CPI (official monthly change, chained; 2025 average = 100). UF and US$: period averages of the daily UF and the observed exchange rate (Central Bank).</li>"),
    ("<li>H2 = año completo − primer semestre. Si los documentos clasifican distinto, H2 puede salir negativo en alguna categoría.</li>",
     "<li>H2 = full year − first half. If the filings classify differently, a category can come out negative in H2.</li>"),
    ("<li>C13: «Otros ingresos» incluye venta de activos en 2018 (M$6.430.098) y 2020 (M$13.771.539), según la nota.</li>",
     "<li>C13: “Other revenue” includes asset sales in 2018 (M$6,430,098) and 2020 (M$13,771,539), per the note.</li>"),
    ("<li>TVN 2025: la tabla del EEFF tiene fuente corrupta; cifras del piloto validado, coinciden con la lectura OCR.</li>",
     "<li>TVN 2025: the filing's table has a corrupt font; figures come from the hand-validated pilot and match the OCR reading.</li>"),
    ("<li>Los EEFF escaneados se leyeron con OCR y cuadran línea a línea con el total.</li>",
     "<li>Scanned filings were read with OCR and reconcile line by line with the total.</li>"),
    ('const LANG = "es", LOC = "es-CL";', 'const LANG = "en", LOC = "en-US";'),
]

# palabras que delatan texto sin traducir (se buscan fuera de los datos incrustados y de los comentarios)
RESTOS = ["Publicidad", "ingresos", "Ingresos", "período", "Período", "Nivel", "Anual", "Semestral", "Descargar", "planilla",
          "Eventos marcados", "reclasificado", "Pase el cursor", "Montos", "Consolidado", "Solo TV", "Miles de millones",
          "Composición", "Participación", "Frecuencia", "Clasificación", "advertencias", "desglose", "Tabla de datos"]


def a_ingles(html):
    out = html
    for es, en in sorted(FRASES, key=lambda p: -len(p[0])):
        if es not in out:
            raise SystemExit(f"Traducción: no se encontró el texto «{es[:70]}»")
        out = out.replace(es, en)
    import json
    out = out.replace("/*__TR__*/{}", json.dumps(NOMBRES, ensure_ascii=False))
    # control de restos: solo fuera del bloque de datos, de las claves de datos y de comentarios
    visible = re.sub(r"//[^\n]*|/\*.*?\*/", "", out, flags=re.S)
    visible = re.sub(r'k: "[^"]*"|l: "[^"]*"|"[^"]*_[^"]*"', "", visible)  # claves y etiquetas (se traducen con tr)
    visible = re.sub(r"const TR = \{.*?\};", "", visible, flags=re.S)
    visible = re.sub(r'=== "[^"]*"|"(Publicidad|Otros ingresos|Otros operacionales|Otros ingresos operacionales)"', "", visible)
    restos = sorted({w for w in RESTOS if w in visible})
    if restos:
        ctx = [visible[max(0, visible.index(w) - 60): visible.index(w) + 40].replace("\n", " ") for w in restos]
        raise SystemExit("Traducción incompleta:\n" + "\n".join(f"  {w}: …{c}…" for w, c in zip(restos, ctx)))
    return out
