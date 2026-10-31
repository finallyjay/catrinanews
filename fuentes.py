"""News sources for the daily sheet.

Free RSS for now. A SerpApi Google News source can be added later with the
same shape: a function that returns a list of {"titular", "fuente", "url"}.
"""

import itertools
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 (hoja-volante; +https://github.com/finallyjay)"}

FEEDS = {
    "elpais": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada",
    "google": "https://news.google.com/rss/search?"
    + urllib.parse.urlencode({
        "q": "tecnológica OR startup OR app OR inteligencia artificial",
        "hl": "es", "gl": "ES", "ceid": "ES:es",
    }),
}


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def rss(nombre: str, limite: int = 30) -> list[dict]:
    """Headlines from one RSS feed. Titles are untrusted text: only used as prompt data."""
    root = ET.fromstring(_fetch(FEEDS[nombre]))
    out = []
    for item in root.findall(".//item")[:limite]:
        titulo = (item.findtext("title") or "").strip()
        fuente = nombre
        if nombre == "google" and " - " in titulo:
            # Google News appends " - Outlet" to every title.
            titulo, fuente = titulo.rsplit(" - ", 1)
        if titulo:
            out.append({"titular": titulo[:200], "fuente": fuente, "url": item.findtext("link") or ""})
    return out


def titulares(nombres: list[str], limite: int = 30) -> list[dict]:
    """Interleaved across sources, so the editor step doesn't just pick from the first feed."""
    listas = [rss(nombre, limite) for nombre in nombres]
    vistos, out = set(), []
    for fila in itertools.zip_longest(*listas):
        for t in filter(None, fila):
            clave = t["titular"].lower()
            if clave not in vistos:
                vistos.add(clave)
                out.append(t)
    return out
