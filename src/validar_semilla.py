"""Control: la base reproduce exactamente los montos de piloto/semilla_lineas_validadas.csv.

Compara contra data/lineas_mapeadas.csv (paso 5), usando el documento que cita la semilla
(p. ej. "EEFF Canal 13 SpA jun-2026" -> documento con cierre 2026-06-30).
Salida: revision/validacion_semilla.csv
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from pdftexto import norm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MES = {"mar": "03", "jun": "06", "sep": "09", "dic": "12"}
FIN = {"03": "31", "06": "30", "09": "30", "12": "31"}


def linea_norm(s):
    s = re.sub(r"\((\d|[a-z])\)", "", norm(str(s)))
    return re.sub(r"\s+", " ", s).strip(" .:*")


def main():
    s = pd.read_csv(ROOT / "piloto" / "semilla_lineas_validadas.csv")
    m = s["documento"].str.extract(r"(mar|jun|sep|dic)-(\d{4})")
    s["fecha_cierre"] = m[1] + "-" + m[0].map(MES) + "-" + m[0].map(MES).map(FIN)
    s["linea_norm"] = s["linea_original"].map(linea_norm)
    b = pd.read_csv(ROOT / "data" / "lineas_mapeadas.csv", dtype={"monto": int})
    # la semilla usa el rótulo vigente; la base puede traer el rótulo antiguo: se compara por categoría y medio
    clave = ["canal", "periodo", "fecha_cierre", "nivel2", "napoli_principal", "medio"]
    agg = b.groupby(clave, as_index=False).agg(monto_base=("monto", "sum"),
                                                lineas_base=("linea_original", " | ".join),
                                                origen=("origen_cifra", "first"))
    r = s.merge(agg, on=clave, how="left")
    r["ok"] = r["monto_miles_clp"] == r["monto_base"]
    out = r[["canal", "periodo", "fecha_cierre", "linea_original", "monto_miles_clp", "monto_base", "lineas_base",
             "origen", "ok"]]
    out.to_csv(ROOT / "revision" / "validacion_semilla.csv", index=False, encoding="utf-8")
    print(f"Semilla: {out.ok.sum()}/{len(out)} montos reproducidos exactamente")
    if not out.ok.all():
        print(out[~out.ok].to_string())
    return out.ok.all()


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
