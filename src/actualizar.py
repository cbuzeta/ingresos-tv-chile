"""Actualización trimestral en un solo paso.

    python src/actualizar.py            # busca EEFF nuevos en la CMF, los baja y rehace la base
    python src/actualizar.py --sin-red  # rehace la base con lo que ya está en data/ (sin consultar la CMF)

Se detiene en el primer paso que falle (p. ej. una línea nueva sin clasificar en el paso 5:
se aprueba en mapeo/lineas_mapeo.csv y se vuelve a correr).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASOS = [
    ["src/00_novedades.py", "--descargar"],
    ["src/00_externos.py"],
    ["src/01_inventario.py"],
    ["src/03_identificar.py"],
    ["src/04_extraer_nota.py", "--nuevos"],
    ["src/04b_mega_geografia.py"],
    ["src/05_mapear.py"],
    ["src/validar_semilla.py"],
    ["src/06_exportar.py"],
    ["-m", "pytest", "tests", "-q"],
]


def main():
    sin_red = "--sin-red" in sys.argv
    for paso in PASOS:
        if sin_red and paso[0] in ("src/00_novedades.py", "src/00_externos.py"):
            continue
        print(f"\n== {' '.join(paso)}", flush=True)
        r = subprocess.run([sys.executable, *paso], cwd=ROOT)
        # 00_novedades devuelve 10 cuando encontró EEFF nuevos: no es un error
        if r.returncode not in (0, 10 if paso[0] == "src/00_novedades.py" else 0):
            sys.exit(f"Falló: {' '.join(paso)} (código {r.returncode})")
    print("\nListo. Revisar cambios con `git status` y publicar con commit + push (Pages se reconstruye solo).")


if __name__ == "__main__":
    main()
