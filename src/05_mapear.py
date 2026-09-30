"""Paso 5: mapea cada línea extraída a las categorías de mapeo/lineas_mapeo.csv y arma la base.

- Las líneas sin mapeo detienen el proceso y se listan en revision/lineas_sin_mapear.csv.
- Se guardan todas las versiones de cada período (una por documento que lo informa).
  La serie principal usa la versión del documento más reciente (propuesta 6.1 de CLAUDE.md);
  se marca reclasificado=True cuando las versiones de un mismo período difieren en alguna línea.
- revision/manual_lineas.csv permite cargar cifras que no se pueden extraer del PDF (p. ej. TVN dic-2025,
  fuente corrupta), siempre con su fuente documentada.

Salida: data/ingresos.sqlite (tabla lineas) y data/lineas_mapeadas.csv
"""
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from pdftexto import norm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def linea_norm(s):
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", str(s))  # "PublicidadOtras" -> "Publicidad Otras"
    s = norm(s).replace("!", " ")  # separadores de palabra en algunos PDF de TVN
    s = re.sub(r"\(\s*(\d|[a-z]|\*+)\s*\)|\*+", " ", s)  # llamadas a nota: (1), ( 2 ), (a), (*)
    return re.sub(r"\s+", " ", s).strip(" .:")


def etiqueta(r):
    a = r["fin"][:4]
    m = int(r["fin"][5:7])
    t = r["tipo_periodo"]
    if t == "anual":
        return f"FY{a}"
    if t == "semestre":
        return f"H1 {a}"
    if t == "acumulado9m":
        return f"9M {a}"
    return f"Q{m // 3} {a}"


def main():
    x = pd.read_csv(ROOT / "data" / "lineas_extraidas.csv", dtype=str)
    x = x[x["es_total"] != "True"].copy()
    x["monto"] = x["monto"].astype(int)
    x["origen_cifra"] = "extraccion"
    manual = ROOT / "revision" / "manual_lineas.csv"
    if manual.exists():
        m = pd.read_csv(manual, dtype=str)
        m["monto"] = m["monto"].astype(int)
        m["origen_cifra"] = "manual"
        # una cifra manual reemplaza lo extraído del mismo documento y período
        clave = ["documento", "tipo_periodo", "fin"]
        x = x.merge(m[clave].drop_duplicates(), on=clave, how="left", indicator=True)
        x = x[x["_merge"] == "left_only"].drop(columns="_merge")
        x = pd.concat([x, m], ignore_index=True)

    # Algunos ZIP traen dos copias del EEFF (C13 jun-2022, Mega sep-2023): se usa una sola,
    # previa verificación de que ambas informan las mismas cifras.
    for (canal, fecha), g in x.groupby(["canal", "fecha_cierre"]):
        docs = sorted(g["documento"].unique())
        if len(docs) > 1:
            firmas = {d: sorted(zip(g.loc[g.documento == d, "fin"], g.loc[g.documento == d, "monto"])) for d in docs}
            iguales = all(firmas[d] == firmas[docs[0]] for d in docs)
            print(f"{canal} {fecha}: {len(docs)} copias del EEFF, cifras {'idénticas' if iguales else 'DISTINTAS'};"
                  f" se usa {docs[0]}")
            if not iguales:
                sys.exit(f"ALTO: copias con cifras distintas en {canal} {fecha}")
            x = x[~((x.canal == canal) & (x.fecha_cierre == fecha) & (x.documento != docs[0]))]

    x["linea_norm"] = x["linea_original"].map(linea_norm)
    # Desgloses documentados en las notas (p. ej. venta de activos de C13 dentro de "Otros ingresos de
    # explotación"): se separan de la línea madre en todas las versiones del período. Solo montos que la nota informa.
    desg = ROOT / "mapeo" / "desgloses_nota.csv"
    if desg.exists():
        x["periodo"] = x.apply(etiqueta, axis=1)
        nuevas = []
        for _, d in pd.read_csv(desg, dtype=str).iterrows():
            m = (x.canal == d.canal) & (x.periodo == d.periodo) & (x.linea_norm == d.linea_padre_norm)
            if not m.any():
                sys.exit(f"ALTO: desglose sin línea madre: {d.canal} {d.periodo} {d.linea_padre_norm}")
            for i in x.index[m]:
                monto = int(d.monto)
                if x.at[i, "monto"] < monto:
                    sys.exit(f"ALTO: desglose mayor que la línea madre en {d.canal} {d.periodo} ({x.at[i, 'documento']})")
                x.at[i, "monto"] -= monto
                r = x.loc[i].copy()
                r["linea_original"], r["linea_norm"], r["monto"] = d.linea_nueva, linea_norm(d.linea_nueva), monto
                r["origen_cifra"] = f"desglose de nota ({d.documento_fuente}, p. {d.pagina_fuente})"
                nuevas.append(r)
        x = pd.concat([x, pd.DataFrame(nuevas)], ignore_index=True).drop(columns="periodo")

    mapeo = pd.read_csv(ROOT / "mapeo" / "lineas_mapeo.csv", dtype=str)
    mapeo = mapeo.drop(columns=["linea_original"])
    y = x.merge(mapeo, on=["canal", "linea_norm"], how="left")
    sin = y[y["nivel1"].isna()]
    if len(sin):
        out = (sin.groupby(["canal", "linea_norm"])
               .agg(linea_original=("linea_original", "first"), documentos=("documento", "nunique"),
                    primer_cierre=("fecha_cierre", "min"), ultimo_cierre=("fecha_cierre", "max"),
                    ejemplo_monto=("monto", "first"))
               .reset_index())
        out.to_csv(ROOT / "revision" / "lineas_sin_mapear.csv", index=False, encoding="utf-8")
        print(f"ALTO: {len(out)} líneas sin mapeo -> revision/lineas_sin_mapear.csv")
        print(out.to_string())
        sys.exit(1)

    y["periodo"] = y.apply(etiqueta, axis=1)
    # versión: el documento que informa la cifra; la más reciente es la principal
    y = y.sort_values(["canal", "periodo", "fecha_cierre"])
    ult = y.groupby(["canal", "periodo"])["fecha_cierre"].transform("max")
    y["version_principal"] = y["fecha_cierre"] == ult
    # reclasificación = cambian los totales por categoría (N2 y Napoli/pureza) entre documentos;
    # un simple cambio de rótulo o una apertura más fina de la misma categoría no cuenta.
    y["_cat"] = y["nivel2"] + "|" + y["napoli_principal"] + "|" + y["pureza"]
    firma = (y.groupby(["canal", "periodo", "fecha_cierre", "_cat"])["monto"].sum().reset_index()
             .groupby(["canal", "periodo", "fecha_cierre"])
             .apply(lambda g: tuple(sorted(zip(g["_cat"], g["monto"]))), include_groups=False)
             .rename("firma").reset_index())
    n_ver = firma.groupby(["canal", "periodo"])["firma"].nunique().rename("n_versiones_distintas").reset_index()
    y = y.merge(n_ver, on=["canal", "periodo"])
    y["reclasificado"] = y["n_versiones_distintas"] > 1
    y = y.drop(columns="_cat")

    y.to_csv(ROOT / "data" / "lineas_mapeadas.csv", index=False, encoding="utf-8")
    with sqlite3.connect(ROOT / "data" / "ingresos.sqlite") as con:
        y.to_sql("lineas", con, if_exists="replace", index=False)
    print(f"{len(y)} montos mapeados; {y[y.version_principal].groupby(['canal', 'periodo']).ngroups} canal-períodos;"
          f" {y[y.reclasificado].groupby(['canal', 'periodo']).ngroups} con versiones distintas")


if __name__ == "__main__":
    main()
