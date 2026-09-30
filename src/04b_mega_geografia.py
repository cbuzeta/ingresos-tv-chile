"""Paso 4b: desagregación geográfica de Mega (nota 7 b: ventas nacionales / al extranjero).

La tabla 7 b tiene 8 columnas (3 líneas de servicio + total, año actual y anterior) y su diagramación
cambia entre años, así que no se interpreta por posición. En cambio, para cada monto ya extraído de la
nota 7 a) se busca el único par (nacional, extranjero) de las filas de 7 b que suma exactamente ese monto.
El total de la fila nacional y de la extranjera debe cuadrar además con la columna "Total".

Salida: data/mega_geografia.csv (documento, período, línea de 7 a, nacional, extranjero, página, fuente)
        revision/mega_geografia.csv (documentos sin 7 b o con cuadre ambiguo)
"""
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).parent))
from pdftexto import norm, ocr_pagina, texto_pagina  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NUM = re.compile(r"(?<![\d.])\(?\d{1,3}(?:\.\d{3})+\)?(?![\d.])|(?<=\s)-(?=\s|$)")


def valores(linea):
    out = []
    for m in NUM.finditer(linea):
        t = m.group(0)
        out.append(0 if t == "-" else int(re.sub(r"\D", "", t)) * (-1 if t.startswith("(") else 1))
    return out


def filas_geo(lines):
    """Devuelve (nacionales, extranjero) como listas de montos, o None."""
    nac = ext = None
    for i, l in enumerate(lines):
        ln = norm(l).strip()
        # el rótulo a veces se parte: "Ventas" en una línea y "nacionales 73.131.778 ..." en la siguiente
        if re.match(r"(ventas )?nacionales\b", ln) and nac is None and valores(l):
            nac = valores(l)
        elif re.match(r"(ventas )?(al )?extranjero\b", ln) and ext is None and valores(l):
            ext = valores(l)
        elif ln == "ventas al" and i + 1 < len(lines) and norm(lines[i + 1]).strip().startswith("extranjero") \
                and ext is None:
            ext = valores(lines[i + 1])
    if nac and ext is not None:
        return nac, ext
    return None


def fuentes(pdf, p, npag):
    rng = [q for q in (p, p + 1, p + 2) if q <= npag]
    with pdfplumber.open(pdf) as d:
        yield "pdfplumber", "\n".join(d.pages[q - 1].extract_text() or "" for q in rng).splitlines()
    yield "pdftotext-layout", "\n".join(texto_pagina(pdf, q) for q in rng).splitlines()
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", "-raw", "-f", str(p), "-l", str(rng[-1]), pdf, "-"],
                       capture_output=True)
    yield "pdftotext-raw", r.stdout.decode("utf-8", "ignore").splitlines()
    for dpi, psm in ((300, 6), (400, 4)):
        t = "\n".join(ocr_pagina(pdf, q, dpi, psm) for q in rng)
        yield f"ocr{dpi}", re.sub(r"(?<=\d),(?=\d{3}\b)", ".", t).splitlines()


def emparejar(montos, nac, ext):
    """Para cada monto de 7 a, el único par (n, e) de 7 b con n + e == monto. None si falta o es ambiguo."""
    res = {}
    for clave, T in montos.items():
        if T <= 0:
            continue
        cands = {(n, e) for n in set(nac) | {0} for e in set(ext) | {0} if n + e == T and (n or e)}
        if len(cands) != 1:
            return None, f"{clave}: {len(cands)} pares para {T}"
        res[clave] = cands.pop()
    return res, ""


def main():
    x = pd.read_csv(ROOT / "data" / "lineas_extraidas.csv")
    log = pd.read_csv(ROOT / "data" / "extraccion_log.csv")
    docs = pd.read_csv(ROOT / "data" / "documentos.csv")
    npag = dict(zip(docs.pdf, docs.paginas))
    x = x[(x.canal == "Mega") & (x.es_total.astype(str) != "True")]
    # 7 b solo trae acumulados; los trimestres se excluyen salvo cuando el trimestre es el acumulado (marzo)
    x = x[(x.tipo_periodo != "trimestre") | (x.fecha_cierre.str[5:7] == "03")]
    salida, revision = [], []
    for doc, g in x.groupby("documento"):
        fila_log = log[log.documento == doc].iloc[0]
        p = int(fila_log.pagina)
        montos = {(r.linea_original, r.tipo_periodo, r.rol, r.fin): int(r.monto) for r in g.itertuples()}
        motivo = "no se encontró la tabla 7 b"
        for nombre, lines in fuentes(str(ROOT / doc), p, int(npag[doc])):
            fg = filas_geo(lines)
            if not fg:
                continue
            nac, ext = fg
            res, motivo = emparejar(montos, nac, ext)
            if res is None:
                continue
            # control: por rol, la suma de nacionales y de extranjero de las líneas aparece como columna Total
            ok = True
            for rol in {k[2] for k in res}:
                sn = sum(v[0] for k, v in res.items() if k[2] == rol)
                se = sum(v[1] for k, v in res.items() if k[2] == rol)
                if sn not in nac or (se and se not in ext):
                    ok, motivo = False, f"totales nacional/extranjero no cuadran ({rol})"
            if not ok:
                continue
            for (linea, tipo, rol, fin), (n, e) in res.items():
                salida.append({"documento": doc, "fecha_cierre": g.fecha_cierre.iloc[0], "linea_original": linea,
                               "tipo_periodo": tipo, "rol": rol, "fin": fin, "nacional": n, "extranjero": e,
                               "pagina": p, "fuente_texto": nombre})
            break
        else:
            revision.append({"documento": doc, "fecha_cierre": g.fecha_cierre.iloc[0], "motivo": motivo})
    pd.DataFrame(salida).to_csv(ROOT / "data" / "mega_geografia.csv", index=False, encoding="utf-8")
    pd.DataFrame(revision).to_csv(ROOT / "revision" / "mega_geografia.csv", index=False, encoding="utf-8")
    hechos = pd.DataFrame(salida)
    print(f"{hechos.documento.nunique() if len(hechos) else 0} EEFF con 7 b; {len(revision)} sin 7 b o sin cuadre")
    for r in revision:
        print("  ", r["fecha_cierre"], r["motivo"])


if __name__ == "__main__":
    main()
