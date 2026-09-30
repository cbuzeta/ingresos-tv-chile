"""Controles externos: compara los totales de la serie con fuentes independientes.

- SEP (Sistema de Empresas Públicas), ficha de TVN: «Ingresos de actividades ordinarias» anual y
  trimestral acumulado, tal como lo publica el SEP. Se compara con todas las versiones de la base.
- AAM (contexto): inversión publicitaria neta en TV abierta (todo el mercado, sin comisión de agencia
  ni IVA) frente a la publicidad de los seis canales. No es un control: cubre más canales y otra fuente.

Salida: salidas/controles_externos.csv (fuente, canal, período, valor externo, valores de la serie, estado).
"""
import html
import re
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
SEP_TVN = "https://empresasestatales.gob.cl/informacion-por-empresa?id=33"


def filas_tabla(page):
    out = []
    for tabla in re.findall(r"<table.*?</table>", page, re.S):
        filas = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tabla, re.S):
            celdas = [html.unescape(re.sub(r"<[^>]+>", " ", c)).strip()
                      for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)]
            filas.append([re.sub(r"\s+", " ", c) for c in celdas])
        out.append(filas)
    return out


def num(c):
    c = c.replace(" ", "").replace(".", "")
    return int(c) if re.fullmatch(r"-?\d+", c) else None


def sep_tvn():
    """[(periodo, fin, valor)] del estado de resultados publicado por el SEP."""
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (investigacion academica; Universidad de los Andes, Chile)"
    page = s.get(SEP_TVN, timeout=60).text
    res = []
    for filas in filas_tabla(page):
        encabezado = next((f for f in filas if sum(bool(re.fullmatch(r"20\d\d( T[1-4])?", c)) for c in f) >= 3), None)
        ingresos = next((f for f in filas if f and f[0].startswith("Ingresos de actividades ordinarias")), None)
        if not encabezado or not ingresos:
            continue
        cols = [c for c in encabezado if re.fullmatch(r"20\d\d( T[1-4])?", c)]
        vals = [num(c) for c in ingresos[1:]]
        for col, v in zip(cols, vals[-len(cols):]):
            if v is None:
                continue
            a = col[:4]
            if " T" in col:
                t = int(col[-1])
                periodo = {1: f"Q1 {a}", 2: f"H1 {a}", 3: f"9M {a}", 4: f"FY{a}"}[t]
            else:
                periodo = f"FY{a}"
            res.append((periodo, v))
    return sorted(set(res))


def main():
    y = pd.read_csv(ROOT / "data" / "lineas_mapeadas.csv")
    tot = y.groupby(["canal", "periodo", "fecha_cierre"])["monto"].sum().reset_index()
    filas = []
    for periodo, v in sep_tvn():
        t = tot[(tot.canal == "TVN") & (tot.periodo == periodo)]
        if t.empty:
            filas.append({"fuente": "SEP", "canal": "TVN", "periodo": periodo, "valor_externo": v,
                          "valores_serie": "", "estado": "sin dato en la serie"})
            continue
        versiones = dict(zip(t.fecha_cierre, t.monto))
        coincide = [f for f, m in versiones.items() if m == v]
        estado = "coincide" if coincide else f"difiere ({min(abs(m - v) for m in versiones.values()):,} M$)"
        filas.append({"fuente": "SEP", "canal": "TVN", "periodo": periodo, "valor_externo": v,
                      "valores_serie": "; ".join(f"{f}: {m}" for f, m in versiones.items()), "estado": estado})
    # AAM (contexto, no control): inversión neta en TV abierta de todo el mercado frente a la publicidad
    # que informan los seis canales. Solo años leídos directamente de un informe de la AAM (ver el CSV).
    agg = pd.read_csv(ROOT / "salidas" / "agregados.csv")
    aam = pd.read_csv(ROOT / "data" / "externos" / "aam_tv_abierta.csv")
    for r in aam.itertuples():
        ind = agg[(agg.canal == "6 canales CMF") & (agg.periodo == f"FY{r.anio}")]
        if ind.empty:
            continue
        pub = int(ind.n1_publicidad.iloc[0])
        filas.append({"fuente": "AAM (contexto)", "canal": "6 canales CMF", "periodo": f"FY{r.anio}",
                      "valor_externo": int(r.inversion_tv_abierta_mm) * 1000, "valores_serie": f"publicidad: {pub}",
                      "estado": f"contexto: la publicidad de los 6 canales equivale al {100 * pub / (r.inversion_tv_abierta_mm * 1000):.1f}% "
                                f"de la inversión neta en TV abierta según la AAM (p. {r.pagina})"})
    out = pd.DataFrame(filas)
    out.to_csv(ROOT / "salidas" / "controles_externos.csv", index=False, encoding="utf-8")
    print(out.estado.str.split(" ").str[0].value_counts().to_string())
    for r in out[out.fuente.str.startswith("AAM")].itertuples():
        print(f"  {r.periodo}: {r.estado}")
    malos = out[~out.estado.eq("coincide") & ~out.fuente.str.startswith("AAM")]
    if len(malos):
        print(malos.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
