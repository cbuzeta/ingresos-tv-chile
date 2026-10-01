"""Paso 5b: clasifica el costo de ventas (paso 4c) y arma la serie de resultados (paso 4d).

Costos
- Cada línea se clasifica con mapeo/costos_mapeo.csv (clave = rótulo normalizado sin espacios, para absorber
  variantes como «Produccióndeprogramas»). Una línea sin clasificar detiene el proceso.
- Control adicional: el total de la nota debe ser igual al costo de ventas del estado de resultados del mismo EEFF
  (paso 4d). Si difiere, el documento se descarta (p. ej. una tabla de gastos de administración que también sumaba).
Resultados
- Se usa, para cada canal y período, la versión del documento más reciente (como en ingresos).

Salidas: data/costos_mapeados.csv, data/resultados_serie.csv, revision/costos_sin_mapear.csv, revision/costos_control.csv
"""
import importlib.util
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("m", ROOT / "src" / "05_mapear.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def clave(s):
    return re.sub(r"\s+", "", m.linea_norm(s))


def version_principal(df, claves):
    ult = df.groupby(claves)["fecha_cierre"].transform("max")
    return df["fecha_cierre"] == ult


def main():
    # resultados (utilidades)
    r = pd.read_csv(ROOT / "data" / "resultados.csv")
    # cifras transcritas a mano desde EEFF que no se leen bien (revision/manual_resultados.csv, con su fuente):
    # reemplazan lo extraído del mismo documento y período, y deben cumplir las mismas identidades
    man_f = ROOT / "revision" / "manual_resultados.csv"
    if man_f.exists():
        man = pd.read_csv(man_f)
        for x in man.itertuples():
            assert abs(x.ingresos + x.costo_ventas - x.ganancia_bruta) <= 2, f"manual: identidad bruta {x.canal} {x.fin}"
            assert abs(x.antes_impuestos + x.impuesto - x.resultado_continuadas) <= 2, f"manual: identidad impuesto {x.canal} {x.fin}"
        k_man = ["documento", "tipo_periodo", "fin"]
        r = r.merge(man[k_man], on=k_man, how="left", indicator=True)
        r = pd.concat([r[r._merge == "left_only"].drop(columns="_merge"), man.drop(columns="nota_fuente")], ignore_index=True)
    r = r.drop_duplicates(["canal", "fecha_cierre", "tipo_periodo", "fin"])  # copias duplicadas del EEFF
    r["periodo"] = r.apply(m.etiqueta, axis=1)
    r["version_principal"] = version_principal(r, ["canal", "periodo"])
    r.to_csv(ROOT / "data" / "resultados_serie.csv", index=False, encoding="utf-8")

    # costos
    log = pd.read_csv(ROOT / "data" / "costos_log.csv")
    ok = set(log[log.estado.isin(["OK", "REVISAR"])].documento)
    c = pd.read_csv(ROOT / "data" / "costos_extraidos.csv")
    c = c[c.documento.isin(ok)].copy()
    # notas de costos transcritas a mano (revision/manual_costos.csv, con su fuente): reemplazan lo extraído del mismo
    # documento y pasan por el mismo control contra el estado de resultados
    man_c = ROOT / "revision" / "manual_costos.csv"
    if man_c.exists():
        mc = pd.read_csv(man_c).drop(columns="nota_fuente")
        c = pd.concat([c[~c.documento.isin(set(mc.documento))], mc], ignore_index=True)
    c["es_total"] = c.es_total.astype(str) == "True"

    # control contra el estado de resultados del mismo EEFF
    tot = c[c.es_total][["documento", "fecha_cierre", "tipo_periodo", "fin", "monto"]]
    ctl = tot.merge(r[["documento", "tipo_periodo", "fin", "costo_ventas"]], on=["documento", "tipo_periodo", "fin"], how="left")
    ctl["estado"] = ctl.apply(lambda x: "sin estado de resultados" if pd.isna(x.costo_ventas)
                              else ("coincide" if abs(abs(x.monto) - abs(x.costo_ventas)) <= 2 else "difiere"), axis=1)
    ctl.to_csv(ROOT / "revision" / "costos_control.csv", index=False, encoding="utf-8")
    malos = set(ctl[ctl.estado == "difiere"].documento)
    c = c[~c.documento.isin(malos) & ~c.es_total].copy()

    c["clave"] = c.linea_original.map(clave)
    mp = pd.read_csv(ROOT / "mapeo" / "costos_mapeo.csv")
    y = c.merge(mp[["canal", "clave", "categoria"]], on=["canal", "clave"], how="left")
    sin = y[y.categoria.isna()]
    if len(sin):
        sin.groupby(["canal", "clave"]).linea_original.first().reset_index().to_csv(
            ROOT / "revision" / "costos_sin_mapear.csv", index=False, encoding="utf-8")
        sys.exit(f"ALTO: {sin.groupby(['canal', 'clave']).ngroups} líneas de costos sin clasificar -> revision/costos_sin_mapear.csv")
    y = y.drop_duplicates(["canal", "fecha_cierre", "tipo_periodo", "fin", "orden"])  # copias duplicadas del EEFF
    y["periodo"] = y.apply(m.etiqueta, axis=1)
    y["version_principal"] = version_principal(y, ["canal", "periodo"])
    y.to_csv(ROOT / "data" / "costos_mapeados.csv", index=False, encoding="utf-8")
    print(f"Resultados: {r[r.version_principal].groupby(['canal', 'periodo']).ngroups} canal-períodos")
    print(f"Costos: {y[y.version_principal].groupby(['canal', 'periodo']).ngroups} canal-períodos; "
          f"control con estado de resultados: {ctl.estado.value_counts().to_dict()}")
    if malos:
        print("  descartados por no coincidir con el costo de ventas:", sorted({d.split('/')[3] + ' ' + f
                                                                              for d, f in zip(ctl.documento, ctl.fecha_cierre) if d in malos}))


if __name__ == "__main__":
    main()
