"""Series externas del Banco Central de Chile (BDE, Indicadores diarios), para expresar montos comparables.

- IPC general, variación mensual (% c/r al período anterior, 1 decimal): se encadena en un índice.
- UF diaria (valor en $): se promedia por período.
- Dólar observado diario (CLP por USD): se promedia por período.

Salida: data/externos/bcch_ipc_var.csv, bcch_uf.csv, bcch_dolar.csv (fecha, valor), más el HTML crudo.
Descargas con pausas; no se vuelve a bajar lo que ya existe salvo el año en curso.
"""
import html
import re
import time
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "externos"
BASE = "https://si3.bcentral.cl/Indicadoressiete/secure/Serie.aspx"
SERIES = {
    "ipc_var": ("IPC", "UQBSAEYAYwAxAFIARABYADAALQBqAHAAWABKAHEAcQBzAHAAQgB4ADcATwBHAGIAMgBfAEwATgBOAHIAWQA1ACMAZwBsAC4AeABtAEwATQBsAHcAdQBvAGQARwBQAGUARQBvAG0ASwB4AEQAbABTAGgARgAxAGUAQgBxAHkAcwA5AG8ARQAzAGgAMQBPAFQARgBSAEwASABZAE0ARgBKAFoAMwBmAHYATgBoAGMANQBpAE8ANwBFAGMAJAA="),
    "dolar": ("PRE_TCO", "RABmAFYAWQB3AGYAaQBuAEkALQAzADUAbgBNAGgAaAAkADUAVwBQAC4AbQBYADAARwBOAGUAYwBjACMAQQBaAHAARgBhAGcAUABTAGUAdwA1ADQAMQA0AE0AawBLAF8AdQBDACQASABzAG0AXwA2AHQAawBvAFcAZwBKAEwAegBzAF8AbgBMAHIAYgBDAC4ARQA3AFUAVwB4AFIAWQBhAEEAOABkAHkAZwAxAEEARAA="),
    "uf": ("UF", "RABmAFYAWQB3AGYAaQBuAEkALQAzADUAbgBNAGgAaAAkADUAVwBQAC4AbQBYADAARwBOAGUAYwBjACMAQQBaAHAARgBhAGcAUABTAGUAYwBsAEMAMQA0AE0AawBLAF8AdQBDACQASABzAG0AXwA2AHQAawBvAFcAZwBKAEwAegBzAF8AbgBMAHIAYgBDAC4ARQA3AFUAVwB4AFIAWQBhAEEAOABkAHkAZwAxAEEARAA="),
}
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
         "Noviembre", "Diciembre"]
ANIOS = range(2015, date.today().year + 1)


def num(s):
    s = s.strip().replace(".", "").replace(",", ".")
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else None


def celdas(page):
    """Filas de la grilla: lista de listas de textos de celda."""
    filas = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        tds = [html.unescape(re.sub(r"<[^>]+>", "", td)).strip() for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if tds:
            filas.append(tds)
    return filas


def hidden(page):
    return {k: html.unescape(v) for k, v in re.findall(r'name="(__[A-Z]+)"[^>]*value="([^"]*)"', page)}


def diaria(nombre, gcode, param, s):
    """Grilla de un año: filas = día, columnas = meses. Se pide cada año con el selector DrDwnFechas."""
    url = f"{BASE}?gcode={gcode}&param={param}"
    first = s.get(url, timeout=60).text
    rows = []
    for anio in ANIOS:
        raw = OUT / f"bcch_{nombre}_{anio}.html"
        if raw.exists() and anio < date.today().year:
            page = raw.read_text(encoding="utf-8")
        elif anio == date.today().year:  # el año en curso viene en la página por defecto; el POST lo devuelve vacío
            page = first
            raw.write_text(page, encoding="utf-8")
        else:
            data = {**hidden(first), "__EVENTTARGET": "DrDwnFechas", "__EVENTARGUMENT": "", "DrDwnFechas": str(anio)}
            page = s.post(url, data=data, timeout=60).text
            raw.write_text(page, encoding="utf-8")
            time.sleep(2)
        for f in celdas(page):
            if len(f) == 13 and re.fullmatch(r"\d{1,2}", f[0]):
                for m, v in enumerate(f[1:], start=1):
                    x = num(v)
                    if x is not None:
                        rows.append((f"{anio}-{m:02d}-{int(f[0]):02d}", x))
    return rows


def ipc(s):
    gcode, param = SERIES["ipc_var"]
    page = s.get(f"{BASE}?gcode={gcode}&param={param}", timeout=60).text
    (OUT / "bcch_ipc_var.html").write_text(page, encoding="utf-8")
    rows = []
    for f in celdas(page):
        if len(f) == 13 and re.fullmatch(r"\d{4}", f[0]) and int(f[0]) >= 2009:
            for m, v in enumerate(f[1:], start=1):
                x = num(v)
                if x is not None:
                    rows.append((f"{f[0]}-{m:02d}", x))
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (investigacion academica; U. de los Andes)"
    for nombre, rows in (("ipc_var", ipc(s)),
                         ("uf", diaria("uf", *SERIES["uf"], s)),
                         ("dolar", diaria("dolar", *SERIES["dolar"], s))):
        rows = sorted(set(rows))
        (OUT / f"bcch_{nombre}.csv").write_text("fecha,valor\n" + "\n".join(f"{a},{b}" for a, b in rows) + "\n",
                                                 encoding="utf-8")
        print(nombre, len(rows), rows[0] if rows else None, rows[-1] if rows else None)


if __name__ == "__main__":
    main()
