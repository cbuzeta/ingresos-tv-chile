"""Pruebas de consistencia de la base. Corren sobre los archivos versionados (no necesitan los PDF).

    python -m pytest tests

Si un cambio en la extracción es intencional, actualizar la referencia con:
    python tests/actualizar_referencia.py
"""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
CANALES = ["TVN", "Canal 13", "Mega", "Chilevisión", "La Red", "TV+"]


@pytest.fixture(scope="module")
def agregados():
    return pd.read_csv(ROOT / "salidas" / "agregados.csv")


@pytest.fixture(scope="module")
def lineas():
    return pd.read_csv(ROOT / "data" / "lineas_mapeadas.csv")


def test_semilla_48_de_48():
    """El pipeline reproduce exactamente los montos validados a mano del piloto."""
    spec = importlib.util.spec_from_file_location("v", ROOT / "src" / "validar_semilla.py")
    v = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v)
    assert v.main()


def test_extraccion_igual_a_referencia():
    """Ningún monto ya extraído cambia o desaparece sin que se actualice la referencia a propósito."""
    ref = pd.read_csv(ROOT / "tests" / "referencia_extraccion.csv")
    x = pd.read_csv(ROOT / "data" / "lineas_extraidas.csv")
    clave = ["canal", "fecha_cierre", "documento", "tipo_periodo", "fin", "orden"]
    m = ref.merge(x[clave + ["linea_original", "monto"]], on=clave, how="outer", suffixes=("_ref", ""), indicator=True)
    # los EEFF nuevos agregan montos (permitido); ningún monto de la referencia puede desaparecer o cambiar
    faltan = m[m._merge == "left_only"]
    assert faltan.empty, f"{len(faltan)} montos de la referencia desaparecieron:\n{faltan[clave].head(20)}"
    m = m[m._merge == "both"]
    distintos = m[(m.monto_ref != m.monto) | (m.linea_original_ref != m.linea_original)]
    assert distintos.empty, f"{len(distintos)} montos cambiaron:\n{distintos.head(20)}"


@pytest.mark.parametrize("nivel", ["n1", "n2", "n3", "n4"])
def test_cada_nivel_suma_el_total(agregados, nivel):
    cols = [c for c in agregados if c.startswith(nivel + "_")]
    assert cols
    dif = agregados[cols].sum(axis=1) - agregados["total"]
    assert (dif == 0).all(), agregados.loc[dif != 0, ["canal", "periodo"]]


def test_niveles_anidados(agregados):
    a = agregados
    assert (a.n1_publicidad == a.n2_publicidad).all()
    assert (a.n3_publicidad_tv_y_digital + a.n3_publicidad_en_otros_medios == a.n2_publicidad).all()
    assert (a.n3_transferencias_del_estado == a.n2_transferencias).all()
    con = [c for c in a if c.startswith("n4_contenidos_y_senales")]
    assert (a[con].sum(axis=1) == a.n3_contenidos_y_senales).all()


def test_agregados_suman_canales(agregados):
    """Los agregados de industria son la suma de sus canales, solo en períodos donde todos informan."""
    grupos = {"4 grandes": CANALES[:4], "6 canales CMF": CANALES}
    for nombre, g in grupos.items():
        for _, r in agregados[agregados.canal == nombre].iterrows():
            partes = agregados[(agregados.canal.isin(g)) & (agregados.periodo == r.periodo)]
            assert set(partes.canal) == set(g), (nombre, r.periodo)
            assert partes.total.sum() == r.total, (nombre, r.periodo)


def test_toda_linea_tiene_clasificacion(lineas):
    for c in ["nivel1", "nivel2", "nivel3", "nivel4"]:
        assert lineas[c].notna().all(), c


def test_trazabilidad(lineas):
    """Toda cifra tiene documento de origen y, si fue extraída, página."""
    assert lineas.documento.notna().all()
    extraidas = lineas[lineas.origen_cifra.str.startswith("extraccion")]
    assert extraidas.pagina.notna().all()


def test_serie_anual_completa(agregados):
    """Panel anual 2016–2025 para los canales con historia completa (TV+ desde 2017)."""
    for c in CANALES:
        anios = set(agregados[(agregados.canal == c) & (agregados.tipo_periodo == "anual")].periodo)
        desde = 2017 if c == "TV+" else 2016
        assert {f"FY{a}" for a in range(desde, 2026)} <= anios, c


def test_controles_externos_sep():
    """Los ingresos de TVN publicados por el SEP coinciden con alguna versión de la serie."""
    c = pd.read_csv(ROOT / "salidas" / "controles_externos.csv")
    sep = c[c.fuente == "SEP"]
    assert len(sep) > 0
    assert (sep.estado == "coincide").all(), sep[sep.estado != "coincide"]
