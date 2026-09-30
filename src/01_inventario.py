"""Paso 1-2 (versión local): inventario de los archivos ya descargados en data/{canal}/.

Los ZIP y PDF fueron bajados a mano desde la CMF (concesionarias) y el sitio de TVN.
Este script no descarga nada: registra cada archivo con su hash en data/manifest.csv
y descomprime los PDF en data/raw/pdf/{canal}/{articulo}/, sin tocar los originales.
"""
import csv
import hashlib
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT_PDF = DATA / "raw" / "pdf"
CANALES = {  # carpeta -> nombre canónico
    "Canal 13": "Canal 13",
    "Megamedia": "Mega",
    "Chilevisión": "Chilevisión",
    "TVN": "TVN",
    "La Red": "La Red",
    "TV Mas": "TV+",
}


def sha256(path_or_bytes):
    h = hashlib.sha256()
    if isinstance(path_or_bytes, bytes):
        h.update(path_or_bytes)
    else:
        with open(path_or_bytes, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()


def main():
    manifest, pdfs = [], []
    for carpeta, canal in CANALES.items():
        src = DATA / carpeta
        if not src.is_dir():
            continue
        for f in sorted(src.iterdir()):
            if not f.is_file():
                continue
            m = re.search(r"articles-(\d+)_recurso", f.name)
            articulo = m.group(1) if m else ""
            manifest.append({
                "canal": canal, "carpeta": carpeta, "archivo": f.name, "articulo": articulo,
                "url_articulo": f"https://www.cmfchile.cl/portal/estadisticas/617/w4-article-{articulo}.html" if articulo else "",
                "bytes": f.stat().st_size, "sha256": sha256(f),
            })
            dest = OUT_PDF / canal / (articulo or f.stem)
            dest.mkdir(parents=True, exist_ok=True)
            if f.suffix.lower() == ".zip":
                with zipfile.ZipFile(f) as z:
                    seen = set()
                    for info in z.infolist():
                        if info.is_dir() or not info.filename.lower().endswith(".pdf"):
                            continue
                        data = z.read(info)
                        h = sha256(data)
                        if h in seen:  # los ZIP de la CMF traen PDF repetidos
                            continue
                        seen.add(h)
                        out = dest / Path(info.filename).name
                        if not out.exists():
                            out.write_bytes(data)
                        pdfs.append({"canal": canal, "articulo": articulo, "origen": f.name,
                                     "pdf": str(out.relative_to(ROOT)).replace("\\", "/"), "sha256": h})
            elif f.suffix.lower() == ".pdf":
                out = dest / f.name
                if not out.exists():
                    shutil.copy2(f, out)
                pdfs.append({"canal": canal, "articulo": articulo, "origen": f.name,
                             "pdf": str(out.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(f)})

    for name, rows in (("manifest.csv", manifest), ("pdfs.csv", pdfs)):
        with open(DATA / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(f"{len(manifest)} archivos en manifest, {len(pdfs)} PDF únicos")

    # Criterio de aceptación: artículos de la tabla 3.1 de CLAUDE.md
    esperados = {"Canal 13": "113709 111123 109182 98820 93013 68977 47350 28617 29080",
                 "Mega": "113710 111125 109207 98823 93019 68984 47352 28606 29085",
                 "Chilevisión": "113714 111126 109184 98825 93017 68983 47353 28710 29083"}
    presentes = {(r["canal"], r["articulo"]) for r in manifest}
    faltan = [(c, a) for c, s in esperados.items() for a in s.split() if (c, a) not in presentes]
    print("Artículos de control faltantes:", faltan or "ninguno")


if __name__ == "__main__":
    main()
