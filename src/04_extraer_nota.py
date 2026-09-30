"""Paso 4: extrae la nota "Ingresos de actividades ordinarias" de cada EEFF.

Estrategia: se buscan las páginas donde aparece el encabezado de la nota y se prueba con varias
fuentes de texto (pdfplumber, pdftotext -layout, pdftotext -raw, OCR). Solo se acepta una tabla que
pase el autocontrol aritmético: en cada columna, la suma de las líneas es igual a la fila de total.
Luego se controla que el total aparezca en el estado de resultados y se compara contra la semilla.

Salidas:
  data/lineas_extraidas.csv   una fila por (documento, línea, columna)
  data/extraccion_log.csv     estado por documento
  revision/extraccion/*.txt   texto de los casos que no se pudieron extraer
"""
import csv
import re
import subprocess
import sys
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).parent))
from pdftexto import norm, ocr_pagina, pagina, texto_pagina  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CANALES = {"TVN", "Canal 13", "Mega", "Chilevisión", "La Red", "TV+"}

HEAD = re.compile(r"ingresos (?:de|por) (?:las )?actividades ordinarias|ingresos ordinarios|ingresos de explotacion"
                  r"|ingresos operacionales")
NOTA_HEAD = re.compile(r"^\s*(?:nota|note)?\s*n?[°º]?\s*\d{1,2}[\.\-–:)\s]+.*?(" + HEAD.pattern + ")")
AMT = re.compile(r"(?<![\d/\-])\(?-?\d{1,3}(?:\.\d{3})+\)?(?![\d/\-])|(?<![\w\d/\-.,])\(?\d{1,3}\)?(?![\w\d/\-.,%])"
                 r"|(?<=\s)-(?=\s|$)")
FECHA = re.compile(r"(\d{2})[-/](\d{2})[-/](\d{4})")


def amount(tok):
    tok = tok.strip()
    if tok == "-":
        return 0
    neg = tok.startswith("(") or tok.startswith("-")
    v = int(re.sub(r"[^\d]", "", tok))
    return -v if neg else v


def split_line(line):
    """Separa una línea en (rótulo, [montos]). Los números de nota tipo '(1)' o '(a)' quedan en el rótulo."""
    if "¦" in line:  # fuente por coordenadas: celdas ya separadas
        partes = [x.strip() for x in line.split("¦")]
        lab = re.sub(r"\s+", " ", partes[0]).strip(" .:$")
        return lab, [amount(x) for x in partes[1:]]
    toks = list(AMT.finditer(line))
    # descartar montos pequeños sin puntos que sean referencias de nota "(1)" pegadas al rótulo
    nums, cut = [], None
    for m in toks:
        s = m.group(0)
        if re.fullmatch(r"\(\d{1,2}\)", s) and not nums:
            continue
        if s == "-" and re.match(r"\s*[^\W\d_]", line[m.end():]):
            continue  # guion dentro del rótulo ("Ingresos de operación - canje"), no una celda vacía
        if re.fullmatch(r"\d{1,2}", s) and not nums and len(toks) > 1:
            # número de nota en la columna "Nota" del estado de resultados
            continue
        nums.append(amount(s))
        if cut is None:
            cut = m.start()
    label = line[:cut] if cut is not None else line
    label = re.sub(r"\bM(?:US)?\$", " ", label)
    label = re.sub(r"\s+", " ", label).strip(" .:$")
    return label, nums


HEADER_LABEL = re.compile(r"^(m\$|mus\$|nota|notas|detalle|el detalle|conceptos?|al \d|a continuacion|"
                          r"\d{2}[-/]\d{2}[-/]\d{4}|\d{4}|ejercicio|periodo|acumulado|trimestre|"
                          r"01[-/]0\d|(\d{2}[-/]\d{2}[-/]\d{4}\s*)+$)")


def es_encabezado(label_n, label=""):
    label_n = re.sub(r"\d{2}[-/]\d{2}[-/]\d{4}", " ", label_n)
    label_n = re.sub(r"\s+", " ", label_n).strip()
    if not label_n or len(label_n) < 3:
        return True
    if re.match(r"^[a-z0-9]\)\s", label_n):  # subtítulo "a) Ingreso de actividades ordinarias"
        return True
    if label and label.isupper() and not re.search(r"total|ingres", label_n):  # continuación del título
        return True
    if re.fullmatch(r"(ingresos? (de|por) actividades ordinarias|ingresos ordinarios|ingresos de explotacion)"
                    r"( \(.\))?", label_n):
        return True
    if HEADER_LABEL.match(label_n):
        return True
    if re.fullmatch(r"(ingresos (de|por) actividades ordinarias|ingresos ordinarios|ingresos de explotacion)"
                    r"( \(.\))?", label_n):
        return True
    if any(k in label_n for k in ("es el siguiente", "son los siguientes", "detalle de", "composicion de",
                                   "al 31 de", "al 30 de", "correspondiente", "terminado")):
        return True
    if re.fullmatch(r"[\d\s\-/de]+|(\d{2}[-/]\d{2}[-/]\d{4}\s*)+|(de )?\d{4}( y \d{4})?", label_n):
        return True
    if len(label_n.split()) > 18:  # párrafo de texto, no rótulo
        return True
    return False


def buscar_tabla(lines, ks=(1, 2, 4)):
    """Primero exige cuadre exacto; si no hay, acepta diferencias de redondeo de hasta M$2 por columna.

    ks=None: filas con todas las columnas de la página (fuente por coordenadas); se descartan las columnas
    que la tabla no usa y recién entonces se exige 1, 2 o 4 columnas.
    """
    for tol in (0, 2):
        filas, parsed = _buscar_tabla(lines, tol, ks)
        if filas:
            return filas, parsed
    return None, parsed


def _buscar_tabla(lines, tol, ks=(1, 2, 4)):
    """Encuentra el primer bloque de filas numéricas con igual n° de columnas cuya última fila es la suma.

    Devuelve (i_ini, i_fin, k) sobre la lista de índices de filas numéricas, o None.
    """
    parsed = [(i, *split_line(l)) for i, l in enumerate(lines)]
    num = [(i, lab, v) for i, lab, v in parsed if v and any(x != 0 for x in v)]
    for a in range(len(num)):
        k = len(num[a][2])
        if ks and k not in ks:  # la nota a) trae 2 o 4 columnas; 8 es la desagregación geográfica b)
            continue
        for b in range(a + 1, min(a + 25, len(num))):
            if len(num[b][2]) != k:
                break
            # una sola línea igual al total solo vale si la fila siguiente se rotula como total (TV+ 2017)
            if b == a + 1 and not re.search(r"total", norm(num[b][1])):
                continue
            filas = [r[2] for r in num[a:b]]
            if any(len(f) != k for f in filas):
                break
            if all(abs(sum(f[c] for f in filas) - num[b][2][c]) <= tol for c in range(k)) and max(num[b][2]) > 1000:
                bloque = num[a:b + 1]
                if ks is None:
                    usadas = [c for c in range(k) if any(r[2][c] for r in bloque)]
                    if len(usadas) not in (1, 2, 4):
                        continue
                    bloque = [(i, lab, [v[c] for c in usadas]) for i, lab, v in bloque]
                return bloque, parsed
    return None, parsed


def rotulos(parsed, filas, head_idx):
    """Rótulos candidatos entre el encabezado de la nota y la fila de total, en orden de aparición."""
    fin = filas[-1][0]
    labs = []
    for i, lab, v in parsed:
        if i < head_idx or i > fin:
            continue
        ln = norm(lab)
        if es_encabezado(ln, lab):
            continue
        labs.append((i, lab))
    return labs


def asignar(filas, labs):
    """Empareja filas numéricas con rótulos. Si hay más rótulos que filas, se prueba con rótulos
    pegados a la misma línea primero; si no calza, se devuelve None."""
    n = len(filas)
    same = {i: lab for i, lab in labs}
    # caso 1: cada fila tiene su rótulo en la misma línea
    if all(same.get(f[0]) for f in filas):
        return [same[f[0]] for f in filas]
    # caso 2: rótulos y cifras en bloques separados pero en el mismo orden
    if len(labs) == n:
        return [lab for _, lab in labs]
    # caso 3: sin rótulo de total (la fila de total no trae texto)
    if len(labs) == n - 1:
        return [lab for _, lab in labs] + ["Total"]
    # caso 4: sobran rótulos (restos de encabezado): se toman los n últimos, solo si el último es el total
    # y ningún otro lo es
    if len(labs) > n:
        ult = [lab for _, lab in labs[-n:]]
        if re.search(r"total", norm(ult[-1])) and not any(re.search(r"total", norm(l)) for l in ult[:-1]):
            return ult
    return None


SEP = " ¦ "  # separador explícito de celdas en la fuente por coordenadas
NUM_TOK = re.compile(r"\(?-?\d{1,3}(?:\.\d{3})+\)?|\(?\d{1,3}\)?|-")


def lineas_por_columnas(page):
    """Reconstruye filas por coordenadas: celdas vacías quedan como '-' (cero).

    Las cifras van alineadas a la derecha, así que las columnas se definen agrupando el borde derecho (x1)
    de los números con puntos de miles. Cada fila se escribe con todas las columnas de la página;
    las columnas que la tabla no usa quedan en cero y se descartan después (ver extraer_doc).
    """
    words = page.extract_words(keep_blank_chars=False, x_tolerance=3)
    filas = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if filas and abs(filas[-1][0] - w["top"]) <= 3:
            filas[-1][1].append(w)
        else:
            filas.append([w["top"], [w]])
    xs = sorted(w["x1"] for w in words if re.fullmatch(r"\(?-?\d{1,3}(?:\.\d{3})+\)?", w["text"]))
    anclas = []
    for x in xs:
        if anclas and x - anclas[-1][-1] <= 12:
            anclas[-1].append(x)
        else:
            anclas.append([x])
    anclas = [sum(a) / len(a) for a in anclas if len(a) >= 2]
    out = []
    for _, ws in filas:
        ws.sort(key=lambda w: w["x0"])
        nums = [w for w in ws if NUM_TOK.fullmatch(w["text"]) and anclas
                and min(abs(w["x1"] - a) for a in anclas) <= 14]
        label = " ".join(w["text"] for w in ws if w not in nums)
        if not nums:
            out.append(label)
            continue
        celdas = ["-"] * len(anclas)
        for w in nums:
            j = min(range(len(anclas)), key=lambda j: abs(w["x1"] - anclas[j]))
            celdas[j] = w["text"]
        out.append(label + SEP + SEP.join(celdas))
    return out


def fuentes(pdf, page, npag):
    """Genera (nombre_fuente, lineas) para una página y la siguiente (tablas que se cortan)."""
    rng = [page] + ([page + 1] if page < npag else [])
    cols = None
    try:
        with pdfplumber.open(pdf) as doc:
            t = "\n".join(doc.pages[p - 1].extract_text() or "" for p in rng)
            cols = [l for p in rng for l in lineas_por_columnas(doc.pages[p - 1])]
        yield "pdfplumber", t.splitlines()
    except Exception:
        pass
    yield "pdftotext-layout", "\n".join(texto_pagina(pdf, p) for p in rng).splitlines()
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", "-raw", "-f", str(page), "-l", str(rng[-1]), pdf, "-"],
                       capture_output=True)
    yield "pdftotext-raw", r.stdout.decode("utf-8", "ignore").splitlines()
    if cols:  # por coordenadas: solo si el texto corrido no alcanza (celdas vacías, p. ej. La Red)
        yield "pdfplumber-columnas", cols
    # último recurso: tabla sin capa de texto utilizable (caracteres sueltos o fuente corrupta)
    yield from fuentes_ocr(pdf, page, npag)


def fuentes_ocr(pdf, page, npag):
    """OCR estándar (300 dpi, psm 6) y, si no basta, a 400 dpi con psm 4 (lee mejor filas con recuadros)."""
    rng = [page] + ([page + 1] if page < npag else [])
    for nombre, dpi, psm in (("ocr", 300, 6), ("ocr400", 400, 4)):
        t = "\n".join(ocr_pagina(pdf, p, dpi, psm) for p in rng)
        # el OCR confunde a veces el punto de miles con coma; en M$ no hay decimales
        t = re.sub(r"(?<=\d),(?=\d{3}\b)", ".", t)
        yield nombre, t.splitlines()


def paginas_nota(pdf, npag, ocr):
    """Páginas con el encabezado de la nota de ingresos (no el índice ni el estado de resultados)."""
    cands = []
    for p in range(1, npag + 1):
        t = ocr_pagina(pdf, p) if ocr else pagina(pdf, p)[0]  # OCR si la página no trae texto
        tn = norm(t)
        if not HEAD.search(tn):
            continue
        score = 0
        if len(re.findall(r"\.{5,}", tn)) > 5 or len(re.findall(r"(?m)^\s*nota\s*n?[°º]?\s*\d+", tn)) > 5:  # índice
            continue
        for l in tn.splitlines():
            if NOTA_HEAD.search(l) and not re.search(r"\.{5,}", l):
                score = 2
                break
        if score == 0 and re.search(r"\d{1,3}\.\d{3}\.\d{3}", t):
            score = 1
        if score:
            cands.append((score, p))
    # primero las que tienen encabezado de nota; dentro de cada grupo, en orden de página
    return [p for s, p in sorted(cands, key=lambda x: (-x[0], x[1]))]


def extraer_doc(doc):
    pdf, npag, ocr = str(ROOT / doc["pdf"]), int(doc["paginas"]), doc.get("ocr") == "S"
    intentos = []
    for p in paginas_nota(pdf, npag, ocr)[:8]:
        escaneada = ocr or len(texto_pagina(pdf, p).strip()) < 30
        srcs = fuentes_ocr(pdf, p, npag) if escaneada else fuentes(pdf, p, npag)
        for nombre, lines in srcs:
            head_idx = next((i for i, l in enumerate(lines) if NOTA_HEAD.search(norm(l))), None)
            if head_idx is None:
                head_idx = next((i for i, l in enumerate(lines) if HEAD.search(norm(l))), 0)
            filas, parsed = buscar_tabla(lines[head_idx:head_idx + 70],
                                         None if nombre == "pdfplumber-columnas" else (1, 2, 4))
            if not filas:
                intentos.append((p, nombre, "sin tabla que sume"))
                continue
            if filas[0][0] > 35:  # la tabla debe estar cerca del encabezado de la nota
                intentos.append((p, nombre, "tabla lejos del encabezado"))
                continue
            labs = rotulos(parsed, filas, 0)
            asign = asignar(filas, labs)
            if not asign:
                intentos.append((p, nombre, f"{len(filas)} filas vs {len(labs)} rótulos: "
                                 + " | ".join(l for _, l in labs)))
                continue
            if not any(re.search(r"ingres|publicid|\bventas?\b|subvenc", norm(l)) for l in asign[:-1]) \
                    or any(re.search(r"costo|gasto|ganancia|perdida|margen", norm(l)) for l in asign):
                # p. ej. el propio estado de resultados: ingresos - costo de ventas = ganancia bruta
                intentos.append((p, nombre, "tabla que suma pero no es de ingresos: " + " | ".join(asign)))
                continue
            return {"pagina": p, "fuente": nombre, "filas": [(lab, f[2]) for lab, f in zip(asign, filas)],
                    "encabezado": "\n".join(lines[head_idx:filas[0][0] + head_idx])}, intentos
    return None, intentos


PERIODOS = {  # (mes de cierre, n° columnas) -> [(tipo_periodo, rol)]
    (12, 1): [("anual", "actual")],
    (12, 2): [("anual", "actual"), ("anual", "comparativo")],
    (3, 2): [("trimestre", "actual"), ("trimestre", "comparativo")],
    (6, 2): [("semestre", "actual"), ("semestre", "comparativo")],
    (9, 2): [("acumulado9m", "actual"), ("acumulado9m", "comparativo")],
    (6, 4): [("semestre", "actual"), ("semestre", "comparativo"), ("trimestre", "actual"), ("trimestre", "comparativo")],
    (9, 4): [("acumulado9m", "actual"), ("acumulado9m", "comparativo"), ("trimestre", "actual"),
             ("trimestre", "comparativo")],
}


def columnas(fecha_cierre, k, encabezado):
    a, m = int(fecha_cierre[:4]), int(fecha_cierre[5:7])
    spec = PERIODOS.get((m, k), [])
    cols = []
    for tipo, rol in spec:
        anio = a if rol == "actual" else a - 1
        if tipo == "trimestre":
            ini_m = m - 2
        elif tipo == "anual":
            ini_m = 1
        else:
            ini_m = 1
        fin = f"{anio}-{m:02d}-{fecha_cierre[8:]}"
        cols.append({"tipo_periodo": tipo, "rol": rol, "inicio": f"{anio}-{ini_m:02d}-01", "fin": fin})
    # Si el encabezado trae las fechas de inicio y fin de cada columna, mandan ellas.
    # pdftotext puede leerlas por filas (inicios, luego fines) o por columnas (inicio, fin, inicio, fin...).
    fechas = [f"{y}-{mm}-{d}" for d, mm, y in FECHA.findall(encabezado)]
    aviso = ""
    if len(fechas) == 2 * k:
        lecturas = [list(zip(fechas[:k], fechas[k:])), list(zip(fechas[0::2], fechas[1::2]))]
        validas = [l for l in lecturas if all(periodo_valido(i, f) for i, f in l)]
        validas = [l for n, l in enumerate(validas) if l not in validas[:n]]
        if len(validas) == 1:
            cols = [col_desde_fechas(i, f, fecha_cierre) for i, f in validas[0]]
        elif len(validas) > 1:
            aviso = f"encabezado ambiguo {validas}"
        elif cols and sorted(c["fin"] for c in cols) == sorted(f for f in fechas if f in {c["fin"] for c in cols}) \
                and len([f for f in fechas if f in {c["fin"] for c in cols}]) == k:
            # errata en una fecha de inicio (p. ej. TVN mar-2026 "01-03-2025"): los cierres calzan con el supuesto
            pass
        else:
            aviso = f"fechas de encabezado no interpretables {fechas}"
    elif len(fechas) == k:
        if fechas != [c["fin"] for c in cols]:
            aviso = f"encabezado {fechas} ≠ supuesto {[c['fin'] for c in cols]}"
    else:
        anios = re.findall(r"\b(20\d{2})\b", encabezado)
        if k == 2 and m == 12 and anios[-2:] and [int(x) for x in anios[-2:]] != [a, a - 1]                 and [int(x) for x in anios[:2]] != [a, a - 1]:
            aviso = f"años en encabezado {anios} ≠ [{a}, {a - 1}]"
    if not cols:
        return None, aviso or f"n° de columnas inesperado ({k}) para cierre {fecha_cierre}"
    return cols, aviso


def periodo_valido(ini, fin):
    yi, mi, di = map(int, ini.split("-"))
    yf, mf, df = map(int, fin.split("-"))
    meses = (yf - yi) * 12 + mf - mi + 1
    return di == 1 and yi == yf and meses in (3, 6, 9, 12) and mf % 3 == 0


def col_desde_fechas(ini, fin, fecha_cierre):
    yi, mi = int(ini[:4]), int(ini[5:7])
    mf = int(fin[5:7])
    meses = mf - mi + 1
    tipo = {12: "anual", 9: "acumulado9m", 6: "semestre", 3: "trimestre"}[meses]
    rol = "actual" if int(fin[:4]) == int(fecha_cierre[:4]) else "comparativo"
    return {"tipo_periodo": tipo, "rol": rol, "inicio": ini, "fin": fin}


def total_en_eerr(pdf, npag, totales, ocr):
    """¿Aparece el total de la nota (actual o comparativo) en el estado de resultados?

    Se compara solo la secuencia de dígitos, porque el OCR a veces pierde o cambia los puntos de miles.
    """
    for p in range(1, min(npag, 25) + 1):
        t = ocr_pagina(pdf, p) if ocr else pagina(pdf, p)[0]  # OCR si la página no trae texto
        tn = norm(t)
        if not ("resultado" in tn or "ganancia" in tn or "perdida" in tn):
            continue
        # números completos del texto (con o sin puntos de miles): se comparan enteros, no subcadenas
        nums = {re.sub(r"\D", "", n) for n in re.findall(r"\d[\d.,]*\d", t)}
        if any(str(abs(x)) in nums for x in totales if abs(x) > 100000):
            return p
    return 0


def main(solo=None):
    with open(ROOT / "data" / "documentos.csv", encoding="utf-8") as fh:
        docs = [d for d in csv.DictReader(fh) if d["tipo_documento"] == "EEFF" and d["canal"] in CANALES]
    if solo:
        docs = [d for d in docs if solo(d)]
    salida, log = [], []
    rev = ROOT / "revision" / "extraccion"
    rev.mkdir(parents=True, exist_ok=True)
    for d in sorted(docs, key=lambda d: (d["canal"], d["fecha_cierre"])):
        base = {"canal": d["canal"], "fecha_cierre": d["fecha_cierre"], "documento": d["pdf"]}
        if not d["fecha_cierre"]:
            log.append({**base, "estado": "REVISION", "detalle": "documento sin fecha de cierre"})
            continue
        try:
            res, intentos = extraer_doc(d)
        except Exception as e:  # noqa: BLE001
            res, intentos = None, [(0, "error", repr(e))]
        if not res:
            log.append({**base, "estado": "REVISION", "detalle": "; ".join(f"p{p} {n}: {m}" for p, n, m in intentos[:6])})
            print("REVISION", d["canal"], d["fecha_cierre"])
            continue
        k = len(res["filas"][0][1])
        cols, aviso = columnas(d["fecha_cierre"], k, res["encabezado"])
        total = res["filas"][-1][1][0]
        p_eerr = total_en_eerr(str(ROOT / d["pdf"]), int(d["paginas"]), res["filas"][-1][1], d.get("ocr") == "S")
        estado = "OK" if cols and not aviso and p_eerr else "REVISAR"
        filas_v = [v for _, v in res["filas"]]
        dif = [filas_v[-1][c] - sum(f[c] for f in filas_v[:-1]) for c in range(k)]
        redondeo = f"descuadre de redondeo en la fuente (total - suma = {dif})" if any(dif) else ""
        detalle = "; ".join(x for x in [aviso, redondeo, "" if p_eerr else "total no hallado en EERR",
                                         "" if cols else "columnas no interpretables"] if x)
        log.append({**base, "estado": estado, "detalle": detalle, "pagina": res["pagina"], "fuente": res["fuente"],
                    "n_lineas": len(res["filas"]) - 1, "columnas": k, "total_actual": total, "pagina_eerr": p_eerr})
        for j, (lab, vals) in enumerate(res["filas"]):
            for c, v in enumerate(vals):
                col = cols[c] if cols else {"tipo_periodo": "", "rol": f"col{c}", "inicio": "", "fin": ""}
                salida.append({**base, **col, "orden": j, "es_total": j == len(res["filas"]) - 1,
                               "linea_original": lab, "monto": v, "pagina": res["pagina"], "fuente_texto": res["fuente"],
                               "estado_doc": estado})
        print(estado, d["canal"], d["fecha_cierre"], f"p{res['pagina']}", res["fuente"], k, "cols",
              [lab for lab, _ in res["filas"]], detalle)

    for name, rows in (("lineas_extraidas.csv", salida), ("extraccion_log.csv", log)):
        if solo and (ROOT / "data" / name).exists():
            # corrida parcial: se reemplazan solo los documentos procesados
            hechos = {d["pdf"] for d in docs}
            with open(ROOT / "data" / name, encoding="utf-8") as fh:
                previas = [r for r in csv.DictReader(fh) if r["documento"] not in hechos]
            rows = previas + rows
            rows.sort(key=lambda r: (r["canal"], r["fecha_cierre"] or ""))
        cols = list(dict.fromkeys(c for r in rows for c in r))
        with open(ROOT / "data" / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
    from collections import Counter
    print(Counter(r["estado"] for r in log))


if __name__ == "__main__":
    filtro = None
    if len(sys.argv) > 1:
        c, f = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ""
        filtro = lambda d: d["canal"] == c and d["fecha_cierre"].startswith(f)  # noqa: E731
    main(filtro)
