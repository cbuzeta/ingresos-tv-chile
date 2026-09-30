"""Utilidades comunes: texto de PDF (pdftotext) con caché y OCR (tesseract) para PDF escaneados."""
import hashlib
import re
import subprocess
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache_texto"
TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA = ROOT / "tools" / "tessdata"


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[ \t]+", " ", s)


def paginas(pdf):
    r = subprocess.run(["pdfinfo", str(pdf)], capture_output=True)
    m = re.search(rb"Pages:\s+(\d+)", r.stdout)
    return int(m.group(1)) if m else 0


def texto_pagina(pdf, page):
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-"],
                       capture_output=True)
    return r.stdout.decode("utf-8", "ignore")


def _key(pdf, page, kind):
    h = hashlib.sha1(str(Path(pdf).resolve()).encode()).hexdigest()[:16]
    return CACHE / f"{h}_{page:04d}.{kind}.txt"


def ocr_pagina(pdf, page, dpi=300, psm=6):
    """OCR de una página (español), con caché en data/cache_texto/."""
    out = _key(pdf, page, "ocr" if (dpi, psm) == (300, 6) else f"ocr{dpi}p{psm}")
    if out.exists():
        return out.read_text(encoding="utf-8")
    CACHE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "p"
        subprocess.run(["pdftoppm", "-r", str(dpi), "-gray", "-f", str(page), "-l", str(page), "-png",
                        "-singlefile", str(pdf), str(base)], capture_output=True)
        if not (base.parent / "p.png").exists():
            return ""
        r = subprocess.run([TESSERACT, str(base) + ".png", "stdout", "-l", "spa", "--psm", str(psm),
                            "--tessdata-dir", str(TESSDATA)], capture_output=True)
    t = r.stdout.decode("utf-8", "ignore")
    out.write_text(t, encoding="utf-8")
    return t


def pagina(pdf, page, ocr_si_vacio=True):
    """Texto de la página; si no hay capa de texto, OCR. Devuelve (texto, 'texto'|'ocr')."""
    t = texto_pagina(pdf, page)
    if len(t.strip()) < 30 and ocr_si_vacio:
        return ocr_pagina(pdf, page), "ocr"
    return t, "texto"
