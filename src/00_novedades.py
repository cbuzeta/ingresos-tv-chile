"""Revisa si la CMF publicó EEFF nuevos de los seis canales y, con --descargar, los baja.

    python src/00_novedades.py              # solo informa (lo usa el aviso mensual de GitHub Actions)
    python src/00_novedades.py --descargar  # además descarga a data/{canal}/, con pausas

- Concesionarias (C13, La Red, Mega, CHV, TV+): página de cada canal en la CMF; los enlaces
  «Estados financieros … al <fecha>» se comparan con data/manifest.csv. El ZIP se toma desde la
  página del artículo (ruta .../626/w4-article-N.html; el enlace del ZIP lleva ?ts=).
- TVN: ficha de entidad de la CMF por trimestre; un trimestre está publicado cuando aparece el
  enlace «Estados financieros (PDF)», que se descarga en la misma sesión (el enlace lleva tokens).

Salida: revision/novedades_cmf.csv. Código de salida 10 si hay novedades (para automatizar).
"""
import csv
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.cmfchile.cl"
PAUSA = 2.0
CANALES = {  # canal: (property value en la CMF, carpeta en data/)
    "Canal 13": (46330, "Canal 13"), "La Red": (46331, "La Red"), "Mega": (46333, "Megamedia"),
    "Chilevisión": (46334, "Chilevisión"), "TV+": (46336, "TV Mas"),
}
MESES = {"marzo": "03", "junio": "06", "septiembre": "09", "diciembre": "12"}
TVN_URL = (BASE + "/institucional/mercados/entidad.php?mercado=V&rut=81689800&grupo=0&tipoentidad=RGEIN&vig=VI"
           "&row=AAAwy2ACTAAAByxAAA&mm={mm}&aa={aa}&tipo=I&orig=lista&control=svs&tipo_norma=IFRS&pestania=3")


def sesion():
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (investigacion academica; Universidad de los Andes, Chile)"
    return s


def fecha_de(texto):
    m = re.search(r"(\d{1,2}) de (marzo|junio|septiembre|diciembre) de (\d{4})", texto.lower())
    return f"{m.group(3)}-{MESES[m.group(2)]}-{int(m.group(1)):02d}" if m else ""


def concesionarias(s, descargar):
    conocidos = set()
    with open(ROOT / "data" / "manifest.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            conocidos.add((r["canal"], r["articulo"]))
    nuevos = []
    for canal, (pv, carpeta) in CANALES.items():
        t = s.get(f"{BASE}/portal/estadisticas/617/w3-propertyvalue-{pv}.html", timeout=60).text
        time.sleep(PAUSA)
        for m in re.finditer(r'<a[^>]+href="[^"]*w4-article-(\d+)\.html"[^>]*>(.*?)</a>', t, re.S):
            texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
            if not texto.lower().startswith("estados financieros") or (canal, m.group(1)) in conocidos:
                continue
            art = m.group(1)
            fila = {"canal": canal, "articulo": art, "fecha_cierre": fecha_de(texto), "titulo": texto,
                    "url": f"{BASE}/portal/estadisticas/626/w4-article-{art}.html", "archivo": ""}
            if descargar:
                pag = s.get(fila["url"], timeout=60).text
                time.sleep(PAUSA)
                z = re.search(r'href="([^"]*articles-%s_recurso_1\.(?:zip|pdf)[^"]*)"' % art, pag)
                if z:
                    url = urljoin(fila["url"], z.group(1))
                    ext = ".pdf" if ".pdf" in url.split("?")[0] else ".zip"
                    destino = ROOT / "data" / carpeta / f"articles-{art}_recurso_1{ext}"
                    destino.write_bytes(s.get(url, timeout=120).content)
                    fila["archivo"] = str(destino.relative_to(ROOT))
                    time.sleep(PAUSA)
            nuevos.append(fila)
            conocidos.add((canal, art))
    return nuevos


def tvn(s, descargar):
    with open(ROOT / "data" / "documentos.csv", encoding="utf-8") as fh:
        fechas = [r["fecha_cierre"] for r in csv.DictReader(fh) if r["canal"] == "TVN" and r["tipo_documento"] == "EEFF"
                  and r["fecha_cierre"]]
    ultima = max(fechas)
    a, m = int(ultima[:4]), int(ultima[5:7])
    nuevos = []
    hoy = date.today()
    while True:
        m += 3
        if m > 12:
            a, m = a + 1, 3
        if (a, m) > (hoy.year, hoy.month):
            break
        url = TVN_URL.format(mm=f"{m:02d}", aa=a)
        t = s.get(url, timeout=60).text
        time.sleep(PAUSA)
        link = re.search(r'href="([^"]*safec_ifrs_verarchivo\.php\?[^"]+)"[^>]*>\s*Estados financieros \(PDF\)', t)
        if not link:
            continue
        fin = {3: "31", 6: "30", 9: "30", 12: "31"}[m]
        fila = {"canal": "TVN", "articulo": "", "fecha_cierre": f"{a}-{m:02d}-{fin}",
                "titulo": f"Estados financieros TVN al {fin}-{m:02d}-{a}", "url": url, "archivo": ""}
        if descargar:
            href = link.group(1).replace("&amp;", "&")
            pdf_url = urljoin(url, href)  # el enlace es relativo ("../inc/...") y su token puede contener "/"
            destino = ROOT / "data" / "TVN" / f"Estados-Financieros-TVN-{a}-{m:02d}.pdf"
            destino.write_bytes(s.get(pdf_url, timeout=120).content)
            fila["archivo"] = str(destino.relative_to(ROOT))
            time.sleep(PAUSA)
        nuevos.append(fila)
    return nuevos


def main():
    descargar = "--descargar" in sys.argv
    s = sesion()
    nuevos = concesionarias(s, descargar) + tvn(s, descargar)
    (ROOT / "revision").mkdir(exist_ok=True)
    with open(ROOT / "revision" / "novedades_cmf.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["canal", "articulo", "fecha_cierre", "titulo", "url", "archivo"])
        w.writeheader()
        w.writerows(nuevos)
    if not nuevos:
        print("Sin EEFF nuevos en la CMF.")
        return 0
    print(f"{len(nuevos)} EEFF nuevos:")
    for n in nuevos:
        print(f"  {n['canal']:12} {n['fecha_cierre']}  {n['archivo'] or n['url']}")
    if not descargar:
        print("Para bajarlos: python src/00_novedades.py --descargar")
    return 10


if __name__ == "__main__":
    sys.exit(main())
