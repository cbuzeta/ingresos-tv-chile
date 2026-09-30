"""Actualiza tests/referencia_extraccion.csv después de un cambio intencional en la extracción.
Revisar antes con `git diff tests/referencia_extraccion.csv` qué montos cambian y por qué."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
x = pd.read_csv(ROOT / "data" / "lineas_extraidas.csv")
cols = ["canal", "fecha_cierre", "documento", "tipo_periodo", "fin", "orden", "linea_original", "monto"]
x[cols].sort_values(cols[:6]).to_csv(ROOT / "tests" / "referencia_extraccion.csv", index=False, encoding="utf-8")
print(f"{len(x)} montos en la referencia")
