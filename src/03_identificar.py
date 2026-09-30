"""Paso 3: identifica cada PDF por su contenido (sociedad, fecha de cierre, tipo de documento).

Salida: data/documentos.csv (todos los PDF) y revision/identificacion.csv
(canal-período con cero o más de un EEFF, o EEFF sin fecha reconocible).
"""
import csv
import re
import subprocess
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
CIERRES = {(31, 3), (30, 6), (30, 9), (31, 12)}
SOCIEDADES = [
    ("Canal 13", r"canal 13 s\.?p\.?a"),
    ("Mega", r"megamedia|red televisiva megavision"),
    ("Chilevisión", r"red de television chilevision|chilevision s\.a"),
    ("TVN", r"television nacional de chile"),
    ("La Red", r"compania chilena de television|la red"),
    ("TV+", r"tv\+|television mas|tv mas|ucv|compania de television"),
]


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[ \t]+", " ", s)


def texto(pdf, first=1, last=3):
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", "-f", str(first), "-l", str(last), "-layout", pdf, "-"],
                       capture_output=True)
    return r.stdout.decode("utf-8", "ignore")


def paginas(pdf):
    r = subprocess.run(["pdfinfo", pdf], capture_output=True)
    m = re.search(rb"Pages:\s+(\d+)", r.stdout)
    return int(m.group(1)) if m else 0


FIN_TRIM = {3: 31, 6: 30, 9: 30, 12: 31}


def fecha_cierre(t):
    """La fecha de cierre más reciente de fin de trimestre que aparece en la portada.

    Los intermedios citan también el comparativo (p. ej. "31 de marzo de 2022, 31 de diciembre de 2021"),
    por eso se toma la máxima. Se admite el día omitido ("al de marzo 2022", error de portada de TVN).
    """
    fechas = []
    for m in re.finditer(r"(\d{1,2})?\s*(?:de\s+)?(" + "|".join(MESES) + r")\s*(?:de|del)?\s*(\d{4})", t):
        mes, a = MESES[m.group(2)], int(m.group(3))
        d = int(m.group(1)) if m.group(1) else FIN_TRIM.get(mes)
        if (d, mes) in CIERRES and 2008 < a < 2030:
            fechas.append(f"{a}-{mes:02d}-{d:02d}")
    return max(fechas) if fechas else ""


def tipo_doc(t1, n):
    """t1: texto normalizado de la primera página; n: páginas."""
    head = t1[:1500]
    if "analisis razonado" in head:
        return "analisis_razonado"
    if "oficio circular" in head:
        return "oficio_498"
    if "hecho esencial" in head or "hechos esenciales" in head or "hechos relevantes" in head:
        return "hechos_esenciales"
    if "declaracion de responsabilidad" in head or "declaracion jurada" in head:
        return "declaracion"
    if n <= 3 and ("senores" in head or "presente" in head or "estimados" in head):
        return "carta"
    if "estados financieros" in head or "estado de situacion financiera" in head:
        return "EEFF" if n >= 20 else "eeff_corto"
    if not head.strip():
        return "sin_texto"
    return "otro"


def main():
    rows = []
    with open(ROOT / "data" / "pdfs.csv", encoding="utf-8") as fh:
        pdfs = list(csv.DictReader(fh))
    for p in pdfs:
        path = str(ROOT / p["pdf"])
        n = paginas(path)
        t = norm(texto(path, 1, 3))
        t1 = norm(texto(path, 1, 1))
        ocr = ""
        if not t1.strip() and n >= 20:  # EEFF escaneado: OCR de la portada
            from pdftexto import ocr_pagina
            t1 = norm(ocr_pagina(path, 1))
            t = t1 + norm(ocr_pagina(path, 2))
            ocr = "S"
        soc = next((c for c, pat in SOCIEDADES if re.search(pat, t[:3000])), "")
        fecha = fecha_cierre(t1) or fecha_cierre(t)
        tipo = tipo_doc(t1, n)
        if ocr and n >= 40:  # escaneo único que empaqueta carta + EEFF + análisis (dic-2017 y otros)
            tipo = "EEFF"
        rows.append({**p, "paginas": n, "ocr": ocr, "tipo_documento": tipo,
                     "sociedad_detectada": soc, "fecha_cierre": fecha,
                     "primera_linea": next((l.strip() for l in t1.splitlines() if l.strip()), "")[:80]})

    with open(ROOT / "data" / "documentos.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    eeff = defaultdict(list)
    revision = []
    for r in rows:
        if r["tipo_documento"] == "EEFF":
            if not r["fecha_cierre"]:
                revision.append({**r, "motivo": "EEFF sin fecha de cierre reconocida"})
            eeff[(r["canal"], r["fecha_cierre"])].append(r)
            if r["sociedad_detectada"] and r["sociedad_detectada"] != r["canal"]:
                revision.append({**r, "motivo": f"sociedad detectada {r['sociedad_detectada']} ≠ carpeta"})
    articulos = {(r["canal"], r["articulo"] or r["origen"]) for r in rows}
    con_eeff = {(r["canal"], r["articulo"] or r["origen"]) for r in rows if r["tipo_documento"] == "EEFF"}
    for canal, art in sorted(articulos - con_eeff):
        if canal != "TVN":
            revision.append({"canal": canal, "articulo": art, "motivo": "ZIP/archivo sin EEFF identificado"})
    for (canal, fecha), docs in eeff.items():
        if len(docs) > 1:
            for d in docs:
                revision.append({**d, "motivo": f"{len(docs)} EEFF para el mismo canal y fecha"})

    (ROOT / "revision").mkdir(exist_ok=True)
    cols = ["motivo", "canal", "articulo", "origen", "pdf", "paginas", "tipo_documento",
            "sociedad_detectada", "fecha_cierre", "primera_linea"]
    with open(ROOT / "revision" / "identificacion.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(revision)

    from collections import Counter
    print(Counter(r["tipo_documento"] for r in rows))
    print(f"{len(eeff)} pares canal-fecha con EEFF; {len(revision)} casos a revisión")


if __name__ == "__main__":
    main()
