# Cifras pendientes de lectura manual

Ventana 2016–2025 (más el primer semestre de 2026). Generado el 1-oct-2026. Para cada caso: copiar el texto o la tabla tal como aparece (como se hizo con Canal 13 dic-2019 y TVN dic-2025). Cada cifra se registra en `revision/manual_resultados.csv` o `revision/manual_costos.csv` con su fuente y se acepta solo si cumple las mismas identidades que lo extraído.

## Se pueden completar leyendo un EEFF que ya está en `data/raw/pdf/`

| # | Canal | Período | Qué falta | Archivo | Página | Qué copiar |
|---|---|---|---|---|---|---|
| 1 | Mega | H1 2026 (y H1 2025) | Resultado | `data/raw/pdf/Mega/113710/2026090594478-1.pdf` | 11 | Estado de resultados, columnas acumuladas 01-01 a 30-06 de 2026 y 2025: ingresos, costos de ventas, ganancia bruta, gastos de administración, ganancia antes de impuestos, impuestos, ganancia. |
| 2 | La Red | H1 2026 (y H1 2025) | Resultado | `data/raw/pdf/La Red/113715/2026090587585-2.pdf` | 10 | Estado de resultados, columnas acumuladas a junio 2026 y 2025: las mismas líneas. La línea de impuesto no se leyó; la lectura automática tomó la ganancia por acción como resultado. |
| 3 | TV+ | H1 2020 y H1 2019 | Resultado | `data/raw/pdf/TV+/29825/4.pdf` | 7 | Estado de resultados a junio 2020 y 2019: ingresos de explotación, costo de explotación, margen bruto, gastos de administración, resultado antes de impuestos, impuesto, resultado del período. |
| 4 | TV+ | H1 2024 (y H1 2023) | Costo de ventas (desglose) | `data/raw/pdf/TV+/85362/2024090475132_3.pdf` | 36 | Nota «Costo de explotación», columnas a junio 2024 y junio 2023: cada línea y el total. Debe sumar el costo de explotación del estado de resultados (M$1.961.233 en H1 2024). |

## Requiere un documento que no está en la CMF

| # | Canal | Período | Qué falta | Dónde podría estar |
|---|---|---|---|---|
| 5 | La Red | Año 2018 | Desglose de ingresos | EEFF de Compañía Chilena de Televisión S.A. al 31-12-2018. La sección de concesionarias de la CMF publica dic-2017, dic-2019 y desde 2020, pero no dic-2018; y el EEFF de dic-2019 compara con 9M-2018, no con el año. Opciones: pedirlo a La Red, a la CMF (que lo recibe por el art. 18 de la Ley 18.838, vía transparencia) o al CNTV. Qué copiar: Nota de ingresos de actividades ordinarias 2018 (ingresos de operación, canje, otros ingresos de operación); el total debe ser M$5.088.103, el ingreso 2018 del estado de resultados. |

## No se pueden completar (no existe el desglose en ningún EEFF)

- **Mega 2016–2017, costo de ventas por línea:** el EEFF de dic-2017 no tiene nota de costo de ventas (pasa de ingresos ordinarios, nota 6, a gastos de administración y otras ganancias).
- **TVN H1 2016 y H1 2017, costo de ventas por línea:** los EEFF semestrales de TVN solo informan el total (por ejemplo, M$25.185.415 en H1 2017); el desglose aparece en los EEFF anuales.
- **La Red, costo de ventas por línea:** La Red no publica esa nota en ningún período.
- **TV+ 2016:** la sociedad (UCVTV SpA) empezó a operar en 2017.
