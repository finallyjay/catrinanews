"""Render a sheet (hoja_YYYY-MM-DD.json) as a Posada-style broadside in HTML.

Usage:
  python3 render.py                       # latest hoja_*.json → site/index.html
  python3 render.py hoja_2026-10-31.json
"""

import glob
import html
import json
import os
import sys

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

FUENTES = {"elpais": "El País"}

CALAVERA_SVG = """<svg class="skull" viewBox="0 0 120 130" aria-hidden="true">
  <path d="M60 6C30 6 10 28 10 56c0 16 7 28 18 35v14c0 5 4 9 9 9h46c5 0 9-4 9-9V91c11-7 18-19 18-35C110 28 90 6 60 6z" fill="#1b1611"/>
  <ellipse cx="40" cy="58" rx="13" ry="15" fill="#efe6cf"/>
  <ellipse cx="80" cy="58" rx="13" ry="15" fill="#efe6cf"/>
  <path d="M60 72l-8 14h16z" fill="#efe6cf"/>
  <g stroke="#efe6cf" stroke-width="3">
    <line x1="44" y1="100" x2="44" y2="114"/><line x1="54" y1="100" x2="54" y2="114"/>
    <line x1="66" y1="100" x2="66" y2="114"/><line x1="76" y1="100" x2="76" y2="114"/>
  </g>
  <g fill="#c8102e"><circle cx="40" cy="30" r="5"/><circle cx="60" cy="24" r="6"/><circle cx="80" cy="30" r="5"/></g>
</svg>"""

CSS = """
:root { --paper:#efe6cf; --ink:#1b1611; --red:#c8102e; --muted:#5b5146; }
* { box-sizing:border-box; }
body { margin:0; background:#2a241d; color:var(--ink);
  font-family:"IM Fell English", Georgia, "Times New Roman", serif; }
.hoja { max-width:880px; margin:32px auto; padding:36px 44px 28px;
  background: radial-gradient(circle at 20% 10%, #f6efdc 0, transparent 45%),
              radial-gradient(circle at 85% 90%, #e2d5b5 0, transparent 50%), var(--paper);
  border:3px double var(--ink); outline:10px solid var(--paper); box-shadow:0 0 0 13px var(--ink), 0 20px 60px #0008; }
.top { display:flex; justify-content:space-between; font-size:.85rem; letter-spacing:.08em;
  text-transform:uppercase; border-bottom:1px solid var(--ink); padding-bottom:6px; }
header { text-align:center; padding:18px 0 10px; border-bottom:4px double var(--ink); }
.skull { width:84px; height:auto; display:block; margin:0 auto 6px; }
h1 { font-family:"Rye", "IM Fell English", serif; font-weight:400; font-size:clamp(2rem, 6vw, 3.4rem);
  line-height:1.05; margin:0; letter-spacing:.02em; }
h1 em { color:var(--red); font-style:normal; }
.sub { font-style:italic; margin:8px auto 0; max-width:36em; }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:0; }
article { padding:22px 20px 18px; border-bottom:1px solid var(--ink); }
article:nth-child(odd) { border-right:1px solid var(--ink); }
article:last-child:nth-child(odd) { grid-column:1 / -1; border-right:none; text-align:center; }
.kicker { font-size:.8rem; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); margin:0 0 4px; }
.titular { font-weight:700; font-size:.98rem; margin:0 0 12px; }
.titular a { color:inherit; text-decoration:none; border-bottom:1px dotted var(--muted); }
.versos { font-size:1.25rem; line-height:1.45; margin:0 0 10px; }
.versos span { display:block; }
.versos span:nth-child(even) { padding-left:1.4em; }
.en { font-size:.86rem; font-style:italic; color:var(--muted); margin:0 0 10px; line-height:1.4; }
.en span { display:block; }
.check { font-family:ui-monospace, Menlo, monospace; font-size:.7rem; color:var(--muted); }
.check b { color:var(--red); font-weight:600; }
footer { text-align:center; font-size:.85rem; padding-top:14px; font-style:italic; }
footer strong { font-style:normal; }
@media (max-width:700px) {
  .hoja { margin:0; padding:22px 18px; outline:none; box-shadow:none; }
  .grid { grid-template-columns:1fr; }
  article:nth-child(odd) { border-right:none; }
}
"""


def fecha_larga(iso: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} de {MESES[m - 1]} de {y}"


def articulo(c: dict) -> str:
    e = html.escape
    fuente = FUENTES.get(c.get("fuente", ""), c.get("fuente", ""))
    titular = e(c["titular"])
    if c.get("url", "").startswith("https://"):
        titular = f'<a href="{e(c["url"])}" rel="noopener">{titular}</a>'
    versos = "".join(f"<span>{e(v)}</span>" for v in c["versos"])
    en = "".join(f"<span>{e(v)}</span>" for v in c.get("english", []))
    check = c.get("check", {})
    meter = "-".join(str(m) for m in check.get("meter", []))
    rima = "rima 2-4 <b>✓</b>" if check.get("ok") else "rima 2-4 ✗"
    if check.get("rhyme_1_3"):
        rima += " · 1-3 <b>✓</b>"
    return f"""<article>
  <p class="kicker">Según {e(fuente)}</p>
  <p class="titular">{titular}</p>
  <p class="versos" lang="es">{versos}</p>
  {f'<p class="en" lang="en">{en}</p>' if en else ''}
  <p class="check">{rima} · sílabas {e(meter)}</p>
</article>"""


def render(data: dict) -> str:
    arts = "\n".join(articulo(c) for c in data["calaveras"] if c.get("versos"))
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gran Calavera Tecnológica · {fecha_larga(data["fecha"])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=Rye&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<main class="hoja">
  <div class="top"><span>Hoja volante</span><span>{fecha_larga(data["fecha"])}</span><span>Día de Muertos</span></div>
  <header>
    {CALAVERA_SVG}
    <h1>¡Gran Calavera <em>Tecnológica</em>!</h1>
    <p class="sub">Donde la Flaca visita a las empresas que salieron hoy en las noticias,
    como hacía la prensa satírica del siglo XIX con los poderosos.</p>
  </header>
  <section class="grid">
{arts}
  </section>
  <footer>
    Escrita por <strong>{html.escape(data["modelo"])}</strong>, un modelo abierto que corre en un portátil.
    La rima y la métrica no las juzga el modelo: las comprueba el código, verso a verso.
  </footer>
</main>
</body>
</html>
"""


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("hoja_*.json"))[-1]
    with open(path) as f:
        data = json.load(f)
    os.makedirs("site", exist_ok=True)
    out = os.path.join("site", "index.html")
    with open(out, "w") as f:
        f.write(render(data))
    print(f"{path} → {out}")


if __name__ == "__main__":
    main()
