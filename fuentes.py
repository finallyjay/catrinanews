"""News sources for the daily sheet.

Each source returns a list of {"titular", "fuente", "url"}:
  elpais   El País Tecnología RSS (free, no key)
  google   Google News RSS search (free, no key)
  serpapi  SerpApi's Google News engine: structured results with the outlet name
           and real article URLs (needs SERPAPI_API_KEY)
"""

import itertools
import json
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0 (catrinanews; +https://catrinanews.tech)"}

CONSULTA = "tecnológica OR startup OR app OR inteligencia artificial"
# For SerpApi, ask for the companies themselves: satire needs a company or product to aim at,
# and a generic "inteligencia artificial" query returned op-eds and celebrities.
CONSULTA_EMPRESAS = (
    "Apple OR Google OR Meta OR Amazon OR Microsoft OR Tesla OR OpenAI OR Samsung "
    "OR TikTok OR Netflix OR Nvidia"
)

FEEDS = {
    "elpais": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada",
    "google": "https://news.google.com/rss/search?"
    + urllib.parse.urlencode({"q": CONSULTA, "hl": "es", "gl": "ES", "ceid": "ES:es"}),
}


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def _env_key(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    for path in (".env", "../.env"):
        if os.path.exists(path):
            for line in open(path):
                if line.startswith(f"{name}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


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


def serpapi(limite: int = 30, consulta: str = CONSULTA_EMPRESAS) -> list[dict]:
    """Today's headlines from SerpApi's Google News engine (Spain, Spanish, last day)."""
    key = _env_key("SERPAPI_API_KEY")
    if not key:
        raise SystemExit("SERPAPI_API_KEY not found (env, ./.env or ../.env)")
    params = {
        "engine": "google_news",
        "q": f"{consulta} when:1d",  # Google News operator: only the last 24 hours
        "gl": "es",
        "hl": "es",
        "api_key": key,
    }
    data = json.loads(_fetch("https://serpapi.com/search.json?" + urllib.parse.urlencode(params)))
    if "error" in data:
        raise SystemExit(f"SerpApi: {data['error']}")
    out = []
    for r in data.get("news_results", []):
        # Some results are clusters ("stories") with the articles inside.
        for art in [r] + r.get("stories", []):
            titulo = (art.get("title") or "").strip()
            if titulo:
                out.append({
                    "titular": titulo[:200],
                    "fuente": (art.get("source") or {}).get("name", "SerpApi"),
                    "url": art.get("link", ""),
                })
    return out[:limite]


def fuente(nombre: str, limite: int) -> list[dict]:
    return serpapi(limite) if nombre == "serpapi" else rss(nombre, limite)


def titulares(nombres: list[str], limite: int = 30) -> list[dict]:
    """Interleaved across sources, so the editor step doesn't just pick from the first feed."""
    listas = [fuente(nombre, limite) for nombre in nombres]
    vistos, out = set(), []
    for fila in itertools.zip_longest(*listas):
        for t in filter(None, fila):
            clave = t["titular"].lower()
            if clave not in vistos:
                vistos.add(clave)
                out.append(t)
    return out
