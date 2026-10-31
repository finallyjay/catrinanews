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
  <path d="M60 6C30 6 10 28 10 56c0 16 7 28 18 35v6h64v-6c11-7 18-19 18-35C110 28 90 6 60 6z" fill="#1b1611"/>
  <ellipse cx="40" cy="58" rx="13" ry="15" fill="#efe6cf"/>
  <ellipse cx="80" cy="58" rx="13" ry="15" fill="#efe6cf"/>
  <path d="M60 72l-8 14h16z" fill="#efe6cf"/>
  <g stroke="#efe6cf" stroke-width="3">
    <line x1="44" y1="89" x2="44" y2="97"/><line x1="54" y1="89" x2="54" y2="97"/>
    <line x1="66" y1="89" x2="66" y2="97"/><line x1="76" y1="89" x2="76" y2="97"/>
  </g>
  <g class="mandibula">
    <path d="M30 99h60v10c0 5-4 9-9 9H39c-5 0-9-4-9-9z" fill="#1b1611"/>
    <g stroke="#efe6cf" stroke-width="3">
      <line x1="44" y1="99" x2="44" y2="107"/><line x1="54" y1="99" x2="54" y2="107"/>
      <line x1="66" y1="99" x2="66" y2="107"/><line x1="76" y1="99" x2="76" y2="107"/>
    </g>
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
.lema { font-family:"Rye", "IM Fell English", serif; font-size:1.3rem; margin:6px 0 0; letter-spacing:.04em; }
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
audio { width:100%; height:32px; margin:0 0 8px; filter:sepia(.6); }
.check { font-family:ui-monospace, Menlo, monospace; font-size:.7rem; color:var(--muted); }
.check b { color:var(--red); font-weight:600; }
html[data-lang="en"] .i18n[lang="es"], html[data-lang="es"] .i18n[lang="en"] { display:none; }
.langs button { font:inherit; font-size:.75rem; letter-spacing:.08em; background:none; border:1px solid var(--ink);
  color:var(--ink); padding:1px 6px; cursor:pointer; }
html[data-lang="en"] .b-en, html[data-lang="es"] .b-es { background:var(--ink); color:var(--paper); }
html[data-lang="en"] .en { font-size:.95rem; color:var(--ink); }
.about { padding:18px 6px 4px; border-bottom:4px double var(--ink); }
.about h2 { font-family:"Rye", serif; font-weight:400; font-size:1.4rem; margin:0 0 8px; text-align:center; }
.about p { margin:0 0 10px; line-height:1.5; }
.escuchar { margin-top:12px; font-family:"Rye", serif; font-size:1rem; background:var(--ink); color:var(--paper);
  border:none; padding:8px 18px; cursor:pointer; letter-spacing:.04em; }
.escuchar:hover { background:var(--red); }
article { transition:background .4s; }
article.activa { background:#f7efd9; box-shadow:inset 4px 0 0 var(--red); }
.catrina-flotante { position:fixed; right:22px; bottom:22px; width:96px; padding:10px 10px 4px;
  background:var(--paper); border:3px double var(--ink); border-radius:50%; box-shadow:0 8px 30px #0007;
  opacity:0; transform:translateY(20px); transition:opacity .3s, transform .3s; pointer-events:none; }
.catrina-flotante .skull { width:100%; margin:0; }
body.recitando .catrina-flotante { opacity:1; transform:none; }
footer { text-align:center; font-size:.85rem; padding-top:14px; font-style:italic; }
footer strong { font-style:normal; }
@media (max-width:700px) {
  .hoja { margin:0; padding:22px 18px; outline:none; box-shadow:none; }
  .grid { grid-template-columns:1fr; }
  article:nth-child(odd) { border-right:none; }
}
"""


MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def fecha_larga(iso: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} de {MESES[m - 1]} de {y}"


def date_long(iso: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{MONTHS[m - 1]} {d}, {y}"


def t(es: str, en: str) -> str:
    """Both languages in the page; CSS shows the active one (works without JS: English)."""
    return f'<span class="i18n" lang="es">{es}</span><span class="i18n" lang="en">{en}</span>'


def articulo(c: dict) -> str:
    e = html.escape
    fuente = FUENTES.get(c.get("fuente", ""), c.get("fuente", ""))
    titular = e(c["titular"])
    if c.get("titular_en"):
        titular = t(titular, e(c["titular_en"]))
    if c.get("url", "").startswith("https://"):
        titular = f'<a href="{e(c["url"])}" rel="noopener">{titular}</a>'
    versos = "".join(f"<span>{e(v)}</span>" for v in c["versos"])
    en = "".join(f"<span>{e(v)}</span>" for v in c.get("english", []))
    check = c.get("check", {})
    meter = "-".join(str(m) for m in check.get("meter", []))
    rima = t("rima", "rhyme") + (" 2-4 <b>✓</b>" if check.get("ok") else " 2-4 ✗")
    if check.get("rhyme_1_3"):
        rima += " · 1-3 <b>✓</b>"
    return f"""<article>
  <p class="kicker">{t(f"Según {e(fuente)}", f"From {e(fuente)}")}</p>
  <p class="titular">{titular}</p>
  <p class="versos" lang="es">{versos}</p>
  {f'<p class="en" lang="en">{en}</p>' if en else ''}
  {f'<audio controls preload="none" src="{e(c["audio"])}"></audio>' if c.get("audio") else ''}
  <p class="check">{rima} · {t("sílabas", "syllables")} {e(meter)}</p>
</article>"""


ABOUT_EN_1 = (
    "A <em>calavera literaria</em> is a short satirical poem Mexicans write for Día de los Muertos, "
    "imagining Death coming to take someone away. In the 19th century the press used them to mock "
    "the powerful; José Guadalupe Posada's skeletons, the Catrina among them, were born on those pages."
)
ABOUT_ES_1 = (
    "Una <em>calavera literaria</em> es un poema satírico que en México se escribe por el Día de Muertos, "
    "imaginando que la Muerte viene a llevarse a alguien. En el siglo XIX la prensa las usaba para burlarse "
    "de los poderosos; las calaveras de José Guadalupe Posada, la Catrina entre ellas, nacieron en esas páginas."
)
ABOUT_EN_2 = (
    "Catrina News brings that back for tech: it reads today's headlines, skips anything about real people "
    "or tragedies, and writes a calavera for the companies and products in the news. "
    "<strong>Gemma 3</strong>, an open-weight model, writes the verses on a laptop through Ollama. "
    "Plain Python checks every rhyme and syllable count and tells the model exactly what to fix. "
    "ElevenLabs gives the Catrina her voice."
)
ABOUT_ES_2 = (
    "Catrina News recupera esa tradición para la tecnología: lee los titulares del día, descarta los que "
    "hablan de personas concretas o de tragedias, y escribe una calavera para las empresas y productos "
    "de la noticia. <strong>Gemma 3</strong>, un modelo abierto, escribe los versos en un portátil con Ollama. "
    "Python puro comprueba cada rima y cada sílaba y le dice al modelo qué corregir. "
    "ElevenLabs le pone la voz a la Catrina."
)
ABOUT_EN_3 = (
    "Rhymes don't survive translation, so the Spanish is the original and the English below each "
    "calavera is a line-by-line gloss."
)
ABOUT_ES_3 = (
    "La rima no sobrevive a la traducción: el español es el original, y el inglés de cada calavera "
    "es una traducción verso a verso para quien no lo habla."
)


def render(data: dict) -> str:
    arts = "\n".join(articulo(c) for c in data["calaveras"] if c.get("versos"))
    voiced = any(c.get("audio") for c in data["calaveras"])
    return f"""<!doctype html>
<html lang="en" data-lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Catrina News · {fecha_larga(data["fecha"])}</title>
<meta name="description" content="Calaveras literarias de las noticias tecnológicas del día, escritas por un modelo abierto en local y recitadas por la Catrina.">
<meta property="og:title" content="Catrina News · {fecha_larga(data["fecha"])}">
<meta property="og:description" content="Today's tech news as Día de los Muertos calaveras: written by a local open model, rhyme checked in code, read aloud by the Catrina.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=Rye&display=swap" rel="stylesheet">
<style>{CSS}</style>
<script>
  // Spanish for Spanish-speaking browsers, English otherwise; the choice is remembered.
  (function () {{
    var saved = localStorage.getItem("lang");
    var lang = saved || ((navigator.language || "").slice(0, 2) === "es" ? "es" : "en");
    document.documentElement.dataset.lang = lang;
    document.documentElement.lang = lang;
  }})();
  function setLang(lang) {{
    document.documentElement.dataset.lang = lang;
    document.documentElement.lang = lang;
    localStorage.setItem("lang", lang);
  }}
</script>
</head>
<body>
<main class="hoja">
  <div class="top">
    <span>{t("Hoja volante", "Broadside")}</span>
    <span>{t(fecha_larga(data["fecha"]), date_long(data["fecha"]))}</span>
    <span class="langs" role="group" aria-label="Language / Idioma">
      <button type="button" onclick="setLang('en')" class="b-en">EN</button>
      <button type="button" onclick="setLang('es')" class="b-es">ES</button>
    </span>
  </div>
  <header>
    {CALAVERA_SVG}
    <h1>Catrina <em>News</em></h1>
    <p class="lema">¡Gran Calavera Tecnológica!</p>
    {f'<button type="button" class="escuchar" onclick="escucharHoja()">▶ {t("Escuchar la hoja", "Listen to the broadside")}</button>' if voiced else ''}
    <p class="sub">{t(
        "Donde la Flaca visita a las empresas que salieron hoy en las noticias, "
        "como hacía la prensa satírica del siglo XIX con los poderosos.",
        "Where Death pays a visit to the tech companies in today's news, "
        "the way Mexico's 19th-century satirical press mocked the powerful.",
    )}</p>
  </header>
  <section class="grid">
{arts}
  </section>
  <section class="about">
    <h2>{t("¿Qué es esto?", "What is this?")}</h2>
    <p>{t(ABOUT_ES_1, ABOUT_EN_1)}</p>
    <p>{t(ABOUT_ES_2, ABOUT_EN_2)}</p>
    <p>{t(ABOUT_ES_3, ABOUT_EN_3)}</p>
  </section>
  <footer>
    {t(
        f'Escrita por <strong>{html.escape(data["modelo"])}</strong>, un modelo abierto que corre en un portátil. '
        + ("Recitada por la Catrina con la voz de ElevenLabs. " if voiced else "")
        + "La rima y la métrica no las juzga el modelo: las comprueba el código, verso a verso.",
        f'Written by <strong>{html.escape(data["modelo"])}</strong>, an open model running on a laptop. '
        + ("Read aloud by the Catrina, voiced with ElevenLabs. " if voiced else "")
        + "The model doesn't judge its own rhymes: code checks every line.",
    )}
  </footer>
</main>
<div class="catrina-flotante" aria-hidden="true">{CALAVERA_SVG}</div>
<script>
  // The Catrina's jaw follows the loudness of her voice (Web Audio API, no services).
  (function () {{
    var audios = Array.prototype.slice.call(document.querySelectorAll("audio"));
    var jaws = document.querySelectorAll(".mandibula");
    var ctx, analyser, data, raf, level = 0, playingAll = false;

    function hook(a) {{
      if (a._hooked) return;
      ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
      if (!analyser) {{
        analyser = ctx.createAnalyser();
        analyser.fftSize = 512;
        analyser.connect(ctx.destination);
        data = new Uint8Array(analyser.fftSize);
      }}
      ctx.createMediaElementSource(a).connect(analyser);
      a._hooked = true;
    }}
    function setJaw(px) {{
      for (var i = 0; i < jaws.length; i++) jaws[i].setAttribute("transform", "translate(0 " + px.toFixed(1) + ")");
    }}
    function tick() {{
      analyser.getByteTimeDomainData(data);
      var sum = 0;
      for (var i = 0; i < data.length; i++) {{ var v = (data[i] - 128) / 128; sum += v * v; }}
      var rms = Math.sqrt(sum / data.length);
      level = level * 0.55 + Math.min(1, rms * 5) * 0.45;  // smooth, so it talks instead of twitching
      setJaw(level * 11);
      raf = requestAnimationFrame(tick);
    }}
    function stop() {{
      cancelAnimationFrame(raf);
      level = 0;
      setJaw(0);
      document.body.classList.remove("recitando");
    }}
    audios.forEach(function (a, i) {{
      a.addEventListener("play", function () {{
        hook(a);
        ctx.resume();
        audios.forEach(function (o) {{ if (o !== a) o.pause(); }});
        document.querySelectorAll("article.activa").forEach(function (el) {{ el.classList.remove("activa"); }});
        var art = a.closest("article");
        art.classList.add("activa");
        if (playingAll) art.scrollIntoView({{ behavior: "smooth", block: "center" }});
        document.body.classList.add("recitando");
        cancelAnimationFrame(raf);
        tick();
      }});
      a.addEventListener("pause", stop);
      a.addEventListener("ended", function () {{
        stop();
        if (playingAll && audios[i + 1]) audios[i + 1].play();
        else playingAll = false;
      }});
    }});
    window.escucharHoja = function () {{
      playingAll = true;
      audios[0].currentTime = 0;
      audios[0].play();
    }};
  }})();
</script>
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
