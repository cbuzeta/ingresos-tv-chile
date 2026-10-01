"""Paso 4d: líneas principales del estado de resultados (utilidades) de cada EEFF.

Se leen siete líneas: ingresos, costo de ventas, ganancia bruta, gastos de administración, resultado antes
de impuestos, impuesto y resultado del ejercicio. Solo se acepta una lectura si cumple, en cada columna:
  1. ingresos + costo de ventas = ganancia bruta (±M$2)
  2. resultado antes de impuestos + impuesto = resultado del ejercicio (±M$2)
  3. los ingresos son iguales al total de la nota de ingresos ya extraída (paso 4) para algún período;
     esa coincidencia también asigna el período de cada columna, sin depender del encabezado.
La página es la del estado de resultados donde el paso 4 encontró el total (data/extraccion_log.csv).

Salida: data/resultados.csv y revision/resultados.csv (documentos que no pasan los controles).
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("extractor", ROOT / "src" / "04_extraer_nota.py")
x = importlib.util.module_from_spec(spec)
spec.loader.exec_module(x)
norm, split_line = x.norm, x.split_line

FILAS = [  # (campo, patrón del rótulo normalizado); se buscan en este orden, cada una después de la anterior
    ("ingresos", r"^ingresos (de|por) actividades ordinarias|^ingresos (de|por) explotacion|^ingresos ordinarios"),
    ("costo_ventas", r"^costos? de (la )?(ventas?|explotacion|actividades ordinarias)|^costo de venta"),
    ("ganancia_bruta", r"^(ganancia|perdida|margen|resultado|utilidad)( \(perdida\))? brut"),
    ("gastos_admin", r"^gastos? de administracion"),
    ("antes_impuestos", r"antes de impuesto"),
    ("impuesto", r"impuesto"),
    ("resultado", r"^(\(?perdida\)?|\(?ganancia\)?|resultado del (ejercicio|periodo)|utilidad|ganancia \(perdida\)|perdida \(ganancia\))"),
]


def limpiar(lines):
    """Arregla problemas de diagramación frecuentes en los estados de resultados."""
    out = []
    for l in lines:
        # "( 6 . 8 7 9)" -> "(6.879)"
        l = re.sub(r"\(\s*((?:\d\s*[.\s]\s*){2,}\d)\s*\)", lambda m: "(" + re.sub(r"\s", "", m.group(1)) + ")", l)
        # referencias a notas con letra, "(11 b)" o "(23a)": no son montos
        l = re.sub(r"\(\s*\d{1,2}\s*[a-z]\s*\)", " ", l)
        # "( 20)": número de nota con espacio interior (un monto negativo no se escribe así)
        l = re.sub(r"\(\s+\d{1,2}\s*\)", " ", l)
        out.append(l)
    # rótulos partidos: "Ganancia (pérdida), antes de" + "impuestos (11.919.758) ..." -> una sola línea
    unidas, i = [], 0
    while i < len(out):
        lab, vals = split_line(out[i])
        if not vals and i + 1 < len(out):
            lab2, vals2 = split_line(out[i + 1])
            if vals2 and re.match(r"^[a-záéíóúñ]", lab2.strip()):
                unidas.append(out[i].rstrip() + " " + out[i + 1].lstrip())
                i += 2
                continue
        unidas.append(out[i])
        i += 1
    return unidas


def fuentes(pdf, p, npag):
    """El estado de resultados puede seguir en la página siguiente: se leen p y p+1."""
    rng = [q for q in (p, p + 1) if q <= npag]
    with pdfplumber.open(pdf) as d:
        yield "pdfplumber", "\n".join(d.pages[q - 1].extract_text() or "" for q in rng).splitlines()
    yield "pdftotext-layout", "\n".join(x.texto_pagina(pdf, q) for q in rng).splitlines()
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", "-raw", "-f", str(p), "-l", str(rng[-1]), pdf, "-"],
                       capture_output=True)
    yield "pdftotext-raw", r.stdout.decode("utf-8", "ignore").splitlines()
    for dpi, psm in ((300, 6), (400, 4)):
        t = "\n".join(x.ocr_pagina(pdf, q, dpi, psm) for q in rng)
        yield f"ocr{dpi}", re.sub(r"(?<=\d),(?=\d{3}\b)", ".", t).splitlines()


# Si no hay línea «antes de impuestos» (p. ej. TV+ la rotula «Pérdida del periodo»), se toma la primera línea de
# resultado que viene antes del impuesto; la identidad antes + impuesto = resultado sigue exigiéndose.
ANTES_ALT = r"^(\(?perdida\)?|\(?ganancia\)?|resultado|utilidad)\b"


def leer(lines):
    """Dict campo -> lista de montos, respetando el orden de las filas. None si falta alguna obligatoria."""
    lines = limpiar(lines)
    v = _leer(lines, FILAS)
    if v is None:
        alt = [(c, ANTES_ALT if c == "antes_impuestos" else p) for c, p in FILAS]
        v = _leer(lines, alt)
    return v


def _leer(lines, filas):
    out, desde = {}, 0
    parsed = [split_line(l) for l in lines]
    for campo, pat in filas:
        for i in range(desde, len(parsed)):
            lab, vals = parsed[i]
            ln = norm(lab).strip(" -:")
            if campo == "impuesto" and "antes" in ln:
                continue
            if re.search(pat, ln) and vals:
                out[campo] = vals
                desde = i + 1
                break
        else:
            # gastos de administración: no todos los canales la rotulan así. Ingresos e impuesto: el OCR de algunos
            # EEFF escaneados pierde la línea; se resuelve con controles más estrictos en controlar().
            if campo not in ("gastos_admin", "ingresos", "impuesto"):
                return None
    # Operaciones discontinuadas (C13 2019: venta de las radios): la primera línea de resultado después del impuesto es
    # el resultado de operaciones continuadas; el resultado del ejercicio es la siguiente «Ganancia (pérdida)», después
    # de la línea de discontinuadas. Se guardan ambos y se exige continuadas + discontinuadas = resultado.
    for i in range(desde, min(desde + 8, len(parsed))):
        lab, vals = parsed[i]
        if "discontinu" in norm(lab) and vals:
            for j in range(i + 1, min(i + 10, len(parsed))):
                lab2, vals2 = parsed[j]
                ln2 = norm(lab2).strip(" -:")
                if re.match(r"^\(?(ganancia|perdida)", ln2) and "atribuible" not in ln2 and vals2:
                    out["resultado_continuadas"], out["discontinuadas"], out["resultado"] = out["resultado"], vals, vals2
                    break
            break
    return out


def controlar(v, totales, fecha_cierre):
    """Columnas válidas: [(indice_columna, periodo, control)] según las identidades y los totales de la nota.

    control = "completo" si pasan los tres controles. Casos acotados, siempre con al menos dos controles:
    - "ingresos derivados": el OCR perdió la línea; ingresos = ganancia bruta − costo, y debe igualar el total de la nota.
    - "impuesto no leído": el OCR perdió la línea; se exige ingresos + costo = ganancia bruta y el total de la nota.
    - "sin total de nota": columna comparativa anual de un EEFF de diciembre cuyo período no está en la nota de ingresos
      (La Red dic-2019 compara con 9M-2018 en la nota, pero con el año 2018 en el estado de resultados); se exigen las
      dos identidades completas y que la otra columna sí coincida con la nota.
    """
    k = len(v["costo_ventas"])
    flags = []
    if "ingresos" not in v:
        if len(v["ganancia_bruta"]) != k:
            return None, "distinto número de columnas entre filas"
        v["ingresos"] = [b - c for b, c in zip(v["ganancia_bruta"], v["costo_ventas"])]
        flags.append("ingresos derivados")
    if "impuesto" not in v:
        flags.append("impuesto no leído")
    for c in v:  # una fila de puros guiones ("- - -") vale cero en todas las columnas, aunque falte un guion
        if len(v[c]) < k and all(n == 0 for n in v[c]):
            v[c] = [0] * k
    if any(len(v[c]) != k for c in v):
        return None, "distinto número de columnas entre filas"
    if "ingresos derivados" in flags and "impuesto no leído" in flags:
        return None, "faltan ingresos e impuesto: controles insuficientes"
    if "impuesto no leído" in flags and all(a_ == r_ for a_, r_ in zip(v["antes_impuestos"], v["resultado"])):
        # sin impuesto y con resultado idéntico a «antes de impuestos» en todas las columnas: probablemente se leyó
        # dos veces la misma línea (TVN jun-2019 informa un impuesto de M$2.151.450)
        return None, "resultado igual a antes de impuestos en todas las columnas sin línea de impuesto"
    cols = []
    for c in range(k):
        if abs(v["ingresos"][c] + v["costo_ventas"][c] - v["ganancia_bruta"][c]) > 2:
            return None, f"ingresos + costo ≠ ganancia bruta (col {c})"
        if "discontinuadas" in v and abs(v["resultado_continuadas"][c] + v["discontinuadas"][c] - v["resultado"][c]) > 2:
            return None, f"continuadas + discontinuadas ≠ resultado (col {c})"
        cont = v["resultado_continuadas"][c] if "discontinuadas" in v else v["resultado"][c]
        if "impuesto" in v and abs(v["antes_impuestos"][c] + v["impuesto"][c] - cont) > 2:
            return None, f"antes de impuestos + impuesto ≠ resultado (col {c})"
        if "impuesto" not in v:
            # sin la línea de impuesto, el resultado debe ser una versión plausible después de impuestos del resultado
            # antes de impuestos: mismo signo y entre 0,3 y 1,7 veces (descarta, p. ej., la ganancia por acción)
            a_, r_ = v["antes_impuestos"][c], cont
            if a_ != r_ and not (a_ != 0 and 0.3 <= r_ / a_ <= 1.7):
                return None, f"resultado {r_} no plausible frente a antes de impuestos {a_} (impuesto no leído)"
        if v["ingresos"][c] == 0:  # p. ej. TV+ 2016: la sociedad aún no operaba
            continue
        # ±M$2: la nota y el estado de resultados a veces difieren en un peso por redondeo de la fuente
        per = next((totales[t] for t in totales if abs(t - v["ingresos"][c]) <= 2), None)
        control = ", ".join(flags) or "completo"
        if per is None:
            otra = cols[0] if cols else None
            if (fecha_cierre[5:7] == "12" and k == 2 and c == 1 and not flags and otra
                    and otra[1][0] == "anual" and otra[1][2] == "actual"):
                a = int(fecha_cierre[:4]) - 1
                per, control = ("anual", f"{a}-12-31", "comparativo"), "sin total de nota"
            else:
                return None, f"ingresos {v['ingresos'][c]} no coinciden con la nota de ingresos"
        cols.append((c, per, control))
    return cols, ""


def paginas_candidatas(pdf, npag, ya):
    """Otras páginas que parecen un estado de resultados (cuando la del paso 4 no sirve)."""
    out = []
    for q in range(1, min(npag, 30) + 1):
        if q == ya:
            continue
        t = norm(x.pagina(pdf, q)[0])
        if "resultado" in t and re.search(r"costos? de (ventas?|explotacion)", t) and re.search(r"ganancia|perdida|resultado del", t):
            out.append(q)
    return out[:4]


def main(solo=None):
    log = pd.read_csv(ROOT / "data" / "extraccion_log.csv")
    ext = pd.read_csv(ROOT / "data" / "lineas_extraidas.csv")
    tot = ext[ext.es_total.astype(str) == "True"]
    log = log[log.estado.isin(["OK", "REVISAR"]) & log.pagina_eerr.fillna(0).gt(0)]
    docs = pd.read_csv(ROOT / "data" / "documentos.csv")
    paginas = dict(zip(docs.pdf, docs.paginas))
    if solo:
        log = log[log.apply(solo, axis=1)]
    filas, revision = [], []
    for r in log.itertuples():
        pdf, p = str(ROOT / r.documento), int(r.pagina_eerr)
        t = tot[tot.documento == r.documento]
        totales = {int(m): (tp, fin, rol) for m, tp, fin, rol in zip(t.monto, t.tipo_periodo, t.fin, t.rol)}
        motivo = "no se encontraron las líneas del estado de resultados"
        npag = int(paginas.get(r.documento, p))
        hecho = False
        for q in [p] + paginas_candidatas(pdf, npag, p):
            for nombre, lines in fuentes(pdf, q, npag):
                v = leer(lines)
                if not v:
                    continue
                cols, motivo = controlar(v, totales, r.fecha_cierre)
                if not cols:
                    continue
                for c, (tp, fin, rol), control in cols:
                    filas.append({"canal": r.canal, "fecha_cierre": r.fecha_cierre, "documento": r.documento, "pagina": q,
                                  "fuente_texto": nombre, "tipo_periodo": tp, "fin": fin, "rol": rol, "control": control,
                                  **{campo: (v[campo][c] if campo in v else None) for campo, _ in FILAS},
                                  "resultado_continuadas": (v["resultado_continuadas"][c] if "discontinuadas" in v
                                                            else v["resultado"][c])})
                hecho = True
                break
            if hecho:
                break
        if not hecho:
            revision.append({"canal": r.canal, "fecha_cierre": r.fecha_cierre, "documento": r.documento,
                             "pagina": p, "motivo": motivo})
    pd.DataFrame(filas).to_csv(ROOT / "data" / "resultados.csv", index=False, encoding="utf-8")
    pd.DataFrame(revision).to_csv(ROOT / "revision" / "resultados.csv", index=False, encoding="utf-8")
    print(f"{len(log) - len(revision)} EEFF con estado de resultados; {len(revision)} a revisión")
    for rv in revision:
        print(f"  {rv['canal']:12} {rv['fecha_cierre']}  {rv['motivo']}")


if __name__ == "__main__":
    filtro = None
    if len(sys.argv) > 1:
        c, f = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ""
        filtro = lambda r: (not c or r["canal"] == c) and str(r["fecha_cierre"]).startswith(f)  # noqa: E731
    main(filtro)
