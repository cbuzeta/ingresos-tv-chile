"""Paso 4c: extrae la nota de costo de ventas con el mismo método y los mismos controles que la de ingresos.

Reutiliza src/04_extraer_nota.py cambiando qué nota se busca y qué rótulos se aceptan:
- encabezado: «Costo(s) de venta(s)», «Costos de actividades ordinarias», «Costos de explotación»;
- la tabla debe tener rótulos de costos y ninguno de ingresos o márgenes (así se descartan la tabla de
  ingresos cuando comparte nota, como en TVN, y el propio estado de resultados);
- el total debe aparecer en el estado de resultados.

Salidas: data/costos_extraidos.csv y data/costos_log.csv.
    python src/04c_extraer_costos.py                 # todos
    python src/04c_extraer_costos.py "Canal 13" 2025 # parcial
"""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("extractor", ROOT / "src" / "04_extraer_nota.py")
x = importlib.util.module_from_spec(spec)
spec.loader.exec_module(x)

x.HEAD = re.compile(r"costos? de (?:la )?(?:ventas?|explotacion|actividades ordinarias)")
x.NOTA_HEAD = re.compile(r"^\s*(?:nota|note)?\s*n?[°º]?\s*\d{1,2}[\.\-–:)\s]+.*?(" + x.HEAD.pattern + ")"
                         r"|^\s*[a-z]\)\s*(" + x.HEAD.pattern + ")")
x.RE_OK = (r"costo|produc|remunerac|derecho|material|elenco|depreciac|amortiz|servicio|program|exhib|personal|"
           r"pelicul|licenc|transmis|operac|señal|senal|contenido|mantenc|agencia|bonificac")
x.RE_NO = r"^ingres|ingresos (de|por)|ganancia|margen|utilidad|resultado|administra|deuda|largo plazo|pasivo|cobros|pagos|flujo|leasing|terrenos|edificio|acumulada|discontinu"
x.ENCABEZADO_NOTA = r"(costos? de (la )?(ventas?|explotacion|actividades ordinarias)|conceptos?)( \(.\))?"
x.SALIDA_LINEAS, x.SALIDA_LOG = "costos_extraidos.csv", "costos_log.csv"

if __name__ == "__main__":
    filtro = None
    if len(sys.argv) > 1:
        c, f = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ""
        filtro = lambda d: d["canal"] == c and d["fecha_cierre"].startswith(f)  # noqa: E731
    x.main(filtro)
