"""Paso 6: exportación.

Entradas: data/lineas_mapeadas.csv (paso 5), data/externos/ipc_mindicador_*.json, data/extraccion_log.csv
Salidas (salidas/):
  lineas_larga.csv          una fila por línea, período y versión (documento)
  agregados.csv             serie principal por canal y período: N1, N2, Napoli (piso/punto/techo), perímetro TV
  ingresos_tv_chile.xlsx    planilla con las tablas anteriores, anchas por nivel, versiones y notas
  viz_data.json             datos para viz/ (también se incrustan en viz/ingresos_tv.html)
"""
import glob
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAL = ROOT / "salidas"
BASE_IPC = 2025  # CLAUDE.md 6.4: año base por definir; provisional

CANALES = ["TVN", "Canal 13", "Mega", "Chilevisión", "La Red", "TV+"]
AGREGADOS = {"4 grandes": CANALES[:4], "6 canales CMF": CANALES}
CATS = {"A": "Audiencias", "C": "Contenidos", "F": "Fuera de Napoli"}
FLAG = {"A": "puede_audiencias", "C": "puede_contenidos", "F": "puede_fuera"}

EVENTOS = [
    {"corto": "IFRS 15", "fecha": "2018-01-01", "canal": None, "texto": "IFRS 15 entra en vigencia (posible quiebre 2017→2018)"},
    {"corto": "Venta activos", "fecha": "2018-12-31", "canal": "Canal 13", "texto": "C13: venta de activos 2018 (Secuoya M$5.376.862; torres M$1.053.236), separada como Fuera de Napoli"},
    {"corto": "COVID-19", "fecha": "2020-03-15", "canal": None, "texto": "Pandemia COVID-19"},
    {"corto": "Venta activos", "fecha": "2020-12-31", "canal": "Canal 13", "texto": "C13: venta de activos 2020 por M$13.771.539, separada como Fuera de Napoli (Q1 y Q2 2020 sin desglose)"},
    {"corto": "Megamedia", "fecha": "2020-01-01", "canal": "Mega", "texto": "Mega: la sociedad informante pasa de Red Televisiva Megavisión a Megamedia; el 2019 informado por ambas coincide"},
    {"corto": "Paramount", "fecha": "2021-01-01", "canal": "Chilevisión", "texto": "CHV: controlador pasa a Paramount/ViacomCBS"},
    {"corto": "TILA → publicidad", "fecha": "2023-01-01", "canal": "Chilevisión", "texto": "CHV: la comisión TILA (TV paga) se integra a 'Ingresos por publicidad'"},
    {"corto": "Subvención NTV", "fecha": "2025-01-01", "canal": "TVN", "texto": "TVN: inicia subvención NTV (Ley 19.132 art. 37)"},
    {"corto": "Vytal", "fecha": "2026-01-01", "canal": "Chilevisión", "texto": "CHV: controlador pasa a Vytal Group"},
]


def ipc():
    """Índice IPC mensual encadenado desde las variaciones mensuales oficiales del Banco Central
    (IPC general, % c/r al período anterior, publicadas con un decimal). Promedio BASE_IPC = 100."""
    d = pd.read_csv(ROOT / "data" / "externos" / "bcch_ipc_var.csv").rename(columns={"fecha": "mes", "valor": "var"})
    d = d.sort_values("mes").reset_index(drop=True)
    d["indice"] = (1 + d["var"] / 100).cumprod()
    base = d[d.mes.str[:4] == str(BASE_IPC)]["indice"].mean()
    d["indice"] = 100 * d["indice"] / base
    return d


def deflactor(idx, inicio, fin):
    """Promedio del índice en los meses del período; si faltan meses, usa el último disponible."""
    meses = pd.period_range(inicio[:7], fin[:7], freq="M").astype(str)
    v = idx.set_index("mes")["indice"].reindex(meses)
    completo = v.notna().all()
    v = v.fillna(idx["indice"].iloc[-1])
    return v.mean(), completo


def promedio_diario(serie, inicio, fin):
    """Promedio simple de los valores diarios publicados (UF o dólar observado) dentro del período."""
    v = serie[(serie.fecha >= inicio) & (serie.fecha <= fin)]["valor"]
    return v.mean(), len(v) > 0 and serie.fecha.max() >= fin


def agregar(g):
    tot = g["monto"].sum()
    r = {"total": tot}
    r["n1_publicidad"] = g.loc[g.nivel1 == "Publicidad", "monto"].sum()
    r["n1_otros"] = tot - r["n1_publicidad"]
    for n2, k in (("Publicidad", "n2_publicidad"), ("Otros ingresos operacionales", "n2_otros_operacionales"),
                  ("Transferencias del Estado", "n2_transferencias")):
        r[k] = g.loc[g.nivel2 == n2, "monto"].sum()
    for c, nombre in CATS.items():
        es = g.napoli_principal == nombre
        r[f"{c}_punto"] = g.loc[es, "monto"].sum()
        r[f"{c}_piso"] = g.loc[es & (g.pureza == "Pura"), "monto"].sum()
        r[f"{c}_techo"] = g.loc[g[FLAG[c]] == "S", "monto"].sum()
    tv = g[g.medio != "Radio/cable"]
    r["tvp_total"] = tv["monto"].sum()
    r["tvp_n1_publicidad"] = tv.loc[tv.nivel1 == "Publicidad", "monto"].sum()
    for c, nombre in CATS.items():
        es = tv.napoli_principal == nombre
        r[f"tvp_{c}_punto"] = tv.loc[es, "monto"].sum()
        r[f"tvp_{c}_piso"] = tv.loc[es & (tv.pureza == "Pura"), "monto"].sum()
        r[f"tvp_{c}_techo"] = tv.loc[tv[FLAG[c]] == "S", "monto"].sum()
    return pd.Series(r)


def main():
    SAL.mkdir(exist_ok=True)
    y = pd.read_csv(ROOT / "data" / "lineas_mapeadas.csv", dtype={"monto": "int64"})
    y.to_csv(SAL / "lineas_larga.csv", index=False, encoding="utf-8")
    p = y[y.version_principal].copy()

    keys = ["canal", "periodo", "tipo_periodo", "inicio", "fin"]
    agg = p.groupby(keys).apply(agregar, include_groups=False).reset_index()
    info = p.groupby(["canal", "periodo"]).agg(documento=("documento", "first"), fecha_documento=("fecha_cierre", "first"),
                                                reclasificado=("reclasificado", "max"),
                                                origen_cifra=("origen_cifra", lambda s: ",".join(sorted(set(s))))
                                                ).reset_index()
    agg = agg.merge(info, on=["canal", "periodo"])

    # H2 = año - H1, por agregado (solo si existen ambos en la serie principal)
    num = [c for c in agg.columns if c not in keys + ["documento", "fecha_documento", "reclasificado", "origen_cifra"]]
    h2 = []
    for (canal, anio), g in agg.assign(anio=agg.fin.str[:4]).groupby(["canal", "anio"]):
        fy = g[g.tipo_periodo == "anual"]
        h1 = g[g.tipo_periodo == "semestre"]
        if len(fy) == 1 and len(h1) == 1:
            r = {"canal": canal, "periodo": f"H2 {anio}", "tipo_periodo": "semestre2", "inicio": f"{anio}-07-01",
                 "fin": f"{anio}-12-31", "documento": fy.documento.iloc[0] + " − " + h1.documento.iloc[0],
                 "fecha_documento": fy.fecha_documento.iloc[0], "reclasificado": bool(fy.reclasificado.iloc[0] or h1.reclasificado.iloc[0]),
                 "origen_cifra": "derivado (anual − H1)"}
            for c in num:
                r[c] = int(fy[c].iloc[0]) - int(h1[c].iloc[0])
            h2.append(r)
    agg = pd.concat([agg, pd.DataFrame(h2)], ignore_index=True)
    neg = agg[(agg[num] < 0).any(axis=1)]
    if len(neg):
        print("Aviso: agregados negativos (H2 derivado con líneas reclasificadas entre documentos):")
        print(neg[["canal", "periodo"]].to_string())

    # Agregado de industria: suma de canales solo en los períodos en que todos informan (panel balanceado)
    ind = []
    for nombre, grupo in AGREGADOS.items():
        sub = agg[agg.canal.isin(grupo)]
        for (periodo, tipo), g in sub.groupby(["periodo", "tipo_periodo"]):
            if set(g.canal) != set(grupo):
                continue
            r = {"canal": nombre, "periodo": periodo, "tipo_periodo": tipo, "inicio": g.inicio.iloc[0], "fin": g.fin.iloc[0],
                 "documento": "suma de " + ", ".join(grupo), "fecha_documento": g.fecha_documento.max(),
                 "reclasificado": bool(g.reclasificado.any()), "origen_cifra": "agregado"}
            for c in num:
                r[c] = int(g[c].sum())
            ind.append(r)
    agg = pd.concat([agg, pd.DataFrame(ind)], ignore_index=True)

    idx = ipc()
    d = agg.apply(lambda r: deflactor(idx, r["inicio"], r["fin"]), axis=1)
    agg["ipc_indice"] = [x[0] for x in d]
    agg["ipc_completo"] = [x[1] for x in d]
    for nombre in ("uf", "dolar"):
        serie = pd.read_csv(ROOT / "data" / "externos" / f"bcch_{nombre}.csv")
        d = agg.apply(lambda r: promedio_diario(serie, r["inicio"], r["fin"]), axis=1)
        agg[f"{nombre}_prom"] = [x[0] for x in d]
        agg[f"{nombre}_completo"] = [x[1] for x in d]
    agg = agg.sort_values(["canal", "fin", "tipo_periodo"]).reset_index(drop=True)
    agg.to_csv(SAL / "agregados.csv", index=False, encoding="utf-8")

    # planilla
    anual = agg[agg.tipo_periodo == "anual"]
    with pd.ExcelWriter(SAL / "ingresos_tv_chile.xlsx", engine="openpyxl") as xw:
        pd.DataFrame({"nota": [
            "Ingresos de actividades ordinarias de TVN, Canal 13, Mega (consolidado) y Chilevisión, en M$ nominales.",
            "Fuente: notas de ingresos de los EEFF (CMF y TVN). Cada cifra de 'lineas' lleva documento y página.",
            "Serie principal = versión del documento más reciente para cada período (decisión 6.1, confirmada 2026-09-30).",
            "Napoli: punto = según código principal; piso = líneas puras; techo = líneas que pueden contener la categoría.",
            "tvp_* = perímetro TV (sin publicidad radial y cable de Mega).",
            f"$ reales: índice IPC encadenado desde las variaciones mensuales del Banco Central de Chile (BDE, 1 decimal), promedio {BASE_IPC} = 100.",
            "UF: promedio de la UF diaria del período (BDE). USD: promedio del dólar observado diario del período (BDE).",
            "H2 = anual − H1 (derivado).",
        ]}).to_excel(xw, sheet_name="LEEME", index=False)
        for nombre, cols in (("N1", ["n1_publicidad", "n1_otros", "total"]),
                             ("N2", ["n2_publicidad", "n2_otros_operacionales", "n2_transferencias", "total"])):
            w = anual.pivot_table(index="periodo", columns="canal", values=cols, aggfunc="sum")
            w.to_excel(xw, sheet_name=f"{nombre}_anual")
        napoli = agg[["canal", "periodo", "total"] + [f"{c}_{m}" for c in CATS for m in ("piso", "punto", "techo")]].copy()
        for c in CATS:
            for m in ("piso", "punto", "techo"):
                napoli[f"%{c}_{m}"] = (100 * napoli[f"{c}_{m}"] / napoli["total"]).round(1)
        napoli.to_excel(xw, sheet_name="Napoli", index=False)
        agg.to_excel(xw, sheet_name="agregados", index=False)
        y.to_excel(xw, sheet_name="lineas", index=False)
        pd.read_csv(ROOT / "mapeo" / "lineas_mapeo.csv").to_excel(xw, sheet_name="mapeo", index=False)
        v = y[y.reclasificado].groupby(["canal", "periodo", "fecha_cierre", "nivel2"])["monto"].sum().unstack().reset_index()
        v.to_excel(xw, sheet_name="versiones", index=False)
        pd.read_csv(ROOT / "data" / "extraccion_log.csv").to_excel(xw, sheet_name="log_extraccion", index=False)

    # datos para la visualización
    lineas = p[["canal", "periodo", "linea_original", "monto", "nivel1", "nivel2", "napoli_principal", "pureza",
                "medio", "documento", "pagina", "fuente_texto", "origen_cifra"]].copy()
    lineas["documento"] = lineas["documento"].str.replace("data/raw/pdf/", "", regex=False)
    agg_v = agg.copy()
    agg_v["documento"] = agg_v["documento"].str.replace("data/raw/pdf/", "", regex=False)
    reclas = (y[y.reclasificado].groupby(["canal", "periodo"])["fecha_cierre"].apply(lambda s: sorted(set(s)))
              .reset_index().to_dict("records"))
    data = {"generado": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "base_ipc": BASE_IPC,
            "agregados": json.loads(agg_v.to_json(orient="records")),
            "lineas": json.loads(lineas.to_json(orient="records")),
            "eventos": EVENTOS, "reclasificaciones": reclas}
    (SAL / "viz_data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    plantilla = ROOT / "viz" / "plantilla.html"
    if plantilla.exists():
        html = plantilla.read_text(encoding="utf-8").replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
        (ROOT / "viz" / "ingresos_tv.html").write_text(html, encoding="utf-8")
        # GitHub Pages (https://cbuzeta.github.io/ingresos-tv-chile): la misma página como documento HTML completo
        (ROOT / "docs").mkdir(exist_ok=True)
        corte = html.index("</style>") + len("</style>")  # título, fuentes y estilos van al <head>
        cabeza, cuerpo = html[:corte], html[corte:]
        pagina = ("<!doctype html>\n<html lang=\"es\">\n<head>\n<meta charset=\"utf-8\">\n"
                  "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
                  "<meta name=\"description\" content=\"Ingresos de la TV abierta chilena 2016-2026: venta de audiencias "
                  "y de contenidos según las notas de los estados financieros (marco Napoli 2003).\">\n"
                  "<style>[hidden]{display:none!important} img{max-width:100%}</style>\n"
                  + cabeza + "\n</head>\n<body>\n" + cuerpo + "\n</body>\n</html>\n")
        (ROOT / "docs" / "index.html").write_text(pagina, encoding="utf-8")
        (ROOT / "docs" / ".nojekyll").write_text("", encoding="utf-8")
    print(f"{len(agg)} filas agregadas ({len(h2)} H2 derivados); planilla y viz_data.json en salidas/")


if __name__ == "__main__":
    sys.exit(main())
