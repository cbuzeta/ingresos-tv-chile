# Metodología

Este documento explica cómo se construye la serie de ingresos de la TV abierta chilena, qué decisiones se tomaron y por qué, y qué límites tienen los datos. Las cifras de cobertura y control que aparecen aquí corresponden a la versión de datos del 30 de septiembre de 2026.

Contenido: [1. Pregunta y marco](#1-pregunta-y-marco) · [2. Fuentes y cobertura](#2-fuentes-y-cobertura) · [3. Extracción y controles](#3-extracción-y-controles) · [4. Versiones y reclasificaciones](#4-versiones-y-reclasificaciones) · [5. Períodos](#5-períodos) · [6. Clasificación](#6-clasificación) · [7. Decisiones por canal](#7-decisiones-por-canal) · [8. Agregados de industria](#8-agregados-de-industria) · [9. Unidades monetarias](#9-unidades-monetarias) · [10. Limitaciones](#10-limitaciones) · [11. Utilidades y costo de ventas](#11-utilidades-y-costo-de-ventas) · [12. Trazabilidad y reproducción](#12-trazabilidad-y-reproducción)

---

## 1. Pregunta y marco

¿Qué parte de los ingresos de los canales de TV abierta viene de vender audiencias a los anunciantes y qué parte de vender contenidos? La referencia es la Tabla 1.1 de Napoli (2003), *Audience Economics: Media Institutions and the Audience Marketplace* (Columbia University Press), que ubica a la TV abierta estadounidense de c. 2001 cerca del 100% de ingresos por audiencias y a las cadenas de cable en torno al 60%. Esas dos cifras se usan como referencia en la visualización.

**Comparadores actuales.** Las cifras de Napoli describen EE.UU. c. 2001. Como referencia de hoy se agrega, como punto fechado y no como línea, el de las estaciones locales de TV de EE.UU. en 2022: la publicidad over-the-air (US$20,5 mil millones, Pew Research Center con datos de BIA Advisory Services) equivale al 58,6% de la suma de esa publicidad y los derechos de retransmisión que pagan los cableoperadores (US$14.461,9 millones, proyección de Kagan/S&P publicada por Pew). Es una aproximación: combina un dato efectivo con una proyección y excluye la publicidad digital de las estaciones. Los retransmission fees son, en la práctica, venta de contenidos a los distribuidores. Las referencias viven en `data/externos/referencias/referencias.csv`, con su fuente; los informes de Ofcom (Reino Unido) y del Observatorio Audiovisual Europeo no se pudieron descargar automáticamente y quedan pendientes.

La medida principal es la **participación de la publicidad** en los ingresos de actividades ordinarias. Se mide con la información que los propios canales publican; no se estima nada que las notas no informen.

## 2. Fuentes y cobertura

**Documentos.** Estados financieros (EEFF) anuales e intermedios, bajo IFRS, publicados en la Comisión para el Mercado Financiero (CMF): sección de concesionarias de TV para los canales privados y ficha de entidad para TVN. De cada paquete se usa solo el PDF de estados financieros; el análisis razonado, las cartas y los hechos esenciales no se usan (una revisión de los análisis razonados de 2020 y 2025 no encontró desglose de ingresos adicional al de las notas).

| Canal | Sociedad informante | Años | Semestres | Documentos |
|---|---|---|---|---|
| TVN | Televisión Nacional de Chile | 2010–2025 | desde 2010 | 50 EEFF: trimestrales desde 2017, junio y diciembre 2011–2016 |
| Canal 13 | Canal 13 SpA | 2016–2025 | desde 2019 | 28 |
| Mega | Megamedia S.A., consolidado (Red Televisiva Megavisión S.A. en los EEFF 2017 y 2019) | 2016–2025 | desde 2019 | 28 |
| Chilevisión | Red de Televisión Chilevisión S.A. | 2016–2025 | desde 2019 | 28 |
| La Red | Compañía Chilena de Televisión S.A. | 2016–2025 | desde 2019 | 28 |
| TV+ | TVMAS SpA (UCVTV SpA en 2017) | 2017–2025 | desde 2019 | 28 |

Se incluye además el primer semestre de 2026. TVN se extiende hasta 2010 con los EEFF de junio y diciembre 2011–2016 de su ficha en la CMF (el de diciembre 2011 trae 2010 como comparativo); queda fuera del panel balanceado de los agregados, que parten en 2016. Para los privados, la CMF publica el EEFF de diciembre de 2017 (que trae 2016 como comparativo), el de diciembre de 2019 (que trae 2018) y todos los trimestres desde marzo de 2020. Por eso los años 2016 y 2018 salen de comparativos y los semestres parten en 2019. TVN publica todos los trimestres desde 2017.

**Perímetro.** Mega se mide consolidado (incluye radios y cable); la visualización ofrece además la variante «solo TV», que resta la publicidad radial y de cable. Los estados individuales de Megamedia (anexos del Oficio Circular 498) no traen desglose de ingresos y no se usan.

**Moneda de origen.** Miles de pesos chilenos nominales (M$), tal como vienen en los EEFF.

## 3. Extracción y controles

**Identificación del documento.** Los nombres de archivo de la CMF no identifican el contenido. Cada PDF se clasifica leyendo sus primeras páginas: sociedad, fecha de cierre (la más reciente de fin de trimestre que aparece en la portada) y tipo de documento. Se exige exactamente un EEFF por canal y fecha. Dos paquetes traían dos copias del EEFF (Canal 13 junio 2022 y Mega septiembre 2023); se verificó que informan cifras idénticas y se usa una.

**Extracción de la nota.** Se busca la nota «Ingresos de actividades ordinarias» (su número cambia según canal y año) y se lee con varias fuentes de texto, en este orden, hasta que una pasa los controles: texto del PDF por filas (pdfplumber), pdftotext con diagramación, pdftotext sin diagramación, lectura por coordenadas (para tablas con celdas vacías) y reconocimiento óptico de caracteres (OCR, Tesseract en español, a 300 y a 400 ppp) para los EEFF escaneados o con fuentes ilegibles.

**Controles obligatorios.** Una tabla solo se acepta si:
1. En **cada columna**, la suma de las líneas es igual a la fila de total (autocontrol aritmético). Se acepta una diferencia de hasta M$2 solo cuando está en la fuente; ocurrió en 4 documentos (Chilevisión septiembre 2021 y junio 2023; TV+ marzo 2022 y marzo 2023) y queda registrada en el log.
2. Sus rótulos son de ingresos (se descartan tablas con costos, gastos o márgenes, como el propio estado de resultados).
3. El total (actual o comparativo) aparece como número completo en el estado de resultados.
4. Las columnas se asignan a períodos según las fechas del encabezado cuando están (escritas con guion, barra o punto); si no, según el tipo de EEFF (anual, trimestral). El encabezado manda sobre el supuesto: así se detectó que el EEFF de diciembre 2019 de La Red compara con los nueve meses a septiembre de 2018 («30.09.2018») y no con el año 2018. La Red no tiene, por eso, desglose de ingresos para el año 2018 completo (la CMF no publica su EEFF de diciembre 2018); su ingreso total 2018 según el estado de resultados fue M$5.088.103.

**Controles externos** (`src/07_controles_externos.py`, resultado en `salidas/controles_externos.csv`):
- **SEP.** El Sistema de Empresas Públicas publica los ingresos de actividades ordinarias de TVN (anual 2018–2024 y trimestral acumulado hasta septiembre 2025). Los 31 valores coinciden exactamente con la serie.
- **AAM (contexto).** La inversión publicitaria neta en TV abierta según la Asociación de Agencias de Medios (sin comisión de agencia ni IVA, todos los canales) fue de MM$228.097 en 2024 y MM$229.782 en 2025 (informe de diciembre 2025, pp. 19 y 18). La publicidad que informan los seis canales equivale al 104,7% y al 105,4% de esas cifras. No se espera que coincidan: la publicidad de los canales incluye digital (Canal 13), radio y cable (Mega) y la comisión por TV pagada (Chilevisión), y la AAM cubre a todos los canales de TV abierta. Solo se usan años leídos directamente de un informe de la AAM (`data/externos/aam_tv_abierta.csv`).

Además, la serie reproduce exactamente los **48 montos validados a mano** en el piloto (`piloto/semilla_lineas_validadas.csv`), y al agregar fuentes de lectura nuevas se comparó la extracción completa contra la anterior (ninguna diferencia en los cuatro canales grandes).

**Resultado.** De 178 EEFF distintos por canal y fecha, 177 se extrajeron con todos los controles. Casos especiales:
- **Mega, marzo 2024**: la nota tiene una errata (las líneas suman 21.238.409 y el total, igual al del estado de resultados, es 21.238.459). No se corrige; el primer trimestre de 2024 se toma del comparativo del EEFF de marzo 2025.
- **Chilevisión, diciembre 2021**: la tabla cuadra, pero el estado de resultados está escaneado y el total no se pudo leer ahí. El total 2021 se confirma con el comparativo del EEFF de diciembre 2022.
- **TVN, diciembre 2025**: la tabla de la nota tiene la fuente corrupta. Las cifras vienen del piloto validado a mano (reconstruidas con el análisis razonado y los comparativos) y están en `revision/manual_lineas.csv`; la lectura por OCR coincide.
- 17 documentos se leyeron con OCR. Que las líneas sumen el total en todas las columnas es el principal resguardo contra errores de lectura.

## 4. Versiones y reclasificaciones

Cada período aparece en al menos dos documentos: el EEFF del período y el del año siguiente, como comparativo. Se guardan **todas las versiones**, con su documento de origen. La **serie principal usa la versión más reciente** de cada período, porque incorpora reclasificaciones y reexpresiones posteriores; las versiones originales quedan en la base para análisis de sensibilidad.

Un período se marca como **reclasificado** cuando dos documentos informan distintos totales por categoría. Un simple cambio de rótulo, o una apertura más fina de la misma categoría, no cuenta. Hay 42 canal-períodos reclasificados (Canal 13: 15, Chilevisión: 14, TVN: 8, TV+: 5). En la visualización aparecen con un círculo hueco y se detallan en la hoja «versiones» de la planilla. Ejemplo documentado: el primer semestre de 2025 de Chilevisión se informa como publicidad 31.256.166 y nuevos negocios 3.970.381 en el EEFF de septiembre 2025, y como 33.494.199 y 1.732.348 en el de junio 2026, con el mismo total.

## 5. Períodos

- **Anual** (enero–diciembre) es la serie núcleo.
- **Primer semestre (H1)** se toma tal como viene en los EEFF de junio.
- **Segundo semestre (H2)** se deriva como anual − H1. Si el EEFF anual y el semestral clasifican distinto, alguna categoría de H2 puede salir negativa (ocurre en Canal 13 2019, Chilevisión 2023 y TV+ 2019; y en Nivel 4 en Canal 13 2020, porque el EEFF de junio 2021 informa para el primer semestre de 2020 más publicidad digital, M$4.393.823, que el de diciembre 2021 para todo el año, M$2.956.968). Se muestra en la visualización con una advertencia.
- Los trimestres y el acumulado a septiembre se extraen y quedan en la base, pero no son foco del análisis.

## 6. Clasificación

La clasificación es jerárquica: cada nivel está anidado en el anterior y, en cada canal y período, la suma de las categorías de cualquier nivel es igual al total de ingresos. Cada línea de nota se clasifica una sola vez en `mapeo/lineas_mapeo.csv`, con su justificación y fecha de aprobación. El proceso se detiene si aparece una línea sin clasificar; nunca se asigna una categoría por similitud. El listado completo está en el [anexo de mapeo](METODOLOGIA_anexo_mapeo.md).

**Principio.** Lo que un canal no informa queda como «sin desglose». No se reparte con supuestos, aunque haya información cualitativa (por ejemplo, que «otros ingresos» de TVN son «principalmente» venta de señal internacional).

| Nivel | Categorías | Criterio |
|---|---|---|
| 1 | Publicidad · Otros ingresos | Publicidad = toda línea que vende espacio publicitario. Cuando el rótulo no dice «publicidad», se usa la política contable del canal (La Red, TV+) |
| 2 | Publicidad · Otros ingresos operacionales · Transferencias del Estado | Separa la subvención NTV de TVN (desde 2025) |
| 3 | Publicidad TV y digital · Publicidad en otros medios · Arriendo de pantalla · Contenidos y señales · Otros ingresos · Venta de activos · Transferencias del Estado | Agrupa por tipo de negocio |
| 4 | Publicidad TV abierta · Publicidad digital · Publicidad TV + digital (sin desglose) · Canje (publicidad en especie) · Publicidad radio y cable · Comisión publicidad TV paga · Arriendo de pantalla · Contenidos y señales (nacional / extranjero / sin desglose geográfico) · Eventos · Arriendos y servicios · Otros sin desglose · Venta de activos · Transferencias del Estado | Máximo detalle que permiten las notas |

En Nivel 4 la categoría «Otros sin desglose» (Canal 13, Chilevisión, TVN y TV+) representa el 14,1% de los ingresos de los seis canales en 2025. Es la parte de la industria que las notas no permiten clasificar.

**Codificación Napoli con rangos.** La base conserva además una codificación de cada línea como Audiencias, Contenidos o Fuera de Napoli, pura o mixta, con piso y techo por período (columnas `A_*`, `C_*`, `F_*` en `salidas/agregados.csv` y hoja «Napoli» de la planilla). No se usa en la visualización porque, con el nivel de desglose disponible, los rangos resultan demasiado amplios para ser informativos.

## 7. Decisiones por canal

**TVN**
- Hasta marzo 2018 informa «Publicidad en televisión abierta e internet» (Nivel 4: TV + digital sin desglose); desde entonces, «Publicidad en televisión abierta».
- «Otros ingresos» es, según la nota, principalmente venta de señal internacional a operadores de TV pagada y otros servicios: se clasifica como Otros sin desglose.
- La subvención estatal para NTV (Ley 19.132, art. 37) se registra siempre como línea propia (Transferencias del Estado), aunque el EEFF de diciembre 2025 la incluye dentro de «Otros ingresos» (M$2.000.000).

**Canal 13**
- Hasta 2018 informa una sola línea de publicidad (Nivel 4: TV + digital sin desglose); desde 2019 separa pantalla abierta y otras plataformas (digital).
- «Otros ingresos de explotación» incluye, según la nota, cableoperadores, digital no publicitario, nuevas señales, venta de contenidos, venta de activos y arriendos: Otros sin desglose.
- **Venta de activos.** Cuando la nota informa el monto, se separa como línea propia (Nivel 3 y 4: Venta de activos): 2018, M$6.430.098 (equipos a Secuoya Chile SpA, M$5.376.862, y 11 torres a Torres Unidas, M$1.053.236); 2020, M$13.771.539 (propiedades, planta y equipo). En Niveles 1 y 2 sigue dentro de otros ingresos. El primer y el segundo trimestre de 2020 no se ajustan porque la nota no informa en qué trimestre ocurrió la venta. Detalle, documento y página en `mapeo/desgloses_nota.csv`.

**Mega**
- Los EEFF de diciembre 2017 y diciembre 2019 los emite Red Televisiva Megavisión S.A. y subsidiarias; en 2020 la sociedad informante pasa a ser Megamedia S.A. El año 2019 informado en ambos casos (EEFF de diciembre 2019 y comparativo del de diciembre 2020) coincide en todas las categorías, por lo que la serie se trata como continua.
- Cambio de rótulos en 2025: «Ingresos por otros negocios» pasa a «ventas en plataformas y contenidos» y «propios de subsidiarias» a «publicidad radial y cable»; los montos de 2024 coinciden en ambas versiones.
- «Ingresos por publicidad de televisión e internet» no separa TV de internet: Nivel 4 TV + digital sin desglose.
- 2016–2017: «Ingresos radiales y otros» se clasifica como publicidad en radio y cable.
- **Ventas nacionales y al extranjero.** La nota 7 b (desde 2018) divide cada línea por mercado geográfico. Como su diagramación cambia entre años, no se lee por posición: para cada monto de la nota 7 a se busca el único par (nacional, extranjero) de la nota 7 b que lo suma exactamente, y se verifica contra la columna de total. Así se obtienen las ventas de contenidos al extranjero (Nivel 4).

**Chilevisión**
- «Ingresos por publicidad» incluye, según la nota, TV abierta y comisión por TV pagada.
- 2019–2022 informa aparte la «Comisión Publicidad TV (TILA)», una comisión fija sobre las ventas de publicidad de Turner International Latin America en TV pagada (Nivel 4: Comisión publicidad TV paga). **Desde 2023 esa comisión va dentro de «Ingresos por publicidad»**, que en Nivel 4 es Publicidad TV abierta: hay un quiebre de serie, marcado en la visualización.
- «Ingresos nuevos negocios» mezcla, según la política contable, publicidad por internet, venta de señales y licencias, fee de administración y concursos: Otros sin desglose.
- «Eventos y espectáculos» (hasta septiembre 2024): Otros ingresos, Eventos.
- Cambios de controlador (Paramount/ViacomCBS en 2021, Vytal Group en 2026) coinciden con reclasificaciones; se marcan como eventos.

**La Red**
- Ningún rótulo dice «publicidad». La política contable define los ingresos como «venta de publicidad exhibida y de material envasado», y la nota identifica la línea «Otros ingresos de operación» como venta de material envasado. Por eso «Ingresos de operación» se clasifica como Publicidad TV abierta, el «canje» como publicidad en especie y el material envasado como Contenidos y señales (sin desglose geográfico: la nota dice «dentro y fuera del país» sin montos).

**TV+**
- 2017 corresponde a UCVTV SpA, que inició operaciones en el tercer trimestre de ese año (una sola línea, «Ventas Televisión»).
- La política contable define el ingreso como «el importe total de la publicidad exhibida». «Ventas de publicidad», «Ventas de TV» y sus variantes: Publicidad TV abierta.
- **Arriendo de pantalla.** «Venta/arriendo de infomerciales» y «espacio de transmisión» son venta de bloques de pantalla a terceros. Los EEFF anuales los informan juntos, así que llevan el mismo código: Otros ingresos (Nivel 1 y 2), Arriendo de pantalla (Nivel 3 y 4). Fueron cerca de la mitad de los ingresos de TV+ en 2018–2019 (lo que explica su baja participación de publicidad esos años) y entre 21% y 30% desde 2020.
- «Canje» y las ventas con VTR (el balance registra «Canje VTR por facturar»): publicidad en especie.
- «Arriendo de estudios» y «servicios de administración»: Arriendos y servicios. «Otros negocios», sin definición en las notas: Otros sin desglose.
- Varios rótulos aparecen con errores de tipeo en los EEFF («Ventasdepublicidad», «Espaciodetransmisión»); cada variante se clasifica explícitamente en el mapeo.

**Norma contable.** IFRS 15 (2018) pudo cambiar el tratamiento de comisiones de agencia y canjes; 2017→2018 se marca como posible quiebre. IFRS 16 (2019) no afecta los ingresos.

## 8. Agregados de industria

- **4 grandes**: TVN, Canal 13, Mega y Chilevisión (desde 2016).
- **6 canales CMF** («Industria» en la visualización): los anteriores más La Red y TV+ (desde 2017).

Un agregado se calcula solo en los períodos en que todos sus canales informan (panel balanceado) y suma montos, así que la participación de publicidad está ponderada por el tamaño de cada canal. No incluye a otras tres concesionarias que también informan a la CMF (Canal Dos S.A., que opera Telecanal; RDT S.A.; y TBN Enlace Chile S.A.) ni a los canales regionales y locales que no informan, por lo que es un agregado de los seis canales de la muestra y no del mercado completo. En 2025 los 4 grandes son el 98,5% de los ingresos de los seis.

## 9. Unidades monetarias

Todas las series del Banco Central de Chile (Base de Datos Estadísticos, «Indicadores diarios»), descargadas con `src/00_externos.py`:
- **$ nominales**: montos de los EEFF.
- **$ de 2025**: IPC general. El Banco Central publica la variación mensual con un decimal; esas variaciones se encadenan en un índice con promedio 2025 = 100, y cada período se deflacta con el promedio del índice en sus meses. El redondeo a un decimal introduce un error acumulado pequeño.
- **UF**: promedio de la UF diaria del período.
- **US$**: promedio del dólar observado diario del período.

Los porcentajes no dependen de la unidad.

## 10. Limitaciones

- **Ingresos de los canales frente a inversión del mercado.** Los canales informan ingresos netos de comisiones de agencia; la AAM también mide inversión neta (sin comisión ni IVA), pero de todos los canales y solo de TV abierta, así que sirve como orden de magnitud y no como control (ver sección 3).
- **El desglose depende de cada canal.** La digital solo se puede separar en Canal 13 desde 2019; en Mega queda mezclada con TV. Una parte relevante de los ingresos (14,1% en 2025) no se puede clasificar más allá de «otros».
- **Reclasificaciones sin nota explicativa.** Varios canales mueven montos entre líneas de un documento a otro sin explicarlo. La serie principal usa la versión más reciente, pero la historia de cada canal puede no ser homogénea en su interior.
- **Quiebres de serie.** Cambios de rótulo (Mega 2025), de sociedad informante (Mega 2020), de perímetro de líneas (Chilevisión 2023) y de norma (IFRS 15, 2018).
- **Canje.** Solo La Red y TV+ informan el canje por separado; en los demás canales, si existe, va dentro de publicidad.
- **Cobertura.** 2016 y 2018 provienen de comparativos; los privados no tienen semestres antes de 2019.

## 11. Utilidades y costo de ventas

**Utilidades** (`src/04d_extraer_resultados.py`). Del estado de resultados de cada EEFF se leen siete líneas: ingresos, costo de ventas, ganancia bruta, gastos de administración, resultado antes de impuestos, impuesto y resultado del ejercicio. Una lectura se acepta solo si, en cada columna, ingresos + costo de ventas = ganancia bruta y resultado antes de impuestos + impuesto = resultado (±M$2), y si los ingresos son iguales al total de la nota de ingresos ya extraída; esa coincidencia también asigna el período de cada columna. 157 de 187 EEFF pasan los tres controles. El resultado anual está disponible para TVN 2010–2024, Canal 13 y La Red 2016–2025 (sin 2018), y Chilevisión, Mega y TV+ 2018–2025. Faltan sobre todo los EEFF escaneados de 2017 y el de TVN de diciembre 2025 (fuente corrupta). No se calcula un «resultado operacional» común, porque los canales no lo presentan igual (Mega no lo presenta).

**Casos acotados.** En algunos EEFF escaneados el OCR pierde una línea; se aceptan solo con controles equivalentes y quedan marcados en la columna `control` de `data/resultados.csv`: «ingresos derivados» (ganancia bruta − costo, que debe igualar el total de la nota de ingresos; Chilevisión 2016–2017, Canal 13 y TVN en algunos semestres), «impuesto no leído» (el resultado debe tener el signo del resultado antes de impuestos y estar entre 0,3 y 1,7 veces ese monto; Mega 2016–2017) y «sin total de nota» (La Red 2018: la nota compara con 9M-2018, pero el estado de resultados con el año; se exigen las dos identidades). Se rechazan los EEFF en que falta el impuesto y el resultado es idéntico al resultado antes de impuestos en todas las columnas, porque indica que se leyó dos veces la misma línea.

**Ventana de la visualización.** Los gráficos muestran 2016–2025 (más el primer semestre de 2026), el período común a los seis canales. Quedan sin dato, y se marcan «s/d»: el desglose de ingresos de La Red 2018 (no hay EEFF que lo informe), el resultado y los costos de Canal 13 2018 (el escaneo de su EEFF de diciembre 2019 no se lee con confianza) y el resultado de TVN 2025 (fuente corrupta; llegará como comparativo en el EEFF de diciembre 2026). TV+ empieza en 2017 porque la sociedad empezó a operar ese año. TVN 2010–2015 y los años anteriores a 2016 quedan en la planilla y en `salidas/agregados.csv`.

**Costo de ventas** (`src/04c_extraer_costos.py`). La nota de costo de ventas se extrae con el mismo método y controles que la de ingresos. Además, su total debe ser igual al costo de ventas del estado de resultados del mismo EEFF: 336 totales coinciden, 71 no tienen estado de resultados extraído para comparar y 8 difieren (5 EEFF), que se descartan porque correspondían a otras tablas que también sumaban. La Red no publica una nota de costo de ventas. TVN no la desglosa antes de 2016.

Cada línea se clasifica en siete categorías (`mapeo/costos_mapeo.csv`, aprobadas el 30-sep-2026): Contenidos y producción, Personal, Depreciación y amortización, Comercialización de audiencias (comisiones de agencia, medición y verificación publicitaria), Técnica y transmisión, Canje y Otros costos. Los canales desglosan de forma muy distinta (TVN y Mega por naturaleza del gasto; Chilevisión por tipo de contenido), así que la comparación entre canales es gruesa. En Canal 13, «Costos de publicidad exhibida» (86,3% de su costo de ventas en 2025) se clasifica como Contenidos y producción: corresponde al costo de la programación exhibida.

## 12. Trazabilidad y reproducción

Cada monto de la base (`salidas/lineas_larga.csv`, `data/ingresos.sqlite`) registra el documento de origen, la página, la fuente de lectura (texto u OCR) y si es extraído, manual o desglose de nota. Los PDF originales no están en el repositorio; `data/manifest.csv` lista cada paquete con su número de artículo en la CMF y su hash SHA-256. Los pasos para reconstruir la base están en el [README](README.md).

Registro de decisiones: `CLAUDE.md` (sección 6) y la columna de justificación de `mapeo/lineas_mapeo.csv`.
